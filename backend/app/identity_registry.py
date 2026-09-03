"""
Registers merchant/agent identities tied to an authenticated Google account.
Each identity gets a generated ID (e.g. merchant_flipkart_a1b2) that can be
used as agent_id/merchant_id when screening transactions.
"""

import os
import re
import secrets
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()


class RegisteredIdentity(Base):
    __tablename__ = "registered_identities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    google_email = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # "merchant" or "agent"
    display_name = Column(String, nullable=False)
    identity_id = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine) if engine else None


def init_identity_table():
    if engine is None:
        raise RuntimeError("DATABASE_URL not set in .env")
    Base.metadata.create_all(engine)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "identity"


def register_identity(google_email: str, role: str, display_name: str) -> dict:
    if role not in ("merchant", "agent"):
        raise ValueError("role must be 'merchant' or 'agent'")

    session = SessionLocal()
    try:
        slug = _slugify(display_name)
        suffix = secrets.token_hex(2)
        identity_id = f"{role}_{slug}_{suffix}"

        entry = RegisteredIdentity(
            google_email=google_email,
            role=role,
            display_name=display_name,
            identity_id=identity_id,
        )
        session.add(entry)
        session.commit()
        return {
            "id": entry.id,
            "google_email": entry.google_email,
            "role": entry.role,
            "display_name": entry.display_name,
            "identity_id": entry.identity_id,
            "created_at": entry.created_at.isoformat(),
        }
    finally:
        session.close()


def list_identities(google_email: str) -> list:
    session = SessionLocal()
    try:
        rows = (
            session.query(RegisteredIdentity)
            .filter(RegisteredIdentity.google_email == google_email)
            .order_by(RegisteredIdentity.created_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "google_email": r.google_email,
                "role": r.role,
                "display_name": r.display_name,
                "identity_id": r.identity_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()
