"""
Trains an Isolation Forest on simulated transaction data and saves it
to disk, along with the fitted scaler. Run this once (or whenever you
regenerate the dataset) to produce data/risk_model.joblib.
"""

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["agent_verified"] = df["agent_verified"].astype(int)
    df["is_late_night"] = df["hour"].between(0, 5).astype(int)

    df = df.sort_values("timestamp")

    df["agent_avg_amount"] = (
        df.groupby("agent_id")["amount"]
        .transform(lambda s: s.shift().expanding().mean())
        .fillna(df["amount"])
    )
    df["amount_vs_avg"] = df["amount"] / df["agent_avg_amount"].replace(0, 1)

    return df[["amount", "is_late_night", "agent_verified", "amount_vs_avg"]]


def main():
    df = pd.read_csv("data/simulated_transactions.csv")
    X = build_features(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=300,
        contamination=0.1,
        random_state=42,
    )
    model.fit(X_scaled)

    joblib.dump(model, "data/risk_model.joblib")
    joblib.dump(scaler, "data/risk_scaler.joblib")
    joblib.dump(list(X.columns), "data/risk_model_features.joblib")
    print(f"Trained on {len(X)} transactions. Model + scaler saved to data/")

    scores = model.decision_function(X_scaled)
    risk = ((scores.max() - scores) / (scores.max() - scores.min()) * 100).round(1)
    df["ml_risk_score"] = risk
    print(df.groupby("label")["ml_risk_score"].mean().sort_values(ascending=False))


if __name__ == "__main__":
    main()
