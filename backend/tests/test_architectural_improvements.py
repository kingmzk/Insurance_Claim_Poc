import pytest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection
from backend.app.core.auth import Role, validate_review_authorization, resolve_reviewer_role
from backend.app.services.forensics_service import ForensicsService
from backend.app.workflow.graph import claims_graph, resume_claim_workflow, create_traced_node
from backend.app.models.state import ClaimState

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    conn = get_db_connection()
    conn.execute("DELETE FROM review_tasks;")
    conn.execute("DELETE FROM audit_events;")
    conn.execute("DELETE FROM simulated_ledger;")
    conn.execute("DELETE FROM claims;")
    conn.commit()
    conn.close()

# ------------------------------------------------------------------------------
# 1. Test Parallel Execution & Evaluator Join
# ------------------------------------------------------------------------------
def test_parallel_fraud_and_risk_execution():
    """Verifies that fraud and risk nodes run and merge cleanly at the evaluator node."""
    initial_state = {
        "claim_id": "CLM-TEST-PARALLEL",
        "claim_type": "motor",
        "intake_data": {
            "policy_no": "POL-AUTO-99201",
            "claimant_name": "Sarah Connor",
            "loss_date": "2026-03-25",
            "loss_type": "rear_collision",
            "claimed_amt": 2800.00,
            "vin": "1HGCR2F83HA998877",
            "vehicle_make_model": "2023 Honda Accord",
            "incident_description": "Rear bumper tap at intersection",
            "documents": [{"doc_type": "repair_estimate", "filename": "quote.pdf"}],
            "photos": []
        },
        "completeness": 0.0,
        "missing_fields": [],
        "audit_events": [],
        "errors": []
    }
    
    cfg = {"configurable": {"thread_id": "CLM-TEST-PARALLEL"}}
    final_state = claims_graph.invoke(initial_state, config=cfg)
    
    # Both fraud_report and risk_assessment must be populated
    assert "fraud_report" in final_state
    assert "risk_assessment" in final_state
    assert final_state["fraud_report"]["fraud_score"] is not None
    assert final_state["risk_assessment"]["risk_tier"] is not None
    
    # Audit events must contain both stages
    stages = [e["stage"] for e in final_state.get("audit_events", [])]
    assert "FRAUD_DETECTION" in stages
    assert "RISK_ASSESSMENT" in stages
    assert "FRAUD_RISK_EVALUATION" in stages

# ------------------------------------------------------------------------------
# 2. Test Multi-Signal Fraud Intelligence (Claimant Velocity & Cross-Claim VIN)
# ------------------------------------------------------------------------------
def test_multi_signal_fraud_claimant_velocity():
    """Verifies that repetitive claims by the same claimant increase the fraud score."""
    # Seed 2 prior claims in database for claimant Robert Bell
    conn = get_db_connection()
    c1 = {"intake_data": {"claimant_name": "Robert Bell", "policy_no": "POL-1", "vin": "VIN-AAA"}}
    c2 = {"intake_data": {"claimant_name": "Robert Bell", "policy_no": "POL-1", "vin": "VIN-BBB"}}
    conn.execute("INSERT INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json) VALUES ('CLM-P1', 'SETTLED', 'motor', '2026-01-01', '2026-01-01', ?);", (json.dumps(c1),))
    conn.execute("INSERT INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json) VALUES ('CLM-P2', 'SETTLED', 'motor', '2026-02-01', '2026-02-01', ?);", (json.dumps(c2),))
    conn.commit()
    conn.close()

    # Now inspect third claim for Robert Bell
    result = ForensicsService.inspect_claim({
        "claimant_name": "Robert Bell",
        "policy_no": "POL-1",
        "vin": "VIN-CCC",
        "claimed_amt": 3000.0,
        "photos": []
    }, current_claim_id="CLM-NEW")

    assert result["network_signals"]["prior_claims_by_claimant"] >= 2
    assert any("HIGH_CLAIM_VELOCITY" in f for f in result["flags"])

def test_multi_signal_fraud_cross_claim_vin_collusion():
    """Verifies that the same VIN claimed under a different policy triggers collusion warning."""
    conn = get_db_connection()
    past_claim = {"intake_data": {"claimant_name": "Original Owner", "policy_no": "POL-ORIG", "vin": "VIN-SUSPECT-01"}}
    conn.execute("INSERT INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json) VALUES ('CLM-PAST', 'SETTLED', 'motor', '2026-01-01', '2026-01-01', ?);", (json.dumps(past_claim),))
    conn.commit()
    conn.close()

    result = ForensicsService.inspect_claim({
        "claimant_name": "Different Claimant",
        "policy_no": "POL-NEW",
        "vin": "VIN-SUSPECT-01",
        "claimed_amt": 4000.0,
        "photos": []
    }, current_claim_id="CLM-NEW-02")

    assert len(result["network_signals"]["vin_cross_claim_matches"]) >= 1
    assert any("CROSS_CLAIM_VIN_COLLUSION" in f for f in result["flags"])

