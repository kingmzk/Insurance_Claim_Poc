# Autonomous Multi-Agent Insurance Claims Processing PoC
## Three-stage AI implementation prompt pack

Use these prompts sequentially in the same AI coding workspace/repository. Attach or make available the source PDF, **Autonomous Multi-Agent Insurance Claims PoC.pdf**, for Stage 1. Do not run Stage 2 until the Stage 1 specification is reviewed and accepted. Do not run Stage 3 until Stage 2 produces a runnable implementation.

---

# Prompt 1 — Requirements, Architecture and Implementation Specification

```text
Act as a principal software architect and AI systems engineer. Help me plan an internal proof of concept (PoC) for Autonomous Multi-Agent Insurance Claims Processing.

SOURCE OF REQUIREMENTS
Read the provided PDF named “Autonomous Multi-Agent Insurance Claims PoC.pdf” first. Use it as the source blueprint. Preserve its core ideas: five specialized workflow stages, a shared ClaimState, conditional routing, policy/repair knowledge retrieval, fraud indicators, risk assessment, settlement calculation, auditability and human-in-the-loop (HITL) handling. Clearly distinguish items taken from the PDF from decisions made below. Do not silently add production features or claim the proposed KPIs are already achieved.

DECISIONS ALREADY MADE
- Purpose: an internal company/client PoC, not a portfolio-first project or production deployment.
- Initial scope: synthetic/sample motor insurance claims, using the vehicle-damage, repair-estimate, policy and photo examples from the blueprint.
- Delivery target: a complete demonstrable prototype in about 4–5 days. Prioritize a thin, working end-to-end slice over breadth.
- Orchestration: Python + LangGraph.
- Backend: FastAPI.
- Persistence: SQLite. Do not use PostgreSQL.
- Initial local policy/repair retrieval: SQLite FTS5 with source metadata. Describe this accurately as keyword-based retrieval-augmented generation (RAG), not vector/semantic search. Do not add Chroma, pgvector, Pinecone or another vector database.
- Tool integration: ordinary Python functions and API clients/mocks. MCP is explicitly excluded from this PoC. Do not recommend or implement MCP in the design.
- AI model: one configurable/approved LLM provider. Do not assume API keys are present or hardcode secrets. Design a clear configuration boundary and a deterministic development/mock mode so the app can still run in an environment without credentials. Make mock-mode behavior visible.
- External policy, claims, forensic and payment systems are mocked or implemented as local tools. No real payments, claimant notifications or irreversible external actions.
- Any denial is a draft/recommendation for human review, not an automatic final denial. Potential fraud is a flag for investigation, not a conclusion that fraud occurred.
- Use deterministic code for validation, thresholds, currency handling and settlement arithmetic; use the LLM for tasks such as document extraction and evidence-grounded explanation where appropriate.
- For the minimum interface, FastAPI Swagger/OpenAPI is acceptable. Do not make a full React UI mandatory unless an existing project or stakeholder requirement makes it necessary.

THE FIVE LOGICAL WORKFLOW STAGES
1. Claims Intake: extract claim details, record source information, validate required fields and identify missing documents/data.
2. Policy Validation: retrieve relevant policy clauses with citations, and check status, coverage, deductible and limits using a mock authoritative policy lookup where needed. Policy documents alone must not be treated as proof of a policy’s actual active status.
3. Fraud Detection: flag demo indicators such as duplicate images, suspicious metadata and inconsistent claim details. Route uncertain/high-risk cases to human/SIU review.
4. Risk Assessment: compare repair line items against available sample benchmarks, calculate an adjusted estimate and assign a risk tier using explicit rules.
5. Settlement: compute a proposed amount deterministically and route to a simulated straight-through-processing (STP) outcome or a human adjuster queue.

DEMO ROUTING RULES
Treat thresholds as configurable demo rules, not universal insurance standards:
- Required intake data/documents missing -> pause as NEEDS_INFO and record what is missing.
- Coverage is denied, excluded or uncertain -> prepare an evidence-cited coverage exception/denial draft for human review; do not auto-deny.
- Fraud score >= 75 or significant inconsistent evidence -> route to human/SIU review.
- A claim may take the demo STP/simulated-settlement path only when risk_tier is LOW, fraud_score < 25 and the proposed payout is within a configurable authority limit (default demo amount USD 5,000 unless the source or stakeholder specifies otherwise). All other claims require human approval.
- Illustrative settlement formula: max(0, approved_estimate - deductible - depreciation). Validate input values and currency/rounding rules. Do not copy example numbers as real outcomes.

TASK — DESIGN ONLY; DO NOT IMPLEMENT APPLICATION CODE
1. Inspect the provided PDF and, if a code repository is available, inspect its structure without making changes.
2. Produce an implementation-ready specification for the smallest complete PoC. Avoid unnecessary abstractions and infrastructure.
3. Include these deliverables (save them in the repository if supported; otherwise provide them in your answer):
   a. `docs/implementation_spec.md`: problem statement, scope/non-goals, assumptions, components, responsibilities, interfaces and decisions.
   b. `docs/architecture.md`: a Mermaid component architecture and a separate Mermaid end-to-end flow diagram. Ensure the diagrams compile and make the exception routes visible.
   c. `docs/acceptance_criteria.md`: measurable functional acceptance criteria and demo scenarios. Treat any numeric targets from the PDF as proposed targets pending stakeholder agreement, not results.
   d. A proposed folder/package layout, API contract, shared ClaimState schema, SQLite tables, local document-ingestion/retrieval design, error handling and test plan.
4. Specify the minimum API endpoints needed to submit/process a claim, retrieve a claim and its audit events, list review tasks, and record a human review decision. Keep endpoint names and payloads consistent throughout the specification.
5. Define at least five synthetic demo cases: routine claim, missing information, inactive/excluded/uncertain coverage, potential fraud, and high estimate/high risk. Describe expected routing/outcomes.
6. Define how auditability will work: persist each stage’s structured result, timestamps, evidence/source references, route/reason, errors and final status.
7. Include explicit data-safety and reliability requirements: synthetic or approved data only; never log secrets; validate structured model output; treat retrieved text and documents as untrusted data rather than instructions; prevent duplicate simulated settlement records on retries; keep human review decisions auditable.
8. Recommend a practical implementation order that fits the 4–5 day goal, but do not spend the answer planning a long-term roadmap.

IMPORTANT CONSTRAINTS
- No MCP, PostgreSQL, external vector database, real payment gateway, live carrier integration, or automatic final coverage denial.
- Do not build all five stages as independent microservices. They may be separate LangGraph nodes/modules in one application.
- Do not pretend SQLite FTS5 provides semantic vector retrieval.
- Do not invent available client documents, API access, model credentials or stakeholder approvals. Mark assumptions clearly.
- Do not start coding in this stage.

Finish with a short list of decisions that genuinely block implementation. For all other gaps, state a safe assumption and proceed rather than asking a long list of questions.
```

