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

## Readiness recheck — November 2, 2026

- Re-ran backend tests: 36 passed (one upstream Starlette/AnyIO deprecation warning).
- Re-ran frontend tests: 9 passed; production build succeeded.
- Profile saves now show a visible and screen-reader-announced saving/success/
  error status directly in Profile.
- Frontend and API returned HTTP 200. Backend reported deterministic demo mode,
  no configured text/voice provider, and the static support endpoint remained
  available.
- Cleared the exposed key from local ignored `backend/.env` and restarted the
  API against the isolated `data/part33-demo.sqlite3` database. Revoke the key
  in the provider dashboard before using a replacement.
- No new browser recording or visual walkthrough was captured.
- GitHub connector write calls returned HTTP 403, but the configured Git remote
  accepted the clean-clone push. App and documentation updates are published in
  commit `9ef64abd579bbebf6314f7bd8be79e8e46a2566e` on `main`.

## Outstanding Part 3.3 evidence

- Repeat a small live-model selection after a newly rotated key is configured
  locally in `backend/.env`; never paste the key into chat or docs.
- Record and link the app demonstration and failure-investigation screencast.
  Computer Use was interrupted before recording was captured.
- A peer session and intended-user / screen-reader review were not performed.

See `README.md`, `docs/design-pipeline.md`, `docs/verification.md`, and
`docs/part-3.3/` for implementation rationale, run instructions, and scenario
results. This Assignment 3 folder has no standalone Git history or remote; the
parent folder currently reports no commits and no remote. The clean clone at
`.publish-checkout` is used for Git operations; ignored secrets and databases
stay local.
