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

from app.routes import ifc, analysis, chat, graph
from src.utils import resolve_path

app = FastAPI(
    title="Passive Design Advisor API",
    description="Barcelona passive design strategy analysis for IFC building models.",
    version="1.0.0",
)

# Allow requests from the Vite dev server; same-origin needs no CORS.
# (The dev frontend proxies /api through Vite, so this mostly matters for
# anyone hitting the API from the Vite origin directly.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
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
dist = resolve_path("frontend/dist")
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