---

# Prompt 2 — Implement the Approved PoC

```text
Act as a senior Python engineer. Implement the Autonomous Multi-Agent Insurance Claims Processing internal PoC using the approved Stage 1 specification and the agreed constraints below.

FIRST: inspect the current repository and read the approved `docs/implementation_spec.md`, `docs/architecture.md` and `docs/acceptance_criteria.md`. If these files do not exist, stop and tell me which Stage 1 deliverable is missing; do not invent a conflicting architecture. Preserve existing useful code and conventions. Avoid overwriting unrelated files.

FIXED ARCHITECTURE
- Python + FastAPI backend.
- LangGraph orchestrates five logical agent nodes: intake, policy validation, fraud detection, risk assessment and settlement.
- One validated shared ClaimState contract between nodes.
- SQLite for claims, persisted workflow state/results, review tasks and audit events.
- SQLite FTS5 for local keyword-based retrieval from indexed policy/repair document chunks, including source filename and page/section metadata where available.
- One configurable LLM provider behind a small adapter; do not hardcode API keys. Provide an explicit deterministic development/mock mode so tests and a basic demo run without provider credentials. Clearly mark generated/mock results as such.
- Ordinary Python functions/API clients for mock policy status/limits, image/duplicate checks, repair-cost calculations and simulated settlement ledger actions.
- MCP is excluded. Do not install MCP packages or create MCP servers/clients.
- No PostgreSQL, no external vector database, no live policy APIs and no real payments.
- FastAPI Swagger/OpenAPI is sufficient for the minimum interface. Keep any custom UI minimal and only implement it if it fits the approved spec.

WORKFLOW BEHAVIOR
- Intake validates required fields and records missing details. Missing required data pauses the workflow with NEEDS_INFO.
- Policy validation combines retrieved/cited policy wording with a mocked authoritative policy-status/coverage result. If coverage is excluded, inactive or uncertain, create a review task and a cited draft; never finalize an automatic denial.
- Fraud detection computes/records transparent demo indicators and a score based on explicit rules. Score >= 75 or significant uncertainty routes to human/SIU review; do not assert that an anomaly proves fraud.
- Risk assessment uses explicit deterministic rules and available sample repair benchmarks.
- Settlement arithmetic is deterministic and validated, for example `max(0, approved_estimate - deductible - depreciation)`, using consistent currency/rounding rules.
- Simulated STP is allowed only when risk_tier is LOW, fraud_score < 25 and proposed payout is within the configurable demo authority limit (default USD 5,000). Otherwise route to an adjuster. Never move real money.
- All routing thresholds are configurable and documented as demo-only values.
- Every stage persists its structured output, status, timestamps, evidence references, route/reason and relevant errors to SQLite.
- Ensure retries cannot create duplicate simulated settlement ledger entries for the same claim/decision.

IMPLEMENTATION REQUIREMENTS
1. Build the smallest complete, maintainable implementation consistent with the approved specification. Use Pydantic models and explicit types; separate agents, graph orchestration, retrieval, tool functions, DB access and API routes into understandable modules.
2. Provide database initialization/schema creation and predictable local startup. Handle SQLite connections/transactions correctly and document how to reset local demo data safely.
3. Implement document ingestion for the sample document formats specified in Stage 1. Preserve source file and page/section metadata. If OCR or a dependency is unavailable, state the limitation and provide a clear supported path rather than silently returning invented text.
4. Implement FTS5 indexing and retrieval with clear no-results behavior. The Policy/Risk stages must distinguish retrieved evidence from mock authoritative data. Never fabricate citations or claim source support when retrieval returned nothing.
5. Implement the API endpoints agreed in Stage 1 for claim submission/processing, claim detail/status, audit history, review queue and review decisions. Use validation and meaningful HTTP error responses.
6. Seed a small, explicitly synthetic dataset for the five demo cases in the specification. Never use real personal or client data.
7. Add unit and integration tests for model/schema validation, retrieval/source references, deterministic payout math, graph routing for each scenario, human review actions, SQLite persistence and duplicate-settlement protection.
8. Add `.env.example` without secrets, dependency/lock information appropriate to the repository, a README with installation/start/test instructions and a short demo walkthrough.
9. Keep the code runnable at each step. Prefer simple, known-compatible dependencies over unnecessary tooling. Do not add authentication, deployment infrastructure, vector DBs, advanced OCR or a large frontend unless the approved spec specifically requires it.
10. Run the tests and basic startup checks when tool access permits. Fix errors you can reproduce. Report tests not run or dependencies that cannot be installed; do not claim they passed without evidence.

DEFINITION OF DONE
A user can submit/process a synthetic claim and inspect its final status, route explanation, policy evidence where available, stage outputs and audit history. At minimum, the routine, missing-info and human-review cases work end to end. The other specified scenarios have tests and are demoable where the approved input assets support them.

At completion, summarize the implemented files and API endpoints, exact run/test commands, test results, required environment variables, known limitations and any remaining blockers. Do not redesign the architecture unless a concrete implementation issue requires it; explain any necessary deviation from the approved Stage 1 specification.
```

