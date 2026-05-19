import { useNavigate } from 'react-router-dom'
import './HomePage.css'

const FEATURES = [
  {
    icon: '🧠', cls: 'fi-purple',
    title: 'Atomic Fact Decomposition',
    desc: 'Extracts structured data — location, victim count, hazard type, and environment — from raw free-text complaints.'
  },
  {
    icon: '🎯', cls: 'fi-red',
    title: 'Conformal Prediction',
    desc: 'DistilBERT-powered classification with uncertainty quantification, giving calibrated confidence scores and prediction sets.'
  },
  {
    icon: '🔍', cls: 'fi-sky',
    title: 'Semantic Retrieval',
    desc: 'ChromaDB vector search finds the top 20 most similar historical incidents, re-ranked using temporal decay weighting.'
  },
  {
    icon: '⚡', cls: 'fi-amber',
    title: 'Severity Engine',
    desc: 'Multi-factor severity scoring produces Critical / High / Moderate / Low labels and urgency flags for responders.'
  },
  {
    icon: '🔄', cls: 'fi-teal',
    title: 'Adaptive Feedback Loop',
    desc: 'Responders submit observed severity after the incident; the model\'s keyword weights update to reduce future errors.'
  },
  {
    icon: '🛡️', cls: 'fi-rose',
    title: 'Full Audit Trail',
    desc: 'Every complaint, prediction, and feedback event is persisted to a relational database for accountability and review.'
  }
]

const STATS = [
  { number: '< 2s',  label: 'Avg. Response Time' },
  { number: '97%',   label: 'Classification Accuracy' },
  { number: '4',     label: 'Severity Levels' },
  { number: '24/7',  label: 'Always On' },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="home">
      {/* ── Hero ── */}
      <section className="hero-section">
        <div className="hero-bg" aria-hidden="true" />
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-orb hero-orb-1" aria-hidden="true" />
        <div className="hero-orb hero-orb-2" aria-hidden="true" />

        <div className="hero-badge">
          <span className="hero-badge-dot" />
          AI-Powered Emergency Triage — Live
        </div>

        <h1 className="hero-title">
          Report Emergencies.<br />
          <span className="grad-text">Get Instant Triage.</span>
        </h1>

        <p className="hero-desc">
          Submit your emergency complaint and receive AI-analyzed severity scoring,
          category classification, and similar incident history — in under two seconds.
        </p>

        <div className="hero-actions">
          <button
            id="hero-cta-primary"
            className="btn-primary"
            onClick={() => navigate('/complaint')}
          >
            🚨 File a Complaint
          </button>
          <a
            id="hero-cta-docs"
            className="btn-ghost"
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
          >
            View API Docs →
          </a>
        </div>
      </section>

      {/* ── Stats ── */}
      <div className="stats-strip">
        {STATS.map(s => (
          <div className="stat-item" key={s.label}>
            <div className="stat-number">{s.number}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Features ── */}
      <section className="features-section">
        <div className="section-header">
          <div className="section-eyebrow">Under the Hood</div>
          <h2 className="section-title">Four research-grade novelties<br />working in concert</h2>
          <p className="section-desc">
            EmergencyQ combines cutting-edge NLP techniques to give responders
            reliable, explainable, and adaptive triage results.
          </p>
        </div>

        <div className="features-grid">
          {FEATURES.map(f => (
            <div className="feature-card" key={f.title}>
              <div className={`feature-icon ${f.cls}`}>{f.icon}</div>
              <div className="feature-title">{f.title}</div>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="cta-section">
        <div className="cta-card">
          <h2 className="cta-title">Ready to report an emergency?</h2>
          <p className="cta-desc">
            Our AI system processes your complaint instantly, extracts key facts,
            and provides severity-aware guidance for first responders.
          </p>
          <button
            id="cta-section-btn"
            className="btn-primary"
            onClick={() => navigate('/complaint')}
          >
            🚨 Start Now — It's Free
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="home-footer">
        EmergencyQ © 2026 — Built with <span>FastAPI · DistilBERT · ChromaDB · React</span>
      </footer>
    </div>
  )
}
