# Implementation Specification: Autonomous Multi-Agent Insurance Claims Processing PoC

## 1. Problem Statement
Traditional motor insurance claims handling suffers from fragmented manual reviews, slow policy checks, and delayed decision handoffs between adjusters, SIU (Special Investigations Unit), and settlement teams. 

This internal Proof of Concept (PoC) demonstrates an automated, decision-support claims orchestration workflow. It processes synthetic motor claims through five specialized agent stages, grounding decisions in local policy documents and deterministic business rules, while safely routing edge cases and exceptions to human adjusters.

---

## 2. Scope & Non-Goals

### In Scope
- **Domain**: Synthetic/sample motor insurance claims (First Notice of Loss, repair estimates, vehicle damage photos, policy contracts).
- **Core Orchestrator**: LangGraph state graph governing a canonical, shared `ClaimState` contract.
- **5 Agent Stages**:
  1. *Claims Intake Agent*: Extracts entities, validates required fields, flags missing data (`NEEDS_INFO`).
  2. *Policy Validation Agent*: Verifies policy status via mock lookup, retrieves relevant clauses/deductibles via SQLite FTS5 keyword RAG, drafts coverage exceptions.
  3. *Fraud Detection Agent*: Checks duplicate images (perceptual hashing mock), EXIF timestamp/GPS consistency, calculates composite fraud score (0–100).
  4. *Risk Assessment Agent*: Benchmarks repair estimates against sample OEM parts/labor guides, applies depreciation, assigns risk tier (`LOW`, `MEDIUM`, `HIGH`).
  5. *Settlement Agent*: Evaluates deterministic settlement arithmetic `max(0, approved_estimate - deductible - depreciation)` and routes to simulated Straight-Through Processing (STP) or Human Review Queue.
- **Storage & RAG**: SQLite database with SQLite FTS5 virtual table indexing policy/repair text chunks with source file and page metadata.
- **Backend**: FastAPI REST API providing claim submission, inspection, audit logs, and review decision endpoints.
- **Frontend**: Modern React + Vite UI providing real-time pipeline visualization, single-click synthetic scenario execution, adjuster review interface, and audit trail inspection.
- **Mocks & Testing**: Deterministic mock adapters for external systems and offline LLM mode enabling full test and demo reproducibility without external API dependencies.

### Explicit Non-Goals
- **No Model Context Protocol (MCP)**: MCP is excluded from this PoC; standard Python functions/classes are used instead.
- **No Vector Databases / External DBs**: No PostgreSQL, pgvector, Chroma, Pinecone.
- **No Real Carrier APIs or Payments**: No live Guidewire/Duck Creek PAS, real payment rails (ACH/Stripe), or outbound notifications.
- **No Automated Final Coverage Denials**: All denials remain draft recommendations with citations for human review.
- **No Production Fraud Conclusions**: Fraud flags represent an investigation referral, never an accusation.

---

## 3. Assumptions & Decisions Made

| Decision Area | Selected Design | Rationale |
|---|---|---|
| **Orchestration** | Python + LangGraph | Stateful workflow, conditional edge branching, deterministic exit ramps. |
| **Backend** | FastAPI (Python) | High performance async endpoints, native Pydantic schema validation. |
| **Frontend** | React + Vite (Vanilla CSS) | Responsive, visual pipeline tracking, human-in-the-loop actions. |
| **Database** | SQLite + SQLite FTS5 | Zero external infrastructure, transactional persistence, keyword RAG. |
| **External Tools** | Pure Python Mock Modules | Fast, zero flaky network dependencies, deterministic test cases. |
| **LLM Provider** | Configurable adapter with Mock fallback | Allows zero-credential offline execution and live provider integration. |
| **Demo Authority Limit** | USD 5,000 | Configurable upper bound for automated simulated payout. |
| **Fraud Escalation Threshold**| Fraud Score $\ge 75$ | Deterministic cutoff for SIU escalation. |

---

## 4. Shared `ClaimState` Data Contract

The pipeline communicates through a single canonical typed state dictionary:

```python
class ClaimState(TypedDict, total=False):
    claim_id: str
    claim_type: str
    intake_data: dict          # policy_no, loss_date, loss_type, claimed_amt, documents, vin, vehicle_info
    completeness: float        # 0.0 to 1.0
    missing_fields: list[str]  # e.g., ["repair_estimate", "vin"]
    
    policy_validation: dict    # active, coverage_type, deductible, policy_limit, citations, eligible, exception_draft
    fraud_report: dict         # fraud_score (0-100), indicators, photo_verified, siu_escalate
    risk_assessment: dict      # original_estimate, benchmark_estimate, approved_estimate, depreciation, risk_tier, notes
    settlement_decision: dict  # proposed_payout, status (SIMULATED_STP, NEEDS_APPROVAL, DRAFT_DENIAL), authority_limit, txn_ref
    
    current_status: str        # INTAKE, POLICY_CHECK, FRAUD_CHECK, RISK_ASSESSMENT, SETTLED, NEEDS_INFO, PENDING_REVIEW
    route_reason: str          # Description of the routing decision
    audit_events: list[dict]   # List of captured audit logs
    errors: list[str]
```

