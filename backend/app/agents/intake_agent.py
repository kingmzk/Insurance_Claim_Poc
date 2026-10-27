import time
from datetime import datetime, timezone
from typing import Dict, Any
from ..models.state import ClaimState
from ..services.llm_service import LLMService

def intake_agent(state: ClaimState) -> Dict[str, Any]:
    """
    Intake Agent: Extracts FNOL entities and validates required fields.
    Flags missing items and determines completeness.
    Returns a pure state delta dictionary.
    """
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

    updated_intake = {**intake, **enriched}
    now_ts = datetime.now(timezone.utc).isoformat()

    if completeness < 1.0:
        status = "NEEDS_INFO"
        reason = f"Gate 1 Exit: Missing mandatory fields {missing}."
        event = {
            "stage": "INTAKE",
            "event_type": "NEEDS_INFO",
            "route_reason": reason,
            "evidence": {"missing_fields": missing, "completeness": completeness},
            "timestamp": now_ts
        }
        return {
            "intake_data": updated_intake,
            "completeness": completeness,
            "missing_fields": missing,
            "current_status": status,
            "route_reason": reason,
            "human_review_required": True,
            "human_review_type": "NEEDS_INFO",
            "audit_events": [event]
        }
    else:
        status = "INTAKE_PASSED"
        reason = "Gate 1 Pass: All mandatory fields and documents present."
        event = {
            "stage": "INTAKE",
            "event_type": "INTAKE_COMPLETED",
            "route_reason": reason,
            "evidence": {"completeness": 1.0, "vin": intake.get("vin")},
            "timestamp": now_ts
        }
        return {
            "intake_data": updated_intake,
            "completeness": completeness,
            "missing_fields": missing,
            "current_status": status,
            "route_reason": reason,
            "human_review_required": False,
            "audit_events": [event]
        }
