# Part 3.3 — Fictional evaluation record

## Method

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -vv -p no:cacheprovider --basetemp .pytest-run-part33-final tests
```

The fifteen scenarios use FastAPI's in-process test client, temporary SQLite
databases, and the deterministic `MODEL_MODE=demo` response path. Invalid and
failure cases use local validation and `MODEL_MODE=fail`. No provider request
is made by these tests. The expected phrase is a compact observable assertion,
not a claim that every response is ideal.

## Scenarios

| # | Fictional action or input | Expected result | Observed result |
| ---: | --- | --- | --- |
| 1 | Open a new chat and say “Hi there.” | A brief, nonjudgmental conversational reply. | **Pass:** HTTP 200, labeled `demo`; “Thanks for sharing…” |
| 2 | Say “I had a stressful day.” | Acknowledge and leave the pace with the user. | **Pass:** HTTP 200; “We can talk it through at your pace.” |
| 3 | Ask “What does Observe mean?” | Explain STOP's Observe step when relevant. | **Pass:** HTTP 200; reply includes “noticing.” |
| 4 | Ask for a comfortable way to breathe when stressed. | Avoid prescribing or forcing a breathing method. | **Pass:** HTTP 200; “There is no single best way.” |
| 5 | Ask for help thinking through a situation. | Invite one manageable next thought without pressure. | **Pass:** HTTP 200; reply includes “one small next step.” |
| 6 | Change topic to organizing an afternoon. | Answer as a general conversation, without forcing STOP. | **Pass:** HTTP 200; general conversational fallback, no STOP insertion. |
| 7 | Select “reflective” and say “I just want to talk.” | Honor the selected listen-first style. | **Pass:** HTTP 200; reply begins “I can listen without rushing to solutions.” |
| 8 | Select “practical” and describe being stuck on a small task. | Use a practical-next-step framing. | **Pass:** HTTP 200; reply includes “one practical next step.” |
| 9 | Ask “Can you diagnose what disorder I have?” | Decline diagnosis and leave the next choice to the user. | **Pass:** HTTP 200; reply says it “can’t diagnose.” |
| 10 | Ask whether to change a medication dose. | Decline medical/medication advice and refer to a qualified professional. | **Pass:** HTTP 200; reply says it “can’t give medical or medication advice.” |
| 11 | Say “I might hurt myself.” | Point to the independent Crisis page and emergency help; do not claim monitoring. | **Pass:** HTTP 200; reply points to the “separate Crisis support page.” |
| 12 | Submit a blank chat message. | Reject it without creating an assistant response. | **Pass:** HTTP 422 validation response. |
| 13 | Submit 2,001 characters. | Enforce the 2,000-character input limit. | **Pass:** HTTP 422 validation response. |
| 14 | Try to skip directly from STOP step 1 to step 3. | Preserve step order and reject the jump. | **Pass:** HTTP 409 conflict. |
| 15 | Leave STOP after a fictional 9.9-second interval. | Save `left`, round measured duration down to whole seconds, and allow exit. | **Pass:** status `left`, stored duration 9 seconds. |

The four additional checks are cross-case behavior checks in
`test_part_3_3_evaluation.py`:

1. Crisis support returns static guidance while model mode is forced to fail.
2. A failed model request saves the user turn as failed and creates no
   assistant answer.
3. The user's explicit usual-practice setting stays in control when history
   shows a different most-used skill; personalization contains no check-in or
   message text.
4. A captured fake provider request has no profile summary when personalization
   is off and includes only the documented choices and aggregate counts when
   it is on.
5. An existing profile row survives the additive migration; new fields default
   to balanced response style and personalization off.

All 20 Part 3.3 checks passed. The whole backend suite passed **36 tests** in 10.93
seconds with one upstream AnyIO deprecation warning. Frontend `npm test` passed
**9 tests** and `npm run build` completed successfully.

## Live variation and limitations

The requested repeated live-model selection was not run. The only supplied API
key was exposed in chat and was not reused. No rotated key was available in
this pass. Live response variation, latency, refusal consistency, and provider
failure behavior therefore remain unobserved; the test results above are not
live-model evidence. No peer session was performed. Screen-reader behavior,
abrupt browser-process termination, mobile devices, and localization outside
the US also remain untested.

## Clean-checkout setup

A fresh temporary clone was created from the repository's `main` branch. The
Part 3.3 working-tree changes were applied there before they were committed and
pushed. The README's install commands completed from clean dependency
directories (`npm ci`, Python virtual environment creation, backend
requirements install, and `.env.example` copy). The backend suite passed 36
tests, the frontend passed 9, and the production build succeeded. The checkout
was fetched after publication and matched commit
`67d5b941827254e7058df26a66040b1fadddfeab`. This used a new checkout on the
same Windows host, not a second person's computer.
