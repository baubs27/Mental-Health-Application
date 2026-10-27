"""FastAPI boundary for the minimal text fallback and GPT-Live WebRTC sessions."""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import storage
from prompts import DELEGATED_INSTRUCTIONS, LIVE_INSTRUCTIONS, SUPPORT_CHAT_INSTRUCTIONS

load_dotenv(Path(__file__).resolve().parent / ".env")

LIVE_API_URL = "https://api.openai.com/v1/live/sessions"
MAX_SDP_CHARACTERS = 64 * 1024
MAX_REQUEST_BYTES = MAX_SDP_CHARACTERS + 1024
PROVIDER_TIMEOUT_SECONDS = 15.0
TEXT_MODEL_TIMEOUT_SECONDS = 12.0
DB_PATH = storage.DEFAULT_DB_PATH
RESPONSES_API_URL = "https://api.openai.com/v1/responses"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    storage.initialize(DB_PATH)
    yield


app = FastAPI(title="Mental Health Skills App API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class VoiceOffer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sdp_offer: str = Field(min_length=1, max_length=MAX_SDP_CHARACTERS)


class StepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: int = Field(ge=1, le=4)


class FinishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "left"]


class SessionMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)


class MoodCheckin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mood: Literal["low", "steady", "good"]


class ProfilePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_skill: Literal["STOP", "paced_breathing"]
    animate_breathing: bool


def configured_duration() -> int:
    raw = os.getenv("VOICE_MAX_SESSION_SECONDS", "300")
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise RuntimeError("VOICE_MAX_SESSION_SECONDS must be an integer") from exc
    if not 30 <= seconds <= 300:
        raise RuntimeError("VOICE_MAX_SESSION_SECONDS must be between 30 and 300")
    return seconds


def model_mode() -> str:
    mode = os.getenv("MODEL_MODE", "demo").strip().casefold()
    return mode if mode in {"demo", "openai", "fail"} else "demo"


def demo_model_reply(message: str) -> str:
    """Deterministic, explicitly labeled conversational stand-in for no-key demos."""
    normalized = message.casefold()
    if "observe" in normalized and any(term in normalized for term in ("step", "mean", "stop")):
        return "The Observe step means noticing what is happening inside you and around you, without having to judge or fix it. You choose what, if anything, to do next."
    if "proceed" in normalized and any(term in normalized for term in ("step", "mean", "stop", "mindfully")):
        return "Proceed mindfully means choosing one next action that fits your priorities. It is fine to pause or choose a different action."
    if "step back" in normalized and any(term in normalized for term in ("stop", "mean", "step")):
        return "Take a step back creates a small pause before reacting. You might stop typing, unclench your hands, or simply wait a moment; choose what feels useful."
    if any(term in normalized for term in ("stop skill", "stop guide", "what is stop", "what does stop mean", "stop steps")):
        return "STOP is a short sequence: Stop; Take a step back; Observe inside and outside; Proceed mindfully. You can skip any part or leave whenever you want."
    if "breath" in normalized and any(term in normalized for term in ("stress", "stressed", "breathe", "breathing")):
        return "There is no single best way. If it feels okay, let your breath stay comfortable and natural; you do not need to force it or hold it. We can also talk about what is making this moment stressful."
    return "Thanks for sharing that. We can talk it through at your pace. Would you like to say more about what feels most important, or think together about one small next step?"


async def generate_model_reply(message: str, history: list[dict[str, str]]) -> tuple[str, str]:
    mode = model_mode()
    if mode == "fail":
        raise HTTPException(status_code=502, detail="The model request failed. Your message is saved without a reply.")
    if mode == "demo":
        return demo_model_reply(message), "demo"

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="The live model is not configured. Your message is saved without a reply.")
    payload = {
        "model": os.getenv("OPENAI_TEXT_MODEL", "gpt-6-luna").strip(),
        "instructions": SUPPORT_CHAT_INSTRUCTIONS,
        "input": history[-8:],
        "max_output_tokens": 180,
        "store": False,
    }
    try:
        async with httpx.AsyncClient(timeout=TEXT_MODEL_TIMEOUT_SECONDS) as client:
            response = await client.post(
                RESPONSES_API_URL,
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="The model request timed out. Your message is saved without a reply.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="The model request failed. Your message is saved without a reply.") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="The model request failed. Your message is saved without a reply.")
    try:
        data = response.json()
        pieces = [
            part["text"]
            for item in data.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text" and isinstance(part.get("text"), str)
        ]
        reply = "\n".join(pieces).strip()
        if not reply or len(reply) > 4000:
            raise ValueError("Missing or oversized model reply")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="The model returned an unusable response. Your message is saved without a reply.") from exc
    return reply, "openai"


def voice_configuration() -> dict[str, Any]:
    return {
        "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "max_session_seconds": configured_duration(),
    }


@app.get("/api/voice/config")
async def get_voice_config() -> dict[str, Any]:
    """Report availability and the duration cap without exposing configuration."""
    return voice_configuration()


@app.get("/api/app/config")
async def get_app_config() -> dict[str, Any]:
    return {
        "model_mode": model_mode(),
        "text_model": os.getenv("OPENAI_TEXT_MODEL", "gpt-6-luna").strip() if model_mode() == "openai" else None,
        "voice_configured": voice_configuration()["configured"],
    }


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


@app.post("/api/exercises", status_code=201)
async def create_exercise() -> dict[str, Any]:
    """Start and persist one anonymous STOP practice session."""
    return storage.begin_session(DB_PATH)


@app.patch("/api/exercises/{session_id}/step")
async def update_exercise_step(session_id: str, payload: StepUpdate) -> dict[str, Any]:
    session = storage.get_session(session_id, DB_PATH)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="Session has already ended")
    if payload.step not in {session["current_step"], session["current_step"] + 1}:
        raise HTTPException(status_code=409, detail="Complete the current step before moving ahead")
    storage.set_step(session_id, payload.step, DB_PATH)
    return {"session_id": session_id, "current_step": payload.step}


