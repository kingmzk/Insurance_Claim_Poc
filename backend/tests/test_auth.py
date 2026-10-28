import time
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import (
    create_access_token,
    decode_access_token,
    DEMO_PERSONAS,
    Role
)
from backend.app.workflow.graph import resume_claim_workflow, claims_graph
from backend.app.db.database import get_db_connection
import json

client = TestClient(app)


def test_jwt_token_creation_and_decoding():
    """Verifies HMAC-SHA256 JWT creation, roundtrip decoding, and payload fidelity."""
    payload = {
        "sub": "adjuster_01",
        "user_id": "adjuster_01",
        "role": Role.ADJUSTER,
        "name": "Alice Adjuster",
        "authority_limit": 5000.0
    }
    token = create_access_token(payload, expires_delta=timedelta(minutes=30))
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded["sub"] == "adjuster_01"
    assert decoded["role"] == Role.ADJUSTER
    assert decoded["name"] == "Alice Adjuster"
    assert decoded["authority_limit"] == 5000.0
    assert "exp" in decoded


def test_jwt_token_expiration():
    """Verifies that expired JWT tokens are rejected with a ValueError."""
    payload = {"sub": "expired_user", "role": Role.ADJUSTER}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))

    with pytest.raises(ValueError, match="expired"):
        decode_access_token(token)


def test_jwt_tampered_signature_rejection():
    """Verifies that tampered payloads or signatures are rejected."""
    payload = {"sub": "adjuster_01", "role": Role.ADJUSTER}
    token = create_access_token(payload)
    parts = token.split(".")

    # Tamper with the payload segment
    tampered_token = f"{parts[0]}.eyJob2dnZWQiOiAiZmFrZSJ9.{parts[2]}"
    with pytest.raises(ValueError, match="Invalid JWT signature"):
        decode_access_token(tampered_token)


def test_api_list_personas():
    """Verifies GET /api/auth/personas returns all 5 domain personas."""
    res = client.get("/api/auth/personas")
    assert res.status_code == 200
    personas = res.json()
    assert len(personas) == 5
    roles = {p["role"] for p in personas}
    assert Role.ADJUSTER in roles
    assert Role.SENIOR_ADJUSTER in roles
    assert Role.CLAIMS_MANAGER in roles
    assert Role.SIU_INVESTIGATOR in roles
    assert Role.POLICY_SPECIALIST in roles


