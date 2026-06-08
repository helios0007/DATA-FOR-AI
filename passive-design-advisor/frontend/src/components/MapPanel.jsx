import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet-draw'

if (typeof window !== 'undefined') window.L = L

export default function MapPanel({ siteLat, siteLon, onSiteChange, building, rotationDeg }) {
  const containerRef = useRef(null)
  const mapRef       = useRef(null)
  const markerRef    = useRef(null)
  const footprintRef = useRef(null)
  const compassRef   = useRef([])
  const bldgsRef     = useRef(null)

  // ── Init map once ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return

    const map = L.map(containerRef.current, { zoomControl: true })
      .setView([siteLat || 41.3851, siteLon || 2.1734], 16)
    mapRef.current = map

    // Voyager tiles — readable, balanced light style
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap contributors © CARTO',
      subdomains: 'abcd',
      maxZoom: 20,
    }).addTo(map)

    const bldgs = L.layerGroup().addTo(map)
    bldgsRef.current = bldgs

    if (L.Control && L.Control.Draw) {
      const drawn = new L.FeatureGroup().addTo(map)
      const ctrl  = new L.Control.Draw({
        draw: {
          rectangle: {
            shapeOptions: { color: '#7c6af7', weight: 2, fillOpacity: 0.08 },
            showArea: false,
          },
          polyline: false, polygon: false, circle: false,
          marker: false, circlemarker: false,
        },
        edit: { featureGroup: drawn },
      })
      map.addControl(ctrl)

      map.on(L.Draw.Event.CREATED, e => {
        drawn.clearLayers()
        drawn.addLayer(e.layer)
        const c = e.layer.getBounds().getCenter()
        onSiteChange(c.lat, c.lng)
      })
    }

    map.on('click', e => onSiteChange(e.latlng.lat, e.latlng.lng))
    requestAnimationFrame(() => map.invalidateSize())

    const ro = new ResizeObserver(() => {
      if (mapRef.current) mapRef.current.invalidateSize()
    })
    ro.observe(containerRef.current)

    return () => ro.disconnect()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Marker + surrounding buildings when site changes ──────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || siteLat == null || siteLon == null) return

    markerRef.current?.remove()
    markerRef.current = L.circleMarker([siteLat, siteLon], {
      radius: 7, color: '#7c6af7', fillColor: '#7c6af7', fillOpacity: 0.85, weight: 2,
    }).bindTooltip('Site', { permanent: false }).addTo(map)

    map.setView([siteLat, siteLon], map.getZoom())
    fetchSurroundingBuildings(siteLat, siteLon, bldgsRef.current)
    updateFootprint(map, building, siteLat, siteLon, rotationDeg, footprintRef)
    updateCompass(map, building, siteLat, siteLon, compassRef)
  }, [siteLat, siteLon]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Footprint + compass on rotation / building change ─────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || siteLat == null || siteLon == null) return
    updateFootprint(map, building, siteLat, siteLon, rotationDeg, footprintRef)
    updateCompass(map, building, siteLat, siteLon, compassRef)
  }, [rotationDeg, building]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function updateFootprint(map, building, lat, lon, rotDeg, footprintRef) {
  footprintRef.current?.remove()
  if (!building) return

  const d   = (building.building_depth_m || 14) * 0.000009
  const w   = (building.building_width_m || 9)  * 0.000009
  const rad = ((rotDeg || 0) * Math.PI) / 180
  const cos = Math.cos(rad)
  const sin = Math.sin(rad)

  const corners  = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]
  const latlngs  = corners.map(([x, y]) => [
    lat + x * cos - y * sin,
    lon + x * sin + y * cos,
  ])

  footprintRef.current = L.polygon(latlngs, {
    color: '#7c6af7', fillColor: '#7c6af7', fillOpacity: 0.22, weight: 2,
  }).bindTooltip('Your building', { sticky: true }).addTo(map)
}

function updateCompass(map, building, lat, lon, compassRef) {
  compassRef.current.forEach(m => m.remove())
  compassRef.current = []
  if (!building || lat == null) return

  // Place N/S/E/W labels at fixed geographic cardinal offsets from the site centre.
  // The building footprint rotates relative to them so the user can see which face is north.
  const off  = 0.00026   // ~29 m — well outside any typical building footprint
  const offE = off * 1.32 // compensate for lon degrees being shorter at ~41 °N

  const dirs = [
    { label: 'N', dlat:  off,  dlon: 0    },
    { label: 'S', dlat: -off,  dlon: 0    },
    { label: 'E', dlat:  0,    dlon: offE },
    { label: 'W', dlat:  0,    dlon: -offE },
  ]

  compassRef.current = dirs.map(({ label, dlat, dlon }) => {
    const icon = L.divIcon({
      className: '',
      html: `<div style="
        width:22px;height:22px;border-radius:50%;
        background:rgba(124,106,247,0.92);
        display:flex;align-items:center;justify-content:center;
        font-size:11px;font-weight:700;color:#fff;
        border:1.5px solid rgba(255,255,255,0.55);
        box-shadow:0 1px 5px rgba(0,0,0,.35);
        pointer-events:none;
      ">${label}</div>`,
      iconSize:   [22, 22],
      iconAnchor: [11, 11],
    })
    return L.marker([lat + dlat, lon + dlon], { icon, interactive: false }).addTo(map)
  })
}

async function fetchSurroundingBuildings(lat, lon, layerGroup) {
  if (!layerGroup) return
  layerGroup.clearLayers()

  const q = `[out:json][timeout:15];(way["building"](around:300,${lat},${lon}););out geom;`
  try {
    const res  = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body:   'data=' + encodeURIComponent(q),
    })
    if (!res.ok) return
    const json = await res.json()
    for (const el of json.elements) {
      if (el.type !== 'way' || !el.geometry?.length) continue
      L.polygon(el.geometry.map(n => [n.lat, n.lon]), {
        color: '#7c6af7', fillColor: '#9b8dff', fillOpacity: 0.18, weight: 1,
      }).addTo(layerGroup)
    }
  } catch (_) { /* Overpass may be unavailable */ }
}
