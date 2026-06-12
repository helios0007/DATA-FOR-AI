import { Component } from 'react'
import ReactMarkdown from 'react-markdown'

// ── Error boundary — prevents a render crash from blacking out the whole app ──
class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) return (
      <div style={{ padding: 16, fontSize: 12, color: 'var(--red)' }}>
        Display error: {this.state.error.message}
      </div>
    )
    return this.props.children
  }
}

export default function ResultsPanel({ diagnosis, strategies, site, highlightKey, onToggleHighlight, onGenerateReport }) {
  if (!diagnosis) {
    return (
      <div style={{ padding: 24, color: 'var(--text-dim)', textAlign: 'center', fontSize: 13 }}>
        Run the analysis to see results.
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {onGenerateReport && (
          <button className="btn-primary" style={{ width: '100%' }} onClick={onGenerateReport}>
            📄 Generate Report
          </button>
        )}
        <SiteCard site={site} />
        <DiagnosisCard
          diagnosis={diagnosis}
          highlightKey={highlightKey}
          onToggleHighlight={onToggleHighlight}
        />
        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '1px', textTransform: 'uppercase' }}>
          Ranked Strategies
        </div>
        {(strategies ?? []).map((s, i) => (
          <StrategyCard
            key={s.name ?? i}
            s={s}
            highlightKey={highlightKey}
            onToggleHighlight={onToggleHighlight}
          />
        ))}
      </div>
    </ErrorBoundary>
  )
}

// Eye toggle: shows the given elements on the 3-D model
function HighlightButton({ active, disabled, onClick }) {
  if (disabled) return null
  return (
    <button
      onClick={onClick}
      title={active ? 'Hide on 3-D model' : 'Show affected elements on the 3-D model'}
      style={{
        flexShrink: 0, padding: '2px 8px', fontSize: 10, borderRadius: 4,
        background: active ? 'rgba(255,167,51,.18)' : 'var(--surface2)',
        border: `1px solid ${active ? '#ffa733' : 'var(--border)'}`,
        color: active ? '#ffa733' : 'var(--text-dim)',
        cursor: 'pointer',
      }}
    >
      {active ? '◉ shown in 3-D' : '◎ show in 3-D'}
    </button>
  )
}

// ── Site card ──────────────────────────────────────────────────────────────────
function SiteCard({ site }) {
  if (!site) return null
  return (
    <div className="panel">
      <div className="panel-header">Site Context</div>
      <div className="panel-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 14px', fontSize: 12 }}>
        <KV k="Comfort zone" v={site.thermal_comfort_label ?? '—'} />
        <KV k="SVF"          v={site.svf_mean?.toFixed(2) ?? '—'} />
        <KV k="Canyon H/W"   v={site.canyon_hw_ratio?.toFixed(1) ?? '—'} />
        <KV k="Wind"         v={`${site.summer_mean_wind_m_s?.toFixed(1) ?? '—'} m/s ${site.dominant_wind_direction ?? ''}`} />
        <KV k="July swing"   v={`${site.july_diurnal_swing_C?.toFixed(1) ?? '—'}°C`} />
        <KV k="CDH >26°C"    v={site.summer_CDH_above_26C?.toFixed(0) ?? '—'} />
      </div>
    </div>
  )
}

// ── Diagnosis card ─────────────────────────────────────────────────────────────
function DiagnosisCard({ diagnosis, highlightKey, onToggleHighlight }) {
  const riskColor = { LOW: 'var(--green)', MEDIUM: 'var(--yellow)', HIGH: 'var(--red)', CRITICAL: 'var(--red)' }
  const color = riskColor[diagnosis.risk_level] ?? 'var(--text)'
  const critical = diagnosis.critical_facades ?? []

  return (
    <div className="panel">
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <span>Overheating Diagnosis</span>
        <HighlightButton
          active={highlightKey === 'critical'}
          disabled={!critical.length || !onToggleHighlight}
          onClick={() => onToggleHighlight('critical', 'Critical facades', critical)}
        />
      </div>
      <div className="panel-body" style={{ fontSize: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 22, fontWeight: 700, color }}>{diagnosis.risk_level}</span>
          <span style={{ color: 'var(--text-dim)' }}>proxy ODH = {diagnosis.proxy_odh?.toFixed(2)}</span>
        </div>
        {diagnosis.diagnosis_text && (
          <p style={{ color: 'var(--text)', lineHeight: 1.65 }}>{diagnosis.diagnosis_text}</p>
        )}
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {diagnosis.ventilation_deficit && <Tag label="Ventilation deficit" color="var(--red)" />}
          {diagnosis.night_purge_viable  && <Tag label="Night purge viable"  color="var(--green)" />}
        </div>
      </div>
    </div>
  )
}

