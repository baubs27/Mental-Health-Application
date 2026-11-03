# Part 3.3 — Integration, evaluation, and demonstration

## Submission and included materials

- Repository: [Mental Health Application](https://github.com/baubs27/Mental-Health-Application)
- Submitted application code: [`9ef64abd579bbebf6314f7bd8be79e8e46a2566e`](https://github.com/baubs27/Mental-Health-Application/commit/9ef64abd579bbebf6314f7bd8be79e8e46a2566e)
- Run instructions, included in the repository: [README](../../README.md#run-locally)
- Design rationale, included in the repository: [design pipeline](../design-pipeline.md)
- Verification record, included in the repository: [verification notes](../verification.md)
- Scenario expectations and observed results, included in the repository: [Part 3.3 evaluation](evaluation.md)
- Recording included in the repository: [Part 3.3 submission recording](../recordings/part-3.3-submission.mp4) (MP4 supplied on November 2, 2026).
- The separate [expected-demo reference](../recordings/expected_demo.mov) is a reference clip, not a recording of this application. The supplied MP4 is included as the submission recording; this report does not claim particular failure, evidence, or code-explanation segments without reviewing those segments.

## What is complete

The Vue/FastAPI/SQLite prototype supports a four-step STOP practice, paced breathing, optional check-ins, an open-ended text-chat interface, a local profile, saved practice/chat history, and a Crisis support route that is independent of model output. Home uses the user's explicit usual-practice choice for its featured activity and presents a separate shortcut to repeat the latest completed activity.

The app describes itself as a coursework prototype. It does not claim to provide therapy, diagnosis, emergency support, or monitoring. The interface does not infer distress from check-ins or usage. Users can skip check-ins, choose or change preferences, complete a skill without using chat, leave a skill, and open Crisis support from the shared navigation.

## Personalization, control, and effort

The design balances saved context against privacy and setup effort. Profile stores an explicit usual practice and a chosen chat response style. Chat personalization is off by default and can be changed by the user. When enabled in live mode, the server may provide the selected style, explicit usual practice, and aggregate counts of completed practices to the model. Check-ins and other chat transcripts are excluded from this personalization summary. The current chat's bounded recent turns may be sent as ordinary conversation context.

The initial idea considered using the most-used or self-rated helpful practice to set the Home default. That was revised: app-use counts do not establish current need or preference, and automatic adaptation could take control away from the person. The explicit usual-practice selection therefore remains the featured activity; the latest-completed-practice shortcut is separate and optional. A richer profile or automatic mood-based routing was also considered and rejected because it adds configuration effort or unsupported inference.

The tradeoff is that explicit settings require a small amount of setup and the shared local profile is not per-person. In return, users can see and change the choices, while the app avoids treating usage history as a clinical signal. Optional check-ins, short steps, optional chat, and a direct Leave control reduce the work required to use a skill.

## Research-grounded decisions

The assignment's R/D summary informed the following choices. Its mention counts describe where themes appeared in the study; they are not measures of clinical effectiveness.

| Finding | Design decision, alternative, and tradeoff |
| --- | --- |
| **R1 — attention and duration:** reported attention declined beyond roughly 90–100 seconds. | Paced breathing is five 10-second cycles (50 seconds). STOP presents one step at a time and records elapsed time. The app does not force a completion time; user-chosen pauses and optional chat can extend actual duration. This preserves control but means a user's measured elapsed time is not a guaranteed skill duration. |
| **R2 — frictionless crisis access; D4 — persistent safety:** support should remain easy to reach. | Crisis support is a static app route available independently of the model. A model-controlled or prompt-only safety route was rejected because provider failure must not hide support. The route currently presents US 988 information and general emergency guidance; localization remains unresolved. |
| **R3 — permission to stop:** participants raised stopping as important. | Each practice can be left without a reason prompt, and the app records a `left` status and measured duration when the local service is available. This avoids forcing completion; an abrupt browser/process close remains best-effort. |
| **R4 — control over the journey; D1–D3 — contract, atomic skills, lower effort:** distress detection details were unspecified and disclosure effort matters. | The app does not use a clinical distress detector. Each practice has a focused view, check-ins are optional, and the user can choose, skip, leave, or open support. Automatic distress-based contraction was rejected because the app has no validated signal and the study did not establish a detection method. |
| **D5 — personalize without configuration burden:** a usual skill was requested. | A small explicit preference and optional chat-personalization switch were chosen over a long intake or automatic recommendation. This costs a little setup but makes personalization visible and changeable. |
| **D6 — low-stimulus, non-judgmental design.** | The app uses restrained color, short instructions, optional animation, reduced-motion styling, and visible keyboard focus. Screen-reader behavior has not been tested, so these implementation choices do not establish accessibility compliance. |

## Model role, stored data, and safety boundaries

The model is optional. It can provide a conversational reply or explain STOP when asked; it does not own the skill steps, timer, database, exit behavior, or visibility of Crisis support. The backend bounds chat context, validates provider responses, and records actual replies. A failed request is marked failed and does not create a fabricated assistant answer.

SQLite stores anonymous local profile preferences, chat sessions and messages, practice sessions and durations, and optional user-entered check-ins. The app has no named account or cross-device synchronization. Check-ins can be removed; broader deletion and retention controls for chat and practice history remain unfinished. In the current demo run, model responses are deterministic and the provider is not configured. No live-model behavior is claimed in this report.

For crisis-related wording, the deterministic demo has bounded referral responses. Live instructions also direct the model to the separate support route, but this is not a classifier or risk assessment. The static Crisis endpoint remains available regardless of model mode. The app does not claim to contact emergency services or monitor the user.

## Evaluation and what the checks establish

The included fictional evaluation contains fifteen scenario cases with expected and observed results, plus five cross-case behavior checks. The cases cover ordinary conversation, skill questions, user-selected response styles, diagnosis/medication boundaries, crisis-related wording, invalid input, skipped steps, and leaving early. The detailed case-by-case record is linked above.

The five behavior checks establish that: (1) the static Crisis route responds while model mode is forced to fail; (2) a failed model request saves a failed user turn but no assistant answer; (3) explicit profile choice remains separate from use counts and check-ins are excluded from personalization; (4) the fake-provider request omits profile context when opt-in is off and includes only documented coarse context when on; and (5) the additive profile migration preserves existing values and defaults new personalization to off.

The recorded deterministic/mocked checks passed: 36 backend tests, 9 frontend tests, and a successful Vite production build. A clean checkout was installed and checked on the same Windows host; this does not establish setup on another person's computer. These results establish repeatable software behavior for the tested inputs. They do not establish response quality for a live model, clinical effectiveness, or safety for real users.

One surprising finding was that the deterministic demo path initially bypassed the live prompt's crisis wording and returned a generic answer to immediate-danger phrasing. The scenario check exposed the mismatch. The demo response was revised to provide a bounded referral, and the current scenario expects that response. A limitation not tested is how the app's behavior holds up under screen-reader use; live-model variation and peer testing also remain unverified.

## Live-model, peer, and recording status

No live-model comparison was performed. The previously supplied key was treated as exposed, cleared from local configuration, and not reused. The current app runs without a provider key. Do not describe the deterministic demo or fake-provider tests as live-model results. A small live comparison requires a newly rotated key configured privately. If that is done, the host should set a session cap of no more than 50 model calls and return to mocked responses once the cap is reached.

No peer session was completed. If peer testing is performed, use mocked responses by default and fictional role-play only. No test or demonstration should involve a real person in distress. The supplied MP4 is included above, but its detailed contents have not been independently verified for this report; in particular, this report does not use it to substantiate a failure walkthrough, diagnostic evidence, resulting decision, or generated-code explanation. The expected-demo reference is not evidence of this app running. A verified process screencast remains outstanding.

This coursework project evaluates software behavior and design reasoning. It is not a mental health support tool and must not be offered or recommended for use during a difficult moment.
