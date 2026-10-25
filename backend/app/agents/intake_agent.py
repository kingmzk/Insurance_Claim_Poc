import time
from datetime import datetime, timezone
from ..models.state import ClaimState
from ..services.llm_service import LLMService

def intake_agent(state: ClaimState) -> ClaimState:
    """
    Intake Agent: Extracts FNOL entities and validates required fields.
    Flags missing items and determines completeness.
    """
    start_time = time.time()
    intake = state.get("intake_data", {})
    claim_id = state.get("claim_id", "UNKNOWN")
    
    # Required core fields
    missing = []
    if not intake.get("policy_no"):
        missing.append("policy_no")
    if not intake.get("loss_date"):
        missing.append("loss_date")
    if not intake.get("claimed_amt") or intake.get("claimed_amt", 0) <= 0:
        missing.append("claimed_amt")
    if not intake.get("vin"):
        missing.append("vin")
    
    # Check document attachments
    docs = intake.get("documents", [])
    has_estimate = any(d.get("doc_type") in ["repair_invoice", "repair_estimate"] for d in docs)
    if not has_estimate:
        missing.append("repair_estimate")
        
    completeness = 1.0 if not missing else max(0.0, round(1.0 - (len(missing) * 0.25), 2))
    
    # Enrich narrative if description is provided
    narrative = intake.get("incident_description", "")
    enriched = {}
    if narrative:
        enriched = LLMService.extract_fnol(narrative, {
            "loss_type": intake.get("loss_type", "collision")
        })

    state["intake_data"] = {**intake, **enriched}
    state["completeness"] = completeness
    state["missing_fields"] = missing
    
    audit_events = state.get("audit_events", [])
    
    if completeness < 1.0:
        state["current_status"] = "NEEDS_INFO"
        state["route_reason"] = f"Gate 1 Exit: Missing mandatory fields {missing}."
        audit_events.append({
            "stage": "INTAKE",
            "event_type": "NEEDS_INFO",
            "route_reason": state["route_reason"],
            "evidence": {"missing_fields": missing, "completeness": completeness},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    else:
        state["current_status"] = "INTAKE_PASSED"
        state["route_reason"] = "Gate 1 Pass: All mandatory fields and documents present."
        audit_events.append({
            "stage": "INTAKE",
            "event_type": "INTAKE_COMPLETED",
            "route_reason": state["route_reason"],
            "evidence": {"completeness": 1.0, "vin": intake.get("vin")},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    state["audit_events"] = audit_events
    return state
