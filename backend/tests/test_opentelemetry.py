import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.telemetry import telemetry_manager
from backend.app.api.routes import submit_claim, ClaimSubmissionRequest, SYNTHETIC_SCENARIOS
from backend.app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Initializes DB and clears telemetry spans prior to each test."""
    init_db()
    telemetry_manager.clear_spans()

def test_telemetry_initialization():
    """Verifies OpenTelemetry TracerProvider and MeterProvider are active."""
    status = telemetry_manager.get_telemetry_status()
    assert status["status"] == "active"
    assert status["service_name"] == "insurance-claims-orchestrator"
    assert status["exporters"]["in_memory"] is True
    assert telemetry_manager.tracer is not None
    assert telemetry_manager.meter is not None

def test_agent_span_generation_and_attributes():
    """Verifies that trace_agent context manager generates spans with duration & attributes."""
    claim_id = "CLM-TEST-OTEL-001"
    
    with telemetry_manager.trace_agent("fraud", claim_id, {"fraud.sample_flag": True}) as span:
        assert span is not None
        span.set_attribute("fraud.score", 15.0)

    status = telemetry_manager.get_telemetry_status()
    spans = status["recent_spans"]
    
    assert len(spans) >= 1
    target_span = next((s for s in spans if s["name"] == "agent.fraud"), None)
    assert target_span is not None
    assert target_span["status"] == "OK"
    assert target_span["attributes"]["insurance.agent.name"] == "fraud"
    assert target_span["attributes"]["insurance.claim.id"] == claim_id
    assert float(target_span["attributes"]["fraud.score"]) == 15.0
    assert target_span["duration_ms"] >= 0.0
    assert len(target_span["trace_id"]) == 32
    assert len(target_span["span_id"]) == 16

def test_claim_pipeline_creates_hierarchical_spans():
    """Verifies that running a claim creates a root span and 5 child agent spans sharing the same Trace ID."""
    telemetry_manager.clear_spans()
    
    payload = SYNTHETIC_SCENARIOS["routine_stp"]["payload"]
    req = ClaimSubmissionRequest(**payload)
    final_state = submit_claim(req)
    
    assert final_state.get("otel_trace_id") is not None
    claim_otel_trace_id = final_state["otel_trace_id"]
    assert len(claim_otel_trace_id) == 32

    status = telemetry_manager.get_telemetry_status()
    spans = [s for s in status["recent_spans"] if s["trace_id"] == claim_otel_trace_id]
    
    span_names = [s["name"] for s in spans]
    # Should contain root orchestration span and agent child spans
    assert "insurance.claim.adjudication" in span_names
    assert "agent.intake" in span_names
    assert "agent.policy" in span_names
    assert "agent.fraud" in span_names
    assert "agent.risk" in span_names
    assert "agent.settle" in span_names

    # Check root span attributes
    root = next(s for s in spans if s["name"] == "insurance.claim.adjudication")
    assert root["attributes"]["claim.loss_type"] == payload["loss_type"]
    assert root["attributes"]["claim.status"] == "SETTLED_STP"
    assert root["attributes"]["insurance.claim.id"] == payload["claim_id"]

    # Check that agent child spans link to root or parent context
    child_agents = [s for s in spans if s["name"].startswith("agent.")]
    for child in child_agents:
        assert child["trace_id"] == claim_otel_trace_id

def test_telemetry_metrics_aggregations():
    """Verifies metrics counters and distributions record upon claim execution."""
    initial_processed = telemetry_manager._metric_totals["claims_processed"]
    initial_stp = telemetry_manager._metric_totals["claims_stp"]

    payload = SYNTHETIC_SCENARIOS["routine_stp"]["payload"]
    req = ClaimSubmissionRequest(**payload)
    submit_claim(req)

    assert telemetry_manager._metric_totals["claims_submitted"] >= 1
    assert telemetry_manager._metric_totals["claims_processed"] == initial_processed + 1
    assert telemetry_manager._metric_totals["claims_stp"] == initial_stp + 1
    assert telemetry_manager._metric_totals["total_payout_amount"] > 0
    assert telemetry_manager._metric_totals["fraud_scores_recorded"] >= 1

def test_fastapi_telemetry_header_injection():
    """Verifies that FastAPI HTTP requests inject X-Trace-Id and X-Span-Id headers."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Trace-Id" in response.headers
    assert len(response.headers["X-Trace-Id"]) == 32

def test_telemetry_api_endpoints():
    """Verifies GET /api/telemetry/status and /api/telemetry/spans."""
    client = TestClient(app)
    
    # 1. Status endpoint
    resp = client.get("/api/telemetry/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert "recent_spans" in data
    assert "metric_totals" in data

    # 2. Spans endpoint
    spans_resp = client.get("/api/telemetry/spans?limit=10")
    assert spans_resp.status_code == 200
    spans_data = spans_resp.json()
    assert isinstance(spans_data, list)

    # 3. Reset endpoint
    reset_resp = client.post("/api/telemetry/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "success"

def test_prometheus_metrics_endpoints():
    """Verifies official Prometheus scraping endpoints on /metrics and /api/metrics."""
    client = TestClient(app)
    
    # Run a quick routine STP claim to ensure metrics are recorded
    payload = SYNTHETIC_SCENARIOS["routine_stp"]["payload"]
    req = ClaimSubmissionRequest(**payload)
    submit_claim(req)

    # 1. Root /metrics
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "insurance_claims_submitted_total" in body
    assert "insurance_claims_processed_total" in body
    assert "insurance_claims_settlement_payout_dollars" in body
    assert "insurance_agent_execution_duration_seconds" in body
    assert 'is_stp="true"' in body

    # 2. API /api/metrics
    api_resp = client.get("/api/metrics")
    assert api_resp.status_code == 200
    assert "text/plain" in api_resp.headers["content-type"]
    assert "insurance_claims_processed_total" in api_resp.text
