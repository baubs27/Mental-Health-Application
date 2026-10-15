# Instructions for the coding agent

Work toward the application described in `README.md`. Work inside this project
root and preserve existing code, data, and unfinished work. Read the README and,
when present, `docs/design-pipeline.md` and `handoffs/current.md` before changes.
These instructions are self-contained; no course website is needed to use them.

## Startup boundary

For the startup task, create only the base folders and README.md/AGENTS.md.
Preserve existing supporting files. Do not install dependencies, build an
interface, configure credentials, create a database, or create/capture a Figma
design during this step. Add supporting documents later as work requires them.

The README leaves project-specific design guidelines open. Before implementing
an interface, obtain the developer's chosen skill, intended flow, design
guidelines, and rationale based on class principles. Do not silently substitute
the lecture's breathing example or invent decisions for unfinished placeholders.
The instructions below govern later development as those tasks are requested.

## 1. Keep the frontend, backend, and database separate

- **`frontend/`: Vue with JavaScript, HTML, and CSS.** Put Vue components,
  interface state, input controls, pacing cues, and API-request code here.
  Use Node.js for frontend tooling and declare dependencies in `package.json`.
- **`backend/`: Python with FastAPI.** Put API routes, request validation,
  controllers, data models, database access, and model-provider calls here.
  Use a project environment at `backend/.venv` and declare Python dependencies.
- **`data/`: SQLite and fictional fixtures.** Use `data/app.sqlite3` for the
  working database. Resolve that path from the project location so it does not
  change with the terminal's working directory. Only backend code opens it.
- Vue communicates with FastAPI through HTTP requests and JSON responses.
  Vue must not open SQLite or call the model provider with a private key.
- Follow MVC responsibilities: models define data and relationships; views
  display information and accept input; controllers apply business rules and
  coordinate data operations. Keep FastAPI routes small. Document the actual
  files that own these responsibilities as implementation develops.
- Application code controls the exercise sequence, timers, exits, and support
  route. The conversational model cannot change these rules.

## 2. Put project context in the right place

- `README.md`: purpose, stack, folder map, and verified setup/run instructions.
- `docs/design-pipeline.md`: architecture, request/data flow, behavior contracts,
  design rationale, and decisions that affect implementation.
- `docs/verification.md`: repeatable checks, expected/observed results, and
  anything still unverified.
- `prompts/`: significant instructions worth reusing; use descriptive numbered
  names and remove credentials or private content.
- `handoffs/current.md`: actual current state, unfinished work, checks run, and
  the next task. Include the branch and relevant commit once they exist.

Update the relevant document when a decision or behavior changes. Avoid copying
whole conversations or creating several documents that repeat the same facts.

## 3. Inspect, plan, and make small changes

Confirm the project folder, branch, existing files, and uncommitted changes.
Summarize the requested result, affected files, behavior to preserve, and how
success will be checked. Work on one coherent increment at a time.

Use **CHECK → TAKE ACTION → VERIFY** for environment setup. Inspect Python,
Node.js, and declared dependencies first. Before an installation that has not
already been authorized, show the packages, exact commands, and target environment
and obtain approval. Verify the resulting versions and imports. Keep dependencies
project-local and preserve existing configuration.

Define inputs, outputs, failure behavior, and a worked example before connecting
components. Prove one backend operation, then one complete frontend-to-backend interaction before expanding the feature set.
