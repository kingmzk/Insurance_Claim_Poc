import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    conn = get_db_connection()
    conn.execute("DELETE FROM review_tasks;")
    conn.execute("DELETE FROM audit_events;")
    conn.execute("DELETE FROM simulated_ledger;")
    conn.execute("DELETE FROM claims;")
    conn.commit()
    conn.close()

def test_scenario_1_routine_stp():
    response = client.post("/api/scenarios/run/routine_stp")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-DEMO-001"
    assert data["current_status"] == "SETTLED_STP"
    assert data["completeness"] == 1.0
    assert data["fraud_report"]["fraud_score"] < 25
    assert data["risk_assessment"]["risk_tier"] == "LOW"
    assert data["settlement_decision"]["status"] == "SIMULATED_STP"
    assert data["settlement_decision"]["proposed_payout"] == 2240.00
    assert "ACH-" in data["settlement_decision"]["txn_ref"]

def test_scenario_2_missing_info():
    response = client.post("/api/scenarios/run/missing_info")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-DEMO-002"
    assert data["current_status"] == "NEEDS_INFO"
    assert data["completeness"] < 1.0
    assert "vin" in data["missing_fields"]
    assert "repair_estimate" in data["missing_fields"]

def test_scenario_3_excluded_policy():
    response = client.post("/api/scenarios/run/excluded_policy")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-DEMO-003"
    assert data["current_status"] == "PENDING_REVIEW"
    assert data["policy_validation"]["eligible"] is False
    assert data["settlement_decision"]["status"] == "DRAFT_DENIAL"
    assert "Section 8.3" in data["settlement_decision"]["denial_reason"]

def test_scenario_4_fraud_freeze():
    response = client.post("/api/scenarios/run/fraud_freeze")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-DEMO-004"
    assert data["current_status"] == "PENDING_REVIEW"
    assert data["fraud_report"]["fraud_score"] >= 75
    assert data["fraud_report"]["siu_escalate"] is True
    assert any("DUPLICATE_PHOTO" in f for f in data["fraud_report"]["flags"])

def test_scenario_5_high_estimate():
    response = client.post("/api/scenarios/run/high_estimate")
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"] == "CLM-DEMO-005"
    assert data["current_status"] == "PENDING_REVIEW"
    assert data["settlement_decision"]["status"] == "NEEDS_ADJUSTER_APPROVAL"
    assert data["settlement_decision"]["proposed_payout"] == 14000.00
    assert data["risk_assessment"]["risk_tier"] == "HIGH"

def test_audit_trail_recorded():
    client.post("/api/scenarios/run/routine_stp")
    response = client.get("/api/claims/CLM-DEMO-001/audit")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 4
    stages = [e["stage"] for e in events]
    assert "INTAKE" in stages
    assert "POLICY_VALIDATION" in stages
    assert "SETTLEMENT" in stages

def test_human_review_decision_flow():
    # Populate high estimate review task
    client.post("/api/scenarios/run/high_estimate")
    res = client.get("/api/reviews?status=PENDING")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) > 0
    
    # Approve the high estimate claim
    high_task = next((t for t in tasks if t["claim_id"] == "CLM-DEMO-005"), None)
    assert high_task is not None
    task_id = high_task["task_id"]
    decision_res = client.post(f"/api/reviews/{task_id}/decision", json={
        "decision": "APPROVED",
        "notes": "Verified certified Audi OEM quote with local shop. Approved.",
        "adjusted_payout": 14000.00,
        "reviewer_id": "senior_adjuster_07"
    })
    assert decision_res.status_code == 200
    assert decision_res.json()["updated_claim_status"] == "SETTLED_MANUAL"

def test_idempotent_ledger_no_duplicate_payout():
    # Submit routine claim first
    client.post("/api/scenarios/run/routine_stp")
    from backend.app.services.ledger_service import LedgerService
    res1 = LedgerService.disburse_settlement("CLM-DEMO-001", 2240.00, "John Doe")
    assert res1["success"] is True
    assert res1["is_duplicate"] is True
