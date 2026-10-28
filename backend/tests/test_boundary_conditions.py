import pytest
import json
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import (
    DEFAULT_AUTHORITY_LIMIT,
    SENIOR_ADJUSTER_APPROVAL_LIMIT,
    FRAUD_THRESHOLD_ESCALATION,
    DEFAULT_DEDUCTIBLE
)
from backend.app.services.forensics_service import ForensicsService
from backend.app.services.ledger_service import LedgerService
from backend.app.models.state import ClaimState
from backend.app.agents.settlement_agent import settlement_agent
from backend.app.agents.intake_agent import intake_agent

client = TestClient(app)

# ------------------------------------------------------------------------------
# 1. Fraud Risk Escalation Boundary Tests (74 vs 75)
# ------------------------------------------------------------------------------
def test_fraud_score_below_escalation_boundary_74():
    """Fraud score 74 must not trigger SIU escalation."""
    # Base clean score is 12. EXIF predates (+40) + No photos (+15) = 55 (below 75).
    photos = [{
        "photo_id": "p1",
        "phash": "unmatched_hash_1234",
        "exif_timestamp": "2026-03-10T10:00:00",
        "is_tampered": False
    }]
    loss_date = "2026-03-15"
    result = ForensicsService.inspect_claim({
        "photos": photos,
        "loss_date": loss_date,
        "claimed_amt": 2000.0,
        "claimant_name": "Boundary Test 74",
        "vin": "VIN-BOUND-74"
    })
    # Exif discrepancy: 40 points -> total 40 < 75
    assert result["fraud_score"] < FRAUD_THRESHOLD_ESCALATION
    assert result["requires_siu"] is False

def test_fraud_score_at_or_above_escalation_boundary_75():
    """Fraud score >= 75 must trigger SIU escalation and freeze automation."""
    # Duplicate photo (+45) + EXIF discrepancy (+40) = 85 (>= 75)
    photos = [{
        "photo_id": "p_reuse",
        "phash": "a8b4c9e1f203d456",  # Known duplicate in PRIOR_CLAIM_HASHES (+45)
        "exif_timestamp": "2026-01-10T09:00:00",  # Predates loss date by 2 months (+40)
        "is_tampered": False
    }]
    loss_date = "2026-03-20"
    result = ForensicsService.inspect_claim({
        "photos": photos,
        "loss_date": loss_date,
        "claimed_amt": 3000.0,
        "claimant_name": "Boundary Test 75",
        "vin": "VIN-BOUND-75"
    })
    assert result["fraud_score"] >= FRAUD_THRESHOLD_ESCALATION
    assert result["requires_siu"] is True

# ------------------------------------------------------------------------------
# 2. STP Authority Limit Boundary Tests ($5,000.00 vs $5,000.01)
# ------------------------------------------------------------------------------
def test_stp_authority_limit_exact_boundary_5000():
    """Payout of exactly $5,000.00 qualifies for automated STP clearance."""
    state: ClaimState = {
        "claim_id": "CLM-BOUND-5000",
        "intake_data": {"claimant_name": "Jane Doe", "claimed_amt": 5500.00},
        "policy_validation": {"eligible": True, "deductible": 500.00},
        "fraud_report": {"fraud_score": 10},
        "risk_assessment": {
            "approved_estimate": 5500.00,
            "depreciation": 0.00,
            "risk_tier": "LOW"
        },
        "audit_events": []
    }
    delta = settlement_agent(state)
    assert delta["settlement_decision"]["proposed_payout"] == DEFAULT_AUTHORITY_LIMIT
    assert delta["current_status"] == "SETTLED_STP"
    assert delta["human_review_required"] is False
    assert delta["settlement_decision"]["status"] == "SIMULATED_STP"

def test_stp_authority_limit_exceeded_by_one_cent_5000_01():
    """Payout of $5,000.01 exceeds authority limit and routes to Adjuster Queue."""
    state: ClaimState = {
        "claim_id": "CLM-BOUND-5000-01",
        "intake_data": {"claimant_name": "Jane Doe", "claimed_amt": 5500.01},
        "policy_validation": {"eligible": True, "deductible": 500.00},
        "fraud_report": {"fraud_score": 10},
        "risk_assessment": {
            "approved_estimate": 5500.01,
            "depreciation": 0.00,
            "risk_tier": "LOW"
        },
        "audit_events": []
    }
    delta = settlement_agent(state)
    assert delta["settlement_decision"]["proposed_payout"] == 5000.01
    assert delta["current_status"] == "PENDING_REVIEW"
    assert delta["human_review_required"] is True
    assert delta["settlement_decision"]["status"] == "NEEDS_ADJUSTER_APPROVAL"
    assert any("exceeds authority limit" in r for r in delta["settlement_decision"]["approval_reasons"])

