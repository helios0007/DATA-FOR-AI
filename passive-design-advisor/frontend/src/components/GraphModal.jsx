import { useEffect, useRef, useState, useCallback } from 'react'

const API = 'http://localhost:8000'
const W = 900
const H = 560

const NODE_COLOR = {
  strategy:      '#7c6af7',
  design_option: '#4ade80',
  standard:      '#facc15',
  paper:         '#fb923c',
}
const NODE_R = {
  strategy: 15, design_option: 9, standard: 8, paper: 8,
}
const EDGE_META = {
  has_variant:  { color: '#44445a', w: 1 },
  justified_by: { color: '#facc15', w: 1.5 },
  synergy_with: { color: '#4ade80', w: 2.5 },
  no_conflict:  { color: '#60a5fa', w: 1.5 },
}

// ── Force simulation (pure function, no React) ────────────────────────────────

function initPos(nodes) {
  const byType = {}
  nodes.forEach(n => { (byType[n.type] = byType[n.type] || []).push(n) })
  const pos = {}
  const ring = (list, r) =>
    list.forEach((n, i) => {
      const a = (i / list.length) * 2 * Math.PI
      pos[n.id] = { x: W / 2 + Math.cos(a) * r, y: H / 2 + Math.sin(a) * r, vx: 0, vy: 0 }
    })
  ring(byType.strategy      || [], 70)
  ring(byType.design_option || [], 210)
  ring([...(byType.standard || []), ...(byType.paper || [])], 350)
  return pos
}

