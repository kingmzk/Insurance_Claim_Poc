from datetime import datetime, timezone
from ..models.state import ClaimState
from ..services.policy_service import PolicyService
from ..services.llm_service import LLMService

def policy_agent(state: ClaimState) -> ClaimState:
    """
    Policy Validation Agent: Checks active policy status via mock PAS
    and retrieves relevant policy clauses using SQLite FTS5.
    """
    intake = state.get("intake_data", {})
    policy_no = intake.get("policy_no", "")
    loss_type = intake.get("loss_type", "collision")
    incident_desc = intake.get("incident_description", "")
    
    # Authoritative PAS check
    pas_info = PolicyService.get_policy_status(policy_no)
    
    # Retrieve clauses using SQLite FTS5 keyword RAG
    search_query = f"{loss_type} coverage deductible exclusion collision {incident_desc}"
    clauses = PolicyService.retrieve_clauses(policy_no, search_query)
    
    # Check if incident mentions exclusions (e.g., racing, track day)
    is_racing_or_excluded = any(w in incident_desc.lower() for w in ["racing", "track", "speed contest", "drift", "speedway"])
    
    eligible = True
    rejection_reason = ""
    
    if not pas_info.get("found"):
        eligible = False
        rejection_reason = f"Policy {policy_no} not found in authoritative records."
    elif pas_info.get("status") == "LAPSED":
        eligible = False
        rejection_reason = f"Policy {policy_no} lapsed on {pas_info.get('expiration_date')} prior to loss."
    elif is_racing_or_excluded:
        eligible = False
        rejection_reason = "Loss occurred during excluded activity (racing / speed contest as defined in Section 8.3)."
        
    explanation = LLMService.generate_coverage_rationale(clauses, {
        "claim_id": state.get("claim_id"),
        "loss_type": loss_type,
        "claimed_amt": intake.get("claimed_amt"),
        "incident_description": incident_desc
    })

    deductible = pas_info.get("standard_deductible", 500.0) if eligible else 0.0
    policy_limit = pas_info.get("single_incident_limit", 50000.0)

    policy_validation = {
        "policy_no": policy_no,
        "active": pas_info.get("status") == "ACTIVE",
        "eligible": eligible,
        "deductible": deductible,
        "policy_limit": policy_limit,
        "citations": clauses,
        "coverage_explanation": explanation,
        "exception_reason": rejection_reason if not eligible else None
    }
    
    state["policy_validation"] = policy_validation
    audit_events = state.get("audit_events", [])
    
    if not eligible:
        state["current_status"] = "PENDING_REVIEW"
        state["route_reason"] = f"Gate 2 Exit: Coverage Exception Drafted — {rejection_reason}"
        audit_events.append({
            "stage": "POLICY_VALIDATION",
            "event_type": "COVERAGE_EXCEPTION",
            "route_reason": state["route_reason"],
            "evidence": {
                "pas_status": pas_info.get("status"),
                "citations": [c.get("section_title") for c in clauses],
                "explanation": explanation
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    else:
        state["current_status"] = "POLICY_VERIFIED"
        state["route_reason"] = f"Gate 2 Pass: Coverage confirmed under active policy {policy_no}."
        audit_events.append({
            "stage": "POLICY_VALIDATION",
            "event_type": "POLICY_CONFIRMED",
            "route_reason": state["route_reason"],
            "evidence": {
                "deductible": deductible,
                "citations": [c.get("section_title") for c in clauses]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    state["audit_events"] = audit_events
    return state
