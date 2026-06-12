import { useRef, useState, useEffect } from 'react'
import IFCViewer    from './components/IFCViewer'
import MapPanel     from './components/MapPanel'
import ResultsPanel from './components/ResultsPanel'
import ChatPanel    from './components/ChatPanel'
import GraphModal   from './components/GraphModal'
import ReportModal  from './components/ReportModal'
import './App.css'

// API calls use relative paths: the Vite dev server proxies /api to the
// backend (vite.config.js), and in production the backend serves the bundle.

// ── Workflow steps (derived from state) ──────────────────────────────────────
// 0 = upload IFC
// 1 = set site location on map
// 2 = orient building (rotation)
// 3 = run analysis
// 4 = results ready

export default function App() {
  const [sessionId, setSessionId]   = useState(null)
  const [building, setBuilding]     = useState(null)
  const [siteLat, setSiteLat]       = useState(41.3851)
  const [siteLon, setSiteLon]       = useState(2.1734)
  const [siteSet, setSiteSet]       = useState(false)   // true once user actively picks a location
  const [buildingUse, setUse]       = useState('residential')
  const [rotationDeg, setRotation]  = useState(0)
  const [skipLlm, setSkipLlm]       = useState(false)
  const [result, setResult]         = useState(null)
  const [phase, setPhase]           = useState('idle')  // 'idle' | 'upload' | 'analysis'
  const [progress, setProgress]     = useState(null)    // SSE stage label during analysis
  const [error, setError]           = useState(null)
  const [rightTab, setRightTab]     = useState('results')
  const [highlight, setHighlight]   = useState(null)   // { key, label, ids } — 3-D element highlight
  const [graphOpen, setGraphOpen]   = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportSnaps, setReportSnaps] = useState(null) // { overall, critical, byStrategy }
  const [splitPct, setSplitPct]     = useState(55)
  const fileRef   = useRef(null)
  const centerRef = useRef(null)
  const dragRef   = useRef(false)
  const viewerRef = useRef(null)

  const loading = phase !== 'idle'
  const step =
    !building ? 0 :
    !siteSet  ? 1 :
    result    ? 4 :
    phase === 'analysis' ? 3 : 2

  // Drag-to-resize between IFC viewer and map
  useEffect(() => {
    const onMove = e => {
      if (!dragRef.current || !centerRef.current) return
      const rect = centerRef.current.getBoundingClientRect()
      const pct  = ((e.clientY - rect.top) / rect.height) * 100
      setSplitPct(Math.max(20, Math.min(80, pct)))
    }
    const onUp = () => { dragRef.current = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',  onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',  onUp)
    }
  }, [])

  const applyParsedBuilding = data => {
    setBuilding(data)
    setSessionId(data.session_id)
    setResult(null)
    setHighlight(null)
  }

  // Toggle highlighting of strategy-affected elements in the 3-D viewer
  const toggleHighlight = (key, label, ids) =>
    setHighlight(h => (h?.key === key ? null : { key, label, ids }))

  // Capture per-strategy 3-D snapshots and open the printable report
  const generateReport = () => {
    if (!result) return
    const cap = ids => viewerRef.current?.capture?.(ids) ?? null
    const byStrategy = {}
    for (const s of result.strategies ?? []) {
      if (s.precondition_met !== 'NO' && s.affected_elements?.length) {
        byStrategy[s.name] = cap(s.affected_elements)
      }
    }
    setReportSnaps({
      overall: cap(null),
      critical: result.diagnosis?.critical_facades?.length
        ? cap(result.diagnosis.critical_facades)
        : null,
      byStrategy,
    })
    setReportOpen(true)
  }

  // ── Step 0 → 1: Upload IFC ────────────────────────────────────────────────
  const handleUpload = async e => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setPhase('upload')
    const fd = new FormData()
    fd.append('file', file)
    fd.append('site_lat', siteLat)
    fd.append('site_lon', siteLon)
    fd.append('building_use', buildingUse)
    try {
      const res  = await fetch('/api/ifc/upload', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      applyParsedBuilding(data)
    } catch (e) {
      setError(e.message)
    }
    setPhase('idle')
    // reset input so the same file can be re-uploaded
    e.target.value = ''
  }

  // Load the bundled Duplex sample — lets users try the tool with no IFC file
  const loadSample = async () => {
    setError(null)
    setPhase('upload')
    const fd = new FormData()
    fd.append('site_lat', siteLat)
    fd.append('site_lon', siteLon)
    fd.append('building_use', buildingUse)
    try {
      const res  = await fetch('/api/ifc/sample', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Sample load failed')
      applyParsedBuilding(data)
    } catch (e) {
      setError(e.message)
    }
    setPhase('idle')
  }

  // Site picked on map
  const handleSiteChange = (lat, lon) => {
    setSiteLat(lat)
    setSiteLon(lon)
    setSiteSet(true)
  }

  // ── Step 3 → 4: run analysis (SSE — per-stage progress) ───────────────────
  const runAnalysis = async () => {
    setError(null)
    setPhase('analysis')
    setProgress('Starting analysis…')
    try {
      const res = await fetch('/api/analysis/run-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id:          sessionId,
          site_lat:            siteLat,
          site_lon:            siteLon,
          building_use:        buildingUse,
          rotation_offset_deg: rotationDeg,
          skip_llm:            skipLlm,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Analysis failed (HTTP ${res.status})`)
      }
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let finished = false
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const events = buf.split('\n\n')
        buf = events.pop()
        for (const block of events) {
          const line = block.split('\n').find(l => l.startsWith('data: '))
          if (!line) continue
          const evt = JSON.parse(line.slice(6))
          if (evt.stage === 'error') throw new Error(evt.detail)
          if (evt.stage === 'done') {
            setResult(evt.result)
            setRightTab('results')
            setHighlight(null)
            finished = true
          } else {
            setProgress(evt.label)
          }
        }
      }
      if (!finished) throw new Error('Analysis stream ended unexpectedly')
    } catch (e) {
      setError(e.message)
    }
    setPhase('idle')
    setProgress(null)
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>

      {/* ── Top bar ── */}
      <header style={{
        height: 48, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px',
        background: 'var(--surface)', borderBottom: '1px solid var(--border)',
      }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--heading)', letterSpacing: '.3px' }}>
          Passive Design Advisor — Barcelona 2025
        </span>
        <StepBar step={step} />
      </header>

      {/* ── Main 3-column layout ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Left sidebar ── */}
        <aside style={{
          width: 268, flexShrink: 0,
          background: 'var(--surface)', borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
          padding: '16px 14px', gap: 20,
        }}>
          {/* BUILDING section */}
          <Section label="Building">
            <button
              className="btn-primary"
              style={{ width: '100%' }}
              onClick={() => fileRef.current?.click()}
              disabled={loading}
            >
              {phase === 'upload' ? 'Parsing…' : building ? '↑ Re-upload IFC' : '↑ Upload IFC'}
            </button>
            <input
              ref={fileRef} type="file" accept=".ifc" style={{ display: 'none' }}
              onChange={handleUpload}
            />
            {!building && (
              <button
                className="btn-secondary"
                style={{ width: '100%', fontSize: 11 }}
                onClick={loadSample}
                disabled={loading}
              >
                ✦ Try sample building (Duplex)
              </button>
            )}

            {building && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 2, marginTop: 4 }}>
                <Row k="Area"    v={`${building.total_floor_area_m2?.toFixed(0)} m²`} />
                <Row k="Floors"  v={building.number_of_floors} />
                <Row k="Facades" v={building.facades?.length} />
                <Row k="D × W"   v={`${building.building_depth_m?.toFixed(1)} × ${building.building_width_m?.toFixed(1)} m`} />
              </div>
            )}

            <label style={{ marginTop: 4 }}>Building Use</label>
            <select value={buildingUse} onChange={e => setUse(e.target.value)}>
              <option value="residential">Residential</option>
              <option value="office">Office</option>
              <option value="mixed">Mixed</option>
            </select>
          </Section>

          {/* SITE section — visible once IFC uploaded */}
          {building && (
            <Section label="Site Location">
              <p style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.6 }}>
                Draw a rectangle on the map. The building will be placed at its centre.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4 }}>
                <div><label>Latitude</label><input value={siteLat.toFixed(5)} readOnly /></div>
                <div><label>Longitude</label><input value={siteLon.toFixed(5)} readOnly /></div>
              </div>
              {!siteSet && (
                <div style={{ fontSize: 11, color: 'var(--yellow)', marginTop: 4 }}>
                  ↓ Draw a rectangle on the map below
                </div>
              )}
            </Section>
          )}

          {/* ORIENTATION section — visible as soon as IFC is uploaded */}
          {building && (
            <Section label="Orientation">
              <p style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.6 }}>
                Drag the 3-D viewer or use the slider to set the building orientation before running analysis.
              </p>
              <label style={{ marginTop: 4 }}>
                Rotation offset: {((rotationDeg % 360 + 360) % 360).toFixed(0)}°
              </label>
              <input
                type="range" min={-180} max={180} step={1} value={rotationDeg}
                onChange={e => setRotation(Number(e.target.value))}
                style={{ padding: 0, border: 'none', background: 'none', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', gap: 5, marginTop: 4 }}>
                {[0, 45, 90, 135, 180].map(d => (
                  <button key={d} className="btn-secondary"
                    style={{ flex: 1, padding: '4px 0', fontSize: 10 }}
                    onClick={() => setRotation(d)}>
                    {d}°
                  </button>
                ))}
              </div>
            </Section>
          )}

          {/* ANALYSIS section — visible once IFC is uploaded */}
          {building && (
            <Section label="Analysis">
              <button
                className="btn-primary" style={{ width: '100%' }}
                onClick={runAnalysis}
                disabled={loading || !sessionId || !siteSet}
              >
                {phase === 'analysis' ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                    <span className="spin-ring" style={{ width: 14, height: 14 }} /> Running…
                  </span>
                ) : '▶ Run Analysis'}
              </button>
              {!siteSet && (
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                  Set the site location on the map first.
                </div>
              )}

              {phase === 'analysis' && progress && (
                <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 6, lineHeight: 1.5 }}>
                  {progress}
                </div>
              )}

              <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, cursor: 'pointer', fontWeight: 400, fontSize: 12 }}>
                <input type="checkbox" checked={skipLlm} onChange={e => setSkipLlm(e.target.checked)}
                  style={{ width: 'auto', cursor: 'pointer' }} />
                Skip LLM report (faster)
              </label>

              {error && (
                <div style={{
                  marginTop: 8, padding: '8px 10px', borderRadius: 6, fontSize: 11,
                  background: 'rgba(248,113,113,.12)', border: '1px solid var(--red)', color: 'var(--red)',
                }}>
                  {error}
                </div>
              )}
            </Section>
          )}
          {/* Knowledge graph button — pinned to sidebar bottom */}
          <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <button
              className="btn-secondary"
              style={{ width: '100%', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
              onClick={() => setGraphOpen(true)}
            >
              <span style={{ fontSize: 14 }}>⬡</span> View Knowledge Graph
            </button>
          </div>
        </aside>

        {/* ── Centre: IFC viewer + map ──
            Before a building is loaded the 3-D viewer is empty, so the map
            gets the full centre area; the viewer + split appear after upload. */}
        <div ref={centerRef} style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {building && (
            <>
              {/* IFC Viewer */}
              <div style={{ flex: `0 0 ${splitPct}%`, position: 'relative', minHeight: 0, overflow: 'hidden' }}>
                <IFCViewer
                  ref={viewerRef}
                  sessionId={sessionId}
                  rotationDeg={rotationDeg}
                  highlightIds={highlight?.ids}
                  highlightLabel={highlight?.label}
                />
              </div>

              {/* Drag handle */}
              <div
                onMouseDown={e => { dragRef.current = true; e.preventDefault() }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--accent)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--border)'}
                style={{
                  height: 6, flexShrink: 0, cursor: 'row-resize',
                  background: 'var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'background 0.15s',
                }}
              >
                <div style={{ width: 28, height: 2, borderRadius: 1, background: 'var(--text-dim)', opacity: 0.45, pointerEvents: 'none' }} />
              </div>
            </>
          )}

          {/* Map */}
          <div style={{ flex: 1, position: 'relative', minHeight: 0, overflow: 'hidden' }}>
            <MapPanel
              siteLat={siteLat}
              siteLon={siteLon}
              onSiteChange={handleSiteChange}
              building={building}
              rotationDeg={rotationDeg}
            />
            {!building && (
              <div style={{
                position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
                background: 'rgba(15,15,19,.88)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '8px 16px', zIndex: 500,
                pointerEvents: 'none', fontSize: 12, color: 'var(--text)',
                boxShadow: '0 2px 12px rgba(0,0,0,.4)',
              }}>
                Upload an IFC file (or try the sample) — you can already pick the site location on the map
              </div>
            )}
          </div>
        </div>

        {/* ── Right panel: Results + Chat ── */}
        <aside style={{
          width: 380, flexShrink: 0,
          borderLeft: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* Tab bar */}
          <div style={{ display: 'flex', background: 'var(--surface)', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            {[['results', '📊 Results'], ['chat', '💬 Chat']].map(([id, label]) => (
              <button key={id} onClick={() => setRightTab(id)} style={{
                flex: 1, padding: '11px 0', background: 'none', borderRadius: 0,
                borderBottom: rightTab === id ? '2px solid var(--accent)' : '2px solid transparent',
                color: rightTab === id ? 'var(--heading)' : 'var(--text-dim)',
                fontSize: 12, fontWeight: 600, letterSpacing: '.5px', textTransform: 'uppercase',
              }}>
                {label}
              </button>
            ))}
          </div>

          {rightTab === 'results' ? (
            <div style={{ flex: 1, overflowY: 'auto', padding: 14 }}>
              <ResultsPanel
                diagnosis={result?.diagnosis}
                strategies={result?.strategies}
                site={result?.site}
                highlightKey={highlight?.key}
                onToggleHighlight={toggleHighlight}
                onGenerateReport={generateReport}
              />
            </div>
          ) : (
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <ChatPanel sessionId={sessionId} analysisResult={result} />
            </div>
          )}
        </aside>

      </div>
    <GraphModal open={graphOpen} onClose={() => setGraphOpen(false)} />
    <ReportModal
      open={reportOpen}
      onClose={() => setReportOpen(false)}
      result={result}
      building={building}
      snapshots={reportSnaps}
      siteLat={siteLat}
      siteLon={siteLon}
      buildingUse={buildingUse}
    />
    </div>
  )
}

// ── Step bar ──────────────────────────────────────────────────────────────────
const STEPS = ['Upload IFC', 'Set Site', 'Orient', 'Analyse', 'Results']

function StepBar({ step }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {STEPS.map((label, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {i > 0 && <div style={{ width: 16, height: 1, background: 'var(--border)' }} />}
          <div className={`step-dot ${i < step ? 'done' : i === step ? 'active' : ''}`}>
            {i < step ? '✓' : i + 1}
          </div>
          <span style={{
            fontSize: 10, letterSpacing: '.3px',
            color: i === step ? 'var(--heading)' : 'var(--text-dim)',
            display: window.innerWidth > 1000 ? 'inline' : 'none',
          }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Small helpers ─────────────────────────────────────────────────────────────
function Section({ label, children }) {
  return (
    <div>
      <div style={{
        fontSize: 10, fontWeight: 700, color: 'var(--text-dim)',
        letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 10,
      }}>
        {label}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {children}
      </div>
    </div>
  )
}

function Row({ k, v }) {
  return (
    <div>
      <span style={{ color: 'var(--text-dim)' }}>{k}: </span>
      <span style={{ color: 'var(--text)' }}>{v}</span>
    </div>
  )
}
