import ReactMarkdown from 'react-markdown'

/**
 * ReportModal — a printable, document-style report of the full analysis.
 * Rendered as a light "paper" document (unlike the dark app UI) so the
 * browser's Print → Save as PDF produces a clean deliverable.
 *
 * Props:
 *   open, onClose
 *   result      – AnalysisResponse (site / diagnosis / strategies)
 *   building    – ParsedBuilding from upload
 *   snapshots   – { overall, critical, byStrategy: {name: dataURL} }
 *   siteLat, siteLon, buildingUse
 */

const LEVEL_COLOR = { HIGH: '#15803d', MEDIUM: '#b45309', LOW: '#b91c1c' }
const RISK_COLOR  = { LOW: '#15803d', MEDIUM: '#b45309', HIGH: '#b91c1c', CRITICAL: '#b91c1c' }
const PRECON_COLOR = { YES: '#15803d', PARTIAL: '#b45309', NO: '#b91c1c' }

export default function ReportModal({
  open, onClose, result, building, snapshots, siteLat, siteLon, buildingUse,
}) {
  if (!open || !result) return null
  const { site, diagnosis, strategies } = result
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div
      className="report-overlay"
      style={{
        position: 'fixed', inset: 0, zIndex: 1100,
        background: 'rgba(0,0,0,0.75)', overflowY: 'auto',
        padding: '28px 16px',
      }}
      onClick={onClose}
    >
      {/* Floating toolbar (hidden when printing) */}
      <div
        className="no-print"
        style={{
          position: 'fixed', top: 14, right: 22, zIndex: 1200,
          display: 'flex', gap: 8,
        }}
        onClick={e => e.stopPropagation()}
      >
        <button className="btn-primary" onClick={() => window.print()}>
          🖨 Print / Save as PDF
        </button>
        <button
          onClick={onClose}
          style={{
            background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 6, color: 'var(--text)', padding: '6px 14px', fontSize: 13,
          }}
        >✕ Close</button>
      </div>

      {/* Document */}
      <div
        className="report-doc report-print-area"
        style={{
          maxWidth: 860, margin: '0 auto', background: '#ffffff',
          color: '#1f2430', borderRadius: 10, padding: '44px 52px',
          fontSize: 13, lineHeight: 1.65,
          boxShadow: '0 8px 48px rgba(0,0,0,.5)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Title block ── */}
        <div style={{ borderBottom: '3px solid #1f2430', paddingBottom: 18, marginBottom: 24 }}>
          <div style={{ fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: '#6b7280' }}>
            Passive Design Advisor — Barcelona
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: '6px 0 10px', color: '#111827' }}>
            Passive Cooling Strategy Report
          </h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 26px', fontSize: 12, color: '#4b5563' }}>
            <span><b>Model:</b> {building?.ifc_filename ?? '—'}</span>
            <span><b>Site:</b> {siteLat?.toFixed(5)}, {siteLon?.toFixed(5)}</span>
            <span><b>Use:</b> {buildingUse}</span>
            <span><b>Date:</b> {today}</span>
          </div>
        </div>

        {/* ── Building + overall view ── */}
        <SectionTitle>1 · Building</SectionTitle>
        <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start', marginBottom: 26 }}>
          <div style={{ flex: '1 1 46%', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Stat label="Floor area" value={`${building?.total_floor_area_m2?.toFixed(0) ?? '—'} m²`} />
            <Stat label="Floors" value={building?.number_of_floors ?? '—'} />
            <Stat label="Facades" value={building?.facades?.length ?? '—'} />
            <Stat label="Depth × Width" value={`${building?.building_depth_m?.toFixed(1)} × ${building?.building_width_m?.toFixed(1)} m`} />
            <Stat label="Operable windows" value={`${building?.operable_window_area_m2?.toFixed(1) ?? '—'} m²`} />
            <Stat label="Opposing openings" value={building?.has_opposing_openings ? 'Yes' : 'No'} />
          </div>
          {snapshots?.overall && (
            <figure style={{ flex: '1 1 54%', margin: 0 }}>
              <img src={snapshots.overall} alt="Building model" style={{ width: '100%', borderRadius: 8, border: '1px solid #e5e7eb' }} />
              <figcaption style={{ fontSize: 10.5, color: '#6b7280', marginTop: 4 }}>
                Building model as analysed (orientation applied).
              </figcaption>
            </figure>
          )}
        </div>

        {/* ── Site context ── */}
        <SectionTitle>2 · Site Context</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 26 }}>
          <Stat label="Thermal comfort zone" value={`${site?.thermal_comfort_gridcode} — ${site?.thermal_comfort_label}`} />
          <Stat label="Sky view factor" value={site?.svf_mean?.toFixed(2)} />
          <Stat label="Canyon H/W" value={site?.canyon_hw_ratio?.toFixed(1)} />
          <Stat label="Summer wind" value={`${site?.summer_mean_wind_m_s?.toFixed(1)} m/s ${site?.dominant_wind_direction}`} />
          <Stat label="July diurnal swing" value={`${site?.july_diurnal_swing_C?.toFixed(1)} °C`} />
          <Stat label="CDH > 26 °C" value={site?.summer_CDH_above_26C?.toFixed(0)} />
        </div>

        {/* ── Diagnosis ── */}
        <SectionTitle>3 · Overheating Diagnosis</SectionTitle>
        <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start', marginBottom: 26 }}>
          <div style={{ flex: '1 1 54%' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 8 }}>
              <span style={{
                fontSize: 24, fontWeight: 800,
                color: RISK_COLOR[diagnosis?.risk_level] ?? '#1f2430',
              }}>
                {diagnosis?.risk_level}
              </span>
              <span style={{ color: '#6b7280', fontSize: 12 }}>
                proxy ODH = {diagnosis?.proxy_odh?.toFixed(3)}
              </span>
            </div>
            {diagnosis?.diagnosis_text && <p style={{ margin: '0 0 10px' }}>{diagnosis.diagnosis_text}</p>}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {diagnosis?.ventilation_deficit && <Pill text="Ventilation deficit" color="#b91c1c" />}
              {diagnosis?.night_purge_viable && <Pill text="Night purge viable" color="#15803d" />}
            </div>
            {diagnosis?.critical_facades?.length > 0 && (
              <p style={{ fontSize: 11, color: '#6b7280', marginTop: 10 }}>
                Critical facades: <code style={{ fontSize: 10.5 }}>{diagnosis.critical_facades.join(', ')}</code>
              </p>
            )}
          </div>
          {snapshots?.critical && (
            <figure style={{ flex: '1 1 46%', margin: 0 }}>
              <img src={snapshots.critical} alt="Critical facades" style={{ width: '100%', borderRadius: 8, border: '1px solid #e5e7eb' }} />
              <figcaption style={{ fontSize: 10.5, color: '#6b7280', marginTop: 4 }}>
                <span style={{ color: '#d97706' }}>■</span> Critical facades driving solar heat gain.
              </figcaption>
            </figure>
          )}
        </div>

        {/* ── Strategies ── */}
        <SectionTitle>4 · Ranked Passive Strategies</SectionTitle>
        {(strategies ?? []).map(s => (
          <StrategySection key={s.name} s={s} snapshot={snapshots?.byStrategy?.[s.name]} />
        ))}

        {/* ── Footer ── */}
        <div style={{
          marginTop: 30, paddingTop: 14, borderTop: '1px solid #e5e7eb',
          fontSize: 10.5, color: '#9ca3af', display: 'flex', justifyContent: 'space-between',
        }}>
          <span>Generated by Passive Design Advisor — MAUT scoring per published sensitivity analyses; LLM-drafted recommendations require professional review.</span>
          <span>{today}</span>
        </div>
      </div>
    </div>
  )
}

