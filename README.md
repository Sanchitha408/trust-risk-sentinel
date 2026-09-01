# Trust & Risk Sentinel

**A real-time trust and risk-scoring layer for AI agent-to-agent commerce**, built for the Razorpay Buildathon — Open Innovation Track.

As AI agents begin making purchases on behalf of users, merchants have no standard way to answer a simple question: *"should this agent-initiated transaction be trusted?"* Trust & Risk Sentinel sits between an AI buyer-agent and a merchant's Razorpay checkout, screening every transaction in real time — approving, holding, or escalating it, with a plain-language reason and an immutable audit trail for every decision.

## Live Demo

[Add your deployed link here once live]

## The Problem

Agent-to-agent commerce (NPCI's UAP, ACP, AP2, x402, and similar protocols) is enabling AI agents to transact on a user's behalf — but there's no mature infrastructure to verify that an agent-initiated payment is legitimate, explainable, or auditable before money moves. Regulators, merchants, and platforms all need visibility and a paper trail before they'll trust AI agents near real transactions.

## What It Does

Every transaction that comes through the Sentinel is evaluated by three layers before a decision is made:

1. **Rule Engine** — deterministic checks for velocity limits, single-transaction ceilings, and agent verification status. Catches hard violations instantly, with zero ambiguity.
2. **ML Anomaly Detection** — an Isolation Forest model trained on transaction patterns flags statistically unusual behavior that fixed rules would miss (spending spikes, drift from an agent's own baseline).
3. **Explainable Decisions** — SHAP values identify which features drove the ML risk score; an LLM (via Groq) turns that into a clear, plain-language explanation for the merchant dashboard.

Every decision — approved, held, or escalated — is written to an immutable Postgres audit log with the full reasoning, risk scores, and (for approved transactions) a real Razorpay test-mode order ID.

## Architecture

[Agent/Buyer Simulator] → [Razorpay Test-Mode API]
↓
[Trust & Risk Sentinel — FastAPI]
├─ Rule Engine (velocity, amount thresholds, agent-identity checks)
├─ ML Risk Model (Isolation Forest anomaly scoring)
├─ Explainability Layer (SHAP → Groq plain-language explanation)
├─ Decision Gate (approve / hold / escalate)
└─ Audit Log (Postgres, immutable, timestamped)
↓
[React Dashboard — live feed, risk scores, explanations, audit trail]

## Tech Stack

- **Backend**: FastAPI, Python, scikit-learn (Isolation Forest), SHAP, SQLAlchemy
- **Frontend**: React + Vite
- **Database**: Postgres (Supabase)
- **Payments**: Razorpay (test mode)
- **LLM**: Groq (`openai/gpt-oss-20b`) for plain-language explanations
- **Auth**: Google Sign-In (OAuth)

## Project Structure 
trust-risk-sentinel/
├── backend/
│ ├── app/
│ │ ├── main.py # API entrypoint, orchestrates the full pipeline
│ │ ├── rule_engine.py # Deterministic rule checks
│ │ ├── ml_risk_scorer.py # Isolation Forest anomaly scoring
│ │ ├── explainer.py # SHAP + Groq explainability
│ │ ├── audit_log.py # Postgres audit trail
│ │ ├── razorpay_client.py # Razorpay test-mode order creation
│ │ ├── train_risk_model.py # Trains the Isolation Forest on simulated data
│ │ └── simulate_data.py # Generates synthetic transaction data
│ └── data/ # Trained model artifacts + simulated dataset
└── frontend/
└── src/
├── App.jsx # Dashboard UI: hero, live demo form, audit feed
└── api.js # API client

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js (via nvm recommended)
- A Razorpay account (test mode)
- A free Groq API key ([console.groq.com](https://console.groq.com))
- A free Supabase Postgres database ([supabase.com](https://supabase.com))
- A Google Cloud OAuth Client ID (for login)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`: 
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
GROQ_API_KEY=your_groq_key
DATABASE_URL=your_supabase_postgres_connection_string

Train the risk model and initialize the database:
```bash
python app/simulate_data.py
python app/train_risk_model.py
python -m app.init_db
```

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:
VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id

Run the dashboard:
```bash
npm run dev
```

Open `http://localhost:5173`.

## API

**`POST /screen`** — screens a transaction
```json
{
  "agent_id": "agent_grocery_bot_01",
  "merchant_id": "merchant_flipkart_test",
  "amount": 46000,
  "currency": "INR",
  "agent_verified": true
}
```
Returns a decision (`approve` / `hold` / `escalate`), risk scores, a plain-language explanation, and — if approved — a real Razorpay test-mode order ID.

**`GET /audit-log`** — returns the most recent screened transactions from the immutable audit log.

## What's Next

- Multi-tenant support so any merchant can plug in with their own config and audit log
- Per-merchant configurable rule thresholds
- Public deployment with authenticated API access for merchants

## Built For

Razorpay Buildathon 2026 — Open Innovation Track
