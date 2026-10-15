# Mental Health Skills App

IST 402 — Assignment 3 starter

## Purpose

Build a local application that lets someone practice a short skill, stop at any
point, and return to useful session history. The interface should ask for little
reading or typing and keep the person in control. A conversational model can
help introduce the skill and explain the app, using reviewed content and saved
context.

This is a coursework prototype, tested only with fictional scenarios. It must
not diagnose, provide therapy, imply human monitoring, or be offered as a real
mental health support service.

## Startup scope

Create the base folders, README.md, and AGENTS.md. This step establishes project
context. The application capabilities below are plans for later implementation.
There is no selected interface design or running application yet.

## Your design guidelines — to be completed

Before asking an agent to build the interface, add your own design guidelines
here. Use the principles taught in class and the research discussed for
Assignment 3 to explain your choices. The starter does not choose the skill,
screen layout, or interaction flow for you.

Class principles to carry into your design:

- Keep the guided skill within 90 seconds at its intended pace. Show one clear
  action at a time and keep reading, typing, and configuration demands low.
- Let people start, stop, skip, and change their choices. Keep support information
  visible and usable independently of model responses.
- Use calm, readable language, sufficient contrast, visible keyboard focus,
  a narrow-screen layout, and an alternative to motion.
- Make personalization understandable and changeable. Keep self-report,
  observed behavior, and interpretation distinct; clicks do not establish an
  emotional state or diagnosis.
- Explain how a design choice follows from a class finding, what alternative
  you considered, and what tradeoff you accepted. Check the running result later.

Add your project-specific decisions when you are ready:

- Chosen skill and fictional user/task: [to be decided]
- Main interaction flow and user controls: [to be decided]
- Interface guidelines and their class/research rationale: [to be added]
- Model's role, saved context, and useful personalization: [to be decided]
- Alternative designs and reasons for the selected direction: [to be added]

You may choose paced breathing, sensory grounding, STOP, or a cognitive reframe
within the assignment's scope. Record detailed design decisions in
`docs/design-pipeline.md` as the design develops.

## Technology and separation

- Frontend: Vue with JavaScript, HTML, and CSS. It presents the interface,
  responds to input, and sends HTTP requests to the backend. Node.js provides
  the frontend development tools.
- Backend: Python with FastAPI. It exposes the API, validates requests, applies
  business rules, calls the conversational model, and reads/writes the database.
- Database: SQLite. The planned database is data/app.sqlite3. Only the Python
  backend accesses it; the frontend receives data through the API.

The application runs on localhost.

## Secrets and APIs

Store model-provider API keys and other secrets in `backend/.env`. Keep this
file out of Git with `.gitignore` before adding credentials. Provide a
`backend/.env.example` containing variable names and empty or dummy values so
another developer knows what to configure. The backend must explicitly load its
configuration; placing a file in the folder does not load it automatically.
Never put private keys in Vue code, browser-exposed environment variables,
API responses, logs, screenshots, prompts, or Figma.

Vue calls our FastAPI endpoints using HTTP and JSON. FastAPI validates requests,
calls the external model API, and reads or writes SQLite. Document each endpoint's
input, response, and failure behavior in `docs/design-pipeline.md`. Use finite
timeouts, clear loading and failure states, and a bounded number of provider
calls. A configured key, a mocked response, and a successful live API call are
different checks. Ordinary history browsing should not require a model call.

## Conversations, RAG, and data views

Save submitted user messages and actual model replies in SQLite, linked by a
conversation ID. Keep a message ID, role, content, timestamp, and request status
so the app can reconstruct the conversation in order. Store exercise outcomes
and preferences in related records. A failed model request must not create a
fabricated reply, and a failed database write must not appear as a successful
save. Saved records should survive refresh and backend restart without duplicates.

**Retrieval-augmented generation (RAG)** supplies relevant stored information to
the model before it answers. Use the SQL-based pattern covered in class:

1. FastAPI sends the question and relevant database schema to the model API.
2. The model proposes a retrieval query. FastAPI checks it, restricts it to
   allowed data for the current conversation or demo user, and executes it using
   read-only SQLite access with limits on the results.
3. FastAPI sends the selected records and reviewed skill information in a second
   model call. The answer should identify its supporting records and acknowledge
   missing information instead of inventing history.
4. Backend application code saves the actual reply and returns the result to Vue.

The model never connects directly to SQLite. RAG retrieval cannot insert,
update, or delete records; normal conversation saves use separate, parameterized
backend operations. The query-planning and answer-generation calls both count
toward the API budget. SQLite is sufficient for this baseline; it does not
require a vector database.

Make the saved data visible. Provide a Vue conversation-history view and a
session table or timeline, both populated through FastAPI from SQLite. Show
message order and time, plus exercise duration and stopped/completed status.
Any summary or chart must come from those records and must not imply a diagnosis
or improvement in mental health. During development, also inspect the schema,
relationships, and rows with an available SQLite viewer or read-only queries.
Compare the database, API response, and displayed history for the same fictional
conversation, including after a refresh and backend restart.

## Project folders

```text
project-root/
|-- README.md                 Project purpose and starting direction
|-- AGENTS.md                  Instructions for the coding agent
|-- .gitignore                 Local files to exclude from Git
|-- frontend/                  Vue interface and frontend dependencies
|-- backend/                   Python/FastAPI API and application logic
|   |-- .env                   Local secrets; ignored by Git
|   `-- .env.example           Configuration names with safe placeholders
|-- data/                      Local SQLite database and fictional fixtures
|-- docs/
|   |-- design-pipeline.md     Architecture, behavior, and design decisions
|   `-- verification.md        Checks to run and evidence of what happened
|-- prompts/
|   `-- 01-start.md            First scoped instruction for the agent
`-- handoffs/
    `-- current.md            Current state and next step for a new session
```

This map includes files to add as the project develops. At startup, create only
the base folders and the two root documents, README.md and AGENTS.md. Leave
existing supporting files intact if you already have them. Add the ignore rules
before introducing credentials or runtime data; create environment files and
the SQLite database during implementation. Keep fictional fixtures separate
from runtime records and do not commit the working database.

## Later design workflow

The separate Figma and MCP activity covers building a small interface, bringing
it into editable Figma frames, and using a selected design to guide a Vue
revision. That work comes after this startup step and your initial design
guidelines. Figma edits do not automatically update application code.

## Getting started

Read `AGENTS.md`, create the base folders, and keep the undecided design items
visible. Startup is complete when the folders and these two documents are in
place. Complete your design guidelines before requesting implementation.

Add supporting project notes as work requires them. Installation, interface
building, FastAPI/model connections, SQLite, RAG, and data views are later tasks.
Record actual setup, configuration, run, stop, and test commands here only after
they have been implemented and checked.
