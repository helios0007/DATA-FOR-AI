# Passive Design Advisor — Barcelona 2025

A web application that analyses an IFC building model and recommends passive cooling strategies for Mediterranean climates. Upload a building, place it on the map, set its orientation, and get a ranked set of design interventions backed by a knowledge graph and Claude AI.

For a full technical specification and pipeline see [PASSIVE_DESIGN_ADVISOR_SPEC.md](PASSIVE_DESIGN_ADVISOR_SPEC.md). To see the app in action watch [Demo.mp4](Demo.mp4).

---

## What it does

1. **Parse IFC** — extracts facade geometry, orientation, floor area, and construction mass from an IFC file
2. **Enrich site context** — fetches solar irradiance, wind data, sky view factor, and thermal comfort zone for the chosen location in Barcelona
3. **Thermal diagnosis** — estimates overheating risk using a proxy Overheating Degree Hours (ODH) calculation
4. **Strategy scoring** — ranks five passive strategies (shading, cross-ventilation, thermal mass, night purge, green roof) using a Multi-Attribute Utility Theory (MAUT) model
5. **LLM recommendations** — generates specific, geometric design recommendations per strategy using Claude, grounded in a knowledge graph of literature and standards
6. **Chat** — ask follow-up questions about the results

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | backend |
| Node.js | 18+ | frontend |
| Anthropic API key | — | get one at [console.anthropic.com](https://console.anthropic.com) |

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd passive-design-advisor
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Mac / Linux:** `source .venv/bin/activate`

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the API key

Copy the example env file and add your Anthropic API key:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder:

```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
```

> **Important — Windows gotcha:** Do NOT set `ANTHROPIC_API_KEY` as a Windows system or user environment variable. If it is set there, it will override `.env` and cause 401 errors. Check with:
> ```powershell
> [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
> [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "Machine")
> ```
> If either prints a key, remove it:
> ```powershell
> [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")
> [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "Machine")
> ```

### 5. Build the knowledge graph

```bash
python scripts/build_graph.py
```

This writes `graph/strategy_graph.json` — the structured knowledge base used for LLM context retrieval.

### 6. (Optional) Build the RAG vector store

```bash
python scripts/build_rag.py
```

This indexes 221 literature chunks into a local ChromaDB store at `graph/chroma_db/`. The app works without this step but LLM recommendations will lack literature references.

### 7. Install frontend dependencies

```bash
cd frontend
npm install
```

Copy the web-ifc WASM files into `public/` so the IFC viewer can load them:

```bash
cp node_modules/web-ifc/web-ifc.wasm public/
cp node_modules/web-ifc/web-ifc-mt.wasm public/
```

---

## Running the app

Open **two terminals** from the project root.

**Terminal 1 — backend:**

```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Open the URL that Vite prints (usually **http://localhost:5173**) in your browser.

> If ports 5173/5174 are already in use, Vite will pick the next available port and print it. Always use the URL Vite prints, not a hardcoded one.

---

## Workflow

1. **Upload IFC** — click "Upload IFC" in the left sidebar and select a `.ifc` file
2. **Set site location** — draw a rectangle on the map; the building snaps to its centre. Or click anywhere on the map
3. **Orient the building** — use the rotation slider or the preset buttons (0°, 45°, 90°…). The building footprint on the map rotates in real time. The N/S/E/W compass labels show geographic cardinal directions
4. **Run analysis** — click "▶ Run Analysis". Check "Skip LLM report" for a faster result without text recommendations
5. **Read results** — the right panel shows the thermal diagnosis, ranked strategies, and LLM-generated recommendations
6. **Chat** — switch to the Chat tab to ask questions about the analysis

---

## Project structure

```
passive-design-advisor/
├── app/                    FastAPI backend
│   ├── main.py             app entry point, CORS, routes
│   ├── models.py           Pydantic request/response schemas
│   ├── session.py          in-memory session store
│   └── routes/
│       ├── ifc.py          IFC upload + file serving
│       ├── analysis.py     full pipeline (stages 2–5)
│       ├── chat.py         streaming chat endpoint
│       └── graph.py        knowledge graph endpoint
├── src/                    analysis pipeline
│   ├── ifc_parser.py       Stage 1 — IFC → BuildingFeatures
│   ├── context_enricher.py Stage 2 — site context (solar, wind, SVF)
│   ├── thermal_diagnosis.py Stage 3 — overheating risk
│   ├── strategy_scorer.py  Stage 4 — MAUT strategy ranking
│   └── recommender.py      Stage 5 — LLM recommendations + GraphRAG
├── scripts/
│   ├── build_graph.py      builds graph/strategy_graph.json
│   └── build_rag.py        indexes literature into ChromaDB
├── graph/
│   ├── strategy_graph.json knowledge graph (committed)
│   └── chroma_db/          vector store (generated, not committed)
├── frontend/               React + Vite SPA
│   ├── src/
│   │   ├── App.jsx         main layout and workflow state
│   │   └── components/
│   │       ├── IFCViewer.jsx   3D model viewer (web-ifc + Three.js)
│   │       ├── MapPanel.jsx    Leaflet map with draw tools
│   │       ├── ResultsPanel.jsx diagnosis + strategy cards
│   │       ├── ChatPanel.jsx   streaming chat UI
│   │       └── GraphModal.jsx  interactive knowledge graph viewer
│   └── public/
│       ├── web-ifc.wasm    IFC parser WASM (copy from node_modules)
│       └── web-ifc-mt.wasm IFC parser WASM multithreaded
├── .env                    your secrets (never commit this)
├── .env.example            template
└── requirements.txt        Python dependencies
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Black screen on load | Stale Vite cache | Delete `frontend/node_modules/.vite` and restart `npm run dev` |
| Map not visible | CSS load order issue | Ensure Leaflet CSS is imported in `main.jsx`, not in the component |
| `LLM unavailable: 401` | Wrong or revoked API key | Check `.env` has the correct key; check for Windows system env var conflict (see Setup §4) |
| `Building has no exterior facades` | IFC file uses unusual wall types | The app falls back to synthetic facades automatically; re-run analysis |
| Surrounding buildings show 429 | Overpass API rate limit | Wait a minute and reload the map; this doesn't affect the analysis |
| IFC viewer shows nothing | WASM files missing from `public/` | Copy `.wasm` files from `node_modules/web-ifc/` to `frontend/public/` |
