"""Web chat for the Microfinance assistant (way 2 of 2: a ready-made AI app).

    uv run --extra app app.py            # http://127.0.0.1:8001

Needs the REST API running (MICROFINANCE_API_URL, default http://localhost:8080) and
ANTHROPIC_API_KEY. The page and the MCP server work without the key; only answers need it.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

import server
from agent import MODEL, Assistant, AssistantError

HERE = Path(__file__).resolve().parent
MAX_QUESTION = 2000
MAX_HISTORY = 20

assistant = Assistant()


async def index(_: Request):
    return FileResponse(HERE / "static" / "index.html")


async def health(_: Request):
    try:
        await server.api_get("/fin/getaepsbal")
        api_ok = True
    except Exception:
        api_ok = False
    return JSONResponse({"api": api_ok, "api_url": server.API_URL, "model": MODEL,
                         "llm_configured": bool(os.environ.get("ANTHROPIC_API_KEY"))})


async def chat(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "Request body must be JSON."}, status_code=400)
    question = str(body.get("question", "")).strip()
    if not question:
        return JSONResponse({"error": "Ask a question."}, status_code=400)
    if len(question) > MAX_QUESTION:
        return JSONResponse({"error": f"Questions are limited to {MAX_QUESTION} characters."}, status_code=400)
    history = body.get("history") or []
    if not isinstance(history, list):
        return JSONResponse({"error": "history must be a list."}, status_code=400)
    try:
        return JSONResponse(await assistant.answer(question, history[-MAX_HISTORY:]))
    except AssistantError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)


app = Starlette(routes=[
    Route("/", index),
    Route("/api/health", health),
    Route("/api/chat", chat, methods=["POST"]),
])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Microfinance assistant web app")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", "8001")))
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
