import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// Module-level singleton so WASM initialises only once per page load
let _ifcApi = null
let _initPromise = null

async function getIfcApi() {
  if (_ifcApi) return _ifcApi
  if (_initPromise) return _initPromise
  _initPromise = (async () => {
    const mod = await import('web-ifc')
    const IfcAPI = mod.IfcAPI ?? mod.default?.IfcAPI
    const api = new IfcAPI()
    api.SetWasmPath('/')        // web-ifc.wasm is in frontend/public/
    await api.Init()
    _ifcApi = api
    return api
  })()
  return _initPromise
}

// ── Highlight material helpers ────────────────────────────────────────────────

function clearHighlight(group) {
  group.traverse(o => {
    if (o.isMesh && o.userData.origMaterial) {
      o.material.dispose()
      o.material = o.userData.origMaterial
      delete o.userData.origMaterial
    }
  })
}

// Highlights the meshes for the given GlobalIds, ghosting all others.
// Returns the number of ids that matched geometry.
function applyHighlight(group, idMap, ids) {
  const targets = new Set()
  let matched = 0
  for (const gid of ids) {
    const meshes = idMap.get(gid)
    if (meshes?.length) matched++
    for (const m of meshes ?? []) targets.add(m)
  }
  group.traverse(o => {
    if (!o.isMesh) return
    o.userData.origMaterial = o.material
    o.material = targets.has(o)
      ? new THREE.MeshLambertMaterial({
          color: 0xffa733, emissive: 0x9a5a00, side: THREE.DoubleSide,
        })
      : new THREE.MeshLambertMaterial({
          color: 0x3a3a46, transparent: true, opacity: 0.15,
          side: THREE.DoubleSide, depthWrite: false,
        })
  })
  return matched
}

/**
 * IFCViewer — renders an IFC file with web-ifc + Three.js.
 * Props:
 *   sessionId      – triggers model load when it changes
 *   rotationDeg    – Y-axis rotation of the model group
 *   highlightIds   – IFC GlobalIds to highlight (others ghost out); null = off
 *   highlightLabel – caption shown while a highlight is active
 * Ref API:
 *   capture(ids)   – returns a PNG data-URL of the current view with the given
 *                    GlobalIds highlighted (empty/null ids = plain view)
 */
