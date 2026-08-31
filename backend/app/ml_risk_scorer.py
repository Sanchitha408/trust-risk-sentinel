"""
Loads the trained Isolation Forest + scaler and turns a single
incoming transaction into a 0-100 ML risk score.
"""

import joblib
from datetime import datetime
from collections import defaultdict

MODEL_PATH = "data/risk_model.joblib"
SCALER_PATH = "data/risk_scaler.joblib"
FEATURES_PATH = "data/risk_model_features.joblib"


class MLRiskScorer:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        self.feature_names = joblib.load(FEATURES_PATH)
        self.agent_amounts: dict[str, list[float]] = defaultdict(list)
        self._score_min = -0.15
        self._score_max = 0.15

    def _features_for(self, agent_id: str, amount: float, timestamp: datetime, agent_verified: bool):
        past = self.agent_amounts[agent_id]
        avg = (sum(past) / len(past)) if past else amount
        amount_vs_avg = amount / avg if avg else 1.0
        is_late_night = 1 if timestamp.hour in (0, 1, 2, 3, 4, 5) else 0

        row = {
            "amount": amount,
            "is_late_night": is_late_night,
            "agent_verified": int(agent_verified),
            "amount_vs_avg": amount_vs_avg,
        }
        return [[row[name] for name in self.feature_names]]

    def score(self, agent_id: str, amount: float, timestamp: datetime, agent_verified: bool) -> float:
        X = self._features_for(agent_id, amount, timestamp, agent_verified)
        X_scaled = self.scaler.transform(X)
        raw = self.model.decision_function(X_scaled)[0]

        self.agent_amounts[agent_id].append(amount)

        risk = (self._score_max - raw) / (self._score_max - self._score_min) * 100
        return round(max(0.0, min(100.0, risk)), 1)