---

# Prompt 3 — Validate, Fix and Prepare the Internal Demo

```text
Act as an independent senior QA engineer and PoC reviewer. Validate the actual implementation of Autonomous Multi-Agent Insurance Claims Processing against the approved Stage 1 specification and Stage 2 code. Your job is to find and fix concrete defects, then prepare a reliable internal/client demonstration. Do not merely review the README or assert that the design looks correct—inspect and run the implementation where the environment permits.

NON-NEGOTIABLE ARCHITECTURE
- LangGraph + FastAPI + SQLite + SQLite FTS5 retrieval + ordinary Python tools.
- Five logical workflow stages: intake, policy validation, fraud detection, risk assessment and settlement.
- MCP is excluded. No PostgreSQL, no external vector database, no live carrier system and no real payment execution.
- Only synthetic or explicitly approved sample data. Do not include secrets or sensitive client data in logs, test artifacts or demo material.

VALIDATION TASKS
1. Read the approved implementation spec, architecture and acceptance criteria, then trace each requirement to code and tests.
2. Run the documented installation/startup checks and full test suite if the environment permits. Record actual commands and outcomes. Never claim a test ran when it did not.
3. Exercise at least these five synthetic scenarios and confirm the expected graph route, status and persisted audit history:
   a. Routine eligible claim -> deterministic proposed payout and simulated settlement only when all configured demo gates pass.
   b. Missing required document/field -> NEEDS_INFO and no downstream settlement.
   c. Inactive, excluded or uncertain coverage -> evidence-backed exception/draft and human review; no automatic final denial.
   d. Fraud score >= 75 or significant uncertainty -> human/SIU review; no automatic declaration of fraud.
   e. High-risk or over-authority claim -> adjuster review rather than simulated STP.
4. Verify that policy retrieval returns actual indexed text and source filename/page/section metadata where available. Verify that no citations are invented when no matching source exists. Confirm the application differentiates policy wording from the mocked authoritative policy-status response.
5. Verify the payout calculation, non-negative amount, currency rounding, required-value validation and the configurable demo thresholds. Test edge cases such as zero/negative invalid inputs, missing deductible, repeated processing and duplicate settlement attempts.
6. Verify persistence in SQLite for claims, ClaimState, agent outputs, route reasons, timestamps, errors, evidence references and human decisions. Confirm retry/reprocessing cannot duplicate the simulated settlement record.
7. Verify API request validation and expected error responses. Inspect for unsafe file paths, secret leakage, untrusted document instructions, broad exception swallowing, misleading status messages and accidental live external actions.
8. Fix reproducible defects in code and tests. Keep changes within the approved scope; do not add MCP, PostgreSQL, a vector DB, real payment handling, a production fraud model or an unnecessary UI redesign.
9. Prepare a concise stakeholder demo pack:
   - final architecture and claim-flow diagrams that match the implementation;
   - exact setup/run/test commands;
   - an ordered 5–10 minute demo script showing one routine claim and at least two exception cases;
   - a table of acceptance criteria with PASS / FAIL / NOT TESTED, evidence and limitations;
   - a brief known-limitations section, including whether the LLM was live or mocked and the limits of SQLite FTS5 keyword retrieval.
10. Report observed metrics only. Do not fabricate accuracy, fraud recall, time savings or production-readiness claims from a tiny synthetic dataset. If the PDF’s proposed KPI targets are retained, mark them as targets and report measured results separately.

FINAL RESPONSE FORMAT
- Overall status: Demo-ready / Demo-ready with limitations / Not yet demo-ready.
- What you tested and exact outcomes.
- Defects found and fixes made.
- Acceptance-criteria status table.
- Steps to run the application and execute the demo.
- Remaining blockers and limitations, prioritized.

Be candid. If an integration, model call or test could not be executed in this environment, state that plainly and explain the consequence for the demo.
```

---

## How to use the prompts

1. **Run Prompt 1 first** with the original PDF available. Review the generated specification and diagrams before approving it.
2. **Run Prompt 2** in the same repository/workspace, with the approved Stage 1 files retained.
3. **Run Prompt 3** only after the implementation exists. Keep its test report as the evidence for the internal demonstration.

## Final agreed scope

- Internal/client PoC for synthetic/sample motor insurance claims.
- LangGraph + FastAPI + SQLite + SQLite FTS5 + one configurable LLM provider.
- Five logical agent stages, structured shared state, conditional routing, auditable outputs and human review.
- Mocked external tools and simulated settlement only.
- No MCP, PostgreSQL, external vector database, live insurer integrations or real payment execution.
