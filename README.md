# Data for AI Applications — IAAC 2025–2026

This repository contains coursework submissions and the main project deliverable for the Data for AI Applications seminar.

## The tool: Passive Design Advisor

The project is a web application that analyses an IFC building model and recommends passive cooling strategies for Mediterranean climates. It combines IFC geometry parsing, live site-context data (solar irradiance, wind, sky view factor), a MAUT strategy-scoring model, a knowledge graph, and Claude AI to generate specific, geometry-grounded design recommendations.

**Go here to run it:**

```
passive-design-advisor/
```

To see the app in action, watch the demo: [passive-design-advisor/Demo.mp4](passive-design-advisor/Demo.mp4).

Full setup and usage instructions are in [passive-design-advisor/README.md](passive-design-advisor/README.md).

### Quick start

```bash
# 1 — enter the project folder
cd passive-design-advisor

# 2 — create and activate a Python virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac / Linux:
source .venv/bin/activate

# 3 — install Python dependencies
pip install -r requirements.txt

# 4 — add your Anthropic API key
cp .env.example .env   # then edit .env and paste your key

# 5 — build the knowledge graph (one-time)
python scripts/build_graph.py

# 6 — install frontend dependencies
cd frontend && npm install
cp node_modules/web-ifc/web-ifc.wasm public/
cp node_modules/web-ifc/web-ifc-mt.wasm public/
cd ..

# 7 — run backend and frontend in two separate terminals
uvicorn app.main:app --reload --port 8000   # terminal 1
cd frontend && npm run dev                  # terminal 2
```

Open the URL Vite prints (usually **http://localhost:5173**).

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| Anthropic API key | [console.anthropic.com](https://console.anthropic.com) |

---

## Repository layout

```
passive-design-advisor/   ← the tool (start here)
data/                     course datasets
notebooks/                exploratory notebooks
scripts/                  utility scripts
src/                      shared source modules
outputs/                  generated outputs
docs/                     documentation
```