def test_api_issue_access_token_persona():
    """Verifies POST /api/auth/token generates a valid Bearer token for a persona."""
    res = client.post("/api/auth/token", json={"persona": "senior_adjuster"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == Role.SENIOR_ADJUSTER
    assert data["user"]["authority_limit"] == 10000.0

    # Call /api/auth/me with the issued Bearer token
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["role"] == Role.SENIOR_ADJUSTER
    assert me_data["user_id"] == "senior_adjuster_07"


def test_api_auth_me_unauthorized():
    """Verifies GET /api/auth/me returns 401 when no token is provided."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Not authenticated" in res.json()["detail"]


def test_api_auth_me_invalid_token():
    """Verifies GET /api/auth/me returns 401 when a malformed token is provided."""
    headers = {"Authorization": "Bearer malformed.token.here"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401
    assert "Authentication failed" in res.json()["detail"]


def test_review_decision_with_jwt_authorization():
    """
    Verifies that a Review Task correctly uses the role and identity from the Bearer JWT.
    - Adjuster ($5,000 cap) attempting $8,500 payout -> 403 Forbidden.
    - Senior Adjuster ($10,000 cap) attempting $8,500 payout -> 200 Approved.
    """
    claim_id = "CLM-AUTH-TEST-001"
    task_id = "TSK-AUTH-001"
    now = "2026-03-22T10:00:00"

    claim_state = {
        "claim_id": claim_id,
        "current_status": "PENDING_REVIEW",
        "intake_data": {"claimant_name": "Test Driver", "policy_no": "POL-AUTO-99201"},
        "settlement_decision": {"proposed_payout": 8500.0, "requires_human_approval": True},
        "audit_events": [],
        "errors": []
    }

    # Seed claim and review task in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json)
    VALUES (?, 'PENDING_REVIEW', 'motor', ?, ?, ?);
    """, (claim_id, now, now, json.dumps(claim_state)))

    cursor.execute("""
    INSERT OR REPLACE INTO review_tasks (task_id, claim_id, task_type, priority, status, details_json, created_at)
    VALUES (?, ?, 'ADJUSTER_APPROVAL', 'MEDIUM', 'PENDING', ?, ?);
    """, (task_id, claim_id, json.dumps({"proposed_payout": 8500.0}), now))
    conn.commit()
    conn.close()

    # 1. Attempt approval with standard Adjuster token ($5,000 cap < $8,500)
    adj_token_res = client.post("/api/auth/token", json={"persona": "adjuster"})
    adj_token = adj_token_res.json()["access_token"]

    forbidden_res = client.post(
        f"/api/reviews/{task_id}/decision",
        json={"decision": "APPROVED", "adjusted_payout": 8500.0, "notes": "Adjuster trying over-authority"},
        headers={"Authorization": f"Bearer {adj_token}"}
    )
    assert forbidden_res.status_code == 403
    assert "Authority limit exceeded" in forbidden_res.json()["detail"]

    # 2. Approve with Senior Adjuster token ($10,000 cap >= $8,500)
    sr_token_res = client.post("/api/auth/token", json={"persona": "senior_adjuster"})
    sr_token = sr_token_res.json()["access_token"]

    approved_res = client.post(
        f"/api/reviews/{task_id}/decision",
        json={"decision": "APPROVED", "adjusted_payout": 8500.0, "notes": "Senior adjuster approved complex repair"},
        headers={"Authorization": f"Bearer {sr_token}"}
    )
    assert approved_res.status_code == 200
    res_data = approved_res.json()
    assert res_data["decision"] == "APPROVED"
    assert res_data["reviewer_role"] == Role.SENIOR_ADJUSTER
    assert res_data["updated_claim_status"] == "SETTLED_MANUAL"


def test_persistent_state_recovery_after_restart():
    """
    Verifies that when in-memory thread checkpoint is cleared (simulating server restart),
    resume_claim_workflow successfully recovers state from SQLite and records human decision.
    """
    claim_id = "CLM-PERSIST-TEST-002"
    now = "2026-03-22T11:00:00"

    paused_state = {
        "claim_id": claim_id,
        "current_status": "PENDING_REVIEW",
        "claim_type": "motor",
        "intake_data": {"claimant_name": "Persistent Test", "policy_no": "POL-AUTO-99201"},
        "policy_validation": {"eligible": True, "active": True, "deductible": 500.0},
        "fraud_report": {"fraud_score": 10, "siu_escalate": False, "flags": []},
        "risk_assessment": {"risk_tier": "LOW", "approved_estimate": 2500.0, "depreciation": 0.0},
        "settlement_decision": {"proposed_payout": 2000.0, "status": "PENDING_APPROVAL"},
        "audit_events": [{"stage": "INTAKE", "event_type": "STARTED", "route_reason": "Init", "timestamp": now}],
        "errors": []
    }

    # Save to SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json)
    VALUES (?, 'PENDING_REVIEW', 'motor', ?, ?, ?);
    """, (claim_id, now, now, json.dumps(paused_state)))
    conn.commit()
    conn.close()

    # Clear in-memory checkpoint thread if it existed
    claims_graph.checkpointer.delete_thread(claim_id)

    # Resume claim workflow; should transparently recover from SQLite
    resumed = resume_claim_workflow(
        claim_id=claim_id,
        human_decision={
            "decision": "APPROVED",
            "reviewer_id": "senior_adjuster_07",
            "reviewer_role": "senior_adjuster",
            "notes": "Recovered state confirmed and approved."
        }
    )

    assert resumed is not None
    # Verify audit trail has recorded the human decision event
    audit_events = resumed.get("audit_events", [])
    assert any(e.get("event_type") == "DECISION_APPROVED" for e in audit_events)