# ------------------------------------------------------------------------------
# 3. Test Role-Based Authorization & Financial Authority Limits
# ------------------------------------------------------------------------------
def test_role_resolution():
    assert resolve_reviewer_role("adjuster_01") == Role.ADJUSTER
    assert resolve_reviewer_role("senior_adjuster_05") == Role.SENIOR_ADJUSTER
    assert resolve_reviewer_role("siu_specialist_02") == Role.SIU_INVESTIGATOR
    assert resolve_reviewer_role("claims_manager_01") == Role.CLAIMS_MANAGER
    assert resolve_reviewer_role("coverage_attorney", explicit_role="policy_specialist") == Role.POLICY_SPECIALIST

def test_adjuster_cannot_approve_above_authority_limit():
    """A standard adjuster should be forbidden from approving a $14,000 claim."""
    client.post("/api/scenarios/run/high_estimate")
    res = client.get("/api/reviews?status=PENDING")
    tasks = res.json()
    high_task = next((t for t in tasks if t["claim_id"] == "CLM-DEMO-005"), None)
    assert high_task is not None

    # Standard adjuster tries to approve $14,000 -> Should return HTTP 403 Forbidden
    resp = client.post(f"/api/reviews/{high_task['task_id']}/decision", json={
        "decision": "APPROVED",
        "notes": "Attempting unauthorized approval as standard adjuster",
        "adjusted_payout": 14000.00,
        "reviewer_id": "junior_adjuster_01",
        "reviewer_role": "adjuster"
    })
    assert resp.status_code == 403
    assert "exceeds" in resp.json()["detail"].lower()

def test_senior_adjuster_can_approve_high_estimate():
    """A senior adjuster is authorized to approve high estimate claims."""
    client.post("/api/scenarios/run/high_estimate")
    res = client.get("/api/reviews?status=PENDING")
    tasks = res.json()
    high_task = next((t for t in tasks if t["claim_id"] == "CLM-DEMO-005"), None)
    assert high_task is not None

    resp = client.post(f"/api/reviews/{high_task['task_id']}/decision", json={
        "decision": "APPROVED",
        "notes": "Authorized senior approval",
        "adjusted_payout": 14000.00,
        "reviewer_id": "senior_adjuster_07"
    })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "APPROVED"
    assert resp.json()["reviewer_role"] == Role.SENIOR_ADJUSTER

# ------------------------------------------------------------------------------
# 4. Test Human-in-the-Loop Re-entry on Missing Information
# ------------------------------------------------------------------------------
def test_provide_information_re_entry():
    """Verifies that providing missing info advances a halted claim through the graph."""
    client.post("/api/scenarios/run/missing_info")
    claim_res = client.get("/api/claims/CLM-DEMO-002")
    assert claim_res.json()["status"] == "NEEDS_INFO"

    # Submit missing VIN and repair estimate document
    re_entry_res = client.post("/api/claims/CLM-DEMO-002/provide_info", json={
        "vin": "1HGCR2F83HA009988",
        "documents": [{"doc_type": "repair_estimate", "filename": "submitted_quote.pdf"}],
        "notes": "Claimant provided vehicle VIN and certified estimate"
    })
    assert re_entry_res.status_code == 200
    updated_state = re_entry_res.json()
    assert updated_state["completeness"] == 1.0
    assert updated_state["current_status"] in ("SETTLED_STP", "PENDING_REVIEW")

# ------------------------------------------------------------------------------
# 5. Test Graph Error Resilience & Graceful Node Recovery
# ------------------------------------------------------------------------------
def test_graph_node_error_resilience():
    """Ensures node exceptions do not crash the pipeline and are captured in state."""
    def buggy_agent(state):
        raise ValueError("Simulated unexpected downstream API connection timeout")

    fault_tolerant_node = create_traced_node("buggy_test", buggy_agent)
    delta = fault_tolerant_node({"claim_id": "CLM-ERR-01"})
    
    assert delta["current_status"] == "ERROR_HALTED"
    assert delta["human_review_required"] is True
    assert len(delta["errors"]) == 1
    assert "Simulated unexpected" in delta["errors"][0]
