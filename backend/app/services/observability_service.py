import logging
import os
from typing import Dict, Any, List, Optional
from ..core.config import (
    LANGFUSE_SECRET_KEY,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_BASE_URL,
    LANGFUSE_HOST,
)

logger = logging.getLogger("observability")

class ObservabilityService:
    """
    Centralized Langfuse Observability & Tracing Service.
    Provides LangGraph callback integration, trace URL resolution,
    claim metrics scoring, and graceful degradation if disabled or unreachable.
    """
    def __init__(self):
        self.is_enabled: bool = False
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initializes Langfuse client with credentials and tests connectivity."""
        if not LANGFUSE_SECRET_KEY or not LANGFUSE_PUBLIC_KEY:
            logger.info("Langfuse credentials not set. Tracing will run in no-op mode.")
            self.is_enabled = False
            return

        try:
            from langfuse import Langfuse
            
            # Guarantee environment variables for underlying OpenTelemetry exporters
            os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
            os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
            os.environ["LANGFUSE_BASE_URL"] = LANGFUSE_BASE_URL
            os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST

            self.client = Langfuse(
                secret_key=LANGFUSE_SECRET_KEY,
                public_key=LANGFUSE_PUBLIC_KEY,
                host=LANGFUSE_BASE_URL,
            )
            
            auth_ok = self.client.auth_check()
            if auth_ok:
                self.is_enabled = True
                logger.info("Langfuse observability client successfully authenticated.")
            else:
                logger.warning("Langfuse auth_check failed. Observability disabled.")
                self.is_enabled = False
        except Exception as e:
            logger.error(f"Error initializing Langfuse client: {e}")
            self.is_enabled = False
            self.client = None

    def get_langchain_callback(
        self,
        claim_id: str,
        claimant_name: str,
        loss_type: str = "collision",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Generates a Langfuse Langchain / LangGraph CallbackHandler configured
        for the given claim session, tags, and metadata.
        """
        if not self.is_enabled or not self.client:
            return None

        try:
            from langfuse.langchain import CallbackHandler
            
            merged_tags = list(set(["insurance-claims", "autonomous-multi-agent", loss_type] + (tags or [])))
            cb = CallbackHandler()
            return cb
        except Exception as e:
            logger.warning(f"Failed to create Langfuse CallbackHandler: {e}")
            return None

    def get_trace_url(self, trace_id: Optional[str]) -> Optional[str]:
        """Resolves the direct Langfuse web UI URL for a given trace ID."""
        if not trace_id or not self.is_enabled or not self.client:
            return None

        try:
            url = self.client.get_trace_url(trace_id=trace_id)
            if url:
                return url
        except Exception as e:
            logger.debug(f"client.get_trace_url error: {e}")

        # Fallback format if client method doesn't resolve
        base = (LANGFUSE_BASE_URL or "https://us.cloud.langfuse.com").rstrip("/")
        return f"{base}/traces/{trace_id}"

    def record_score(
        self,
        name: str,
        value: float | str,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        comment: Optional[str] = None,
        data_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records a metric score in Langfuse for analytics and evaluation."""
        if not self.is_enabled or not self.client:
            return

        try:
            kwargs: Dict[str, Any] = {
                "name": name,
                "value": value,
            }
            if trace_id:
                kwargs["trace_id"] = trace_id
            elif session_id:
                kwargs["session_id"] = session_id

            if comment:
                kwargs["comment"] = comment
            if data_type:
                kwargs["data_type"] = data_type
            if metadata:
                kwargs["metadata"] = metadata

            self.client.create_score(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to record Langfuse score '{name}': {e}")

    def record_claim_metrics(self, state: Dict[str, Any], trace_id: Optional[str] = None):
        """
        Extracts key outcome metrics from a finished claim run and logs them to Langfuse.
        """
        if not self.is_enabled:
            return

        claim_id = state.get("claim_id")
        session_id = claim_id

        # 1. Intake Completeness
        completeness = float(state.get("completeness", 0.0))
        self.record_score(
            name="intake_completeness",
            value=completeness,
            trace_id=trace_id,
            session_id=session_id,
            comment=f"Missing fields: {state.get('missing_fields', [])}"
        )

        # 2. Policy Eligibility
        policy_val = state.get("policy_validation", {})
        if policy_val:
            is_eligible = 1.0 if policy_val.get("eligible", False) else 0.0
            self.record_score(
                name="policy_eligibility",
                value=is_eligible,
                trace_id=trace_id,
                session_id=session_id,
                comment=policy_val.get("exception_reason") or "Policy active and covers loss"
            )

        # 3. Fraud Risk Score
        fraud_rep = state.get("fraud_report", {})
        if fraud_rep and "fraud_score" in fraud_rep:
            fraud_score = float(fraud_rep.get("fraud_score", 0.0))
            self.record_score(
                name="fraud_risk_score",
                value=fraud_score,
                trace_id=trace_id,
                session_id=session_id,
                comment=f"SIU escalate: {fraud_rep.get('siu_escalate', False)}, Flags: {fraud_rep.get('flags', [])}"
            )

        # 4. Settlement Decision & STP
        settle_dec = state.get("settlement_decision", {})
        status = state.get("current_status", "")
        if settle_dec:
            payout = float(settle_dec.get("proposed_payout", 0.0))
            self.record_score(
                name="proposed_payout",
                value=payout,
                trace_id=trace_id,
                session_id=session_id,
                comment=f"Deductible: ${settle_dec.get('deductible_applied', 0)}, Depreciation: ${settle_dec.get('depreciation_applied', 0)}"
            )

        is_stp = 1.0 if status == "SETTLED_STP" else 0.0
        self.record_score(
            name="straight_through_processing",
            value=is_stp,
            trace_id=trace_id,
            session_id=session_id,
            comment=f"Final claim status: {status}"
        )

    def record_human_review(
        self,
        claim_id: str,
        decision: str,
        reviewer_id: str,
        adjusted_payout: Optional[float] = None,
        notes: str = "",
        trace_id: Optional[str] = None
    ):
        """Records human-in-the-loop adjuster decision in Langfuse."""
        if not self.is_enabled:
            return

        self.record_score(
            name="human_review_decision",
            value=1.0 if decision == "APPROVED" else 0.0,
            trace_id=trace_id,
            session_id=claim_id,
            comment=f"Reviewer: {reviewer_id}, Decision: {decision}, Adjusted Payout: {adjusted_payout}, Notes: {notes}"
        )

    def flush(self):
        """Flushes telemetry buffer."""
        if self.client and self.is_enabled:
            try:
                self.client.flush()
            except Exception as e:
                logger.debug(f"Langfuse flush error: {e}")

# Global singleton instance
observability_service = ObservabilityService()