const IFCViewer = forwardRef(function IFCViewer(
  { sessionId, rotationDeg, highlightIds, highlightLabel },
  ref,
) {
  const mountRef   = useRef(null)
  const rendRef    = useRef(null)
  const sceneRef   = useRef(null)
  const camRef     = useRef(null)
  const ctrlRef    = useRef(null)
  const groupRef   = useRef(null)
  const rafRef     = useRef(null)
  const idMapRef   = useRef(new Map())   // IFC GlobalId -> THREE.Mesh[]
  const activeIdsRef = useRef(null)      // currently prop-driven highlight

  const [phase, setPhase]   = useState('idle')
  const [errMsg, setErrMsg] = useState('')
  const [hitCount, setHitCount] = useState(0)

  // Snapshot API for report generation: render with a temporary highlight,
  // grab the canvas, then restore whatever highlight the UI had active.
  useImperativeHandle(ref, () => ({
    capture(ids) {
      const group = groupRef.current
      const renderer = rendRef.current
      if (!group || !renderer) return null
      clearHighlight(group)
      if (ids?.length) applyHighlight(group, idMapRef.current, ids)
      renderer.render(sceneRef.current, camRef.current)
      const url = renderer.domElement.toDataURL('image/png')
      clearHighlight(group)
      if (activeIdsRef.current?.length) {
        applyHighlight(group, idMapRef.current, activeIdsRef.current)
      }
      renderer.render(sceneRef.current, camRef.current)
      return url
    },
  }))

  // ── Three.js scene init ────────────────────────────────────────────────────
  useEffect(() => {
    const mount = mountRef.current
    if (!mount || rendRef.current) return

    const w = mount.clientWidth  || 800
    const h = mount.clientHeight || 500

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x18181f)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 50000)
    camera.position.set(30, 20, 30)
    camRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(w, h)
    mount.appendChild(renderer.domElement)
    rendRef.current = renderer

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.7))
    const sun = new THREE.DirectionalLight(0xfff5e0, 0.9)
    sun.position.set(60, 100, 60)
    scene.add(sun)
    const fill = new THREE.DirectionalLight(0xaaccff, 0.3)
    fill.position.set(-60, 30, -60)
    scene.add(fill)

    // Orbit controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    ctrlRef.current = controls

    // Render loop
    const tick = () => {
      rafRef.current = requestAnimationFrame(tick)
      controls.update()
      renderer.render(scene, camera)
    }
    tick()

    // Container resize
    const ro = new ResizeObserver(() => {
      const cw = mount.clientWidth
      const ch = mount.clientHeight
      camera.aspect = cw / ch
      camera.updateProjectionMatrix()
      renderer.setSize(cw, ch)
    })
    ro.observe(mount)

    return () => {
      cancelAnimationFrame(rafRef.current)
      ro.disconnect()
      controls.dispose()
      renderer.dispose()
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
      rendRef.current = null
      sceneRef.current = null
      camRef.current = null
      ctrlRef.current = null
    }
  }, [])

  // ── Load IFC when session changes ──────────────────────────────────────────
  useEffect(() => {
    if (!sessionId || !sceneRef.current) return
    let cancelled = false

    ;(async () => {
      setPhase('loading')
      setErrMsg('')

      // Remove previous model
      if (groupRef.current) {
        sceneRef.current.remove(groupRef.current)
        disposeGroup(groupRef.current)
        groupRef.current = null
      }
      idMapRef.current = new Map()

      try {
        const api = await getIfcApi()
        if (cancelled) return

        const res = await fetch(`/api/ifc/file/${sessionId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status} — failed to fetch IFC`)
        const buffer = new Uint8Array(await res.arrayBuffer())
        if (cancelled) return

        const modelId = api.OpenModel(buffer, { COORDINATE_TO_ORIGIN: true, USE_FAST_BOOLS: false })

        const group     = new THREE.Group()
        const allMeshes = api.LoadAllGeometry(modelId)
        const byExpress = new Map()   // expressID -> THREE.Mesh[]

        for (let i = 0; i < allMeshes.size(); i++) {
          const wMesh     = allMeshes.get(i)
          const geoms     = wMesh.geometries
          const expressID = wMesh.expressID

          for (let j = 0; j < geoms.size(); j++) {
            const pg       = geoms.get(j)
            const geomData = api.GetGeometry(modelId, pg.geometryExpressID)
            const rawVerts = api.GetVertexArray(geomData.GetVertexData(),  geomData.GetVertexDataSize())
            const rawIdx   = api.GetIndexArray (geomData.GetIndexData(),   geomData.GetIndexDataSize())

            // web-ifc interleaves position + normal: [x,y,z, nx,ny,nz, ...]
            const numV = rawVerts.length / 6
            const pos  = new Float32Array(numV * 3)
            const nrm  = new Float32Array(numV * 3)
            for (let k = 0; k < numV; k++) {
              pos[k*3]   = rawVerts[k*6];   pos[k*3+1] = rawVerts[k*6+1]; pos[k*3+2] = rawVerts[k*6+2]
              nrm[k*3]   = rawVerts[k*6+3]; nrm[k*3+1] = rawVerts[k*6+4]; nrm[k*3+2] = rawVerts[k*6+5]
            }

            const geo = new THREE.BufferGeometry()
            geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
            geo.setAttribute('normal',   new THREE.BufferAttribute(nrm, 3))
            geo.setIndex(new THREE.BufferAttribute(new Uint32Array(rawIdx), 1))
            geo.applyMatrix4(new THREE.Matrix4().fromArray(pg.flatTransformation))

            const { x: r, y: g, z: b, w: a } = pg.color
            const mat = new THREE.MeshLambertMaterial({
              color: new THREE.Color(r, g, b),
              transparent: a < 0.99,
              opacity: a,
              side: THREE.DoubleSide,
            })
            const mesh = new THREE.Mesh(geo, mat)
            group.add(mesh)
            if (!byExpress.has(expressID)) byExpress.set(expressID, [])
            byExpress.get(expressID).push(mesh)
            geomData.delete()
          }
        }

        // Map IFC GlobalIds (used by the analysis API) to meshes, so
        // strategy results can highlight their affected elements.
        const idMap = new Map()
        for (const [expressID, meshes] of byExpress) {
          try {
            const gid = api.GetLine(modelId, expressID)?.GlobalId?.value
            if (gid) idMap.set(gid, meshes)
          } catch { /* non-product line — skip */ }
        }
        idMapRef.current = idMap

        api.CloseModel(modelId)
        if (cancelled) { disposeGroup(group); return }

        // Compass rotation is clockwise from above; Three.js +Y rotation is
        // counterclockwise from above, so negate.
        group.rotation.y = -THREE.MathUtils.degToRad(rotationDeg || 0)
        sceneRef.current.add(group)
        groupRef.current = group

        // Auto-frame camera
        const box    = new THREE.Box3().setFromObject(group)
        const centre = box.getCenter(new THREE.Vector3())
        const size   = box.getSize(new THREE.Vector3())
        const d      = Math.max(size.x, size.y, size.z) * 1.6
        camRef.current.position.set(centre.x + d, centre.y + d * 0.7, centre.z + d)
        camRef.current.lookAt(centre)
        ctrlRef.current.target.copy(centre)
        ctrlRef.current.update()

        setPhase('ready')
      } catch (e) {
        if (!cancelled) { setPhase('error'); setErrMsg(e.message) }
      }
    })()

    return () => { cancelled = true }
  }, [sessionId])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Rotation ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (groupRef.current)
      groupRef.current.rotation.y = -THREE.MathUtils.degToRad(rotationDeg || 0)
  }, [rotationDeg])

  // ── Element highlighting (strategy "show on model") ───────────────────────
  useEffect(() => {
    activeIdsRef.current = highlightIds
    const group = groupRef.current
    if (!group || phase !== 'ready') return

    clearHighlight(group)
    if (!highlightIds?.length) { setHitCount(0); return }
    setHitCount(applyHighlight(group, idMapRef.current, highlightIds))
  }, [highlightIds, phase])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {phase === 'idle' && (
        <Overlay><span style={{ color: 'var(--text-dim)' }}>Upload an IFC file to view the building</span></Overlay>
      )}
      {phase === 'loading' && (
        <Overlay>
          <div className="spin-ring" />
          <span style={{ color: 'var(--text-dim)' }}>Parsing IFC… this may take 15–30 s</span>
        </Overlay>
      )}
      {phase === 'error' && (
        <div style={{
          position: 'absolute', bottom: 10, left: 10, right: 10,
          background: 'rgba(248,113,113,.15)', border: '1px solid var(--red)',
          borderRadius: 6, padding: '8px 12px', fontSize: 12, color: 'var(--red)',
        }}>
          {errMsg}
        </div>
      )}
      {phase === 'ready' && (
        <div style={{
          position: 'absolute', bottom: 8, left: 8, pointerEvents: 'none',
          background: 'rgba(0,0,0,.5)', borderRadius: 5,
          padding: '3px 9px', fontSize: 11, color: 'var(--text-dim)',
        }}>
          Orbit: left-drag · Zoom: scroll · Pan: right-drag
        </div>
      )}
      {phase === 'ready' && highlightIds?.length > 0 && (
        <div style={{
          position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)',
          pointerEvents: 'none', display: 'flex', alignItems: 'center', gap: 8,
          background: 'rgba(0,0,0,.65)', border: '1px solid rgba(255,167,51,.6)',
          borderRadius: 6, padding: '5px 12px', fontSize: 11, color: '#ffc46b',
        }}>
          <span style={{ width: 9, height: 9, borderRadius: 2, background: '#ffa733', flexShrink: 0 }} />
          {highlightLabel || 'Highlighted elements'}
          {' — '}
          {hitCount > 0
            ? `${hitCount} element${hitCount === 1 ? '' : 's'} on model`
            : 'no matching geometry found'}
        </div>
      )}
    </div>
  )
})

export default IFCViewer

function Overlay({ children }) {
  return (
    <div style={{
      position: 'absolute', inset: 0, background: '#18181f',
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      pointerEvents: 'none',
    }}>
      {children}
    </div>
  )
}

function disposeGroup(group) {
  group.traverse(o => {
    o.geometry?.dispose()
    if (o.material) {
      ;(Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose())
    }
  })
}
