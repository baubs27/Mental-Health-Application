# Live Audio increment

## Scope

This increment adds a small Vue chat shell because the Assignment 3 starter did
not contain the existing Vue/FastAPI chat assumed by the activity. It uses the
STOP skill selected in `docs/report.md` and the accessibility principles already
listed in `README.md`. This voice increment itself does not persist audio/transcripts or implement the complete timed STOP interaction. The later Part 3.2 app has a separate STOP text exercise, SQLite session/message history, and text-model path; see `docs/design-pipeline.md` and `docs/verification.md`. Live Audio remains optional and separate.

The prototype is for fictional coursework scenarios. It does not diagnose,
provide therapy or treatment, give medical advice, monitor people, or provide
emergency support.

## Responsibilities and request flow

```text
Vue (explicit Start + microphone permission)
  ├─ getUserMedia({ audio: true, video: false })
  ├─ RTCPeerConnection + oai-events channel; create offer and gather ICE
  └─ POST /api/voice/sessions { sdp_offer }
        ↓ ordinary HTTP
FastAPI (checks offer, reads backend-only .env, sets model/prompts/policy)
  └─ POST https://api.openai.com/v1/live/sessions
        ↓ SDP answer + validated session ID
Vue applies answer; WebRTC carries microphone and assistant audio directly
  ├─ data channel carries session.started / session.closed / error
  └─ Live delegates detailed in-scope work to its Responses backend
```

Vue owns user-initiated media permission, the visible lifecycle, microphone
mute, the remote audio element, and releasing browser resources. FastAPI owns
the API key, both models, both prompt layers, tool policy, SDP limits, provider
timeout, validation, and a server-side hangup fallback for a late result. FastAPI
does not relay WebRTC audio packets. The client data channel can send only
`session.close`; it cannot change model or prompt configuration. The server
allowlist includes only lifecycle/error events needed by this interface.

## Model roles and prompts

- `gpt-live-1` handles listening, speaking, turn-taking, interruptions, and
  short conversational replies.
- `VOICE_BACKEND_MODEL` (default `gpt-6-luna`) handles delegated Responses work
  when reviewed app knowledge or careful reasoning is needed. It does not
  receive a separate copy of the microphone stream and is not invoked for every
  ordinary conversational turn.
- The Live prompt is `LIVE_INSTRUCTIONS` in `backend/prompts.py`.
- The delegated prompt is `DELEGATED_INSTRUCTIONS` in `backend/prompts.py`.

Both prompts are included in the session request made by FastAPI. The Responses
backend receives no tools in this increment. Its instructions stay within the
reviewed STOP steps, distinguish self-report from interpretation, require
permission before suggesting an activity, acknowledge missing context, and
preserve the app-controlled crisis route.

The session uses `store: false` and the app does not save voice audio or
transcripts. `store: false` controls whether the session is available for API
retrieval/forking; it is not a general statement about provider retention.
Provider data handling remains subject to the configured API account's terms
and controls. No SQLite database or voice-history record is created here.

## Request and failure behavior

| Route | Input | Success | Failure |
| --- | --- | --- | --- |
| `GET /api/voice/config` | None | `{ configured, max_session_seconds }`; no model/key disclosed | Invalid duration configuration fails closed |
| `POST /api/voice/sessions` | JSON with `sdp_offer` only, maximum 64 KiB | `{ session_id, sdp_answer, max_session_seconds }` | 413 for oversize, 422 for unknown/missing fields, 503 if key missing, sanitized 502/504 for provider failure |
| `POST /api/voice/sessions/{id}/hangup` | Validated opaque session ID | Empty 204 response | Sanitized 400/502/503; does not accept a provider URL |
| `POST /api/chat` | `{ message }`, maximum 1,000 characters | Fixed reviewed STOP explanation | Validation error; frontend keeps its local fallback if the backend is unavailable |

