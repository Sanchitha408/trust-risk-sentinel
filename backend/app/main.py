"""
Trust & Risk Sentinel — API entrypoint.

Blends the deterministic rule engine (primary, explainable, always
authoritative for hard violations) with the ML anomaly scorer
(secondary signal for statistically unusual behavior rules don't
explicitly check for).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from app.rule_engine import RuleEngine, Transaction, Decision
from app.razorpay_client import create_test_order
from app.ml_risk_scorer import MLRiskScorer

app = FastAPI(title="Trust & Risk Sentinel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RuleEngine()
ml_scorer = MLRiskScorer()

ML_ESCALATION_THRESHOLD = 65
ML_HOLD_THRESHOLD = 45


class TransactionRequest(BaseModel):
    agent_id: str
    merchant_id: str
    amount: float
    currency: str = "INR"
    agent_verified: bool = True


class ScreenResponse(BaseModel):
    decision: str
    reasons: list[str]
    rule_risk_score: int
    ml_risk_score: float
    combined_risk_score: float
    razorpay_order_id: str | None = None
    timestamp: str


@app.post("/screen", response_model=ScreenResponse)
def screen_transaction(req: TransactionRequest):
    txn = Transaction(
        agent_id=req.agent_id,
        merchant_id=req.merchant_id,
        amount=req.amount,
        currency=req.currency,
        agent_verified=req.agent_verified,
    )

    rule_result = engine.evaluate(txn)
    ml_score = ml_scorer.score(
        agent_id=req.agent_id,
        amount=req.amount,
        timestamp=txn.timestamp,
        agent_verified=req.agent_verified,
    )

    decision = rule_result.decision
    reasons = [r for r in rule_result.reasons if not r.startswith("No rule violations")]
    combined = round((rule_result.rule_risk_score * 0.7) + (ml_score * 0.3), 1)

    if decision == Decision.APPROVE and ml_score >= ML_HOLD_THRESHOLD:
        decision = Decision.HOLD
        reasons.append(f"ML anomaly score ({ml_score}) above threshold for unusual behavior")
    elif decision == Decision.HOLD and ml_score >= ML_ESCALATION_THRESHOLD:
        decision = Decision.ESCALATE
        reasons.append(f"ML anomaly score ({ml_score}) compounds existing rule violation")

    razorpay_order_id = None
    if decision == Decision.APPROVE:
        order = create_test_order(
            amount_inr=req.amount,
            receipt_id=f"{req.agent_id}-{txn.timestamp.timestamp()}",
        )
        razorpay_order_id = order["id"]

    return ScreenResponse(
        decision=decision.value,
        reasons=reasons,
        rule_risk_score=rule_result.rule_risk_score,
        ml_risk_score=ml_score,
        combined_risk_score=combined,
        razorpay_order_id=razorpay_order_id,
        timestamp=txn.timestamp.isoformat(),
    )


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
