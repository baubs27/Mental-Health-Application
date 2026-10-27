# Current handoff

## State

Part 3.2 STOP vertical slice is implemented in this folder and published to
the authorized GitHub repository on `main`. Vue and FastAPI run locally; live
text mode uses ignored `backend/.env`. SQLite evidence and browser verification
are in `docs/verification.md`. Architecture and remaining product questions
are in `docs/design-pipeline.md` and `docs/report.md`.

## Safety and privacy

Never copy `backend/.env` or `data/app.sqlite3` to GitHub. Both are ignored.
The API key was shared in chat; rotate it before further use. Do not include it
in code, notes, logs, or browser artifacts. This is fictional coursework, not
therapy or a monitored service.

## Remaining work

The Part 3.2 vertical slice is complete. If extending it, resolve the open
design questions first. Pause/skip controls, personalization settings, data
deletion/retention controls, crisis localization, optional self-report, and RAG
remain unfinished. Live voice was not tested against a provider.
