"""
Trust & Risk Sentinel — API entrypoint.

Pipeline per transaction:
1. Rule engine evaluates (authoritative for hard violations)
2. ML scorer adds an anomaly signal rules alone would miss
3. Explainer turns the combined signal into a plain-language reason
4. Audit log writes an immutable record of the full decision
5. If approved, a real Razorpay test-mode order is created
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import joblib

from app.rule_engine import RuleEngine, Transaction, Decision
from app.razorpay_client import create_test_order
from app.ml_risk_scorer import MLRiskScorer
from app.explainer import Explainer
from app.audit_log import log_decision, get_recent_logs
from app.identity_registry import register_identity, list_identities

app = FastAPI(title="Trust & Risk Sentinel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RuleEngine()
ml_scorer = MLRiskScorer()

background_X = joblib.load("data/risk_background.joblib")
explainer = Explainer(
    model=ml_scorer.model,
    feature_names=ml_scorer.feature_names,
    background_X_scaled=background_X,
)

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
    explanation: str
    rule_risk_score: int
    ml_risk_score: float
    combined_risk_score: float
    razorpay_order_id: str | None = None
    audit_log_id: int
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
    ml_score, X_raw, X_scaled = ml_scorer.score_with_features(
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

    contributions = explainer.explain(X_raw[0], X_scaled)
    explanation = explainer.to_plain_language(decision.value, reasons, contributions, ml_score)

    razorpay_order_id = None
    if decision == Decision.APPROVE:
        order = create_test_order(
            amount_inr=req.amount,
            receipt_id=f"{req.agent_id}-{txn.timestamp.timestamp()}",
        )
        razorpay_order_id = order["id"]

    audit_id = log_decision(
        agent_id=req.agent_id,
        merchant_id=req.merchant_id,
        amount=req.amount,
        decision=decision.value,
        rule_risk_score=rule_result.rule_risk_score,
        ml_risk_score=float(ml_score),
        combined_risk_score=float(combined),
        explanation=explanation,
        razorpay_order_id=razorpay_order_id,
    )

    return ScreenResponse(
        decision=decision.value,
        reasons=reasons,
        explanation=explanation,
        rule_risk_score=rule_result.rule_risk_score,
        ml_risk_score=ml_score,
        combined_risk_score=combined,
        razorpay_order_id=razorpay_order_id,
        audit_log_id=audit_id,
        timestamp=txn.timestamp.isoformat(),
    )


@app.get("/audit-log")
def audit_log(limit: int = 50):
    return get_recent_logs(limit)
class RegisterIdentityRequest(BaseModel):
    google_email: str
    role: str
    display_name: str


@app.post("/register-identity")
def register_identity_endpoint(req: RegisterIdentityRequest):
    return register_identity(req.google_email, req.role, req.display_name)


@app.get("/identities")
def get_identities(email: str):
    return list_identities(email)

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
