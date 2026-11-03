# Curated, redacted evidence log

This is a selection of project prompts and evidence, not a full chat export.
Only fictional scenarios are included. Credentials, personal information, and
private research-participant material are excluded. Research findings are
represented only by the assignment's aggregate R/D summaries.

| Prompt or evidence source | Change or observation | Verification | Decision / status |
| --- | --- | --- | --- |
| Part 3.1 request: propose a skills experience, explain model/data, connect choices to R/D findings, and leave open questions. | Wrote the STOP proposal and flow in [`report.md`](report.md); documented the chosen skill's sequence, sub-90-second target, optional model role, local records, user control, and independent crisis route. | Design review against assignment summary; proposal records assumptions and unresolved questions. | Fixed reviewed skill steps and app-owned exits/safety affordances. No claim of clinical effectiveness. |
| Part 3.2 request: deliver a working skill across Vue, FastAPI, and SQLite; show persistence, duration, failure, and crisis access. | Implemented breathing and STOP experiences, text chat, history, profile, crisis route, and saved sessions/conversations. | [`verification.md`](verification.md) records browser walkthrough, backend/frontend checks, synthetic SQLite inspection, and isolated cleanup. | Model help is optional; practice and crisis access continue to work independently. Abrupt browser closure remains best-effort. |
| Part 3.3 request: personalize from saved history while preserving user control. | Added off-by-default profile-driven chat personalization, response style, and a recent-practice repeat shortcut. Kept the explicit usual-practice choice as the featured activity. | Migration, prompt-capture, profile persistence, cross-case behavior, and isolated-database checks are documented in [`part-3.3/evaluation.md`](part-3.3/evaluation.md). | Counts describe use only; they are not treated as mood, progress, need, or a replacement for the user's selection. Check-ins and other chats are excluded from the personalization summary. |
| Fifteen fictional deterministic scenarios plus five cross-case checks. | During review, demo-mode crisis language initially received a generic conversational fallback because the deterministic path did not use the live prompt. | The failing behavior was reproduced by the scenario suite; the revised deterministic reply now directs to the independent Crisis route. The report records 36 backend tests, 9 frontend tests, and a successful production build. | Revised the demo path and retained static crisis access as an app-owned route. This is a software-behavior check, not evidence of crisis detection. |
| Browser observation after profile save and reload. | STOP remained the selected usual practice; reflective style and opt-in personalization persisted. Home kept the recent completed-practice shortcut separate. | Browser walkthrough against an isolated demo database; corresponding steps are recorded in [`part-3.3/report.md`](part-3.3/report.md). | Saved settings and history can adapt the interface without silently overriding the explicit preference. |
| Clean-checkout setup described in README. | A temporary clone was installed and checked using the documented npm/Python setup. | [`part-3.3/evaluation.md`](part-3.3/evaluation.md) records `npm ci`, backend dependency installation, tests, and build in that checkout. | Successful on the same Windows host; not independently verified on another person's computer. |
| Readiness request: check the project and improve what can be verified locally. | Re-ran the suites and build; cleared the exposed provider key from ignored local configuration; restarted the app in deterministic demo mode with its isolated database; made profile-save success and failure visible where preferences are edited. | 36 backend tests and 9 frontend tests passed; production build succeeded. Frontend and API returned HTTP 200, the API reported demo mode and no configured provider, and the independent support route returned emergency-support wording. | Kept the app runnable without an exposed credential and made persistence feedback easier to notice. This is a local HTTP/configuration recheck, not a new visual recording or live-model check. See [`verification.md`](verification.md#readiness-recheck--november-2-2026). |

## Evidence not yet collected

- No app walkthrough or process screencast is committed. The process recording
  should show a failure, the evidence used to diagnose it, and the resulting
  code/design decision; the demo recording should show the finished flow.
- No live-model variation sample or peer session was run. The exposed prior
  credential was not reused. Mocked results above must not be presented as live
  model evidence.
- Screen-reader behavior, abrupt browser-process termination, and crisis
  localization outside the configured region remain untested.
