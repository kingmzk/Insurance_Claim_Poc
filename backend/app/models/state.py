from typing import TypedDict, Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field

def merge_audit_events(left: Optional[List[Dict[str, Any]]], right: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Reducer that merges audit event lists across sequential and parallel graph nodes."""
    combined = list(left or [])
    if right:
        combined.extend(right)
    return combined

def merge_errors(left: Optional[List[str]], right: Optional[List[str]]) -> List[str]:
    """Reducer that merges error messages across graph nodes without duplicates."""
    combined = list(left or [])
    if right:
        for err in right:
            if err not in combined:
                combined.append(err)
    return combined

class ClaimDocument(BaseModel):
    doc_type: str = Field(..., description="e.g. fnol_form, repair_invoice, police_report")
    filename: str
    content: Optional[str] = None
    url: Optional[str] = None

class PhotoMetadata(BaseModel):
    photo_id: str
    filename: str
    phash: str
    exif_timestamp: str
    reported_incident_timestamp: str
    gps_coordinates: Optional[str] = None
    is_tampered: bool = False

class ClaimSubmissionRequest(BaseModel):
    claim_id: Optional[str] = None
    claim_type: str = "motor"
    policy_no: str
    claimant_name: str
    loss_date: str
    loss_type: str
    claimed_amt: float
    vin: Optional[str] = None
    vehicle_make_model: Optional[str] = None
    incident_description: Optional[str] = None
    documents: List[ClaimDocument] = Field(default_factory=list)
    photos: List[PhotoMetadata] = Field(default_factory=list)

class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVED, REJECTED, or REQUEST_INFO")
    notes: str = ""
    adjusted_payout: Optional[float] = None
    reviewer_id: str = "adjuster_01"
    reviewer_role: Optional[str] = Field(default=None, description="adjuster, senior_adjuster, claims_manager, siu_investigator, policy_specialist")

class ProvideInfoRequest(BaseModel):
    vin: Optional[str] = None
    documents: List[ClaimDocument] = Field(default_factory=list)
    notes: str = ""

# Shared LangGraph State Schema
class ClaimState(TypedDict, total=False):
    claim_id: str
    claim_type: str
    intake_data: Dict[str, Any]
    completeness: float
    missing_fields: List[str]
    
    policy_validation: Dict[str, Any]
    fraud_report: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    settlement_decision: Dict[str, Any]
    
    current_status: str
    route_reason: str
    audit_events: Annotated[List[Dict[str, Any]], merge_audit_events]
    errors: Annotated[List[str], merge_errors]
    
    trace_id: Optional[str]
    trace_url: Optional[str]
    otel_trace_id: Optional[str]
    
    # Human-in-the-Loop (HITL) Graph Tracking
    human_review_required: bool
    human_review_type: Optional[str]
    human_review_reason: Optional[str]
    human_decision: Optional[Dict[str, Any]]
