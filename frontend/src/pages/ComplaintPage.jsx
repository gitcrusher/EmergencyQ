import { useState, useRef } from 'react'
import { analyzeComplaint, submitFeedback } from '../services/api'
import './ComplaintPage.css'

/* ── helpers ── */
const SEV_CLS = { Critical: 'sev-critical', High: 'sev-high', Moderate: 'sev-moderate', Low: 'sev-low' }
const SEV_ICON = { Critical: '🚨', High: '⚠️', Moderate: '🔵', Low: '✅' }
const ISEV_CLS = { Critical: 'isev-critical', High: 'isev-high', Moderate: 'isev-moderate', Low: 'isev-low' }
const SEVERITIES = ['Critical', 'High', 'Moderate', 'Low']

const FACT_META = [
  { key: 'location',     icon: '📍', label: 'Location' },
  { key: 'victim_count', icon: '👥', label: 'Victims' },
  { key: 'hazard_type',  icon: '☣️',  label: 'Hazard' },
  { key: 'environment',  icon: '🏢', label: 'Environment' },
]

const MAX_CHARS = 2000

/* ── Feedback sub-component ── */
function FeedbackPanel({ complaintId, predictedSeverity }) {
  const [open, setOpen]       = useState(false)
  const [actual, setActual]   = useState(predictedSeverity)
  const [notes, setNotes]     = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone]       = useState(false)
  const [err, setErr]         = useState(null)

  async function handleSubmit() {
    setLoading(true); setErr(null)
    try {
      await submitFeedback({
        complaint_id: complaintId,
        predicted_severity: predictedSeverity,
        actual_severity: actual,
        responder_notes: notes || null,
      })
      setDone(true)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="feedback-section">
      {!open && !done && (
        <button id="feedback-toggle-btn" className="feedback-toggle" onClick={() => setOpen(true)}>
          📋 Responder Feedback — Was our severity correct?
        </button>
      )}

      {open && !done && (
        <div className="feedback-form">
          <div>
            <div className="form-label">Actual observed severity</div>
            <select
              id="feedback-severity-select"
              className="feedback-select"
              value={actual}
              onChange={e => setActual(e.target.value)}
            >
              {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <div className="form-label">Notes (optional)</div>
            <textarea
              id="feedback-notes-textarea"
              className="feedback-notes"
              placeholder="What did you observe on the ground?"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              maxLength={1000}
            />
          </div>
          {err && <div style={{ color: '#fca5a5', fontSize: 13 }}>❌ {err}</div>}
          <div style={{ display: 'flex', gap: 8 }}>
            <button id="feedback-submit-btn" className="feedback-submit" onClick={handleSubmit} disabled={loading}>
              {loading ? 'Sending…' : '✔ Submit Feedback'}
            </button>
            <button className="feedback-submit" style={{ background: 'none', border: '1px solid var(--clr-border)', color: 'var(--clr-text-muted)' }} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {done && (
        <div className="feedback-success">
          ✅ Feedback recorded — model weights updated. Thank you!
        </div>
      )}
    </div>
  )
}

/* ── Result panel ── */
function ResultPanel({ result }) {
  if (!result) {
    return (
      <div className="result-empty">
        <div className="result-empty-icon">🔍</div>
        <div className="result-empty-title">Analysis results will appear here</div>
        <div className="result-empty-desc">
          Submit your emergency complaint on the left and our AI will analyze it instantly.
        </div>
      </div>
    )
  }

  const { category, prediction_set, confidence, severity, urgency, atomic_facts, similar_incidents, complaint_id } = result
  const sevCls = SEV_CLS[severity] || 'sev-moderate'
  const sevIcon = SEV_ICON[severity] || '⚡'
  const confPct = Math.round(confidence * 100)

  return (
    <div className="result-content">
      {/* Severity hero */}
      <div className={`sev-hero ${sevCls}`}>
        <span className="sev-icon">{sevIcon}</span>
        <div>
          <div className="sev-label-sm">Severity Level</div>
          <div className="sev-value">{severity}</div>
        </div>
      </div>

      {/* Info grid */}
      <div className="info-grid">
        <div className="info-cell">
          <div className="info-cell-label">Category</div>
          <div className="info-cell-value">{category}</div>
        </div>
        <div className="info-cell">
          <div className="info-cell-label">Urgency</div>
          <div className="info-cell-value">{urgency}</div>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="conf-bar-wrap">
        <div className="conf-bar-header">
          <span className="conf-bar-label">Model Confidence</span>
          <span className="conf-bar-val">{confPct}%</span>
        </div>
        <div className="conf-bar-track">
          <div className="conf-bar-fill" style={{ width: `${confPct}%` }} />
        </div>
      </div>

      {/* Prediction set */}
      {prediction_set?.length > 0 && (
        <div>
          <div className="facts-title">Prediction Set</div>
          <div className="tag-row">
            {prediction_set.map(p => (
              <span key={p} className={`tag ${p === category ? 'tag-purple' : 'tag-teal'}`}>{p}</span>
            ))}
          </div>
        </div>
      )}

      <hr className="result-divider" />

      {/* Atomic facts */}
      <div className="facts-section">
        <div className="facts-title">Extracted Facts</div>
        <div className="facts-grid">
          {FACT_META.map(fm => {
            const val = atomic_facts?.[fm.key] || ''
            return (
              <div className="fact-item" key={fm.key}>
                <span className="fact-icon">{fm.icon}</span>
                <div>
                  <div className="fact-key">{fm.label}</div>
                  <div className={`fact-val${val ? '' : ' missing'}`}>{val || 'Not detected'}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <hr className="result-divider" />

      {/* Similar incidents */}
      {similar_incidents?.length > 0 && (
        <div className="similar-section">
          <div className="similar-title">Similar Incidents ({similar_incidents.length})</div>
          <div className="incident-list">
            {similar_incidents.slice(0, 4).map((inc, i) => (
              <div className="incident-item" key={i}>
                <div className="incident-meta">
                  <span className="incident-cat">{inc.label}</span>
                  <span className={`incident-sev ${ISEV_CLS[inc.severity] || 'isev-moderate'}`}>{inc.severity}</span>
                  <span className="incident-date">{inc.date?.split('T')[0]}</span>
                </div>
                <div className="incident-text">{inc.text?.slice(0, 100)}{inc.text?.length > 100 ? '…' : ''}</div>
                <div className="incident-score">Similarity: {(inc.adjusted_score * 100).toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <hr className="result-divider" />

      {/* Feedback */}
      <FeedbackPanel complaintId={complaint_id} predictedSeverity={severity} />
    </div>
  )
}

/* ── Main page ── */
export default function ComplaintPage() {
  const [text, setText]       = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)
  const textareaRef           = useRef(null)

  const charCount = text.length
  const charCls   = charCount > 1800 ? 'limit' : charCount > 1500 ? 'warn' : ''

  async function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim() || text.trim().length < 10) return
    setLoading(true); setError(null); setResult(null)
    try {
      const data = await analyzeComplaint(text.trim())
      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="complaint-page">
      {/* Page header */}
      <div className="cp-header">
        <div className="cp-eyebrow">Emergency Triage System</div>
        <h1 className="cp-title">File a Complaint</h1>
        <p className="cp-desc">Describe the emergency below — our AI will analyze it in real-time and return severity, category, and key insights.</p>
      </div>

      <div className="cp-panels">
        {/* ── Left panel: Input ── */}
        <div className={`panel${result || loading ? ' panel-active' : ''}`}>
          <div className="panel-header ph-input">
            <div className="panel-icon">📝</div>
            <div>
              <div className="panel-title">Submit Complaint</div>
              <div className="panel-subtitle">Describe what's happening in detail</div>
            </div>
          </div>

          <div className="panel-body">
            <form onSubmit={handleSubmit}>
              <label htmlFor="complaint-textarea" className="form-label">Your Emergency Description</label>
              <textarea
                id="complaint-textarea"
                ref={textareaRef}
                className="complaint-textarea"
                placeholder="E.g. — A child is trapped inside a flooded house near Main Road Junction. Water level is rising fast and there are 3 adults unable to escape from the second floor. The structure appears unstable."
                value={text}
                onChange={e => setText(e.target.value.slice(0, MAX_CHARS))}
                disabled={loading}
                minLength={10}
                aria-describedby="char-count"
              />

              <div className="form-footer">
                <span id="char-count" className={`char-count${charCls ? ` ${charCls}` : ''}`}>
                  {charCount} / {MAX_CHARS}
                </span>

                <button
                  id="analyze-submit-btn"
                  type="submit"
                  className="submit-btn"
                  disabled={loading || charCount < 10}
                >
                  {loading ? (
                    <><span className="spinner" /> Analyzing…</>
                  ) : (
                    <>⚡ Analyze Complaint</>
                  )}
                </button>
              </div>

              {error && (
                <div className="error-banner" role="alert">
                  <span>🚫</span>
                  <span>{error}</span>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* ── Right panel: Results ── */}
        <div className={`panel${result ? ' panel-active' : ''}`}>
          <div className="panel-header ph-result">
            <div className="panel-icon">🎯</div>
            <div>
              <div className="panel-title">Analysis Results</div>
              <div className="panel-subtitle">
                {result
                  ? `Complaint ID: ${result.complaint_id?.slice(0, 8)}…`
                  : 'Waiting for submission'}
              </div>
            </div>
          </div>

          <div className="panel-body">
            {loading ? (
              <div className="result-empty">
                <span className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
                <div className="result-empty-title" style={{ marginTop: 16 }}>Processing your complaint…</div>
                <div className="result-empty-desc">
                  Running decomposition → classification → retrieval → severity scoring
                </div>
              </div>
            ) : (
              <ResultPanel result={result} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
