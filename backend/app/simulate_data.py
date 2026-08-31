"""
Generates synthetic agent-transaction data: mostly normal behavior,
with a smaller injected set of anomalies (spikes, odd hours, unverified
agents). Used to train the Isolation Forest and to demo the Sentinel.
"""

import random
import csv
from datetime import datetime, timedelta

random.seed(42)

AGENTS = [f"agent_{i:03d}" for i in range(1, 21)]
MERCHANTS = [f"merchant_{c}" for c in "abcdefghij"]


def normal_transaction(base_time: datetime) -> dict:
    agent = random.choice(AGENTS)
    hour_offset = random.randint(0, 60 * 24 * 7)  # spread over a week
    ts = base_time + timedelta(minutes=hour_offset)
    return {
        "agent_id": agent,
        "merchant_id": random.choice(MERCHANTS),
        "amount": round(random.uniform(50, 3000), 2),
        "timestamp": ts.isoformat(),
        "agent_verified": True,
        "label": "normal",
    }


def anomalous_transaction(base_time: datetime) -> dict:
    agent = random.choice(AGENTS)
    hour_offset = random.randint(0, 60 * 24 * 7)
    ts = base_time + timedelta(minutes=hour_offset)
    kind = random.choice(["amount_spike", "unverified", "odd_hour"])

    amount = round(random.uniform(50, 3000), 2)
    verified = True

    if kind == "amount_spike":
        amount = round(random.uniform(40000, 90000), 2)
    elif kind == "unverified":
        verified = False
    elif kind == "odd_hour":
        ts = ts.replace(hour=random.choice([1, 2, 3, 4]))
        amount = round(random.uniform(10000, 30000), 2)

    return {
        "agent_id": agent,
        "merchant_id": random.choice(MERCHANTS),
        "amount": amount,
        "timestamp": ts.isoformat(),
        "agent_verified": verified,
        "label": kind,
    }


def generate_dataset(n_normal: int = 800, n_anomalous: int = 100) -> list[dict]:
    base_time = datetime(2026, 8, 1)
    rows = [normal_transaction(base_time) for _ in range(n_normal)]
    rows += [anomalous_transaction(base_time) for _ in range(n_anomalous)]
    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    rows = generate_dataset()
    out_path = "data/simulated_transactions.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} transactions to {out_path}")