# ------------------------------------------------------------------------------
# 3. Senior Adjuster Approval Boundary Tests ($10,000.00 vs $10,000.01)
# ------------------------------------------------------------------------------
def test_senior_adjuster_can_approve_exact_10000():
    """Senior adjuster can approve claims up to exactly $10,000.00."""
    from backend.app.core.auth import validate_review_authorization, Role
    is_auth, role, err = validate_review_authorization(
        task_type="ADJUSTER_APPROVAL",
        reviewer_id="senior_adjuster_02",
        payout_amount=SENIOR_ADJUSTER_APPROVAL_LIMIT
    )
    assert is_auth is True
    assert role == Role.SENIOR_ADJUSTER
    assert err == ""

def test_senior_adjuster_cannot_approve_above_10000():
    """Claims above $10,000.00 require Claims Manager approval."""
    from backend.app.core.auth import validate_review_authorization, Role
    # Standard adjuster -> Forbidden
    is_auth_adj, _, _ = validate_review_authorization(
        task_type="ADJUSTER_APPROVAL",
        reviewer_id="adjuster_01",
        payout_amount=10000.01
    )
    assert is_auth_adj is False

    # Senior adjuster -> Authorized up to senior limit ($10,000.00), but exceeds limit
    is_auth_sr, _, err_sr = validate_review_authorization(
        task_type="ADJUSTER_APPROVAL",
        reviewer_id="senior_adjuster_01",
        payout_amount=10000.01
    )
    is_auth_mgr, role_mgr, _ = validate_review_authorization(
        task_type="ADJUSTER_APPROVAL",
        reviewer_id="claims_manager_01",
        payout_amount=10000.01
    )
    assert is_auth_mgr is True
    assert role_mgr == Role.CLAIMS_MANAGER

# ------------------------------------------------------------------------------
# 4. Input Validation & Completeness Boundaries
# ------------------------------------------------------------------------------
def test_intake_validation_negative_claimed_amt():
    """Negative claimed amount is rejected as missing/invalid at Gate 1."""
    state: ClaimState = {
        "claim_id": "CLM-BOUND-NEG",
        "intake_data": {
            "policy_no": "POL-AUTO-99201",
            "loss_date": "2026-03-15",
            "vin": "1HGCR2F83HA001234",
            "claimed_amt": -250.00,
            "documents": [{"doc_type": "repair_estimate", "filename": "quote.pdf"}]
        }
    }
    delta = intake_agent(state)
    assert "claimed_amt" in delta["missing_fields"]
    assert delta["completeness"] < 1.0
    assert delta["current_status"] == "NEEDS_INFO"
    assert delta["human_review_required"] is True

def test_intake_validation_zero_claimed_amt():
    """Zero claimed amount is rejected as invalid at Gate 1."""
    state: ClaimState = {
        "claim_id": "CLM-BOUND-ZERO",
        "intake_data": {
            "policy_no": "POL-AUTO-99201",
            "loss_date": "2026-03-15",
            "vin": "1HGCR2F83HA001234",
            "claimed_amt": 0.00,
            "documents": [{"doc_type": "repair_estimate", "filename": "quote.pdf"}]
        }
    }
    delta = intake_agent(state)
    assert "claimed_amt" in delta["missing_fields"]
    assert delta["completeness"] < 1.0
    assert delta["current_status"] == "NEEDS_INFO"

# ------------------------------------------------------------------------------
# 5. Deductible Floor Boundary Test ($0 Floor)
# ------------------------------------------------------------------------------
def test_settlement_payout_floors_at_zero():
    """When approved estimate is less than deductible, payout floors cleanly at $0.00."""
    state: ClaimState = {
        "claim_id": "CLM-BOUND-FLOOR",
        "intake_data": {"claimant_name": "John Doe", "claimed_amt": 350.00},
        "policy_validation": {"eligible": True, "deductible": 500.00},
        "fraud_report": {"fraud_score": 10},
        "risk_assessment": {
            "approved_estimate": 350.00,  # Less than $500 deductible
            "depreciation": 0.00,
            "risk_tier": "LOW"
        },
        "audit_events": []
    }
    delta = settlement_agent(state)
    # max(0, 350 - 500 - 0) = 0.0
    assert delta["settlement_decision"]["proposed_payout"] == 0.00
    assert delta["current_status"] == "SETTLED_STP"
