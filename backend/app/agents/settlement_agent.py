from datetime import datetime, timezone
from typing import Dict, Any
from ..models.state import ClaimState
from ..core.config import DEFAULT_AUTHORITY_LIMIT, FRAUD_THRESHOLD_LOW, DEFAULT_DEDUCTIBLE
from ..services.ledger_service import LedgerService

def settlement_agent(state: ClaimState) -> Dict[str, Any]:
    """
    Settlement Agent: Applies deterministic payout arithmetic,
    evaluates Straight-Through Processing (STP) authority limits,
    and executes idempotent simulated disbursement or routes to human adjuster.
    Returns a pure state delta dictionary.
    """
    claim_id = state.get("claim_id", "UNKNOWN")
    intake = state.get("intake_data", {})
    policy_val = state.get("policy_validation", {})
    fraud_rep = state.get("fraud_report", {})
    risk_ass = state.get("risk_assessment", {})
    claimant_name = intake.get("claimant_name", "Claimant")
    now_ts = datetime.now(timezone.utc).isoformat()
    
    # Case 1: Ineligible / Coverage Denied at Policy Stage
    if not policy_val.get("eligible", False):
        denial_reason = policy_val.get("exception_reason", "Policy exclusion applied")
        settlement_decision = {
            "status": "DRAFT_DENIAL",
            "proposed_payout": 0.0,
            "requires_human_approval": True,
            "authority_limit": DEFAULT_AUTHORITY_LIMIT,
            "denial_reason": denial_reason,
            "citations": policy_val.get("citations", [])
        }
        reason = f"Settlement Action: Coverage Denial Drafted — {denial_reason}"
        event = {
            "stage": "SETTLEMENT",
            "event_type": "DRAFT_DENIAL",
            "route_reason": reason,
            "evidence": {"payout": 0.0, "reason": denial_reason},
            "timestamp": now_ts
        }
        return {
            "settlement_decision": settlement_decision,
            "current_status": "PENDING_REVIEW",
            "route_reason": reason,
            "human_review_required": True,
            "human_review_type": "COVERAGE_EXCEPTION",
            "audit_events": [event]
        }

    # Case 2: Eligible Policy — Deterministic Payout Arithmetic
    approved_estimate = float(risk_ass.get("approved_estimate", 0.0))
    deductible = float(policy_val.get("deductible", DEFAULT_DEDUCTIBLE))
    depreciation = float(risk_ass.get("depreciation", 0.0))
    
    # Formula: max(0, approved_estimate - deductible - depreciation)
    proposed_payout = max(0.0, round(approved_estimate - deductible - depreciation, 2))
    
    risk_tier = risk_ass.get("risk_tier", "HIGH")
    fraud_score = fraud_rep.get("fraud_score", 100)
    
    # Gate 4: STP Rule Verification
    is_low_risk = (risk_tier == "LOW")
    is_low_fraud = (fraud_score < FRAUD_THRESHOLD_LOW)
    within_limit = (proposed_payout <= DEFAULT_AUTHORITY_LIMIT)
    
    stp_qualified = is_low_risk and is_low_fraud and within_limit
    
    if stp_qualified:
        # Execute idempotent simulated ACH payout
        disbursement = LedgerService.disburse_settlement(
            claim_id=claim_id,
            amount=proposed_payout,
            recipient=claimant_name
        )
        
        is_dup = disbursement.get("is_duplicate", False)
        dup_note = " (Existing Disbursement Preserved)" if is_dup else ""
        
        settlement_decision = {
            "status": "SIMULATED_STP",
            "proposed_payout": proposed_payout,
            "net_payout": proposed_payout,
            "requires_human_approval": False,
            "authority_limit": DEFAULT_AUTHORITY_LIMIT,
            "txn_ref": disbursement.get("txn_id"),
            "disbursement_details": disbursement,
            "is_duplicate_disbursement": is_dup
        }
        status = "SETTLED_STP"
        reason = f"Gate 4 Pass: Low Risk & Payout ${proposed_payout:,.2f} <= ${DEFAULT_AUTHORITY_LIMIT:,.2f} — Fast-Track STP Completed{dup_note}."
        
        event = {
            "stage": "SETTLEMENT",
            "event_type": "SIMULATED_STP_DISBURSED",
            "route_reason": reason,
            "evidence": {
                "payout": proposed_payout,
                "txn_ref": disbursement.get("txn_id"),
                "formula": f"max(0, {approved_estimate} - {deductible} - {depreciation})",
                "is_duplicate": is_dup
            },
            "timestamp": now_ts
        }
        return {
            "settlement_decision": settlement_decision,
            "current_status": status,
            "route_reason": reason,
            "human_review_required": False,
            "audit_events": [event]
        }
    else:
        # Route to Adjuster Queue
        reasons = []
        if not is_low_risk:
            reasons.append(f"Risk Tier is {risk_tier}")
        if not is_low_fraud:
            reasons.append(f"Fraud Score ({fraud_score}) exceeds threshold ({FRAUD_THRESHOLD_LOW})")
        if not within_limit:
            reasons.append(f"Proposed Payout (${proposed_payout:,.2f}) exceeds authority limit (${DEFAULT_AUTHORITY_LIMIT:,.2f})")
            
        settlement_decision = {
            "status": "NEEDS_ADJUSTER_APPROVAL",
            "proposed_payout": proposed_payout,
            "net_payout": proposed_payout,
            "requires_human_approval": True,
            "authority_limit": DEFAULT_AUTHORITY_LIMIT,
            "approval_reasons": reasons
        }
        status = "PENDING_REVIEW"
        reason = f"Gate 4 Exit: Routed to Adjuster Queue — {', '.join(reasons)}"
        
        event = {
            "stage": "SETTLEMENT",
            "event_type": "ADJUSTER_APPROVAL_REQUIRED",
            "route_reason": reason,
            "evidence": {
                "proposed_payout": proposed_payout,
                "reasons": reasons
            },
            "timestamp": now_ts
        }
        return {
            "settlement_decision": settlement_decision,
            "current_status": status,
            "route_reason": reason,
            "human_review_required": True,
            "human_review_type": "ADJUSTER_APPROVAL",
            "audit_events": [event]
        }
