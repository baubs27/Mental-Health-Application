# Part 3.3 — Integration, evaluation, and demonstration

## Submitted version

- Repository: [Mental Health Application](https://github.com/baubs27/Mental-Health-Application)
- Application commit: [`9ef64abd579bbebf6314f7bd8be79e8e46a2566e`](https://github.com/baubs27/Mental-Health-Application/commit/9ef64abd579bbebf6314f7bd8be79e8e46a2566e).
- Run instructions: [project README](../../README.md#run-locally)
- Design and generated-code explanation: [design pipeline](../design-pipeline.md#part-33-personalization-update)
- Evaluation cases and observed results: [fictional scenario evaluation](evaluation.md)
- Browser demonstration: the running local app at `http://127.0.0.1:5173/` was inspected after a profile change and reload. A repository recording is not yet available.

## What changed from Part 3.1 and Part 3.2

The earlier design proposed using the last explicitly selected or self-rated
helpful skill as a suggested default. The implementation keeps an explicit
**usual practice** preference as the source of the featured Home activity. It
uses saved history for a separate **Repeat this practice** shortcut to the most
recent completed practice. That shortcut never silently replaces the person's
selected usual practice. This separates a record of prior use from a claim
about current need or preference.

Profile now also stores a chosen chat response style (balanced, reflective, or
practical) and an opt-in switch for chat personalization. When enabled, live
text chat receives the response style, the explicit usual-practice choice, and
aggregate counts of completed STOP and paced-breathing sessions. The application
does not send check-ins or other conversation transcripts as personalization
data. The current conversation's bounded recent turns are still sent as chat
context when live mode is used. Turning the personalization switch off removes
the profile/history summary from the model request. A data migration gives
existing databases safe defaults (`balanced`, off).

The summary uses completed-practice counts as a record only. It does not infer
mood, progress, or preference, and the model is instructed not to recommend a
skill solely from those counts. The profile is anonymous and local; it is not a
named account or a clinical persona.

## Model role and generated code

FastAPI owns the new personalization boundary. `get_personalization_context`
reads only opted-in profile fields and coarse completed-session counts from
SQLite. `personalized_instructions` turns those fields into a bounded
server-owned instruction block. The chat routes call it only when generating
a reply; Vue never reads SQLite or sends this profile summary directly to a
provider. The model still cannot control the practice sequence, access the
database, decide whether Crisis support is visible, or return a diagnosis.

In deterministic demo mode, the selected response style visibly changes a
small canned response. It is a repeatable demonstration, not evidence of live
model quality. Fixed STOP, activity timing, exit handling, and support content
remain application-controlled.

## Evaluation and evidence

The new backend suite exercises fifteen fictional scenarios and five explicit
cross-case behavior checks using a temporary SQLite database and deterministic
demo/failure responses. All 20 Part 3.3 checks passed. The full backend suite
passed 36 tests; the frontend passed 9 tests; the production build succeeded.
The exact cases, expected behavior, observed behavior, and test names are in
[evaluation.md](evaluation.md).

The browser was reloaded against the isolated demo database. The Profile page
showed the selected STOP practice, reflective response style, and enabled
personalization switch after reload, confirming that these choices persisted.
The Home page and activity-history shortcut are implemented from the saved
practice list. Automated integration checks confirmed that the explicit usual
practice remains selected even when the most-used completed practice differs.

The evaluation exposed a surprising gap: the deterministic demo reply path
bypassed the live prompt's crisis wording and returned a generic conversational
answer to immediate-danger phrases. The demo path now has a bounded crisis
referral response, plus clear deterministic boundaries for diagnosis and
medication questions. The separate static Crisis route remains usable during a
forced model failure.

## Recording status

This update does not include the requested continuous demo recording or the
process screencast. Computer Use was interrupted while the built-in screen
recorder was being opened, before a recording could be captured. The browser
walkthrough and automated failure/history assertions are documented, but they
are not represented as a recording.

## Live-model and peer-testing status

No live-model calls were made. The only previously supplied provider key was
pasted into chat and is treated as exposed, so it was not reused. A newly
rotated key must be configured locally in `backend/.env` before doing the
requested small repeated live-model comparison. The mocked tests use no paid
provider calls. No peer tester participated in this pass; the repeatable suite
is appropriate as the default peer-testing mode but does not replace a peer
session.

## Remaining limitations

- The live-model variation check and human peer session remain outstanding.
- Continuous demo and process recordings remain outstanding.
- The anonymous local profile is shared by people using this installation;
  there are no accounts, cross-device sync, or per-person profiles.
- Chat personalization is opt-in but the app has no separate retention or
  delete-all control for saved messages and practice sessions.
- Screen-reader and intended-user reviews, live-provider latency/failure
  variation, and non-US crisis localization remain untested.
- Immediate-danger wording is a fixed demo reply, not crisis monitoring or an
  emergency response service.

The prototype is for fictional coursework scenarios. It is not therapy,
diagnosis, medical advice, monitored support, or an emergency service.
