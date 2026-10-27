# Current handoff

## State

Part 3.2 STOP vertical slice is implemented in this folder. Vue and FastAPI run
locally; local live text mode is configured through ignored `backend/.env`.
SQLite evidence and manual browser notes are in `docs/verification.md`.
Architecture, scope, and open design questions are in `docs/design-pipeline.md`
and `docs/report.md`.

## Safety and privacy

Never copy `backend/.env` or `data/app.sqlite3` to GitHub. Both are ignored.
The key was provided in chat and should be rotated after use. Do not include it
in code, notes, logs, or browser artifacts. App scope is fictional coursework,
not therapy or a monitored service.

## Next actions

1. Run frontend tests/build and backend pytest after any implementation change.
2. Inspect `git status` and the staged file list; exclude credentials, runtime
   SQLite data, dependency folders, and build output.
3. Upload the Part 3.2 source/docs to the already-authorized GitHub repository.
4. If continuing after Part 3.2, resolve open design questions before claiming
   the broader proposal is implemented; pause/skip/personalization/RAG remain
   unfinished.
