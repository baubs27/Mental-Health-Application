# AI use disclosure

This disclosure covers the work recorded in this repository. The prototype is
for fictional coursework scenarios only; AI output is not clinical guidance.

| Tool or model | Version / identifier | Role in the project |
| --- | --- | --- |
| OpenAI Codex desktop | Model family shown to the agent: GPT-6; exact deployment/build identifier was not exposed in the session | Assisted with code edits, test authoring and interpretation, documentation, and browser/database verification. The agent read the supplied assignment materials and project files. |
| OpenAI Responses API, configured application model | `gpt-6-luna` is the model label used by the app; an exact provider snapshot/version was not recorded | Optional live text-chat provider configured by the project. Part 3.3 evaluation did not make live provider calls. Routine behavior checks used deterministic demo/failure responses and a fake provider. |
| Vite/Vue development tooling and the local browser | Versions are recorded in the lockfile and package metadata; the specific browser build was not recorded | Ran and inspected the local prototype; these are development/verification tools, not generative AI systems. |

The previously shared provider credential is considered exposed. It was not
copied into this file, source control, browser code, or the evaluation record,
and was not reused for Part 3.3 live calls. Live-model comparisons remain
unverified until a rotated key is configured privately in `backend/.env`.

AI-assisted content and code were reviewed against the assignment constraints.
The app owns the skill sequence, timing, persistence, failure handling, and
independent crisis route. The model cannot diagnose, modify skill steps, read
SQLite directly, or decide whether crisis support is available. See the
[curated evidence log](docs/evidence-log.md) for selected prompts, observations,
changes, tests, and a revised approach.
