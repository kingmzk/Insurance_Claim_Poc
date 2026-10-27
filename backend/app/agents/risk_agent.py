from datetime import datetime, timezone
from typing import Dict, Any
from ..models.state import ClaimState
from ..services.cost_service import CostService

def risk_agent(state: ClaimState) -> Dict[str, Any]:
    """
    Risk Assessment Agent: Benchmarks repair line items against OEM parts catalog
    and labor guides, applies component depreciation, and assigns a risk tier.
    Returns a pure state delta dictionary.
    """
    intake = state.get("intake_data", {})
    claimed_amt = float(intake.get("claimed_amt", 0.0))
    loss_type = intake.get("loss_type", "collision")
    make_model = intake.get("vehicle_make_model", "")
    
    valuation = CostService.benchmark_repair(claimed_amt, loss_type, make_model)
    
    risk_assessment = {
        "claimed_amount": claimed_amt,
        "approved_estimate": valuation["approved_estimate"],
        "depreciation": valuation["depreciation"],
        "risk_tier": valuation["risk_tier"],
        "valuation_notes": valuation["valuation_notes"]
    }
    
    now_ts = datetime.now(timezone.utc).isoformat()
    reason = f"Risk Assessment Complete: Assigned {valuation['risk_tier']} Risk Tier."
    
    event = {
        "stage": "RISK_ASSESSMENT",
        "event_type": "RISK_ASSESSED",
        "route_reason": reason,
        "evidence": {
            "approved_estimate": valuation["approved_estimate"],
            "depreciation": valuation["depreciation"],
            "risk_tier": valuation["risk_tier"]
        },
        "timestamp": now_ts
    }
    
    return {
        "risk_assessment": risk_assessment,
        "audit_events": [event]
    }
