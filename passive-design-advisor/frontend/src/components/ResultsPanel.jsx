import { Component } from 'react'

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

export default function ResultsPanel({ diagnosis, strategies, site }) {
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
        <SiteCard site={site} />
        <DiagnosisCard diagnosis={diagnosis} />
        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '1px', textTransform: 'uppercase' }}>
          Ranked Strategies
        </div>
        {(strategies ?? []).map((s, i) => <StrategyCard key={s.name ?? i} s={s} />)}
      </div>
    </ErrorBoundary>
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
function DiagnosisCard({ diagnosis }) {
  const riskColor = { LOW: 'var(--green)', MEDIUM: 'var(--yellow)', HIGH: 'var(--red)', CRITICAL: 'var(--red)' }
  const color = riskColor[diagnosis.risk_level] ?? 'var(--text)'

  return (
    <div className="panel">
      <div className="panel-header">Overheating Diagnosis</div>
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
function StrategyCard({ s }) {
  const feasible = s.precondition_met !== 'NO'
  const title    = (s.name ?? '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

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
        <ScoreBar score={s.impact_score ?? 0} />
      </div>

      {feasible && s.recommendation ? (
        <div className="panel-body" style={{ fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
          {s.recommendation}
        </div>
      ) : !feasible && s.precondition_reason ? (
        <div className="panel-body" style={{ fontSize: 12, color: 'var(--text-dim)' }}>
          {s.precondition_reason}
        </div>
      ) : null}
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
