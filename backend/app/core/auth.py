"""
Role-Based Authorization & Approval Access Control for Insurance Claims Workflow.
Enforces segregation of duties and authority limits across human review tasks.
"""
from typing import Optional, Tuple
from .config import DEFAULT_AUTHORITY_LIMIT, SENIOR_ADJUSTER_APPROVAL_LIMIT

class Role:
    ADJUSTER = "adjuster"
    SENIOR_ADJUSTER = "senior_adjuster"
    CLAIMS_MANAGER = "claims_manager"
    SIU_INVESTIGATOR = "siu_investigator"
    POLICY_SPECIALIST = "policy_specialist"

ALL_ROLES = {
    Role.ADJUSTER,
    Role.SENIOR_ADJUSTER,
    Role.CLAIMS_MANAGER,
    Role.SIU_INVESTIGATOR,
    Role.POLICY_SPECIALIST
}

def resolve_reviewer_role(reviewer_id: str, explicit_role: Optional[str] = None) -> str:
    """Resolves reviewer role from explicit parameter or infers from reviewer ID."""
    if explicit_role:
        normalized = explicit_role.strip().lower()
        if normalized in ALL_ROLES:
            return normalized

    rid = (reviewer_id or "").strip().lower()
    if "siu" in rid:
        return Role.SIU_INVESTIGATOR
    if "manager" in rid or "lead" in rid or "supervisor" in rid:
        return Role.CLAIMS_MANAGER
    if "senior" in rid:
        return Role.SENIOR_ADJUSTER
    if "policy" in rid or "coverage" in rid:
        return Role.POLICY_SPECIALIST
    return Role.ADJUSTER

def validate_review_authorization(
    task_type: str,
    reviewer_id: str,
    reviewer_role: Optional[str] = None,
    payout_amount: float = 0.0
) -> Tuple[bool, str, str]:
    """
    Validates whether the reviewer has sufficient authority for the queued task and payout amount.
    Returns: (is_authorized: bool, resolved_role: str, denial_reason: str)
    """
    role = resolve_reviewer_role(reviewer_id, reviewer_role)
    
    # 1. SIU Fraud Investigation Tasks
    if task_type == "SIU_FRAUD":
        if role in (Role.SIU_INVESTIGATOR, Role.CLAIMS_MANAGER):
            return True, role, ""
        return (
            False,
            role,
            f"Insufficient authority: SIU Fraud review tasks require role '{Role.SIU_INVESTIGATOR}' or '{Role.CLAIMS_MANAGER}' (reviewer '{reviewer_id}' has role '{role}')."
        )

    # 2. Coverage Exception Reviews
    if task_type == "COVERAGE_EXCEPTION":
        if role in (Role.POLICY_SPECIALIST, Role.SENIOR_ADJUSTER, Role.CLAIMS_MANAGER):
            return True, role, ""
        return (
            False,
            role,
            f"Insufficient authority: Coverage Exception tasks require role '{Role.POLICY_SPECIALIST}', '{Role.SENIOR_ADJUSTER}', or '{Role.CLAIMS_MANAGER}'."
        )

    # 3. Adjuster Financial Approval Tasks
    if task_type == "ADJUSTER_APPROVAL":
        # Claims above senior adjuster limit ($10,000) require Senior Adjuster or Claims Manager
        if payout_amount > SENIOR_ADJUSTER_APPROVAL_LIMIT:
            if role in (Role.SENIOR_ADJUSTER, Role.CLAIMS_MANAGER):
                return True, role, ""
            return (
                False,
                role,
                f"Authority limit exceeded: Claim payout (${payout_amount:,.2f}) exceeds standard authority limit (${SENIOR_ADJUSTER_APPROVAL_LIMIT:,.2f}). Requires '{Role.SENIOR_ADJUSTER}' or '{Role.CLAIMS_MANAGER}'."
            )
        # Claims between standard authority ($5,000) and $10,000 require at least Senior Adjuster
        elif payout_amount > DEFAULT_AUTHORITY_LIMIT:
            if role in (Role.SENIOR_ADJUSTER, Role.CLAIMS_MANAGER):
                return True, role, ""
            return (
                False,
                role,
                f"Authority limit exceeded: Standard adjusters are capped at ${DEFAULT_AUTHORITY_LIMIT:,.2f}. Payout of ${payout_amount:,.2f} requires '{Role.SENIOR_ADJUSTER}' or '{Role.CLAIMS_MANAGER}'."
            )
        else:
            if role in (Role.ADJUSTER, Role.SENIOR_ADJUSTER, Role.CLAIMS_MANAGER):
                return True, role, ""
            return (
                False,
                role,
                f"Reviewer with role '{role}' is not authorized to approve settlements."
            )

    # 4. Incomplete Information Resolution Tasks
    if task_type == "NEEDS_INFO":
        if role in (Role.ADJUSTER, Role.SENIOR_ADJUSTER, Role.CLAIMS_MANAGER):
            return True, role, ""
        return (
            False,
            role,
            f"Reviewer with role '{role}' cannot process missing info documents."
        )

    # 5. Fallback for system errors / unknown tasks
    if role in (Role.CLAIMS_MANAGER, Role.SENIOR_ADJUSTER):
        return True, role, ""

    return True, role, ""
