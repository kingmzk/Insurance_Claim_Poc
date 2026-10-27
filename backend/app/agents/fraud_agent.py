from datetime import datetime, timezone
from typing import Dict, Any
from ..models.state import ClaimState
from ..services.forensics_service import ForensicsService
from ..core.config import FRAUD_THRESHOLD_ESCALATION, FRAUD_THRESHOLD_LOW

def fraud_agent(state: ClaimState) -> Dict[str, Any]:
    """
    Fraud Detection Agent: Screens for photo duplicates via perceptual hash,
    checks EXIF metadata consistency, inspects claimant velocity and cross-claim VIN collusion.
    Returns a pure state delta dictionary.
    """
    intake = state.get("intake_data", {})
    claim_id = state.get("claim_id", "UNKNOWN")
    
    forensics_result = ForensicsService.inspect_claim(intake, claim_id)
    score = forensics_result["fraud_score"]
    requires_siu = forensics_result["requires_siu"]
    
    fraud_report = {
        "fraud_score": score,
        "flags": forensics_result["flags"],
        "duplicate_matches": forensics_result["duplicate_matches"],
        "exif_discrepancies": forensics_result["exif_discrepancies"],
        "network_signals": forensics_result.get("network_signals", {}),
        "siu_escalate": requires_siu,
        "escalation_threshold": FRAUD_THRESHOLD_ESCALATION
    }
    
    now_ts = datetime.now(timezone.utc).isoformat()

    if requires_siu:
        reason = f"Gate 3 Exit: High Fraud Risk (Score: {score} >= {FRAUD_THRESHOLD_ESCALATION}) — Escalated to SIU."
        event = {
            "stage": "FRAUD_DETECTION",
            "event_type": "SIU_ESCALATION",
            "route_reason": reason,
            "evidence": {
                "fraud_score": score,
                "flags": forensics_result["flags"],
                "network_signals": forensics_result.get("network_signals", {})
            },
            "timestamp": now_ts
        }
    else:
        reason = f"Gate 3 Pass: Fraud score {score} below escalation threshold (< {FRAUD_THRESHOLD_ESCALATION})."
        event = {
            "stage": "FRAUD_DETECTION",
            "event_type": "FRAUD_CLEARED",
            "route_reason": reason,
            "evidence": {
                "fraud_score": score,
                "flags_count": len(forensics_result["flags"]),
                "network_signals": forensics_result.get("network_signals", {})
            },
            "timestamp": now_ts
        }
        
    return {
        "fraud_report": fraud_report,
        "audit_events": [event]
    }