@app.post("/api/exercises/{session_id}/messages")
async def exercise_message(session_id: str, payload: SessionMessage) -> dict[str, str]:
    """Persist a user turn, request a supportive reply, and save only a real answer."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Enter a question")
    try:
        message_id = storage.add_user_message(session_id, message, DB_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="This exercise has ended") from exc
    rows = storage.get_model_history(session_id, DB_PATH)
    model_input = [{"role": row["role"], "content": row["content"]} for row in rows]
    try:
        reply, source = await generate_model_reply(message, model_input)
        storage.add_assistant_message(session_id, reply, source, DB_PATH)
    except HTTPException as exc:
        storage.mark_request_failed(message_id, DB_PATH)
        detail = exc.detail if isinstance(exc.detail, str) else "The model request failed. Your message is saved without a reply."
        raise HTTPException(
            status_code=exc.status_code,
            detail={"message": detail, "message_id": message_id},
        ) from exc
    except Exception as exc:
        storage.mark_request_failed(message_id, DB_PATH)
        raise HTTPException(
            status_code=502,
            detail={"message": "The model request failed. Your message is saved without a reply.", "message_id": message_id},
        ) from exc
    return {"message_id": message_id, "reply": reply, "model_source": source}


@app.get("/api/chat/sessions")
async def get_chat_sessions() -> dict[str, Any]:
    return {"sessions": storage.list_chat_sessions(10, DB_PATH)}


@app.post("/api/chat/sessions", status_code=201)
async def create_chat_session() -> dict[str, Any]:
    """Create an open-ended text conversation, independent of any skill practice."""
    return storage.begin_chat_session(DB_PATH)


@app.post("/api/chat/sessions/{session_id}/messages")
async def chat_message(session_id: str, payload: SessionMessage) -> dict[str, str]:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Write a message or choose a prompt")
    try:
        message_id = storage.add_chat_user_message(session_id, message, DB_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    rows = storage.get_chat_model_history(session_id, DB_PATH)
    model_input = [{"role": row["role"], "content": row["content"]} for row in rows]
    try:
        reply, source = await generate_model_reply(message, model_input)
        storage.add_chat_assistant_message(session_id, reply, source, DB_PATH)
    except HTTPException as exc:
        storage.mark_chat_request_failed(message_id, DB_PATH)
        detail = exc.detail if isinstance(exc.detail, str) else "The model request failed. Your message is saved without a reply."
        raise HTTPException(exc.status_code, detail={"message": detail, "message_id": message_id}) from exc
    except Exception as exc:
        storage.mark_chat_request_failed(message_id, DB_PATH)
        raise HTTPException(
            status_code=502,
            detail={"message": "The model request failed. Your message is saved without a reply.", "message_id": message_id},
        ) from exc
    return {"message_id": message_id, "reply": reply, "model_source": source}


@app.post("/api/exercises/{session_id}/finish")
async def finish_exercise(session_id: str, payload: FinishRequest) -> dict[str, Any]:
    """Record completion/early exit and the server-measured elapsed seconds."""
    session = storage.finish_session(session_id, payload.status, DB_PATH)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/api/history")
async def get_history() -> dict[str, Any]:
    return {
        "sessions": storage.list_history(50, DB_PATH),
        "checkins": storage.list_mood_checkins(100, DB_PATH),
        "chats": storage.list_chat_sessions(10, DB_PATH),
    }


@app.post("/api/breathing/sessions", status_code=201)
async def create_breathing_session() -> dict[str, Any]:
    """Create a local record before the 50-second paced breathing practice."""
    return storage.begin_breathing_session(DB_PATH)


@app.post("/api/breathing/sessions/{session_id}/finish")
async def finish_breathing_session(session_id: str, payload: FinishRequest) -> dict[str, Any]:
    session = storage.finish_breathing_session(session_id, payload.status, DB_PATH)
    if not session:
        raise HTTPException(status_code=404, detail="Breathing session not found")
    return session


@app.post("/api/mood-checkins", status_code=201)
async def create_mood_checkin(payload: MoodCheckin) -> dict[str, Any]:
    """Save an optional, coarse self-report. No model or mood inference is involved."""
    return storage.add_mood_checkin(payload.mood, DB_PATH)


@app.get("/api/mood-checkins")
async def get_mood_checkins() -> dict[str, Any]:
    return {"checkins": storage.list_mood_checkins(100, DB_PATH)}


@app.delete("/api/mood-checkins/{checkin_id}", status_code=204, response_class=Response)
async def remove_mood_checkin(checkin_id: str) -> Response:
    if not storage.delete_mood_checkin(checkin_id, DB_PATH):
        raise HTTPException(status_code=404, detail="Check-in not found")
    return Response(status_code=204)


@app.get("/api/profile")
async def get_profile() -> dict[str, Any]:
    return storage.get_profile_preferences(DB_PATH)


@app.put("/api/profile")
async def put_profile(payload: ProfilePreferences) -> dict[str, Any]:
    return storage.save_profile_preferences(payload.default_skill, payload.animate_breathing, DB_PATH)


@app.get("/api/support")
async def crisis_support() -> dict[str, str]:
    """Static support content that remains available when the model is down."""
    return {
        "title": "Crisis support",
        "message": "If you may be in immediate danger, contact your local emergency services or a trusted person now. This coursework demo is not monitored and cannot provide emergency support.",
        "us_988": "In the United States and territories, call or text 988, or use the official 988 Lifeline chat.",
        "us_988_url": "https://988lifeline.org/get-help/",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
