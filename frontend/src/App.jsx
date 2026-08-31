import { useState, useEffect, useCallback } from "react";
import { screenTransaction, getAuditLog } from "./api";
import "./App.css";

const DECISION_COLORS = {
  approve: "#1a9c4a",
  hold: "#d99a1b",
  escalate: "#d43b3b",
};

function riskColor(score) {
  if (score >= 60) return "#d43b3b";
  if (score >= 30) return "#d99a1b";
  return "#1a9c4a";
}

export default function App() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    agent_id: "agent_demo",
    merchant_id: "merchant_abc",
    amount: 500,
    agent_verified: true,
  });

  const refreshLogs = useCallback(async () => {
    try {
      const data = await getAuditLog(50);
      setLogs(data);
      setError(null);
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    }
  }, []);

  useEffect(() => {
    refreshLogs();
    const interval = setInterval(refreshLogs, 4000);
    return () => clearInterval(interval);
  }, [refreshLogs]);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await screenTransaction({
        ...form,
        amount: Number(form.amount),
        currency: "INR",
      });
      await refreshLogs();
    } catch (err) {
      setError("Failed to screen transaction. Check the backend terminal for details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Trust &amp; Risk Sentinel</h1>
        <p className="subtitle">Live agent-to-agent transaction screening</p>
      </header>

      <section className="panel">
        <h2>Fire a test transaction</h2>
        <form className="txn-form" onSubmit={handleSubmit}>
          <label>
            Agent ID
            <input
              value={form.agent_id}
              onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
            />
          </label>
          <label>
            Merchant ID
            <input
              value={form.merchant_id}
              onChange={(e) => setForm({ ...form, merchant_id: e.target.value })}
            />
          </label>
          <label>
            Amount (INR)
            <input
              type="number"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.agent_verified}
              onChange={(e) => setForm({ ...form, agent_verified: e.target.checked })}
            />
            Agent verified
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Screening..." : "Screen transaction"}
          </button>
        </form>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <h2>Live audit feed</h2>
        <table className="audit-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Agent</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Decision</th>
              <th>Rule</th>
              <th>ML</th>
              <th>Combined</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleTimeString()}</td>
                <td>{log.agent_id}</td>
                <td>{log.merchant_id}</td>
                <td>₹{log.amount.toLocaleString()}</td>
                <td>
                  <span
                    className="decision-badge"
                    style={{ backgroundColor: DECISION_COLORS[log.decision] || "#888" }}
                  >
                    {log.decision}
                  </span>
                </td>
                <td style={{ color: riskColor(log.rule_risk_score) }}>
                  {log.rule_risk_score}
                </td>
                <td style={{ color: riskColor(log.ml_risk_score) }}>
                  {log.ml_risk_score}
                </td>
                <td style={{ color: riskColor(log.combined_risk_score) }}>
                  {log.combined_risk_score}
                </td>
                <td className="explanation-cell">{log.explanation}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan="9" className="empty-row">
                  No transactions yet — fire one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
