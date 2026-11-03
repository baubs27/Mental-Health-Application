# Current handoff

## State

Part 3.3 implementation is published on `main` at
`67d5b941827254e7058df26a66040b1fadddfeab`. The app now has an additive profile
migration, an explicit chat response-style preference, an off-by-default
personalization switch, a Home shortcut to repeat the latest completed
practice, and deterministic crisis/diagnosis/medication boundaries. The user’s
explicit usual-practice preference remains the featured practice. The local
demo servers are running at `127.0.0.1:5173` and `127.0.0.1:8000` with
`MODEL_MODE=demo` and an isolated `data/part33-demo.sqlite3` database.

## Verification

- Backend: 36 tests passed, including 15 fictional scenarios, five behavior /
  migration checks, and the existing voice API tests.
- Frontend: 9 tests passed; production build succeeded.
- Browser: profile selection persisted after reload. A fictional STOP session
  completed and saved in the isolated database; Home then showed the latest
  completed practice shortcut without changing the chosen usual practice.
- No live provider call was made. The previously shared key was treated as
  exposed and not reused.

## Outstanding Part 3.3 evidence

- Repeat a small live-model selection after a newly rotated key is configured
  locally in `backend/.env`; never paste the key into chat or docs.
- Record and link the app demonstration and failure-investigation screencast.
  Computer Use was interrupted before recording was captured.
- A peer session and intended-user / screen-reader review were not performed.

See `README.md`, `docs/design-pipeline.md`, `docs/verification.md`, and
`docs/part-3.3/` for implementation rationale, run instructions, and scenario
results. The workspace copy is not a local Git checkout; publish subsequent
changes through the temporary Git clone workflow.