function tick(nodes, edges, pos, alpha, pinnedId) {
  const REPULSION  = 3000
  const ATTRACT    = 0.05
  const DAMPING    = 0.82
  const GRAVITY    = 0.005

  const fx = {}, fy = {}
  nodes.forEach(n => { fx[n.id] = 0; fy[n.id] = 0 })

  nodes.forEach(n => {
    if (n.id === pinnedId) return
    fx[n.id] += (W / 2 - pos[n.id].x) * GRAVITY * alpha
    fy[n.id] += (H / 2 - pos[n.id].y) * GRAVITY * alpha
  })

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i].id, b = nodes[j].id
      const dx = pos[b].x - pos[a].x, dy = pos[b].y - pos[a].y
      const d2 = Math.max(1, dx * dx + dy * dy), d = Math.sqrt(d2)
      const f = REPULSION / d2 * alpha
      fx[a] -= f * dx / d; fy[a] -= f * dy / d
      fx[b] += f * dx / d; fy[b] += f * dy / d
    }
  }

  ;(edges || []).forEach(e => {
    const s = typeof e.source === 'object' ? e.source.id : e.source
    const t = typeof e.target === 'object' ? e.target.id : e.target
    if (!pos[s] || !pos[t]) return
    if (s === pinnedId || t === pinnedId) return
    const dx = pos[t].x - pos[s].x, dy = pos[t].y - pos[s].y
    fx[s] += dx * ATTRACT * alpha; fy[s] += dy * ATTRACT * alpha
    fx[t] -= dx * ATTRACT * alpha; fy[t] -= dy * ATTRACT * alpha
  })

  const PAD = 24
  const next = {}
  nodes.forEach(n => {
    if (n.id === pinnedId) { next[n.id] = pos[n.id]; return }
    const p = pos[n.id]
    const vx = (p.vx + fx[n.id]) * DAMPING
    const vy = (p.vy + fy[n.id]) * DAMPING
    next[n.id] = {
      x: Math.max(PAD, Math.min(W - PAD, p.x + vx)),
      y: Math.max(PAD, Math.min(H - PAD, p.y + vy)),
      vx, vy,
    }
  })
  return next
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function GraphModal({ open, onClose }) {
  const [graphData, setGraphData] = useState(null)
  const [pos, setPos]             = useState({})   // drives SVG render
  const [viewBox, setViewBox]     = useState(`0 0 ${W} ${H}`)
  const [tooltip, setTooltip]     = useState(null) // { node, clientX, clientY }
  const [err, setErr]             = useState(null)

  // Mutable refs used by RAF / event handlers
  const posRef    = useRef({})       // ground truth positions
  const alphaRef  = useRef(1)
  const rafRef    = useRef(null)
  const pinnedRef = useRef(null)     // node id being dragged
  const vbRef     = useRef({ x: 0, y: 0, w: W, h: H })
  const svgRef    = useRef(null)

  // ── Load graph ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return
    setErr(null)
    fetch(`${API}/api/graph`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(data => {
        const p = initPos(data.nodes)
        posRef.current   = p
        alphaRef.current = 1
        vbRef.current    = { x: 0, y: 0, w: W, h: H }
        setViewBox(`0 0 ${W} ${H}`)
        setGraphData(data)
        setPos({ ...p })
      })
      .catch(e => setErr(e.message))
  }, [open])

  // ── Simulation RAF loop ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!graphData) return
    let frame = 0
    const loop = () => {
      if (alphaRef.current > 0.003) {
        posRef.current   = tick(graphData.nodes, graphData.edges, posRef.current, alphaRef.current, pinnedRef.current)
        alphaRef.current *= 0.994
        if (++frame % 2 === 0) setPos({ ...posRef.current })
      }
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(rafRef.current)
  }, [graphData])

  // ── Helper: client pixel → SVG coordinate ──────────────────────────────────
  const clientToSvg = useCallback((cx, cy) => {
    const rect = svgRef.current.getBoundingClientRect()
    const vb   = vbRef.current
    return {
      x: (cx - rect.left) / rect.width  * vb.w + vb.x,
      y: (cy - rect.top)  / rect.height * vb.h + vb.y,
    }
  }, [])

  // ── Node drag ───────────────────────────────────────────────────────────────
  const onNodeDown = useCallback((e, id) => {
    e.preventDefault()
    e.stopPropagation()
    pinnedRef.current = id
    alphaRef.current  = Math.max(alphaRef.current, 0.4)

    const onMove = ev => {
      const { x, y } = clientToSvg(ev.clientX, ev.clientY)
      posRef.current = { ...posRef.current, [id]: { ...posRef.current[id], x, y, vx: 0, vy: 0 } }
      setPos({ ...posRef.current })   // immediate visual update — no need to wait for RAF
    }
    const onUp = () => {
      pinnedRef.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
  }, [clientToSvg])

  // ── Pan (drag on background) ────────────────────────────────────────────────
  const onBgDown = useCallback(e => {
    const startVb = { ...vbRef.current }
    const sx = e.clientX, sy = e.clientY

    const onMove = ev => {
      const rect = svgRef.current.getBoundingClientRect()
      const dx = (ev.clientX - sx) / rect.width  * startVb.w
      const dy = (ev.clientY - sy) / rect.height * startVb.h
      const nVb = { ...startVb, x: startVb.x - dx, y: startVb.y - dy }
      vbRef.current = nVb
      setViewBox(`${nVb.x} ${nVb.y} ${nVb.w} ${nVb.h}`)
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup',   onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
  }, [])

  // ── Zoom (wheel, non-passive so we can preventDefault) ─────────────────────
  useEffect(() => {
    const el = svgRef.current
    if (!el || !open) return
    const handler = e => {
      e.preventDefault()
      const factor = e.deltaY > 0 ? 1.15 : 0.87
      const rect = el.getBoundingClientRect()
      const vb   = vbRef.current
      const mx   = (e.clientX - rect.left) / rect.width  * vb.w + vb.x
      const my   = (e.clientY - rect.top)  / rect.height * vb.h + vb.y
      const nw   = Math.min(W * 4, Math.max(W * 0.25, vb.w * factor))
      const nh   = nw * (H / W)
      const nVb  = { x: mx - (mx - vb.x) * (nw / vb.w), y: my - (my - vb.y) * (nh / vb.h), w: nw, h: nh }
      vbRef.current = nVb
      setViewBox(`${nVb.x} ${nVb.y} ${nVb.w} ${nVb.h}`)
    }
    el.addEventListener('wheel', handler, { passive: false })
    return () => el.removeEventListener('wheel', handler)
  }, [open, graphData]) // re-attach when modal opens / graph loads

  if (!open) return null

  const nodes = graphData?.nodes ?? []
  const edges = graphData?.edges ?? []

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 14, padding: '16px 20px 14px',
          display: 'flex', flexDirection: 'column', gap: 10,
          maxWidth: '96vw',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20 }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--heading)' }}>Knowledge Graph</span>
            <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 10 }}>
              {nodes.length} nodes · {edges.length} edges · drag nodes · scroll to zoom · drag background to pan
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {Object.entries(NODE_COLOR).map(([t, c]) => (
              <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-dim)' }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: c, flexShrink: 0 }} />
                {t.replace('_', ' ')}
              </span>
            ))}
            <button
              onClick={onClose}
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-dim)', padding: '3px 10px', fontSize: 13 }}
            >✕</button>
          </div>
        </div>

        {/* Canvas */}
        {err ? (
          <div style={{ width: W, height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--red)', fontSize: 13 }}>
            {err}
          </div>
        ) : (
          <div style={{ position: 'relative', userSelect: 'none' }}>
            <svg
              ref={svgRef}
              width={W} height={H}
              viewBox={viewBox}
              onMouseDown={onBgDown}
              style={{ display: 'block', borderRadius: 8, background: '#0d0d12', border: '1px solid var(--border)', cursor: 'grab' }}
            >
              {/* Arrow markers */}
              <defs>
                {Object.entries(EDGE_META).map(([rel, { color }]) => (
                  <marker key={rel} id={`arr-${rel}`} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                    <path d="M0,0 L7,3.5 L0,7 Z" fill={color} fillOpacity="0.7" />
                  </marker>
                ))}
              </defs>

              {/* Edges */}
              {edges.map((e, i) => {
                const src = typeof e.source === 'object' ? e.source.id : e.source
                const tgt = typeof e.target === 'object' ? e.target.id : e.target
                const sp = pos[src], tp = pos[tgt]
                if (!sp || !tp) return null

                const rel = e.relation ?? 'has_variant'
                const { color, w } = EDGE_META[rel] ?? EDGE_META.has_variant

                const dx = tp.x - sp.x, dy = tp.y - sp.y
                const d  = Math.sqrt(dx * dx + dy * dy) || 1
                const rS = (NODE_R[nodes.find(n => n.id === src)?.type] ?? 8) + 2
                const rT = (NODE_R[nodes.find(n => n.id === tgt)?.type] ?? 8) + 6

                return (
                  <line
                    key={i}
                    x1={sp.x + (dx / d) * rS} y1={sp.y + (dy / d) * rS}
                    x2={tp.x - (dx / d) * rT} y2={tp.y - (dy / d) * rT}
                    stroke={color} strokeWidth={w} strokeOpacity={0.6}
                    markerEnd={`url(#arr-${rel})`}
                  />
                )
              })}

              {/* Nodes */}
              {nodes.map(n => {
                const p = pos[n.id]
                if (!p) return null
                const r     = NODE_R[n.type] ?? 8
                const color = NODE_COLOR[n.type] ?? '#888'
                const label = (n.label ?? n.id).replace(/_/g, ' ')
                return (
                  <g
                    key={n.id}
                    onMouseDown={e => onNodeDown(e, n.id)}
                    onMouseEnter={e => setTooltip({ node: n, clientX: e.clientX, clientY: e.clientY })}
                    onMouseMove={e  => setTooltip(t => t ? { ...t, clientX: e.clientX, clientY: e.clientY } : null)}
                    onMouseLeave={() => setTooltip(null)}
                    style={{ cursor: 'grab' }}
                  >
                    <circle cx={p.x} cy={p.y} r={r + 5} fill={color} fillOpacity={0.1} />
                    <circle cx={p.x} cy={p.y} r={r} fill={color} stroke="rgba(255,255,255,0.3)" strokeWidth={1.5} />
                    <text
                      x={p.x} y={p.y + r + 12}
                      textAnchor="middle"
                      fontSize={n.type === 'strategy' ? 10 : 8}
                      fontWeight={n.type === 'strategy' ? 600 : 400}
                      fill={n.type === 'strategy' ? '#f0f0f8' : '#6b6b82'}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {label.length > 20 ? label.slice(0, 19) + '…' : label}
                    </text>
                  </g>
                )
              })}
            </svg>

            {/* Tooltip */}
            {tooltip && <Tooltip tooltip={tooltip} />}
          </div>
        )}

        {/* Edge legend */}
        <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
          {Object.entries(EDGE_META).map(([rel, { color, w }]) => (
            <span key={rel} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-dim)' }}>
              <span style={{ width: 22, height: Math.max(1, w), background: color, opacity: 0.85, display: 'inline-block', borderRadius: 1 }} />
              {rel.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function Tooltip({ tooltip }) {
  const { node: n, clientX, clientY } = tooltip
  const lines = [
    { text: (n.label ?? n.id).replace(/_/g, ' '), bold: true },
    { text: n.type?.replace(/_/g, ' '), accent: true },
    n.description      && { text: n.description },
    n.performance_note && { text: n.performance_note },
  ].filter(Boolean)

  return (
    <div style={{
      position: 'fixed',
      left: Math.min(clientX + 14, window.innerWidth - 270),
      top:  Math.max(clientY - 8, 8),
      width: 256,
      background: '#1c1c2a',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '10px 12px',
      fontSize: 11,
      lineHeight: 1.6,
      zIndex: 1200,
      pointerEvents: 'none',
      boxShadow: '0 4px 20px rgba(0,0,0,.7)',
    }}>
      {lines.map((l, i) => (
        <div key={i} style={{
          color:      l.bold ? '#f0f0f8' : l.accent ? 'var(--accent)' : 'var(--text-dim)',
          fontWeight: l.bold ? 600 : 400,
          marginBottom: 3,
        }}>
          {l.text}
        </div>
      ))}
    </div>
  )
}
