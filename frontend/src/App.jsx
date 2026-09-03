import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { screenTransaction, getAuditLog, registerIdentity, getIdentities } from "./api";
import "./App.css";

const DECISION_COLORS = {
  approve: "#22c55e",
  hold: "#f5a524",
  escalate: "#f13c4f",
};

const SECTIONS = [
  { id: "hero", label: "Home" },
  { id: "how-it-works", label: "How it works" },
  { id: "demo", label: "Live demo" },
];

function riskColor(score) {
  if (score >= 60) return "#f13c4f";
  if (score >= 30) return "#f5a524";
  return "#22c55e";
}

function useReveal() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return [ref, visible];
}

function Reveal({ children, className = "", delay = 0 }) {
  const [ref, visible] = useReveal();
  return (
    <div
      ref={ref}
      className={`reveal ${visible ? "reveal-visible" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

function decodeJwt(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

function Bubbles() {
  const bubbles = [
    { size: 60, left: "6%", duration: 18, delay: 0, color: "rgba(99, 102, 241, 0.18)" },
    { size: 30, left: "15%", duration: 14, delay: 2, color: "rgba(125, 211, 252, 0.18)" },
    { size: 90, left: "25%", duration: 24, delay: 4, color: "rgba(167, 139, 250, 0.14)" },
    { size: 40, left: "38%", duration: 16, delay: 1, color: "rgba(244, 114, 182, 0.14)" },
    { size: 70, left: "50%", duration: 20, delay: 6, color: "rgba(99, 102, 241, 0.16)" },
    { size: 25, left: "60%", duration: 12, delay: 3, color: "rgba(125, 211, 252, 0.2)" },
    { size: 55, left: "70%", duration: 22, delay: 5, color: "rgba(167, 139, 250, 0.16)" },
    { size: 35, left: "80%", duration: 15, delay: 2.5, color: "rgba(244, 114, 182, 0.16)" },
    { size: 80, left: "90%", duration: 26, delay: 7, color: "rgba(99, 102, 241, 0.14)" },
    { size: 45, left: "94%", duration: 17, delay: 1.5, color: "rgba(125, 211, 252, 0.16)" },
    { size: 20, left: "3%", duration: 11, delay: 8, color: "rgba(244, 114, 182, 0.2)" },
    { size: 65, left: "45%", duration: 19, delay: 9, color: "rgba(167, 139, 250, 0.15)" },
  ];

  return (
    <div className="bubbles-layer" aria-hidden="true">
      {bubbles.map((b, i) => (
        <span
          key={i}
          className="bubble"
          style={{
            width: b.size,
            height: b.size,
            left: b.left,
            background: b.color,
            animationDuration: `${b.duration}s`,
            animationDelay: `${b.delay}s`,
          }}
        />
      ))}
    </div>
  );
}

function LiveStatsPanel({ logs, active }) {
  const stats = useMemo(() => {
    const counts = { approve: 0, hold: 0, escalate: 0 };
    logs.forEach((l) => {
      if (counts[l.decision] !== undefined) counts[l.decision]++;
    });
    const avgRisk = logs.length
      ? (logs.reduce((sum, l) => sum + (l.combined_risk_score || 0), 0) / logs.length).toFixed(1)
      : "0.0";
    return { ...counts, total: logs.length, avgRisk };
  }, [logs]);

  return (
    <div className="live-stats-panel">
      <div className="live-stats-header">
        <span className="pulse-dot" />
        Live Sentinel Stats
      </div>
      <div className="stat-row">
        <span className="stat-label">Screened</span>
        <span className="stat-value">{stats.total}</span>
      </div>
      <div className="stat-row">
        <span className="stat-label" style={{ color: DECISION_COLORS.approve }}>
          Approved
        </span>
        <span className="stat-value">{stats.approve}</span>
      </div>
      <div className="stat-row">
        <span className="stat-label" style={{ color: DECISION_COLORS.hold }}>
          Held
        </span>
        <span className="stat-value">{stats.hold}</span>
      </div>
      <div className="stat-row">
        <span className="stat-label" style={{ color: DECISION_COLORS.escalate }}>
          Escalated
        </span>
        <span className="stat-value">{stats.escalate}</span>
      </div>
      <div className="stat-divider" />
      <div className="stat-row">
        <span className="stat-label">Avg. risk</span>
        <span className="stat-value">{stats.avgRisk}</span>
      </div>
      <div className="stat-divider" />
      <div className="panel-nav-links">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            className={`panel-nav-link ${active === s.id ? "active" : ""}`}
            onClick={() => scrollTo(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState("hero");
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("trs_user");
    return saved ? JSON.parse(saved) : null;
  });
  const googleRendered = useRef(false);
  const [form, setForm] = useState({
    agent_id: "agent_demo",
    merchant_id: "merchant_abc",
    amount: 500,
    agent_verified: true,
  });

  const [identities, setIdentities] = useState([]);
  const [regRole, setRegRole] = useState("merchant");
  const [regName, setRegName] = useState("");
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState(null);

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

  useEffect(() => {
    if (!user) {
      setIdentities([]);
      return;
    }
    getIdentities(user.email)
      .then(setIdentities)
      .catch(() => setIdentities([]));
  }, [user]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.4 }
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (user) return;
    if (googleRendered.current) return;

    function initGoogle() {
      const container = document.getElementById("google-btn");
      if (!window.google || !container) return;
      container.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        auto_select: false,
        callback: (response) => {
          const payload = decodeJwt(response.credential);
          if (payload) {
            const profile = {
              name: payload.name,
              email: payload.email,
              picture: payload.picture,
            };
            setUser(profile);
            localStorage.setItem("trs_user", JSON.stringify(profile));
            if (window.google) {
              window.google.accounts.id.cancel();
            }
          }
        },
      });
      window.google.accounts.id.renderButton(container, {
        theme: "filled_black",
        size: "medium",
        shape: "pill",
        text: "signin_with",
      });
      googleRendered.current = true;
    }

    const interval = setInterval(() => {
      if (window.google) {
        initGoogle();
        clearInterval(interval);
      }
    }, 200);
    return () => clearInterval(interval);
  }, [user]);

  function handleLogout() {
    setUser(null);
    localStorage.removeItem("trs_user");
    googleRendered.current = false;
    if (window.google) {
      window.google.accounts.id.disableAutoSelect();
      window.google.accounts.id.cancel();
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    if (!regName.trim()) return;
    setRegLoading(true);
    setRegError(null);
    try {
      const identity = await registerIdentity({
        google_email: user.email,
        role: regRole,
        display_name: regName.trim(),
      });
      setIdentities((prev) => [identity, ...prev]);
      setRegName("");
      if (regRole === "merchant") {
        setForm((f) => ({ ...f, merchant_id: identity.identity_id }));
      } else {
        setForm((f) => ({ ...f, agent_id: identity.identity_id }));
      }
    } catch (err) {
      setRegError("Registration failed. Please try again.");
    } finally {
      setRegLoading(false);
    }
  }

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
      <Bubbles />
      <nav className={`navbar ${scrolled ? "navbar-scrolled" : ""}`}>
        <span className="brand">Trust &amp; Risk Sentinel</span>
        <div className="nav-right">
          <div className="nav-links">
            <button onClick={() => scrollTo("how-it-works")}>How it works</button>
            <button onClick={() => scrollTo("demo")}>Live demo</button>
          </div>
          {user ? (
            <div className="user-chip" onClick={handleLogout} title="Click to sign out">
              <img src={user.picture} alt={user.name} />
              <span>{user.name}</span>
            </div>
          ) : (
            <div id="google-btn" className="google-btn-slot" />
          )}
        </div>
      </nav>

      <LiveStatsPanel logs={logs} active={activeSection} />

      <section id="hero" className="hero">
        <div className="hero-glow" />
        <div className="hero-content">
          <span className="eyebrow">AI Agent Commerce · Risk Infrastructure</span>
          <h1>
            Every AI agent transaction,
            <br />
            <span className="gradient-text">screened, scored, and explained.</span>
          </h1>
          <p className="hero-sub">
            A trust layer between AI buyer-agents and merchants — deterministic
            rules, ML anomaly detection, and plain-language explanations for
            every decision, backed by an immutable audit trail.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" onClick={() => scrollTo("demo")}>
              Try the live demo
            </button>
            <button className="ghost-btn" onClick={() => scrollTo("how-it-works")}>
              See how it works
            </button>
          </div>
        </div>
        <div className="scroll-cue" onClick={() => scrollTo("how-it-works")}>
          <span />
        </div>
      </section>

      <section id="how-it-works" className="section">
        <Reveal className="section-heading">
          <h2>Three layers of trust</h2>
          <p>Every transaction passes through all three before a decision is made.</p>
        </Reveal>

        <div className="card-grid">
          <Reveal delay={0}>
            <div className="feature-card">
              <div className="feature-icon rule">⚖️</div>
              <h3>Rule Engine</h3>
              <p>
                Deterministic checks — velocity limits, amount ceilings, agent
                verification — catch clear violations instantly, with zero
                ambiguity.
              </p>
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div className="feature-card">
              <div className="feature-icon ml">📊</div>
              <h3>ML Anomaly Detection</h3>
              <p>
                An Isolation Forest model scores statistically unusual behavior
                rules alone would miss — spending spikes, odd patterns, drift
                from an agent's baseline.
              </p>
            </div>
          </Reveal>
          <Reveal delay={240}>
            <div className="feature-card">
              <div className="feature-icon xai">💬</div>
              <h3>Explainable Decisions</h3>
              <p>
                SHAP values identify what drove the score; an LLM turns that
                into a plain-language reason — logged immutably for every
                transaction.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      <section id="demo" className="section demo-section">
        <Reveal className="section-heading">
          <h2>Live demo</h2>
          <p>Fire a real transaction below and watch it get screened in real time.</p>
        </Reveal>

        {user && (
          <Reveal>
            <div className="panel">
              <h3>Register a Merchant or Agent Identity</h3>
              <p className="panel-subtext">
                Registered identities are tied to your Google account ({user.email}) and can be used below.
              </p>
              <form className="txn-form" onSubmit={handleRegister}>
                <label>
                  Role
                  <select value={regRole} onChange={(e) => setRegRole(e.target.value)}>
                    <option value="merchant">Merchant</option>
                    <option value="agent">Agent</option>
                  </select>
                </label>
                <label>
                  Display Name
                  <input
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="e.g. Flipkart Store, Grocery Bot"
                  />
                </label>
                <button className="primary-btn" type="submit" disabled={regLoading}>
                  {regLoading ? "Registering..." : "Register"}
                </button>
              </form>
              {regError && <div className="error-banner">{regError}</div>}

              {identities.length > 0 && (
                <div className="identity-list">
                  {identities.map((idn) => (
                    <div key={idn.id} className="identity-chip">
                      <span className={`identity-role role-${idn.role}`}>{idn.role}</span>
                      <span className="identity-name">{idn.display_name}</span>
                      <code className="identity-id">{idn.identity_id}</code>
                      <button
                        type="button"
                        className="ghost-btn identity-use-btn"
                        onClick={() =>
                          setForm((f) =>
                            idn.role === "merchant"
                              ? { ...f, merchant_id: idn.identity_id }
                              : { ...f, agent_id: idn.identity_id }
                          )
                        }
                      >
                        Use
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Reveal>
        )}

        <Reveal>
          <div className="panel">
            <h3>Fire a test transaction</h3>
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
              <button className="primary-btn" type="submit" disabled={loading}>
                {loading ? "Screening..." : "Screen transaction"}
              </button>
            </form>
          </div>
        </Reveal>

        {error && <div className="error-banner">{error}</div>}

        <Reveal>
          <div className="panel">
            <h3>Live audit feed</h3>
            <div className="table-wrap">
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
            </div>
          </div>
        </Reveal>
      </section>

      <footer className="footer">
        <p>Trust &amp; Risk Sentinel — built for Razorpay Buildathon, Open Innovation Track.</p>
        <p className="footer-contact">Contact: trustrisksentinel26@gmail.com</p>
      </footer>
    </div>
  );
}
