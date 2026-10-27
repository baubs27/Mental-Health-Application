# Current handoff

## State

The local prototype includes paced breathing, STOP, optional mood check-ins,
monthly history summary, explicit profile preferences, standalone open-ended
text chat with starter prompts and locally saved recent conversations,
optional voice, and persistent crisis support. The Vue app is available on
`http://127.0.0.1:5173/` and FastAPI was refreshed on `http://127.0.0.1:8000/`.
The previous app increment is published to the user's Mental-Health-Application
repository on branch `main`; this open-chat update is being prepared.

Read `README.md`, `docs/design-pipeline.md`, and `docs/verification.md` before
continuing. The video is treated as a visual/feature reference. The screening
questionnaire and scores are intentionally excluded because no validated
instrument/scoring specification was supplied.

## Verification status

Frontend: 9 tests pass and Vite production build succeeds. The standalone chat
route created a synthetic conversation, generated a demo reply, reloaded both
messages from SQLite in the browser, and then removed the test rows. New SQLite/API
features passed synthetic storage and local HTTP smoke checks, and paced
breathing start/early-stop was checked in the browser. Synthetic test rows were
removed; four pre-existing STOP sessions and their messages were preserved.
SQLite integrity check is `ok`.

The latest backend pytest attempt was blocked by the sandbox's temp-directory
restriction; the in-project temp run stalled, so the new API routes are not
claimed as pytest-verified. Earlier notes recorded 16 pre-change backend tests
passing. Live provider text and voice were not exercised in this pass. Chat uses
a bounded conversational prompt; it can discuss general topics and explain
STOP when relevant. Profile and check-in data are not included in model context.

## Safety and privacy

Never copy `backend/.env` or `data/app.sqlite3` to GitHub. Do not display or
reuse the key shared in chat; rotate it before further live calls. This is
fictional coursework, not therapy or a monitored service. Check-ins are
optional, coarse and removable; do not interpret them as diagnosis or use them
as model context.

## Remaining work

Potential next steps after review: decide retention/deletion for STOP sessions
and conversations, add crisis-resource localization, review wording and breath
pacing with intended users, determine whether recent chat context should be
separately opt-in, and evaluate the proposed RAG workflow. Do not add a clinical
screening flow without a validated instrument and agreed handling.
