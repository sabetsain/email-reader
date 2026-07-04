# Email Summarization Agent — Project Plan & Learning Roadmap

**Stack:** LangGraph (orchestration) · Gemini 3.5 Flash (LLM) · Gmail API (data source) · LangSmith (telemetry) · Agent Chat UI (interface) · GitHub (version control)

**Goal:** An agent that reads Gmail, pulls everything from the last 24 hours, classifies each email (spam / marketing / academic / job-related), and produces a summary — built as a learning project, so the process matters as much as the result.

---

## Design questions to settle first

Answer these in your own words before writing code. They're the real engineering decisions in this project — everything else is mostly following docs.

1. **Classification taxonomy** — Is spam/marketing/academic/job mutually exclusive? Can one email be two categories (e.g. a marketing email from a university)? What's the fallback for emails that fit none — a 5th "other" bucket, or forced into the closest one?
2. **Time window precision** — Gmail's `newer_than:1d` search operator is day-granular. Is that precise enough, or do you need `after:`/`before:` with exact timestamps?
3. **Idempotency** — If you run the agent twice in one day, should it re-summarize emails it already processed? This determines whether you need a DB tracking processed message IDs, or whether stateless is fine for now.
4. **Digest vs. per-email** — One paragraph per email, or a single rolled-up digest ("14 emails: 3 job-related, 9 marketing, 2 academic — here's what matters")? This shapes both your prompt design and your graph structure (fan-out/fan-in vs. one batch call).
5. **Trigger model** — On-demand (via chat), scheduled (cron), or both? Determines whether Agent Chat UI is your only entry point or you also need a scheduler.

> Write your answers down in a `DESIGN.md` in the repo during Phase 1. You will forget your own reasoning three weeks from now — future you will thank present you.

---

## Architecture note: why not Agent Chat UI for everything

Agent Chat UI (LangChain's Next.js template) is built specifically for chatting with a LangGraph agent — threads, token streaming, tool-call rendering. It has no charting primitives and no data layer for questions like "emails per hour" or "who emails me most." If you want analytics later (mentioned as a future goal), treat that as a **separate small app** reading from your own storage (Postgres/SQLite), not something bolted onto the chat UI. Keeps both pieces simple and lets each be good at its own job.

---

## Phase 0 — Orientation
**Time:** a few hours
**Do:** Read LangGraph's core concepts docs: graphs, state, nodes, edges, conditional edges. Skim (don't build) the "structured output" and "persistence/checkpointing" pages so you know they exist for later.
**Checkpoint:** You can explain, in your own words, why this problem needs a graph instead of a linear script.

## Phase 1 — Scaffolding
**Time:** half a day
**Do:**
- Create the GitHub repo, `.gitignore` for secrets, `.env.example`.
- Get a Gemini API key in AI Studio.
- Set up a Gmail API OAuth client (budget real time — the consent screen and scopes are usually the most annoying part).
- Write your `DESIGN.md` answering the 5 design questions above.
**Checkpoint:** A throwaway script authenticates and lists your 5 most recent emails. No LangGraph yet — isolate the auth problem from the agent problem.

## Phase 2 — Minimal graph
**Time:** half a day
**Do:** Build the smallest possible LangGraph — one node, hardcoded fake emails in, fake summaries out via Gemini. No Gmail integration yet.
**Learn:** `StateGraph`, defining a state schema (TypedDict or Pydantic model), a single LLM-calling node, compiling and invoking the graph.
**Checkpoint:** `graph.invoke(...)` returns a summary for a fake email, end to end.

## Phase 3 — Real Gmail fetch node
**Time:** half a day
**Do:** Replace the hardcoded list with a real "fetch" node calling the Gmail API.
**Learn:** How state flows between nodes; handling pagination/empty results; mapping Gmail's message format into your state shape.
**Checkpoint:** The graph pulls your actual last-24h emails into state.

## Phase 4 — Classification node
**Time:** 1 day
**Do:** Add a node that classifies each email into your taxonomy.
**Learn:** Structured output / tool-calling with Gemini via LangChain (reliable enum back, not parsed free text); conditional edges if categories need different handling (e.g. skip summarizing spam).
**Checkpoint:** Each email in state has a category, with plausible accuracy on your real inbox.

## Phase 5 — Summarization + fan-out/fan-in
**Time:** 1 day
**Do:** Add summarization (per-email or batch digest, per your Phase 1 decision).
**Learn:** If per-email, LangGraph's `Send` API for fanning out over a list and collecting results back. This is the single most non-obvious LangGraph concept for beginners — read the docs deliberately rather than guessing.
**Checkpoint:** Full pipeline (fetch → classify → summarize) produces a real digest of your actual inbox.

## Phase 6 — Persistence
**Time:** half a day (skip if Phase 1 Q3 answer was "stateless is fine")
**Do:** Add a checkpointer and/or external DB for idempotency and history.
**Learn:** Checkpointers vs. your own application DB — they solve different problems (checkpointers resume a graph run; they are not "have I seen this email before" business logic).
**Checkpoint:** Running the agent twice doesn't double-summarize.

## Phase 7 — LangSmith
**Time:** a couple hours
**Do:** Turn on tracing, inspect a real trace from Phase 5. Deliberately answer: which node is slow, which is expensive, did classification get it right and can you see why from the trace.
**Learn:** Tracing is free once env vars are set; evaluation/datasets (turning "did it classify correctly" into a repeatable test) is a deeper, separate feature — worth a light read even without building a full eval suite yet.
**Checkpoint:** You can diagnose a bug from a trace without adding print statements.

## Phase 8 — Agent Chat UI
**Time:** half a day
**Do:** Wire the deployed/local graph to Agent Chat UI — mostly configuration, pointing the UI at your graph's endpoint.
**Checkpoint:** You can chat "summarize my last 24 hours" and watch it stream.

## Phase 9 — Deployment
**Time:** half a day to a day
**Do:** Move from local `langgraph dev` to something always-on, if the cloud-hosted piece needs to be real and not just localhost.
**Checkpoint:** The UI works from a device that isn't your dev machine.

## Phase 10 — Analytics (later, separate mini-project)
**Do:** Build the dashboard as its own small app against your Phase 6 storage — a second project, not an afterthought bolted onto Agent Chat UI.

---

## Reference docs, in reading order

1. Gmail API quickstart
2. LangGraph "Graph API" concepts + structured output
3. LangGraph `Send` API (fan-out/fan-in) — for Phase 5
4. LangSmith tracing quickstart
5. Agent Chat UI GitHub README

## Notes to self

- Phase 5's fan-out/fan-in is where most people actually get stuck — budget extra time, not on the "basic graph" parts.
- Phase 1's OAuth setup is boring but can eat a whole evening the first time. Don't schedule it right before something else.