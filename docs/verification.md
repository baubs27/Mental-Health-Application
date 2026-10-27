# Part 3.2 — Verification evidence

Verification date: October 26, 2026 (local Eastern time).

## Automated checks

- Frontend: `npm test` — 9 tests passed.
- Production bundle: `npm run build` — Vite production build completed.
- SQLite storage smoke: initialized a separate temporary database and exercised
  breathing start/leave, a self-report, preference save, and combined history.
- Backend route smoke against the refreshed local API: breathing start/leave,
  check-in save/removal, profile read/save, and history read passed with
  synthetic values. The synthetic check-in and breathing rows were removed
  afterward; profile preferences were restored to the values read beforehand.
- SQLite integrity: read-only `PRAGMA integrity_check` returned `ok`; after
  cleanup the working database retained four existing STOP sessions, three
  messages, zero check-ins, and zero breathing test rows.
- OpenAPI: confirmed breathing, mood-check-in, profile, and history routes are
  registered. `GET /api/profile` returned only `paced_breathing` and the
  animation preference; no secret/configuration value is returned.

The backend pytest suite could not be rerun in this sandbox: its default pytest
base-temp is outside the writable project; an in-project base-temp attempt
stalled before producing test output and was stopped. Earlier Part 3.2
verification recorded 16 backend tests passing before the new routes were
added. No current claim is made that pytest covered the new routes; those were
checked through the local API and storage smoke paths instead.

No provider request or voice call was made during this pass. The shared key in
`backend/.env` was not read or displayed by the verification commands.

## Browser walkthrough

The updated Vue app was opened at `http://127.0.0.1:5173/` with the refreshed
FastAPI app on `http://127.0.0.1:8000/`. The narrow browser view showed the
botanical home card, optional check-in, paced-breathing feature, and fixed six
item navigation. Activities listed paced breathing and STOP. Chat showed the
STOP-only question entry and separate optional voice controls. Profile showed
an editable default practice, animation setting, and the no-screening notice.
History read the four pre-existing STOP sessions from SQLite. Crisis showed
local emergency guidance and US 988 call/text/official chat links independently
of a model response.

Paced breathing was started in the browser. The screen showed “Breathe in
gently,” cycle 1 of 5, and elapsed duration; after selecting Stop practice,
History showed a persisted `left` row with its measured duration (0:05). This
was a synthetic verification session and was then removed from SQLite so it
would not appear as user activity. The separate API smoke session was also
removed. The previous STOP conversation/session data remained intact.

The reference video's screening result and scored assessment are intentionally
not copied. This prototype has no validated assessment instrument/scoring rules.

## Limitations

The breathing cue uses 4-second inhale/6-second exhale timing. People should
breathe comfortably and can stop; it does not require a breath hold. Animation
can be disabled. Voice is opt-in and was not manually tested with a provider.
Session-exit persistence on abrupt tab closure is best-effort. STOP session/chat
delete/retention controls, crisis localization beyond the US link, user
accounts/sync, deployment, and the proposed RAG workflow are unfinished.
The model is a STOP explainer, not a general support chat. Check-ins are coarse,
self-selected and removable, and are not treated as recommendations or
clinical measures. Review new wording and pacing with intended users.

The API key was shared in chat previously; rotate it before further live use.
It remains excluded from code, docs, build output, screenshots, and Git.
