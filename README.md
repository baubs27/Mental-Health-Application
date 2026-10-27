# Mental Health Skills App

IST 402 — Assignment 3

## Purpose and scope

A local coursework prototype for practicing one short skill, STOP. A person can
move through the four reviewed steps, ask an optional question about the skill,
leave at any point, review saved local sessions, or open static crisis-support
information. The app is intended only for fictional scenarios; it is not
therapy, diagnosis, medical advice, crisis monitoring, or emergency support.

The guided practice works without a model response. When live text mode is
configured, FastAPI sends the question and a bounded recent conversation to the
configured OpenAI Responses API model. The browser never receives the API key.
A deterministic demo and a forced-failure mode support offline verification.
The optional voice/WebRTC coursework increment remains separate from text
practice and SQLite conversation history.

## Implemented for Part 3.2

- Vue interface for the sequential STOP exercise, measured elapsed time,
  optional model Q&A, early exit, history, and independent support route.
- FastAPI routes that own model calls, request validation, and SQLite access.
- SQLite conversations, skill sessions, and messages. Actual assistant replies
  are saved; failed user requests are marked failed and do not invent a reply.
- Secret configuration through `backend/.env`; this file is ignored by Git.
- Focused frontend and backend tests, production build, browser walkthrough, and
  read-only SQLite inspection recorded in `docs/verification.md`.

## Design rationale and open work

`docs/report.md` records the Part 3.1 proposal and its links to the supplied
R/D findings. It describes intended timing, personalization, user control, and
unresolved questions. The current build deliberately implements a smaller
vertical slice. It does not yet implement pause/skip controls, editable
personalization, feedback, history deletion, retention settings, crisis
localization, or the proposed RAG query-planning workflow. These are open
product and design decisions; the app does not infer emotion or diagnosis.

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

SQLite tables are `conversations`, `skill_sessions`, and `messages`. The model
has no direct database access. The current prototype uses anonymous local
session IDs; it has no account system or synchronization between devices.

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
