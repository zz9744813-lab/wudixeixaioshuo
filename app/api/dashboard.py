"""Web Dashboard (spec §41).

Serves the self-contained operator console (no build step, no CDN) at ``/`` and
``/dashboard``. It is a *view* over the existing API: every widget talks to the
same governed endpoints a script would, so nothing on this page bypasses the
knowledge gate or the provenance chain.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_HTML_PATH = Path(__file__).resolve().parents[1] / "static" / "dashboard.html"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return _HTML_PATH.read_text(encoding="utf-8")
