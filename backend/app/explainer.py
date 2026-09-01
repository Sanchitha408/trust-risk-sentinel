"""
Explains WHY a transaction got the ML risk score it did, using SHAP
values against the trained Isolation Forest, then turns that into a
plain-language sentence via Groq.
"""

import os
import shap
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


class Explainer:
    def __init__(self, model, feature_names, background_X_scaled):
        self.model = model
        self.feature_names = feature_names
        self.shap_explainer = shap.TreeExplainer(
            model, data=background_X_scaled, model_output="raw"
        )

    def explain(self, X_raw_row: list, X_scaled) -> list:
        shap_values = self.shap_explainer.shap_values(X_scaled)
        row = shap_values[0] if len(shap_values.shape) > 1 else shap_values
        contributions = list(zip(self.feature_names, row, X_raw_row))
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        return contributions

    def to_plain_language(self, decision, rule_reasons, contributions, ml_risk_score) -> str:
        top_features = contributions[:2]
        feature_summary = ", ".join(
            f"{name} ({'high' if val > 0 else 'low'} impact, value={raw:.1f})"
            for name, val, raw in top_features
        )

        if not _groq_client:
            return self._fallback(decision, rule_reasons, top_features, ml_risk_score)

        if decision == "approve":
            action_phrase = "was approved"
            explain_phrase = "why it was approved with low risk"
        elif decision == "hold":
            action_phrase = "was held for manual review"
            explain_phrase = "why it was held"
        else:
            action_phrase = "was escalated"
            explain_phrase = "why it was escalated"

        prompt = (
            f"A fraud-risk system evaluated a transaction and it {action_phrase}, "
            f"with an ML anomaly score of {ml_risk_score}/100. "
            f"Rule-based flags: {rule_reasons or 'none'}. "
            f"Top contributing factors from the ML model: {feature_summary}. "
            f"Write ONE short, plain-language sentence (under 25 words) explaining "
            f"{explain_phrase}, suitable for a merchant dashboard. "
            "Do not say the transaction was 'flagged' unless the decision is hold or escalate. "
            "All amounts are in Indian Rupees — always use the ₹ symbol, never $. "
            "No preamble, just the sentence."
        )
        try:
            response = _groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
                reasoning_effort="low",
            )
            content = response.choices[0].message.content.strip()
            if not content:
                return self._fallback(decision, rule_reasons, top_features, ml_risk_score)
            return content
        except Exception:
            return self._fallback(decision, rule_reasons, top_features, ml_risk_score)
    def _fallback(self, decision, rule_reasons, top_features, ml_risk_score) -> str:
        if rule_reasons:
            return f"{decision.capitalize()}: {rule_reasons[0]}"
        if top_features:
            name, val, raw = top_features[0]
            return (
                f"{decision.capitalize()}: unusual {name} (value={raw:.1f}) "
                f"contributed most to the {ml_risk_score}/100 anomaly score."
            )
        return f"{decision.capitalize()}: anomaly score {ml_risk_score}/100."
