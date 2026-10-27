# Mental Health Skills App

IST 402 — Assignment 3

## Assignment submission index

**Repository:** [Mental Health Application](https://github.com/baubs27/Mental-Health-Application)

**Submitted application version:** [`e78148b271c0e2d263fe4c70ef44e82c8fada0d5`](https://github.com/baubs27/Mental-Health-Application/commit/e78148b271c0e2d263fe4c70ef44e82c8fada0d5) on `main`. This commit identifies the application version described below; subsequent commits update this submission index and its reports.

Upload one `report.md` file for each part. The reports and evidence currently in this repository are:

| Part | `report.md` to upload | Version commit | Design and verification evidence | Recording |
| --- | --- | --- | --- | --- |
| **3.1 — Design proposal** | [`docs/report.md`](docs/report.md) | [`93e06e613ef5ec53768c2d61caec3c305739fe50`](https://github.com/baubs27/Mental-Health-Application/commit/93e06e613ef5ec53768c2d61caec3c305739fe50) | [Design proposal and R/D rationale](docs/report.md); [implemented design map](docs/design-pipeline.md) | [Supplied expected-demo reference](docs/recordings/expected_demo.mov). This is a design reference, not a recording of this app. |
| **3.2 — Working application** | [`docs/part-3.2/report.md`](docs/part-3.2/report.md) | [`e78148b271c0e2d263fe4c70ef44e82c8fada0d5`](https://github.com/baubs27/Mental-Health-Application/commit/e78148b271c0e2d263fe4c70ef44e82c8fada0d5) | [Design and implementation notes](docs/design-pipeline.md); [verification evidence](docs/verification.md); [Live Audio notes](docs/voice-audio.md) | [Supplied expected-demo reference](docs/recordings/expected_demo.mov). No recording of the working app is committed yet. |

**What is complete:** Part 3.1 documents the proposed skill experience, model role, data, user control, and links to the research findings. Part 3.2 provides a Vue/FastAPI/SQLite coursework prototype with STOP, paced breathing, open-ended chat, saved local history, and a crisis route independent of the model.

**What the evidence shows:** The verification notes record a successful frontend build, browser walkthrough, deterministic chat reply, SQLite persistence/retrieval, and database integrity check. They also distinguish demo-mode checks from live-provider behavior.

**Still unresolved:** No app walkthrough recording is in the repository; live text/voice provider behavior is not verified; voice, data deletion/retention, and crisis-resource localization need further review. The app is a fictional coursework prototype, not a support or clinical service.

## Purpose and scope

A local coursework prototype for a small collection of optional skills. It
includes a 50-second paced-breathing practice, a four-step STOP practice,
optional self-reported mood check-ins, local history/profile controls, open-ended
text conversation, STOP explanations when requested, and optional WebRTC voice.
A persistent crisis route works without the model. The app is intended only for
fictional coursework scenarios;
it is not therapy, diagnosis, medical advice, crisis monitoring, or emergency
support.

The guided practice works without a model response. When live text mode is
configured, FastAPI sends the question and a bounded recent conversation to the
configured OpenAI Responses API model. The browser never receives the API key.
A deterministic demo and a forced-failure mode support offline verification.
The optional voice/WebRTC coursework increment remains separate from text
practice and SQLite conversation history.

## Current implementation

- Vue interface for STOP and paced breathing, measured elapsed time, optional
  visual pacing, early exit, self-reported check-ins, a monthly activity summary,
  editable local preferences, history, and independent crisis support.
- Main navigation for Home, Activities, Chat, History, Profile, and Crisis.
- Standalone, open-ended model chat with starter prompts and saved local
  conversations; STOP questions are answered when relevant rather than forcing
  every exchange into the STOP guide. Voice remains a separate opt-in path.
- FastAPI routes that own model calls, request validation, and SQLite access.
- SQLite conversations, STOP sessions, standalone chat sessions/messages,
  breathing sessions, coarse mood check-ins, and profile preferences. Actual
  assistant replies are saved; failed user requests are marked failed and do
  not invent a reply.
- Secret configuration through `backend/.env`; this file is ignored by Git.
- Focused frontend and backend tests, production build, browser walkthrough, and
  read-only SQLite inspection recorded in `docs/verification.md`.

## Design rationale and open work

`docs/report.md` records the Part 3.1 proposal and its links to the supplied
R/D findings. `docs/design-pipeline.md` maps the current multi-view experience
to those findings. The app does not infer mood or diagnosis. It excludes
screening questionnaires and scores because this coursework implementation has
no validated clinical instrument or scoring rules. Remaining work includes
reviewing practice wording and pacing, retention/deletion of session and chat
data, crisis localization, and the proposed RAG query-planning workflow.

Class principles to carry forward:

- Keep the guided skill within 90 seconds at its intended pace, with low reading
  and typing demands.
- Keep language readable, keyboard focus visible, contrast sufficient, layout
  usable on narrow screens, and motion optional.
- Make personalization understandable and changeable. Do not treat clicks or
  duration as evidence of emotional state.
- Explain how choices connect to class findings and make tradeoffs explicit.
- Keep support information independent of model responses.

## Architecture and data

- `frontend/`: Vue, JavaScript, HTML, and CSS. Calls the API over localhost.
- `backend/`: Python/FastAPI, prompt rules, provider adapter, validation, and
  all SQLite reads and writes.
- `data/app.sqlite3`: local runtime database (ignored by Git).
- `docs/`: Part 3.1 proposal, Part 3.2 system notes, and verification evidence.
- `prompts/`: reusable scoped instructions.
- `handoffs/`: current implementation state for the next work session.

SQLite tables are `conversations`, `skill_sessions`, `messages`,
`chat_sessions`, `chat_messages`, `breathing_sessions`, `mood_checkins`, and
`profile_preferences`. The model has
no direct database access. The prototype uses anonymous local session IDs; it
has no account system or synchronization between devices. Check-ins use only a
coarse user-selected value, are not used to personalize model responses, and can
be removed from History.

## Secrets

Put `OPENAI_API_KEY` only in `backend/.env`. That file is ignored by Git. Use
`backend/.env.example` for safe configuration names. Never put secrets in Vue,
`VITE_` variables, screenshots, documentation, API responses, or commits.
Because the development key was shared in this conversation, rotate it in the
provider dashboard before further use; it was shared in chat.

## Run locally

Backend, from `backend/`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Add OPENAI_API_KEY to backend/.env only if using live model mode.
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, from `frontend/`:

```powershell
npm install
npm run dev
```

Open the localhost URL printed by Vite. The API listens on `127.0.0.1:8000`.
To use the deterministic stand-in, set `MODEL_MODE=demo`; to exercise a
sanitized failure response, set `MODEL_MODE=fail` for the backend process.

Run checks with `npm test` and `npm run build` in `frontend/`, and
`python -m pytest` in `backend/`. Verification notes distinguish mocked tests
from the manual live provider request.

## Project structure

```text
Assignment 3/
|-- README.md
|-- AGENTS.md
|-- frontend/
|-- backend/
|-- data/
|-- docs/
|-- prompts/
`-- handoffs/
```
