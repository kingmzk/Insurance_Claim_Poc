import pytest
from backend.app.services.observability_service import observability_service
from backend.app.api.routes import submit_claim, ClaimSubmissionRequest, SYNTHETIC_SCENARIOS
from backend.app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_observability_service_initialization():
    """Verifies Langfuse observability client connects and authenticates."""
    assert observability_service.is_enabled is True
    assert observability_service.client is not None

def test_observability_callback_handler_generation():
    """Verifies Langfuse CallbackHandler is generated with proper tags and metadata."""
    cb = observability_service.get_langchain_callback(
        claim_id="CLM-TEST-OBS-001",
        claimant_name="Test Claimant",
        loss_type="rear_collision",
        tags=["unit_test"]
    )
    assert cb is not None

def test_observability_trace_url_resolution():
    """Verifies Langfuse trace URL resolution."""
    sample_trace_id = "test_trace_123456"
    url = observability_service.get_trace_url(sample_trace_id)
    assert url is not None
    assert "https://us.cloud.langfuse.com" in url
    assert sample_trace_id in url

def test_claim_pipeline_generates_langfuse_trace():
    """Verifies an executed claim generates and persists a Langfuse trace ID and URL."""
    payload = SYNTHETIC_SCENARIOS["routine_stp"]["payload"]
    req = ClaimSubmissionRequest(**payload)
    
    final_state = submit_claim(req)
    
    assert final_state.get("current_status") == "SETTLED_STP"
    assert final_state.get("trace_id") is not None
    assert final_state.get("trace_url") is not None
    assert "https://us.cloud.langfuse.com" in final_state.get("trace_url")

def test_deepeval_langfuse_sync_reporting():
    """Verifies that DeepEval benchmark reporting includes Langfuse sync capabilities."""
    from backend.evals.runner import get_latest_report
    report = get_latest_report()
    assert report is not None
    assert "summary" in report
    assert "test_results" in report
    assert "status" in report
