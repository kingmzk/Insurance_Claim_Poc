from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field

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
    audit_events: List[Dict[str, Any]]
    errors: List[str]
    trace_id: Optional[str]
    trace_url: Optional[str]

