# System Architecture: Autonomous Multi-Agent Insurance Claims PoC

## 1. High-Level Component Architecture

The diagram below illustrates the structural topology of the system, comprising the React UI, FastAPI Backend, LangGraph Orchestration Layer, SQLite Persistence + FTS5 Retrieval, and Mock External Adapters (strictly without MCP).

```mermaid
flowchart TB
    subgraph FRONTEND["Frontend (React + Vite)"]
        UI_DASH["Interactive Claims Dashboard"]
        UI_SIM["1-Click Scenario Runner"]
        UI_GRAPH["Real-Time Agent Flow Visualizer"]
        UI_QUEUE["Adjuster Review & SIU Queue"]
        UI_AUDIT["Audit & Evidence Explorer"]
    end

    subgraph BACKEND["FastAPI Backend Application"]
        API_ROUTER["API Router (/api/claims, /api/reviews, /api/scenarios)"]
        ORCHESTRATOR["LangGraph Orchestration Engine"]
        ADAPTER_SVC["Service Adapter Layer"]
    end

    subgraph AGENTS["LangGraph 5-Agent Pipeline"]
        direction TB
        A1["1. Intake Agent<br/>(Extract & Validate Completeness)"]
        A2["2. Policy Validation Agent<br/>(Policy Check & Clause Retrieval)"]
        A3["3. Fraud Detection Agent<br/>(EXIF Forensics & Duplicate Hashing)"]
        A4["4. Risk Assessment Agent<br/>(OEM Valuation & Risk Tiering)"]
        A5["5. Settlement Agent<br/>(Deterministic Calculation & Routing)"]
    end

    subgraph STORAGE["Local SQLite Persistence"]
        DB_CLAIMS[("claims table")]
        DB_AUDIT[("audit_events & agent_runs")]
        DB_REVIEWS[("review_tasks")]
        DB_LEDGER[("simulated_ledger (Idempotent)")]
        DB_FTS5[("policy_chunks & FTS5 Index")]
    end

    subgraph MOCKS["Deterministic Mock Tool Adapters (No MCP)"]
        M_PAS["Mock PAS / Billing Service"]
        M_EXIF["Mock EXIF & pHash Forensic Service"]
        M_OEM["Mock OEM Labor & Parts Estimator"]
        M_PAY["Mock Settlement Ledger Adapter"]
        M_LLM["LLM Adapter (Offline Mock / Configurable)"]
    end

    FRONTEND <==>|JSON / REST| API_ROUTER
    API_ROUTER --> ORCHESTRATOR
    ORCHESTRATOR --> A1
    A1 --> A2 --> A3 --> A4 --> A5

    A1 -.-> M_LLM
    A2 -.-> M_PAS
    A2 -.-> DB_FTS5
    A3 -.-> M_EXIF
    A4 -.-> M_OEM
    A5 -.-> M_PAY

    ORCHESTRATOR <==> STORAGE
    API_ROUTER <==> STORAGE
```

---

## 2. End-to-End Claim Execution & Exception Flow

The diagram below details the exact state transitions, conditional gating logic, and exception exit ramps for the five demo scenarios.

```mermaid
flowchart TD
    START([Claim Submitted: FNOL Data & Documents]) --> N_INTAKE["Agent 1: Claims Intake<br/>• Entity Extraction<br/>• Required Fields Validation"]

    N_INTAKE --> GATE1{"Gate 1: Completeness<br/>completeness == 1.0?"}
    
    GATE1 -- "No (Missing VIN, Invoice, etc.)" --> EXIT_NEEDS_INFO["Route: NEEDS_INFO<br/>• Status: NEEDS_INFO<br/>• Task: Claimant Info Request<br/>• Action: Halt Pipeline"]
    
    GATE1 -- "Yes (All Mandatory Fields)" --> N_POLICY["Agent 2: Policy Validation<br/>• Mock PAS Status Check<br/>• FTS5 Policy Clause Retrieval<br/>• Peril Coverage Verification"]

    N_POLICY --> GATE2{"Gate 2: Policy Eligible?<br/>Active & Peril Covered?"}
    
    GATE2 -- "No (Lapsed / Excluded Clause)" --> EXIT_COVERAGE["Route: COVERAGE_EXCEPTION<br/>• Status: PENDING_REVIEW<br/>• Task: Coverage Exception Draft<br/>• Action: Cites Section & Halts"]
    
    GATE2 -- "Yes (Policy Active & Covered)" --> N_FRAUD["Agent 3: Fraud Detection<br/>• EXIF Metadata Verification<br/>• Photo Duplicate Hash Match<br/>• Compute Fraud Score (0-100)"]

    N_FRAUD --> GATE3{"Gate 3: Fraud Escalation?<br/>Fraud Score >= 75?"}
    
    GATE3 -- "Yes (Suspicious EXIF / Duplicate Image)" --> EXIT_SIU["Route: SIU_FREEZE<br/>• Status: PENDING_REVIEW<br/>• Task: SIU Investigation Referral<br/>• Action: Freeze Automated Payout"]

    GATE3 -- "No (Fraud Score < 75)" --> N_RISK["Agent 4: Risk Assessment<br/>• Compare OEM Parts & Labor Guide<br/>• Apply Depreciation Schedule<br/>• Assign Risk Tier: LOW / MED / HIGH"]

    N_RISK --> N_SETTLE["Agent 5: Settlement Agent<br/>• Math: max(0, Approved - Deductible - Depr)<br/>• Rounding & Currency Validation"]

    N_SETTLE --> GATE4{"Gate 4: STP Gate<br/>Risk == LOW &<br/>Fraud < 25 &<br/>Payout <= $5,000?"}

    GATE4 -- "Yes (All STP Rules Satisfied)" --> EXIT_STP["Route: SIMULATED_STP<br/>• Status: SETTLED_STP<br/>• Ledger: Record Simulated Disbursement<br/>• Action: Complete Fast-Track"]

    GATE4 -- "No (High Risk or > $5,000)" --> EXIT_ADJUSTER["Route: ADJUSTER_APPROVAL<br/>• Status: PENDING_REVIEW<br/>• Task: Adjuster Approval Queue<br/>• Action: Requires Human Sign-Off"]

    EXIT_NEEDS_INFO --> AUDIT["Persist Immutable Audit Event & ClaimState in SQLite"]
    EXIT_COVERAGE --> AUDIT
    EXIT_SIU --> AUDIT
    EXIT_STP --> AUDIT
    EXIT_ADJUSTER --> AUDIT
    
    AUDIT --> FINISH([State Persisted & Emitted to UI])
```

---

## 3. Human-in-the-Loop (HITL) Workflow

When a claim lands in `PENDING_REVIEW` or `NEEDS_INFO`:
1. A record is inserted into `review_tasks` with `priority` and `task_type`.
2. The React frontend presents the task in the **Human Review Queue** with complete context (extracted claim fields, cited policy clauses, fraud triggers, and proposed numbers).
3. The adjuster or investigator clicks **Approve**, **Reject**, or **Request Information**.
4. The backend API (`POST /api/reviews/{id}/decision`) updates the task, adjusts the settlement amount if requested, updates `claims`, logs an audit entry, and records the simulated disbursement if approved.
