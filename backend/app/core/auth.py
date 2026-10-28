"""
Role-Based Authorization & Approval Access Control for Insurance Claims Workflow.
Enforces segregation of duties, authority limits, and JWT authentication across human review tasks.
"""
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import (
    DEFAULT_AUTHORITY_LIMIT,
    SENIOR_ADJUSTER_APPROVAL_LIMIT,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
)


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

# Standard Pre-configured Demo Personas
DEMO_PERSONAS: Dict[str, Dict[str, Any]] = {
    "adjuster": {
        "user_id": "adjuster_01",
        "username": "adjuster",
        "name": "Alice Adjuster",
        "role": Role.ADJUSTER,
        "title": "Claims Adjuster",
        "authority_limit": DEFAULT_AUTHORITY_LIMIT,
        "description": f"Standard claims handler. Authorized to approve repairs up to ${DEFAULT_AUTHORITY_LIMIT:,.2f}."
    },
    "senior_adjuster": {
        "user_id": "senior_adjuster_07",
        "username": "senior_adjuster",
        "name": "Sarah Senior Adjuster",
        "role": Role.SENIOR_ADJUSTER,
        "title": "Senior Claims Specialist",
        "authority_limit": SENIOR_ADJUSTER_APPROVAL_LIMIT,
        "description": f"Senior adjudicator. Authorized for claims up to ${SENIOR_ADJUSTER_APPROVAL_LIMIT:,.2f} and coverage reviews."
    },
    "claims_manager": {
        "user_id": "manager_01",
        "username": "claims_manager",
        "name": "Michael Manager",
        "role": Role.CLAIMS_MANAGER,
        "title": "Head of Claims Operations",
        "authority_limit": 100000.0,
        "description": "Executive authority. Uncapped approval limits, policy overrides, and SIU concurrence."
    },
    "siu_investigator": {
        "user_id": "siu_agent_03",
        "username": "siu_investigator",
        "name": "Sam SIU Investigator",
        "role": Role.SIU_INVESTIGATOR,
        "title": "Special Investigations Unit (SIU)",
        "authority_limit": 0.0,
        "description": "Fraud specialist. Exclusive authority to clear or confirm SIU fraud freezes."
    },
    "policy_specialist": {
        "user_id": "policy_specialist_01",
        "username": "policy_specialist",
        "name": "Paula Policy Specialist",
        "role": Role.POLICY_SPECIALIST,
        "title": "Coverage & Underwriting Counsel",
        "authority_limit": 0.0,
        "description": "Policy legal analyst. Reviews exclusions, endorsements, and coverage exceptions."
    }
}


# ------------------------------------------------------------------------------
# JWT Token Generation and Cryptographic Verification (HMAC-SHA256)
# ------------------------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data_str: str) -> bytes:
    padding = "=" * ((4 - len(data_str) % 4) % 4)
    return base64.urlsafe_b64decode((data_str + padding).encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed HMAC-SHA256 JWT access token."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = data.copy()
    now_ts = int(time.time())
    if expires_delta:
        exp_ts = now_ts + int(expires_delta.total_seconds())
    else:
        exp_ts = now_ts + (JWT_EXPIRATION_MINUTES * 60)

    payload.setdefault("iat", now_ts)
    payload["exp"] = exp_ts

    header_enc = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_enc = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_enc}.{payload_enc}".encode("utf-8")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_enc = _b64url_encode(signature)

    return f"{header_enc}.{payload_enc}.{sig_enc}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically verifies an HMAC-SHA256 JWT token.
    Raises ValueError on invalid format, expired token, or signature mismatch.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format (expected 3 dot-separated segments)")

    header_enc, payload_enc, sig_enc = parts
    signing_input = f"{header_enc}.{payload_enc}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_sig_enc = _b64url_encode(expected_sig)

    if not hmac.compare_digest(sig_enc, expected_sig_enc):
        raise ValueError("Invalid JWT signature")

    try:
        payload_bytes = _b64url_decode(payload_enc)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to decode token payload: {str(e)}")

    now_ts = int(time.time())
    if "exp" in payload and payload["exp"] < now_ts:
        raise ValueError("JWT token has expired")

    return payload


# ------------------------------------------------------------------------------
# FastAPI Dependencies & RBAC Guards
# ------------------------------------------------------------------------------
security_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[Dict[str, Any]]:
    """
    Extracts and validates current authenticated user from Bearer JWT.
    Returns user dict with user_id, role, name, authority_limit if token is valid.
    Returns None if no Authorization header was supplied (enabling backward-compatible fallback).
    Raises HTTPException 401 if a token was supplied but is expired or invalid.
    """
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials.strip()
    try:
        payload = decode_access_token(token)
        return {
            "user_id": payload.get("sub") or payload.get("user_id"),
            "role": payload.get("role"),
            "name": payload.get("name", "User"),
            "authority_limit": float(payload.get("authority_limit", 0.0))
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory enforcing that the caller possesses one of the allowed roles.
    Raises 401 if unauthenticated and 403 if unauthorized.
    """
    def dependency(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please provide a Bearer JWT token in the Authorization header.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Role '{user_role}' does not have sufficient permissions. Required one of: {list(allowed_roles)}"
            )
        return current_user
    return dependency


# ------------------------------------------------------------------------------
# Domain-Specific Role Resolution and Approval Authority Limits
# ------------------------------------------------------------------------------
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