// ── Strategy card ──────────────────────────────────────────────────────────────
function StrategyCard({ s, highlightKey, onToggleHighlight }) {
  const feasible = s.precondition_met !== 'NO'
  const title    = (s.name ?? '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const affected = s.affected_elements ?? []

  return (
    <div className="panel" style={{ opacity: feasible ? 1 : 0.5 }}>
      <div className="panel-header" style={{ justifyContent: 'space-between' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: 'var(--heading)', fontWeight: 600 }}>
            {s.rank}. {title}
          </span>
          {s.impact_level   && <span className={`badge badge-${s.impact_level}`}>{s.impact_level}</span>}
          {s.precondition_met && <span className={`badge badge-${s.precondition_met}`}>{s.precondition_met}</span>}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <HighlightButton
            active={highlightKey === s.name}
            disabled={!feasible || !affected.length || !onToggleHighlight}
            onClick={() => onToggleHighlight(s.name, title, affected)}
          />
          <ScoreBar score={s.impact_score ?? 0} />
        </span>
      </div>

      {feasible && s.factor_scores && <FactorBars factors={s.factor_scores} />}

      {feasible && s.recommendation ? (
        <div className="panel-body md-body" style={{ fontSize: 12, lineHeight: 1.7 }}>
          <ReactMarkdown>{s.recommendation}</ReactMarkdown>
        </div>
      ) : !feasible && s.precondition_reason ? (
        <div className="panel-body" style={{ fontSize: 12, color: 'var(--text-dim)' }}>
          {s.precondition_reason}
        </div>
      ) : null}
    </div>
  )
}

// ── MAUT factor breakdown — mu is the 0–1 fuzzy membership per factor ─────────
function FactorBars({ factors }) {
  const entries = Object.entries(factors)
  if (!entries.length) return null
  return (
    <div style={{ padding: '8px 12px 2px', display: 'flex', flexDirection: 'column', gap: 4 }}>
      {entries.map(([name, f]) => (
        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
          <span style={{ width: 110, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {name.replace(/_/g, ' ')}
          </span>
          <div style={{ flex: 1, height: 4, background: 'var(--surface2)', borderRadius: 2 }}>
            <div style={{
              width: `${Math.min(100, (f.mu ?? 0) * 100)}%`, height: '100%',
              background: 'var(--accent)', borderRadius: 2,
            }} />
          </div>
          <span style={{ width: 30, textAlign: 'right', color: 'var(--text-dim)' }}>
            {((f.mu ?? 0) * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Shared helpers ─────────────────────────────────────────────────────────────
function ScoreBar({ score }) {
  const color = score >= 66 ? 'var(--green)' : score >= 33 ? 'var(--yellow)' : 'var(--red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 56, height: 4, background: 'var(--surface2)', borderRadius: 2 }}>
        <div style={{ width: `${Math.min(100, score)}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-dim)', minWidth: 34 }}>{score?.toFixed(0)}/100</span>
    </div>
  )
}

function KV({ k, v }) {
  return (
    <div>
      <span style={{ color: 'var(--text-dim)' }}>{k}: </span>
      <span style={{ color: 'var(--heading)' }}>{v}</span>
    </div>
  )
}

function Tag({ label, color }) {
  return (
    <span style={{
      background: color + '22', color,
      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
    }}>
      {label}
    </span>
  )
}
