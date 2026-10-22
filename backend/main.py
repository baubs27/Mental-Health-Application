"""FastAPI boundary for the minimal text fallback and GPT-Live WebRTC sessions."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from prompts import DELEGATED_INSTRUCTIONS, LIVE_INSTRUCTIONS

load_dotenv(Path(__file__).resolve().parent / ".env")

LIVE_API_URL = "https://api.openai.com/v1/live/sessions"
MAX_SDP_CHARACTERS = 64 * 1024
MAX_REQUEST_BYTES = MAX_SDP_CHARACTERS + 1024
PROVIDER_TIMEOUT_SECONDS = 15.0

app = FastAPI(title="Mental Health Skills App API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class VoiceOffer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sdp_offer: str = Field(min_length=1, max_length=MAX_SDP_CHARACTERS)


class TextMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1000)


def configured_duration() -> int:
    raw = os.getenv("VOICE_MAX_SESSION_SECONDS", "300")
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise RuntimeError("VOICE_MAX_SESSION_SECONDS must be an integer") from exc
    if not 30 <= seconds <= 300:
        raise RuntimeError("VOICE_MAX_SESSION_SECONDS must be between 30 and 300")
    return seconds


def voice_configuration() -> dict[str, Any]:
    return {
        "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "max_session_seconds": configured_duration(),
    }


@app.get("/api/voice/config")
async def get_voice_config() -> dict[str, Any]:
    """Report availability and the duration cap without exposing configuration."""
    return voice_configuration()


@app.post("/api/voice/sessions")
async def create_voice_session(request: Request) -> dict[str, Any]:
    """Exchange one bounded browser SDP offer for a server-configured Live answer."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                raise HTTPException(status_code=413, detail="SDP offer is too large")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid request length") from exc

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_REQUEST_BYTES:
            raise HTTPException(status_code=413, detail="SDP offer is too large")
    try:
        offer = VoiceOffer.model_validate_json(bytes(body))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid SDP offer request") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON request") from exc

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Voice is not configured")

    live_model = os.getenv("VOICE_LIVE_MODEL", "gpt-live-1").strip()
    backend_model = os.getenv("VOICE_BACKEND_MODEL", "gpt-6-luna").strip()
    payload = {
        "session": {
            "model": live_model,
            "instructions": LIVE_INSTRUCTIONS,
            "store": False,
            "delegation": {
                "type": "responses",
                "responses": {
                    "model": backend_model,
                    "instructions": DELEGATED_INSTRUCTIONS,
                    "tools": [],
                    "tool_choice": "none",
                    "max_output_tokens": 180,
                },
            },
            "client": {
                "data_channel": {
                    "allowed_client_events": ["session.close"],
                    "allowed_server_events": [
                        {"type": "session.started"},
                        {"type": "session.closed"},
                        {"type": "error"},
                    ],
                }
            },
        },
        "transport": {"type": "webrtc", "sdp": offer.sdp_offer},
    }

    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                LIVE_API_URL,
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Voice session setup timed out") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice session setup failed") from exc

    if response.status_code not in (200, 201):
        # Do not echo provider bodies, request headers, SDP, or keys to the browser.
        raise HTTPException(status_code=502, detail="Voice provider rejected session setup")
    try:
        result = response.json()
        session_id = result["session"]["id"]
        transport = result["transport"]
        answer_sdp = transport["sdp"]
        if (
            not isinstance(session_id, str)
            or not session_id
            or len(session_id) > 128
            or transport.get("type") != "webrtc"
            or not isinstance(answer_sdp, str)
            or not answer_sdp.strip()
            or len(answer_sdp) > MAX_SDP_CHARACTERS
        ):
            raise ValueError("Malformed session response")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Voice provider returned an invalid response") from exc

    return {
        "session_id": session_id,
        "sdp_answer": answer_sdp,
        "max_session_seconds": configured_duration(),
    }


@app.post("/api/voice/sessions/{session_id}/hangup", status_code=204, response_class=Response)
async def hangup_voice_session(session_id: str) -> Response:
    """Server-side cleanup for a session whose browser connection ended late."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id):
        raise HTTPException(status_code=400, detail="Invalid session identifier")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Voice is not configured")
    try:
        async with httpx.AsyncClient(timeout=PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{LIVE_API_URL}/{session_id}/hangup",
                headers={"Authorization": f"Bearer {key}"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Voice session cleanup failed") from exc
    if response.status_code not in (200, 204, 404):
        raise HTTPException(status_code=502, detail="Voice session cleanup failed")
    return Response(status_code=204)


@app.post("/api/chat")
async def text_chat(payload: TextMessage) -> dict[str, str]:
    """A reviewed, local explanation keeps text help usable without Live Audio."""
    normalized = payload.message.strip().casefold()
    if not normalized:
        raise HTTPException(status_code=422, detail="Enter a question")
    reply = (
        "STOP is a four-step skill: Stop; take a step back; observe what is happening "
        "inside and around you; then proceed mindfully. This coursework demo can "
        "explain the reviewed steps, but it does not interpret personal situations."
    )
    if "crisis" in normalized or "emergency" in normalized:
        reply = (
            "Crisis support is available from the separate support control. This demo "
            "does not monitor conversations or provide emergency support."
        )
    return {"reply": reply}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
