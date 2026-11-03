"""Fifteen fictional, deterministic scenarios plus cross-case behavior contracts."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main


SCENARIOS = [
    ("01 greeting", "chat", "Hi there.", "Thanks for sharing"),
    ("02 stressful day", "chat", "I had a stressful day.", "at your pace"),
    ("03 STOP explanation", "chat", "What does Observe mean?", "noticing"),
    ("04 breathing question", "chat", "What is a comfortable way to breathe when stressed?", "There is no single best way"),
    ("05 talk through a choice", "chat", "Can you help me think through a situation?", "one small next step"),
    ("06 topic change", "chat", "Tell me something useful for organizing my afternoon.", "at your pace"),
    ("07 reflective preference", "reflective", "I just want to talk.", "listen without rushing"),
    ("08 practical preference", "practical", "I am stuck on a small task.", "one practical next step"),
    ("09 diagnosis limit", "chat", "Can you diagnose what disorder I have?", "can’t diagnose"),
    ("10 medication limit", "chat", "Should I change my medication dose?", "can’t give medical or medication advice"),
    ("11 immediate danger language", "chat", "I might hurt myself.", "separate Crisis support page"),
    ("12 blank message", "empty", "", "422"),
    ("13 over-limit message", "too_long", "x" * 2001, "422"),
    ("14 requested step skip", "step_skip", "", "409"),
    ("15 leave without finishing", "leave", "", "left"),
]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "app.sqlite3")
    monkeypatch.setenv("MODEL_MODE", "demo")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.mark.parametrize("case_id,action,user_input,expected", SCENARIOS, ids=[x[0] for x in SCENARIOS])
def test_fifteen_fictional_scenarios(client, case_id, action, user_input, expected, monkeypatch):
    if action in {"chat", "reflective", "practical", "empty", "too_long"}:
        if action in {"reflective", "practical"}:
            profile = client.get("/api/profile").json()
            profile.update(response_style=action, personalize_chat=True)
            assert client.put("/api/profile", json=profile).status_code == 200
        session = client.post("/api/chat/sessions").json()
        response = client.post(
            f"/api/chat/sessions/{session['session_id']}/messages",
            json={"message": user_input},
        )
        if action == "empty":
            assert response.status_code == 422
            assert str(response.status_code) == expected
            return
        if action == "too_long":
            assert response.status_code == 422
            assert str(response.status_code) == expected
            return
        assert response.status_code == 200, case_id
        assert expected in response.json()["reply"], case_id
        assert response.json()["model_source"] == "demo"
        return

    if action == "step_skip":
        session = client.post("/api/exercises").json()
        response = client.patch(f"/api/exercises/{session['session_id']}/step", json={"step": 3})
        assert response.status_code == 409
        assert str(response.status_code) == expected
        return

    if action == "leave":
        moments = iter([
            "2026-10-27T12:00:00.000Z",
            "2026-10-27T12:00:09.900Z",
        ])
        monkeypatch.setattr(main.storage, "utc_now", lambda: next(moments))
        session = client.post("/api/exercises").json()
        response = client.post(f"/api/exercises/{session['session_id']}/finish", json={"status": "left"})
        assert response.status_code == 200
        assert response.json()["status"] == expected
        assert response.json()["duration_seconds"] == 9
        return

    session = client.post("/api/chat/sessions").json()
    response = client.post(
        f"/api/chat/sessions/{session['session_id']}/messages",
        json={"message": user_input},
    )
    assert response.status_code == 200, case_id
    assert expected in response.json()["reply"], case_id
    assert response.json()["model_source"] == "demo"


def test_behavior_crisis_route_stays_available_after_model_failure(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "fail")
    response = client.get("/api/support")
    assert response.status_code == 200
    assert "emergency services" in response.json()["message"]
    assert response.json()["us_988_url"].startswith("https://")


def test_behavior_failed_model_turn_is_saved_without_a_fabricated_answer(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "fail")
    session = client.post("/api/chat/sessions").json()
    response = client.post(
        f"/api/chat/sessions/{session['session_id']}/messages",
        json={"message": "This is a fictional failed request."},
    )
    assert response.status_code == 502
    history = client.get("/api/chat/sessions").json()["sessions"][0]["messages"]
    assert [(row["role"], row["request_status"]) for row in history] == [("user", "failed")]


def test_behavior_profile_choice_overrides_history_and_model_context_excludes_checkins(client):
    breathing = client.post("/api/breathing/sessions").json()
    client.post(f"/api/breathing/sessions/{breathing['session_id']}/finish", json={"status": "completed"})
    preferences = client.get("/api/profile").json()
    preferences.update(default_skill="STOP", response_style="reflective", personalize_chat=True)
    assert client.put("/api/profile", json=preferences).json()["default_skill"] == "STOP"
    client.post("/api/mood-checkins", json={"mood": "low"})
    context = main.storage.get_personalization_context(main.DB_PATH)
    assert context == {
        "response_style": "reflective",
        "usual_practice": "STOP",
        "completed_practice_counts": {"STOP": 0, "paced_breathing": 1},
        "most_used_completed_practice": "paced_breathing",
        "last_completed_practice": "paced_breathing",
    }
    assert "mood" not in str(context)
    assert "content" not in context


def test_personalized_context_is_only_sent_when_enabled(client, monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "A mocked answer."}]}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return False
        async def post(self, _url, **kwargs):
            captured.update(kwargs["json"])
            return FakeResponse()

    monkeypatch.setenv("MODEL_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fictional-test-key")
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)
    client.post("/api/mood-checkins", json={"mood": "good"})
    prefs = client.get("/api/profile").json()
    prefs.update(response_style="practical", personalize_chat=False)
    client.put("/api/profile", json=prefs)
    chat = client.post("/api/chat/sessions").json()
    captured = {}
    response = client.post(f"/api/chat/sessions/{chat['session_id']}/messages", json={"message": "A fictional question"})
    assert response.status_code == 200
    assert "User-approved personalization" not in captured["instructions"]
    assert "mood" not in captured["instructions"]

    prefs.update(personalize_chat=True)
    client.put("/api/profile", json=prefs)
    captured.clear()
    response = client.post(f"/api/chat/sessions/{chat['session_id']}/messages", json={"message": "A second fictional question"})
    assert response.status_code == 200
    assert "preferred response style=practical" in captured["instructions"]
    assert "usual practice explicitly selected by user=paced_breathing" in captured["instructions"]
    assert "Check-in data" in captured["instructions"]
    assert "good" not in captured["instructions"]


def test_existing_profile_migration_preserves_choices_and_defaults_personalization_off(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    import sqlite3

    with sqlite3.connect(db_path) as db:
        db.execute(
            """CREATE TABLE profile_preferences (
                   profile_id TEXT PRIMARY KEY, default_skill TEXT NOT NULL,
                   animate_breathing INTEGER NOT NULL, updated_at TEXT NOT NULL
               )"""
        )
        db.execute(
            "INSERT INTO profile_preferences VALUES ('local-demo', 'STOP', 0, '2026-10-01T00:00:00Z')"
        )
    main.storage.initialize(db_path)
    profile = main.storage.get_profile_preferences(db_path)
    assert profile == {
        "default_skill": "STOP",
        "animate_breathing": False,
        "response_style": "balanced",
        "personalize_chat": False,
    }
