# Part 3.2 — Verification evidence

Verification date: October 26, 2026 (local Eastern time).

## Automated checks

- Backend: `python -m pytest --basetemp .pytest-run` — 16 tests passed.
- Frontend: `npm test` — 9 tests passed with Node's built-in test runner.
- Production bundle: `npm run build` — Vite production build completed.
- SQLite: opened with Python `sqlite3` using `mode=ro`; `PRAGMA integrity_check`
  returned `ok`.
- Secret hygiene: `git check-ignore` confirmed `backend/.env`,
  `data/app.sqlite3`, `backend/.venv`, and `frontend/node_modules` are ignored.

Mock tests do not contact the provider. A single brief live text question was
sent during the manual walkthrough because the configured key was explicitly
provided for this app. No Live Audio/WebRTC session was started.

## Browser walkthrough

The Vue app was opened at `http://127.0.0.1:5173/` with FastAPI on
`http://127.0.0.1:8000/`. The live provider response answered the fictional
question “What does Observe mean in the STOP skill? Give a brief explanation
without making assumptions about me.” The displayed answer explained noticing
internal and external experiences without judgment. The browser showed
`GPT-6 Luna`, and the actual response appeared in the saved session history.

The four sequential steps were advanced and completed. The completion view
reported 0:28; history showed the same measured duration and `completed` status.
A second session was left from step 1; history showed `left` and 0:04. Crisis
support was opened from the app and showed the static warning that it is
available without the model and that the demo is not monitored.

For failure verification, the local backend was restarted with
`MODEL_MODE=fail`. A fictional STOP question displayed “The model request
failed. Your message is saved without a reply.” The failed message remained in
the conversation, the app offered continue/leave controls, and the session was
left at 0:07. The live backend was then restarted in its configured mode.

## Read-only SQLite inspection

The database contains three linked conversations/sessions. This is the observed
session summary (IDs shortened for readability):

| Session | Status | Step reached | Duration | Messages |
| --- | --- | ---: | ---: | --- |
| `772e9aff` | completed | 4 | 28 seconds | user complete; assistant complete from `openai` |
| `081f9310` | left | 1 | 4 seconds | none |
| `99cb7ab9` | left | 1 | 7 seconds | user failed; no assistant row |

The user question and response were persisted under one conversation/session.
The failure row contains the submitted user message marked `failed`; it has no
assistant response. A read-only query of the tables, timestamps, duration,
message statuses/source, and integrity check matched what appeared in the
browser history. The database is local-only and excluded from the repository.

For read-only inspection, open `data/app.sqlite3` with Python's `sqlite3` module
using URI `file:data/app.sqlite3?mode=ro` and query the three tables. The local
integrity check was `ok`.

## Limitations

The current UI has sequential Continue controls but no pause or skip. It has no
accounts, explicit preference settings, data deletion/retention controls,
self-report, deployment, remote database, or RAG query-planning. Crisis wording
is generic and does not locate regional resources. The provider call was a
single fictional text question, not a reliability, clinical, or outcome
assessment. The optional voice feature was not manually tested against a live
provider. The user-provided API key was stored only in ignored `backend/.env`
and excluded from the repository; rotate it after the coursework demo because
it was shared in chat.
