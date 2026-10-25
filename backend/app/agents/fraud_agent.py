from datetime import datetime, timezone
from ..models.state import ClaimState
from ..services.forensics_service import ForensicsService

def fraud_agent(state: ClaimState) -> ClaimState:
    """
    Fraud Detection Agent: Screens for photo duplicates via perceptual hash,
    checks EXIF metadata consistency, and calculates composite fraud score.
    """
    intake = state.get("intake_data", {})
    photos = intake.get("photos", [])
    loss_date = intake.get("loss_date", "")
    
    forensics_result = ForensicsService.inspect_photos(photos, loss_date)
    score = forensics_result["fraud_score"]
    requires_siu = forensics_result["requires_siu"]
    
    fraud_report = {
        "fraud_score": score,
        "flags": forensics_result["flags"],
        "duplicate_matches": forensics_result["duplicate_matches"],
        "exif_discrepancies": forensics_result["exif_discrepancies"],
        "siu_escalate": requires_siu
    }
    
    state["fraud_report"] = fraud_report
    audit_events = state.get("audit_events", [])
    
    if requires_siu:
        state["current_status"] = "PENDING_REVIEW"
        state["route_reason"] = f"Gate 3 Exit: High Fraud Risk (Score: {score} >= 75) — Escalated to SIU."
        audit_events.append({
            "stage": "FRAUD_DETECTION",
            "event_type": "SIU_ESCALATION",
            "route_reason": state["route_reason"],
            "evidence": {
                "fraud_score": score,
                "flags": forensics_result["flags"]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    else:
        state["current_status"] = "FRAUD_CLEARED"
        state["route_reason"] = f"Gate 3 Pass: Fraud score {score} below escalation threshold (< 75)."
        audit_events.append({
            "stage": "FRAUD_DETECTION",
            "event_type": "FRAUD_CLEARED",
            "route_reason": state["route_reason"],
            "evidence": {
                "fraud_score": score,
                "flags_count": len(forensics_result["flags"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    state["audit_events"] = audit_events
    return state