// ── Pieces ────────────────────────────────────────────────────────────────────

function SectionTitle({ children }) {
  return (
    <h2 style={{
      fontSize: 15, fontWeight: 700, color: '#111827',
      borderBottom: '1px solid #e5e7eb', paddingBottom: 6, margin: '0 0 14px',
    }}>
      {children}
    </h2>
  )
}

function Stat({ label, value }) {
  return (
    <div style={{ background: '#f7f8fa', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.6, color: '#6b7280' }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginTop: 2 }}>{value ?? '—'}</div>
    </div>
  )
}

function Pill({ text, color }) {
  return (
    <span style={{
      border: `1px solid ${color}`, color, borderRadius: 999,
      padding: '1px 10px', fontSize: 11, fontWeight: 600,
    }}>
      {text}
    </span>
  )
}

function StrategySection({ s, snapshot }) {
  const feasible = s.precondition_met !== 'NO'
  const title = (s.name ?? '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const levelColor = LEVEL_COLOR[s.impact_level] ?? '#6b7280'

  return (
    <div style={{
      border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 20px',
      marginBottom: 16, breakInside: 'avoid',
      opacity: feasible ? 1 : 0.75,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 15, fontWeight: 800, color: '#111827' }}>{s.rank}. {title}</span>
          <Pill text={s.impact_level} color={levelColor} />
          <Pill text={s.precondition_met} color={PRECON_COLOR[s.precondition_met] ?? '#6b7280'} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 110, height: 7, background: '#eceef2', borderRadius: 4 }}>
            <div style={{ width: `${Math.min(100, s.impact_score)}%`, height: '100%', background: levelColor, borderRadius: 4 }} />
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#111827', minWidth: 52 }}>
            {s.impact_score?.toFixed(0)}/100
          </span>
        </div>
      </div>

      <p style={{ fontSize: 11.5, color: '#4b5563', margin: '0 0 12px' }}>{s.precondition_reason}</p>

      <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start' }}>
        {/* Snapshot with affected elements */}
        {snapshot && (
          <figure style={{ flex: '0 0 46%', margin: 0 }}>
            <img src={snapshot} alt={`${title} affected elements`} style={{ width: '100%', borderRadius: 8, border: '1px solid #e5e7eb' }} />
            <figcaption style={{ fontSize: 10.5, color: '#6b7280', marginTop: 4 }}>
              <span style={{ color: '#d97706' }}>■</span> {s.affected_elements?.length ?? 0} affected element{s.affected_elements?.length === 1 ? '' : 's'} highlighted.
            </figcaption>
          </figure>
        )}

        {/* Factors */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {s.key_driver && (
            <div style={{ fontSize: 11.5, marginBottom: 8 }}>
              <b>Key driver:</b> {s.key_driver.replace(/_/g, ' ')}
            </div>
          )}
          {s.factor_scores && Object.entries(s.factor_scores).map(([name, f]) => (
            <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, marginBottom: 4 }}>
              <span style={{ width: 120, color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {name.replace(/_/g, ' ')}
              </span>
              <div style={{ flex: 1, height: 5, background: '#eceef2', borderRadius: 3 }}>
                <div style={{ width: `${Math.min(100, (f.mu ?? 0) * 100)}%`, height: '100%', background: '#6366f1', borderRadius: 3 }} />
              </div>
              <span style={{ width: 34, textAlign: 'right', color: '#6b7280' }}>{((f.mu ?? 0) * 100).toFixed(0)}%</span>
            </div>
          ))}
          {s.affected_elements?.length > 0 && (
            <div style={{ fontSize: 10, color: '#9ca3af', marginTop: 8, wordBreak: 'break-all' }}>
              Elements: {s.affected_elements.slice(0, 8).join(', ')}{s.affected_elements.length > 8 ? ` … +${s.affected_elements.length - 8} more` : ''}
            </div>
          )}
        </div>
      </div>

      {/* Recommendation */}
      {feasible && s.recommendation && (
        <div className="report-md" style={{ marginTop: 12, paddingTop: 10, borderTop: '1px dashed #e5e7eb', fontSize: 12 }}>
          <ReactMarkdown>{s.recommendation}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}