Session creation uses a 15-second HTTP timeout and no automatic retry. The API
key is read only by FastAPI from `backend/.env` or the process environment. The
browser cannot submit a model, prompt, API key, tools, or session policy. Errors
returned to the browser do not contain provider bodies, key material, or SDP.

## Lifecycle and cleanup

`idle → permission → connecting → active ↔ muted → closing → closed`; permission
denial, setup failure, provider errors, and startup timeout lead to `error`, with
text chat still available. Active status is not shown until `session.started`.
The `oai-events` data channel is created and its listener attached before the
offer is created. ICE gathering completes before the offer is sent.

Mute disables only microphone tracks; assistant playback and the session remain
active. End stops microphone tracks immediately, sends `session.close` when the
channel is open, waits up to 1.2 seconds for `session.closed`, then closes the
audio element, data channel, and peer connection. If no close event arrives, the
backend hangup route is used when a session ID is known; the UI reports that
provider finalization was not confirmed. A late session-creation response after
End is sent to the backend hangup route and cannot restore an old active state.
Duplicate Start and End are guarded. Cleanup runs on component unmount, page
exit, the configured duration limit (maximum 300 seconds), and before the
independent crisis-support panel opens. An autoplay block presents an
`Enable assistant audio` button that retries playback after a user gesture.

## Mock checks and manual steps

The focused frontend mocks are in `frontend/test/voice-controller.test.js`; the
FastAPI provider mocks are in `backend/tests/test_voice_api.py`. The checks cover
missing configuration, disallowed browser settings, oversized SDP, provider
failure, malformed provider responses, duplicate Start, repeated End, late
results, microphone denial, Mute versus End, duration cleanup, and text chat
remaining available. They do not contact the provider.

After dependencies are installed and `backend/.env` contains a valid key, use
these manual steps for one conversation under 60 seconds:

1. Start FastAPI and Vite, open the local app, and keep the text chat visible.
2. Select **Start voice** and allow microphone access. Confirm the status changes
   from permission to connecting and only then to active.
3. Use a fictional scenario, for example: “I had a stressful group project
   conversation. Can you explain the STOP steps?” Pause, interrupt the reply,
   and change direction once. Compare turn-taking, interruption, tone,
   validation, and boundaries with the public GPT-Live baseline described in the
   class activity.
4. Select **Mute microphone**, confirm the status changes to muted and assistant
   playback remains available, then select **Unmute microphone**.
5. Select **End voice**. Confirm the microphone indicator is released, the
   status becomes closed (or reports unconfirmed provider finalization), and
   text chat still works.
6. Re-run after denying microphone permission; confirm voice shows an error and
   text chat remains usable. Open Crisis support during an active session and
   confirm the app ends voice before showing its independent static information.

Do not start a live provider call automatically. Creating a WebRTC session may
incur an initialization charge; check the [current WebRTC guide](https://developers.openai.com/api/docs/guides/voice-webrtc)
and your account before a classroom call. The activity says to keep it under 60
seconds. Current GPT-Live request shape, delegation, prompt behavior, and
session-close guidance were checked against the [create-session reference](https://developers.openai.com/api/reference/resources/live/methods/create),
[prompting guide](https://developers.openai.com/api/docs/guides/live-prompting),
[delegation guide](https://developers.openai.com/api/docs/guides/live-delegation),
and [session management guide](https://developers.openai.com/api/docs/guides/live-conversations)
on October 22, 2026. This local code has not yet been exercised against a live
provider account.

## Verification status

- The nine frontend lifecycle mocks passed with Node's built-in test runner.
- All sixteen FastAPI API tests passed with pytest. The tests use
  mocked provider responses and do not contact OpenAI.
- The Vite production build passed. JavaScript syntax checks and Python syntax
  compilation also passed.
- Local dependencies are installed under `frontend/node_modules` and
  `backend/.venv`; neither directory is intended for Git.
- Microphone permission, real SDP negotiation, interruption, provider closure,
  and manual comparison remain unverified until the local dependencies and an
  API key are configured.
