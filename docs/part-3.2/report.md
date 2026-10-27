# Part 3.2 — Working application report

## Submitted version

- Repository: [Mental Health Application](https://github.com/baubs27/Mental-Health-Application)
- Application commit: [`e78148b271c0e2d263fe4c70ef44e82c8fada0d5`](https://github.com/baubs27/Mental-Health-Application/commit/e78148b271c0e2d263fe4c70ef44e82c8fada0d5)
- Design: [Part 3.1 proposal](../report.md) and [Part 3.2 design/implementation notes](../design-pipeline.md)
- Verification: [Part 3.2 verification evidence](../verification.md)
- Related voice increment: [Live Audio notes](../voice-audio.md)
- Recording: [Supplied expected-demo reference](../recordings/expected_demo.mov). It informed the interface but does not show this application running. No app walkthrough recording is committed.

## What is complete

The local coursework prototype connects a Vue interface to a FastAPI backend and SQLite. It includes four-step STOP, 50-second paced breathing, optional coarse check-ins, editable local practice preferences, activity history, an open-ended AI chat with suggested starters, and persistent crisis support that does not depend on model availability. Text conversations persist locally; the model receives only the current conversation's bounded recent turns, not profile or check-in data.

## What the evidence shows

The verification record documents the production frontend build, the browser walkthrough, and a deterministic demo-mode chat round trip. A synthetic chat turn and reply were retrieved from SQLite and appeared in the browser's recent-conversation list; the synthetic chat was then removed. SQLite integrity returned `ok`. The voice tests use provider mocks; no live model or voice-provider request was made for this verification.

See [verification details](../verification.md) for the checks and limitations. The reference recording is a visual benchmark only, not evidence that the application's own flows were recorded.

## Unresolved work

- Record and link a walkthrough of the running application.
- Verify live text and voice behavior only with a rotated, properly configured provider key.
- Decide on conversation and session retention/deletion controls.
- Localize crisis resources and review language and pacing with intended users.
- Validate the optional voice experience in a target browser.

This is a fictional coursework prototype. It is not therapy, diagnosis, medical advice, monitored support, or an emergency service.
