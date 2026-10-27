import json
import pytest
from fastapi.testclient import TestClient

import main


class FakeResponse:
    def __init__(self, status_code=201, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, response, capture):
        self.response = response
        self.capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.capture.update(url=url, **kwargs)
        return self.response


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "app.sqlite3")
    monkeypatch.setenv("MODEL_MODE", "demo")
    with TestClient(main.app) as test_client:
        yield test_client


def test_config_reports_only_configured_status_and_duration(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    monkeypatch.setenv("VOICE_MAX_SESSION_SECONDS", "180")
    result = client.get("/api/voice/config").json()
    assert result == {"configured": True, "max_session_seconds": 180}
    assert "secret-test-key" not in json.dumps(result)


def test_configured_duration_is_bounded(monkeypatch):
    monkeypatch.setenv("VOICE_MAX_SESSION_SECONDS", "301")
    with pytest.raises(RuntimeError):
        main.configured_duration()


def test_browser_cannot_select_provider_settings(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    response = client.post("/api/voice/sessions", json={"sdp_offer": "v=0", "model": "other"})
    assert response.status_code == 422


def test_missing_configuration_does_not_call_provider(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/voice/sessions", json={"sdp_offer": "v=0"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Voice is not configured"


def test_oversized_offer_is_rejected(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    response = client.post("/api/voice/sessions", json={"sdp_offer": "x" * (main.MAX_SDP_CHARACTERS + 1)})
    assert response.status_code in (413, 422)


def test_provider_receives_server_owned_configuration_and_returns_only_validated_fields(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("VOICE_LIVE_MODEL", "gpt-live-1")
    monkeypatch.setenv("VOICE_BACKEND_MODEL", "gpt-6-luna")
    capture = {}
    response_data = {"session": {"id": "live_abc"}, "transport": {"type": "webrtc", "sdp": "v=answer"}, "secret": "discard"}
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: FakeClient(FakeResponse(data=response_data), capture))
    response = client.post("/api/voice/sessions", json={"sdp_offer": "v=offer"})
    assert response.status_code == 200
    assert response.json() == {"session_id": "live_abc", "sdp_answer": "v=answer", "max_session_seconds": 300}
    assert capture["url"] == main.LIVE_API_URL
    assert capture["headers"]["Authorization"] == "Bearer test-key"
    sent = capture["json"]
    assert sent["transport"] == {"type": "webrtc", "sdp": "v=offer"}
    session = sent["session"]
    assert session["model"] == "gpt-live-1"
    assert session["store"] is False
    assert session["delegation"]["type"] == "responses"
    assert session["delegation"]["responses"]["model"] == "gpt-6-luna"
    assert session["delegation"]["responses"]["tools"] == []
    assert session["client"]["data_channel"]["allowed_client_events"] == ["session.close"]


def test_provider_failure_is_sanitized(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    capture = {}
    fake = FakeResponse(status_code=401, text="secret-key provider detail")
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: FakeClient(fake, capture))
    response = client.post("/api/voice/sessions", json={"sdp_offer": "v=offer"})
    assert response.status_code == 502
    assert "secret-key" not in response.text
    assert response.json()["detail"] == "Voice provider rejected session setup"


def test_malformed_provider_response_is_rejected(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: FakeClient(FakeResponse(data={"session": {"id": "live_x"}}), {}))
    response = client.post("/api/voice/sessions", json={"sdp_offer": "v=offer"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Voice provider returned an invalid response"


def test_demo_model_contribution_and_conversation_are_persisted(client):
    session = client.post("/api/exercises").json()
    assert session["status"] == "in_progress"
    response = client.post(
        f"/api/exercises/{session['session_id']}/messages",
        json={"message": "What does Observe mean?"},
    )
    assert response.status_code == 200
    assert response.json()["model_source"] == "demo"
    assert "noticing" in response.json()["reply"]
    history = client.get("/api/history").json()["sessions"][0]
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["model_source"] == "demo"


def test_model_failure_saves_user_message_without_fabricating_reply(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "fail")
    session = client.post("/api/exercises").json()
    response = client.post(
        f"/api/exercises/{session['session_id']}/messages",
        json={"message": "Please explain Observe"},
    )
    assert response.status_code == 502
    assert "saved without a reply" in response.json()["detail"]["message"]
    history = client.get("/api/history").json()["sessions"][0]
    assert len(history["messages"]) == 1
    assert history["messages"][0]["request_status"] == "failed"
    assert history["messages"][0]["role"] == "user"


def test_missing_live_model_configuration_fails_without_api_call(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    session = client.post("/api/exercises").json()
    response = client.post(
        f"/api/exercises/{session['session_id']}/messages",
        json={"message": "Explain the first step"},
    )
    assert response.status_code == 503
    history = client.get("/api/history").json()["sessions"][0]
    assert history["messages"][0]["request_status"] == "failed"
    assert len(history["messages"]) == 1


def test_step_order_is_checked_and_saved(client):
    session = client.post("/api/exercises").json()
    session_id = session["session_id"]
    skipped = client.patch(f"/api/exercises/{session_id}/step", json={"step": 3})
    assert skipped.status_code == 409
    advanced = client.patch(f"/api/exercises/{session_id}/step", json={"step": 2})
    assert advanced.status_code == 200
    assert client.get("/api/history").json()["sessions"][0]["current_step"] == 2


def test_early_exit_records_duration_and_transcript(client, monkeypatch):
    moments = iter([
        "2026-10-22T12:00:00.000Z",
        "2026-10-22T12:00:00.100Z",
        "2026-10-22T12:00:00.200Z",
        "2026-10-22T12:00:07.900Z",
    ])
    monkeypatch.setattr(main.storage, "utc_now", lambda: next(moments))
    session = client.post("/api/exercises").json()
    response = client.post(
        f"/api/exercises/{session['session_id']}/messages",
        json={"message": "I want to stop here"},
    )
    assert response.status_code == 200
    ended = client.post(f"/api/exercises/{session['session_id']}/finish", json={"status": "left"})
    assert ended.status_code == 200
    assert ended.json()["status"] == "left"
    assert ended.json()["duration_seconds"] == 7
    history = client.get("/api/history").json()["sessions"][0]
    assert history["duration_seconds"] == 7
    assert len(history["messages"]) == 2


def test_crisis_support_route_is_static_and_independent(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "fail")
    response = client.get("/api/support")
    assert response.status_code == 200
    assert "local emergency services" in response.json()["message"]


def test_hangup_rejects_invalid_session_identifier(client):
    response = client.post("/api/voice/sessions/bad%3Fid/hangup")
    assert response.status_code == 400


def test_hangup_uses_server_key_and_fixed_provider_host(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    capture = {}
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout: FakeClient(FakeResponse(status_code=204), capture))
    response = client.post("/api/voice/sessions/live_123/hangup")
    assert response.status_code == 204
    assert capture["url"] == f"{main.LIVE_API_URL}/live_123/hangup"
    assert capture["headers"]["Authorization"] == "Bearer test-key"
