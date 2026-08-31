"""
Trust & Risk Sentinel — API entrypoint.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from app.rule_engine import RuleEngine, Transaction, Decision
from app.razorpay_client import create_test_order

app = FastAPI(title="Trust & Risk Sentinel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RuleEngine()


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

    result = engine.evaluate(txn)

    razorpay_order_id = None
    if result.decision == Decision.APPROVE:
        order = create_test_order(
            amount_inr=req.amount,
            receipt_id=f"{req.agent_id}-{txn.timestamp.timestamp()}",
        )
        razorpay_order_id = order["id"]

    return ScreenResponse(
        decision=result.decision.value,
        reasons=result.reasons,
        rule_risk_score=result.rule_risk_score,
        razorpay_order_id=razorpay_order_id,
        timestamp=txn.timestamp.isoformat(),
    )


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
