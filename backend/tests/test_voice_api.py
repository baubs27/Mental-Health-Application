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
def client():
    return TestClient(main.app)


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


def test_text_chat_remains_available_without_voice_configuration(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/chat", json={"message": "What is STOP?"})
    assert response.status_code == 200
    assert "four-step skill" in response.json()["reply"]


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
