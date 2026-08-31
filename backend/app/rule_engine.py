"""
Rule engine for the Trust & Risk Sentinel.

Deterministic, explainable checks that run BEFORE any ML scoring.
Every rule that fires gets logged as a plain-language reason — this
is what makes the decision auditable and defensible on its own,
even with the ML layer switched off.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum


class Decision(str, Enum):
    APPROVE = "approve"
    HOLD = "hold"
    ESCALATE = "escalate"


@dataclass
class Transaction:
    agent_id: str
    merchant_id: str
    amount: float          # in INR
    currency: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_verified: bool = True


@dataclass
class RuleResult:
    decision: Decision
    reasons: list[str]
    rule_risk_score: int   # 0-100, contributed by rules alone


class RuleEngine:
    def __init__(
        self,
        velocity_window_minutes: int = 5,
        velocity_limit: int = 5,
        single_txn_ceiling: float = 50000.0,
        spike_multiplier: float = 5.0,
    ):
        self.velocity_window = timedelta(minutes=velocity_window_minutes)
        self.velocity_limit = velocity_limit
        self.single_txn_ceiling = single_txn_ceiling
        self.spike_multiplier = spike_multiplier
        self.history: dict[str, list[Transaction]] = defaultdict(list)

    def _recent_transactions(self, agent_id: str, now: datetime) -> list[Transaction]:
        cutoff = now - self.velocity_window
        return [t for t in self.history[agent_id] if t.timestamp >= cutoff]

    def _average_amount(self, agent_id: str) -> float | None:
        past = self.history[agent_id]
        if not past:
            return None
        return sum(t.amount for t in past) / len(past)

    def evaluate(self, txn: Transaction) -> RuleResult:
        reasons: list[str] = []
        risk = 0

        if not txn.agent_verified:
            reasons.append("Agent identity is unverified")
            risk += 40

        recent = self._recent_transactions(txn.agent_id, txn.timestamp)
        if len(recent) >= self.velocity_limit:
            reasons.append(
                f"Velocity limit exceeded: {len(recent)} transactions "
                f"in the last {int(self.velocity_window.total_seconds() // 60)} minutes"
            )
            risk += 35

        if txn.amount > self.single_txn_ceiling:
            reasons.append(
                f"Transaction amount ₹{txn.amount:,.0f} exceeds the "
                f"single-transaction ceiling of ₹{self.single_txn_ceiling:,.0f}"
            )
            risk += 30

        avg = self._average_amount(txn.agent_id)
        if avg and txn.amount > avg * self.spike_multiplier:
            reasons.append(
                f"Amount is {txn.amount / avg:.1f}x this agent's average "
                f"(₹{avg:,.0f}), well above the {self.spike_multiplier}x threshold"
            )
            risk += 25

        self.history[txn.agent_id].append(txn)
        risk = min(risk, 100)

        if risk >= 70:
            decision = Decision.ESCALATE
        elif risk >= 30:
            decision = Decision.HOLD
        else:
            decision = Decision.APPROVE
            if not reasons:
                reasons.append("No rule violations; transaction within normal bounds")

        return RuleResult(decision=decision, reasons=reasons, rule_risk_score=risk)
