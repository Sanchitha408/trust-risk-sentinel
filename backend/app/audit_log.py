"""
Immutable audit trail. Every transaction that passes through the
Sentinel gets one write-once row here — no updates, no deletes.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    decision = Column(String, nullable=False)
    rule_risk_score = Column(Integer, nullable=False)
    ml_risk_score = Column(Float, nullable=False)
    combined_risk_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine) if engine else None


def init_db():
    if engine is None:
        raise RuntimeError("DATABASE_URL not set in .env")
    Base.metadata.create_all(engine)


def log_decision(
    agent_id: str,
    merchant_id: str,
    amount: float,
    decision: str,
    rule_risk_score: int,
    ml_risk_score: float,
    combined_risk_score: float,
    explanation: str,
    razorpay_order_id: str | None,
) -> int:
    if SessionLocal is None:
        return -1

    session = SessionLocal()
    try:
        entry = AuditLogEntry(
            agent_id=agent_id,
            merchant_id=merchant_id,
            amount=amount,
            decision=decision,
            rule_risk_score=rule_risk_score,
            ml_risk_score=ml_risk_score,
            combined_risk_score=combined_risk_score,
            explanation=explanation,
            razorpay_order_id=razorpay_order_id,
        )
        session.add(entry)
        session.commit()
        return entry.id
    finally:
        session.close()


def get_recent_logs(limit: int = 50) -> list[dict]:
    if SessionLocal is None:
        return []
    session = SessionLocal()
    try:
        rows = (
            session.query(AuditLogEntry)
            .order_by(AuditLogEntry.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "merchant_id": r.merchant_id,
                "amount": r.amount,
                "decision": r.decision,
                "rule_risk_score": r.rule_risk_score,
                "ml_risk_score": r.ml_risk_score,
                "combined_risk_score": r.combined_risk_score,
                "explanation": r.explanation,
                "razorpay_order_id": r.razorpay_order_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()
