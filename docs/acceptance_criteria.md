# Acceptance Criteria & Demo Scenarios: Autonomous Multi-Agent Insurance Claims PoC

## 1. Measurable Functional Acceptance Criteria

| Criteria ID | Category | Requirement | Verification Method |
|---|---|---|---|
| **AC-01** | **Orchestration** | All 5 agents execute sequentially within a single LangGraph state graph. | Unit/Integration tests verifying node handoffs via `ClaimState`. |
| **AC-02** | **Intake Validation** | If mandatory fields (VIN, estimate, loss date) are missing, pipeline pauses at Gate 1 with status `NEEDS_INFO`. | Test scenario `scenario_missing_info`. |
| **AC-03** | **FTS5 Retrieval** | Policy validation retrieves actual cited text and section titles from SQLite FTS5 index. Returns explicit empty message if no matches; never fabricates citations. | Search index unit tests and query verification. |
| **AC-04** | **Policy Exception** | Excluded peril or lapsed policy produces a cited draft exception for human review; no automated final denial. | Test scenario `scenario_excluded_policy`. |
| **AC-05** | **Fraud Escalation** | Fraud score $\ge 75$ halts automated settlement and routes to SIU review queue. | Test scenario `scenario_fraud_freeze`. |
| **AC-06** | **Deterministic Math** | Settlement calculation strictly follows `max(0, approved_estimate - deductible - depreciation)` with 2 decimal precision. | Unit tests covering positive, zero, and boundary inputs. |
| **AC-07** | **STP Gate** | Simulated STP occurs ONLY if risk tier is `LOW`, fraud score $< 25$, and proposed payout $\le \$5,000$. | Test scenario `scenario_routine_stp`. |
| **AC-08** | **Authority Gate** | Proposed payout $> \$5,000$ or risk $\ne \text{LOW}$ routes to human adjuster approval. | Test scenario `scenario_high_estimate`. |
| **AC-09** | **Idempotent Ledger** | Re-processing or re-submitting an already settled claim does not create duplicate payout records in `simulated_ledger`. | SQLite unique constraint test on `claim_id`. |
| **AC-10** | **Audit Trail** | Every stage records timestamp, node name, route reason, and output payload in `audit_events`. | Inspecting SQLite `audit_events` table after run. |
| **AC-11** | **HITL Decision** | Adjuster can approve, reject, or request info on queued review tasks via API and UI. | End-to-end API test and UI action test. |

---

## 2. The 5 Synthetic Demo Scenarios

These 5 scenarios must be runnable with 1-click in the UI and covered by automated integration tests:

### Scenario 1: Routine Low-Severity Claim (Fast-Track STP)
- **Claim ID**: `CLM-DEMO-001`
- **Input**: Complete documentation, policy `POL-AUTO-99201` active, comprehensive coverage, rear collision, claimed \$3,200, valid photos with matching EXIF.
- **Expected Route**:
  - Intake: `completeness: 1.0` -> Gate 1 Pass.
  - Policy: Active, \$500 deductible, covered under Section 4.2 -> Gate 2 Pass.
  - Fraud: Clean EXIF, no hash matches, fraud score `12` -> Gate 3 Pass.
  - Risk: OEM labor benchmark approved \$2,950, \$210 depreciation, risk tier `LOW`.
  - Settlement: Payout = `2950 - 500 - 210 = $2,240.00`.
  - Gate 4: Low risk, fraud $< 25$, payout $\le \$5,000$ -> **SIMULATED_STP**.
- **Final Status**: `SETTLED_STP` with generated transaction reference `ACH-XXXXXX`.

### Scenario 2: Incomplete Submission (Needs Info)
- **Claim ID**: `CLM-DEMO-002`
- **Input**: Missing vehicle VIN and itemized repair invoice.
- **Expected Route**:
  - Intake: `completeness: 0.5`, `missing_fields: ["vin", "repair_estimate"]`.
  - Gate 1: Completeness $< 1.0$ -> Halts immediately.
- **Final Status**: `NEEDS_INFO`, review task created requesting missing documents from claimant.

### Scenario 3: Excluded Peril / Policy Exception (HITL Draft Denial)
- **Claim ID**: `CLM-DEMO-003`
- **Input**: Active policy, but damage caused by intentional track racing / non-covered wear and tear under Section 8.3.
- **Expected Route**:
  - Intake: `completeness: 1.0` -> Gate 1 Pass.
  - Policy: Clause retrieved citing Section 8.3 (Track / Racing Exclusion).
  - Gate 2: Ineligible -> Bypasses Fraud/Risk/Settlement.
- **Final Status**: `PENDING_REVIEW` with task type `COVERAGE_EXCEPTION` containing cited draft denial for adjuster approval.

### Scenario 4: Suspected Fraud / Duplicate Photo (SIU Freeze)
- **Claim ID**: `CLM-DEMO-004`
- **Input**: Vehicle bumper damage photo matches perceptual hash of previously submitted claim `CLM-2024-1102` + EXIF timestamp date predates reported incident.
- **Expected Route**:
  - Intake: `completeness: 1.0` -> Gate 1 Pass.
  - Policy: Active policy -> Gate 2 Pass.
  - Fraud: Duplicate image match (+40 score) + EXIF timestamp mismatch (+40 score) -> `fraud_score: 80`.
  - Gate 3: Score $\ge 75$ -> Halts automated processing.
- **Final Status**: `PENDING_REVIEW` with task type `SIU_FRAUD` routed to Special Investigations Unit.

### Scenario 5: High Value / Over-Authority Limit (Adjuster Approval)
- **Claim ID**: `CLM-DEMO-005`
- **Input**: Complete claim for luxury front-end collision, active policy with \$1,000 deductible, claimed \$18,500, clean fraud checks.
- **Expected Route**:
  - Intake: `completeness: 1.0` -> Gate 1 Pass.
  - Policy: Active, coverage verified -> Gate 2 Pass.
  - Fraud: Clean EXIF, fraud score `10` -> Gate 3 Pass.
  - Risk: Approved estimate \$16,200, depreciation \$1,200, risk tier `HIGH` (due to severity and amount).
  - Settlement: Payout = `16200 - 1000 - 1200 = $14,000.00`.
  - Gate 4: Proposed payout $> \$5,000$ and risk `HIGH` -> Exceeds STP threshold.
- **Final Status**: `PENDING_REVIEW` with task type `ADJUSTER_APPROVAL` queued with pre-calculated decision brief.
