"""
FastAPI backend for the Passive Design Advisor.

Run from project root:
    uvicorn app.main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv(override=True)   # always use .env value, even if var is set in system env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routes import ifc, analysis, chat, graph

app = FastAPI(
    title="Passive Design Advisor API",
    description="Barcelona passive design strategy analysis for IFC building models.",
    version="1.0.0",
)

# Allow requests from the Vite dev server and same origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # dev only — restrict in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(ifc.router)
app.include_router(analysis.router)
app.include_router(chat.router)
app.include_router(graph.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve built frontend from frontend/dist/ in production
dist = Path("frontend/dist")
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
