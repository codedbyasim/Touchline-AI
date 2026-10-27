"""FastAPI surface for Touchline AI.

Routes are mounted at /api and again without the prefix, because some
Vercel Python mounts strip /api before the app sees the path. The Vite
build is served from / with an SPA fallback when frontend/dist exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.agents.orchestrator import (
    health,
    run_analyze,
    run_auto_event,
    run_diagnose,
    run_recap,
    run_telemetry,
)
from backend.schemas import AnalyzeRequest, AutoEventRequest, DiagnoseRequest

app = FastAPI(title="Touchline AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@app.get("/health")
def get_health() -> dict:
    return health()


@app.post("/analyze-moment")
async def analyze_moment(body: AnalyzeRequest) -> dict:
    return await run_analyze(body.model_dump())


@app.post("/diagnose-struggle")
async def diagnose_struggle(body: DiagnoseRequest) -> dict:
    return await run_diagnose(body.model_dump())


@app.post("/auto-event")
def auto_event(body: AutoEventRequest) -> dict:
    return run_auto_event(body.segment_minute)


@app.get("/recap")
async def recap(
    persona: str = Query(default="CASUAL_FAN"),
    language: str = Query(default="en"),
    favorite_club: str = Query(default="NLR"),
) -> dict:
    if persona not in {"CASUAL_FAN", "TACTICO_ANALYST", "BROADCAST_STUDIO"}:
        persona = "CASUAL_FAN"
    if language not in {"en", "es", "ar"}:
        language = "en"
    if favorite_club not in {"NLR", "MCB"}:
        favorite_club = "NLR"
    return await run_recap(persona, language, favorite_club)


@app.get("/telemetry")
def telemetry(minute: int = Query(default=54, ge=1, le=90)) -> dict:
    return run_telemetry(minute)


@app.get("/live/stream")
async def live_stream(
    start_minute: int = Query(default=1, ge=1, le=90),
    speed: float = Query(default=1.0, ge=0.5, le=30.0),
) -> StreamingResponse:
    async def events():
        import asyncio

        # 1x is one match-minute per second. 10x is ten match-minutes per second.
        delay = 1.0 / float(speed)
        for minute in range(int(start_minute), 91):
            payload = run_telemetry(minute)
            slim = {
                "current_minute": payload["current_minute"],
                "scoreline": payload["scoreline"],
                "control_vs_chaos_index": payload["control_vs_chaos_index"],
                "rhythm_state": payload["rhythm_state"],
                "positions_22_players": payload["positions_22_players"],
                "tactical_anomalies": payload["tactical_anomalies"],
                "speed_and_pass_highlights": payload["speed_and_pass_highlights"],
                "badges": payload.get("badges") or [],
                "window_comparison": payload["window_comparison"],
            }
            yield f"data: {json.dumps(slim, ensure_ascii=False)}\n\n"
            if minute < 90:
                await asyncio.sleep(delay)
        yield "event: end\ndata: {\"done\": true}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _mount_api() -> None:
    # Re-include the same routes under /api. Defined after the handlers exist
    # by cloning the route table, which keeps one implementation.
    from fastapi.routing import APIRoute

    existing = [route for route in app.routes if isinstance(route, APIRoute)]
    for route in existing:
        app.add_api_route(
            "/api" + route.path,
            route.endpoint,
            methods=list(route.methods or []),
            response_model=route.response_model,
            tags=["api"],
        )


_mount_api()

# Literal call so the Vercel Python builder can see the static frontend.
# check_dir is false until `npm run build` has produced frontend/dist.
app.frontend("/", directory=str(DIST), fallback="index.html", check_dir=False)
