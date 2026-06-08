import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const API = 'http://localhost:8000'

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

/**
 * IFCViewer — renders an IFC file with web-ifc + Three.js.
 * Props:
 *   sessionId   – triggers model load when it changes
 *   rotationDeg – Y-axis rotation of the model group
 */
export default function IFCViewer({ sessionId, rotationDeg }) {
  const mountRef   = useRef(null)
  const rendRef    = useRef(null)
  const sceneRef   = useRef(null)
  const camRef     = useRef(null)
  const ctrlRef    = useRef(null)
  const groupRef   = useRef(null)
  const rafRef     = useRef(null)

  const [phase, setPhase]   = useState('idle')
  const [errMsg, setErrMsg] = useState('')

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

      try {
        const api = await getIfcApi()
        if (cancelled) return

        const res = await fetch(`${API}/api/ifc/file/${sessionId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status} — failed to fetch IFC`)
        const buffer = new Uint8Array(await res.arrayBuffer())
        if (cancelled) return

        const modelId = api.OpenModel(buffer, { COORDINATE_TO_ORIGIN: true, USE_FAST_BOOLS: false })

        const group     = new THREE.Group()
        const allMeshes = api.LoadAllGeometry(modelId)

        for (let i = 0; i < allMeshes.size(); i++) {
          const wMesh = allMeshes.get(i)
          const geoms = wMesh.geometries

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
            group.add(new THREE.Mesh(geo, mat))
            geomData.delete()
          }
        }

        api.CloseModel(modelId)
        if (cancelled) { disposeGroup(group); return }

        group.rotation.y = THREE.MathUtils.degToRad(rotationDeg || 0)
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
      groupRef.current.rotation.y = THREE.MathUtils.degToRad(rotationDeg || 0)
  }, [rotationDeg])

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
    </div>
  )
}

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