---

## 5. System Components & Interfaces

### 5.1 Backend Layout
- `backend/app/main.py`: FastAPI application entry point, CORS, and router registration.
- `backend/app/api/`: REST endpoints for `/claims`, `/reviews`, `/scenarios`, `/audit`.
- `backend/app/core/config.py`: Environment settings (authority limits, fraud thresholds, DB paths).
- `backend/app/db/`: SQLite connection manager, schema migrations, and FTS5 search indexing.
- `backend/app/models/`: Pydantic input/output schemas and state models.
- `backend/app/agents/`:
  - `intake_agent.py`
  - `policy_agent.py`
  - `fraud_agent.py`
  - `risk_agent.py`
  - `settlement_agent.py`
- `backend/app/workflow/graph.py`: LangGraph workflow definition and conditional routing gates.
- `backend/app/services/`: Mock adapters for Policy Administration, Forensics, OEM Cost Estimator, Payment Ledger, and LLM Adapter.

### 5.2 SQLite Schema
- `claims`: `claim_id` (PK), `status`, `claim_type`, `created_at`, `updated_at`, `state_json`.
- `agent_runs`: `run_id` (PK), `claim_id`, `agent_name`, `input_json`, `output_json`, `status`, `duration_ms`, `created_at`.
- `audit_events`: `event_id` (PK), `claim_id`, `stage`, `event_type`, `route_reason`, `evidence_json`, `created_at`.
- `review_tasks`: `task_id` (PK), `claim_id`, `task_type` (`NEEDS_INFO`, `COVERAGE_EXCEPTION`, `SIU_FRAUD`, `ADJUSTER_APPROVAL`), `priority`, `status` (`PENDING`, `APPROVED`, `REJECTED`), `created_at`, `decision_note`, `resolved_at`.
- `policy_chunks`: `chunk_id` (PK), `source_file`, `section_title`, `page_number`, `chunk_text`.
- `policy_chunks_fts`: FTS5 virtual table indexing `section_title` and `chunk_text`.
- `simulated_ledger`: `txn_id` (PK), `claim_id` (UNIQUE), `amount`, `status`, `created_at` (prevents duplicate payouts).

---

## 6. API Contract

1. `POST /api/claims/submit`
   - **Payload**: `{ "claim_id": str (optional), "policy_no": str, "claimant_name": str, "loss_date": str, "loss_type": str, "claimed_amt": float, "vin": str, "documents": list[dict], "photo_metadata": list[dict] }`
   - **Response**: Full resolved `ClaimState` and execution summary.
2. `GET /api/claims/{claim_id}`
   - **Response**: Current claim status, full state, and review tasks.
3. `GET /api/claims/{claim_id}/audit`
   - **Response**: Chronological list of agent outputs, routing reasons, and evidence citations.
4. `GET /api/reviews`
   - **Query Params**: `status=PENDING`
   - **Response**: List of human review tasks with associated claim summaries.
5. `POST /api/reviews/{task_id}/decision`
   - **Payload**: `{ "decision": "APPROVED" | "REJECTED" | "REQUEST_INFO", "notes": str, "adjusted_payout": float (optional) }`
   - **Response**: Updated task and final claim state.
6. `GET /api/scenarios`
   - **Response**: Pre-configured synthetic scenarios ready for 1-click execution.
7. `POST /api/scenarios/run/{scenario_key}`
   - **Response**: Immediate execution result of a synthetic scenario.

---

## 7. Data Safety, Untrusted Input & Reliability

1. **Untrusted Documents & Text**: Document text and policy excerpts retrieved via FTS5 are treated strictly as data payloads and never executed as dynamic code or prompt instructions.
2. **Zero Live Payments**: The settlement ledger is simulated in SQLite and rejects duplicate payouts via a `UNIQUE(claim_id)` constraint.
3. **Draft Denials**: If a policy clause excludes coverage, the system outputs a formatted recommendation with cited sections for an adjuster to confirm or overturn.
4. **Offline Determinism**: The system operates with zero external network dependencies, ensuring 100% test reproducibility.
