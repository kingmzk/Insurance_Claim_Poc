import logging
import os
import time
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from collections import deque

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    InMemoryMetricReader,
)

from .config import (
    OTEL_SERVICE_NAME,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_TRACES_CONSOLE,
)

from prometheus_client import (
    Counter as PromCounter,
    Histogram as PromHistogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

logger = logging.getLogger("telemetry")

def get_or_create_prom_counter(name: str, documentation: str, labelnames=()):
    """Safely retrieves existing counter or creates new one without collision."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return PromCounter(name, documentation, labelnames=labelnames)

def get_or_create_prom_histogram(name: str, documentation: str, labelnames=(), buckets=None):
    """Safely retrieves existing histogram or creates new one without collision."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    kwargs = {}
    if buckets is not None:
        kwargs["buckets"] = buckets
    return PromHistogram(name, documentation, labelnames=labelnames, **kwargs)

# Standard Prometheus Metrics
PROM_CLAIMS_SUBMITTED = get_or_create_prom_counter(
    "insurance_claims_submitted_total",
    "Total count of submitted insurance claims",
    labelnames=["claim_type", "loss_type"]
)

PROM_CLAIMS_PROCESSED = get_or_create_prom_counter(
    "insurance_claims_processed_total",
    "Total count of processed insurance claims",
    labelnames=["status", "loss_type", "is_stp"]
)

PROM_SIU_REFERRALS = get_or_create_prom_counter(
    "insurance_claims_siu_referrals_total",
    "Total count of claims escalated to Special Investigations Unit (SIU)",
    labelnames=["reason"]
)

PROM_POLICY_EXCEPTIONS = get_or_create_prom_counter(
    "insurance_claims_policy_exceptions_total",
    "Total count of policy coverage exceptions / denials drafted",
    labelnames=["reason"]
)

PROM_SETTLEMENT_PAYOUT = get_or_create_prom_histogram(
    "insurance_claims_settlement_payout_dollars",
    "Approved claim settlement payout amounts in USD",
    buckets=[0, 500, 1000, 2500, 5000, 10000, 25000, 50000]
)

PROM_FRAUD_SCORE = get_or_create_prom_histogram(
    "insurance_claims_fraud_score",
    "Distribution of composite fraud risk scores (0-100 scale)",
    buckets=[0, 10, 25, 50, 75, 90, 100]
)

PROM_AGENT_DURATION = get_or_create_prom_histogram(
    "insurance_agent_execution_duration_seconds",
    "Execution latency of individual autonomous agents in seconds",
    labelnames=["agent_name"],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

class BoundedInMemorySpanExporter(SpanExporter):
    """
    Thread-safe in-memory ring-buffer span exporter.
    Retains the most recent N spans for live diagnostics, REST API inspection,
    and automated test assertions.
    """
    def __init__(self, max_spans: int = 200):
        self.max_spans = max_spans
        self._spans: deque = deque(maxlen=max_spans)

    def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
        for s in spans:
            self._spans.append(s)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def clear(self) -> None:
        self._spans.clear()

    def get_finished_spans(self) -> List[ReadableSpan]:
        return list(self._spans)


class TelemetryManager:
    """
    Production-grade OpenTelemetry Manager for the Insurance Claims Platform.
    Provides standard TracerProvider, MeterProvider, dual OTLP / In-Memory exporters,
    W3C trace context formatters, semantic agent spans, and telemetry status summaries.
    """
    _instance: Optional["TelemetryManager"] = None

    def __init__(self):
        self.service_name = OTEL_SERVICE_NAME or "insurance-claims-orchestrator"
        self.in_memory_exporter = BoundedInMemorySpanExporter(max_spans=250)
        self.in_memory_metric_reader = InMemoryMetricReader()
        
        # Internal metric aggregation counters for instant API telemetry queries
        self._metric_totals = {
            "claims_submitted": 0,
            "claims_processed": 0,
            "claims_stp": 0,
            "siu_referrals": 0,
            "policy_exceptions": 0,
            "total_payout_amount": 0.0,
            "fraud_scores_recorded": 0,
            "agent_spans_recorded": 0,
        }

        self._init_providers()

    def _init_providers(self):
        """Initializes Resource, TracerProvider, and MeterProvider with exporters."""
        # 1. Define standard OpenTelemetry Resource
        self.resource = Resource.create({
            "service.name": self.service_name,
            "service.namespace": "insurance.claims",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "poc"),
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })

        # 2. Setup TracerProvider
        self.tracer_provider = TracerProvider(resource=self.resource)

        # Always attach bounded in-memory exporter for UI & API diagnostics
        self.tracer_provider.add_span_processor(
            SimpleSpanProcessor(self.in_memory_exporter)
        )

        # Attach standard OTLP exporter if endpoint configured
        otlp_endpoint = OTEL_EXPORTER_OTLP_ENDPOINT.strip()
        self.otlp_enabled = False
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                self.otlp_enabled = True
                logger.info(f"OpenTelemetry OTLP SpanExporter enabled: {otlp_endpoint}")
            except Exception as e:
                logger.warning(f"Failed to initialize OTLP SpanExporter ({otlp_endpoint}): {e}")

        # Optional Console exporter for local developer debugging
        if OTEL_TRACES_CONSOLE:
            self.tracer_provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )

        # Register global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = self.tracer_provider.get_tracer(
            "insurance.claims.tracer",
            schema_url="https://opentelemetry.io/schemas/1.25.0"
        )

        # 3. Setup MeterProvider
        self.meter_provider = MeterProvider(
            resource=self.resource,
            metric_readers=[self.in_memory_metric_reader]
        )
        metrics.set_meter_provider(self.meter_provider)
        self.meter = self.meter_provider.get_meter(
            "insurance.claims.meter",
            version="1.0.0"
        )

        # 4. Create Standard OpenTelemetry Metric Instruments
        self.claims_submitted_counter = self.meter.create_counter(
            name="claims.submitted.total",
            unit="1",
            description="Total count of initial claims submitted to the system."
        )

        self.claims_processed_counter = self.meter.create_counter(
            name="claims.processed.total",
            unit="1",
            description="Total count of claims completed by the multi-agent pipeline."
        )

        self.siu_referrals_counter = self.meter.create_counter(
            name="claims.siu_referrals.total",
            unit="1",
            description="Total count of claims escalated to Special Investigations Unit (SIU)."
        )

        self.policy_exceptions_counter = self.meter.create_counter(
            name="claims.policy_exceptions.total",
            unit="1",
            description="Total count of policy coverage exceptions / denials drafted."
        )

        self.settlement_payout_histogram = self.meter.create_histogram(
            name="claims.settlement.payout",
            unit="USD",
            description="Approved claim settlement payout amounts in USD."
        )

        self.fraud_score_histogram = self.meter.create_histogram(
            name="claims.fraud.score",
            unit="1",
            description="Distribution of composite fraud risk scores (0-100 scale)."
        )

        self.agent_duration_histogram = self.meter.create_histogram(
            name="agent.execution.duration_ms",
            unit="ms",
            description="Execution latency of individual autonomous agents in milliseconds."
        )

    # =========================================================================
    # Context & W3C Trace Formatting Helpers
    # =========================================================================
    @staticmethod
    def format_trace_id(trace_id_int: int) -> str:
        """Converts integer trace ID to 32-character lowercase hex string."""
        return f"{trace_id_int:032x}" if trace_id_int else ""

    @staticmethod
    def format_span_id(span_id_int: int) -> str:
        """Converts integer span ID to 16-character lowercase hex string."""
        return f"{span_id_int:016x}" if span_id_int else ""

    def get_current_trace_id(self) -> Optional[str]:
        """Returns the W3C 32-char hex trace ID of the active span, if any."""
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            if ctx.is_valid:
                return self.format_trace_id(ctx.trace_id)
        return None

    def get_current_span_id(self) -> Optional[str]:
        """Returns the W3C 16-char hex span ID of the active span, if any."""
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            if ctx.is_valid:
                return self.format_span_id(ctx.span_id)
        return None

    # =========================================================================
    # Agent Tracing Context Manager
    # =========================================================================
    @contextmanager
    def trace_agent(
        self,
        agent_name: str,
        claim_id: str,
        initial_attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        OpenTelemetry context manager for autonomous agent execution.
        Creates child span 'agent.<name>', populates standard semantic attributes,
        tracks execution time in milliseconds, and catches/records exceptions.
        """
        span_name = f"agent.{agent_name}"
        t0 = time.perf_counter()

        with self.tracer.start_as_current_span(span_name) as span:
            # Set baseline semantic attributes
            span.set_attribute("insurance.agent.name", agent_name)
            span.set_attribute("insurance.claim.id", claim_id)
            span.set_attribute("insurance.telemetry.domain", "claims_adjudication")

            if initial_attributes:
                for k, v in initial_attributes.items():
                    if v is not None:
                        span.set_attribute(str(k), str(v) if isinstance(v, (list, dict)) else v)

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            finally:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                span.set_attribute("agent.duration_ms", elapsed_ms)
                
                # Record in OpenTelemetry histogram & internal metrics
                self.agent_duration_histogram.record(
                    elapsed_ms,
                    attributes={"agent.name": agent_name}
                )
                self._metric_totals["agent_spans_recorded"] += 1

                # Record in Prometheus histogram (in seconds)
                try:
                    PROM_AGENT_DURATION.labels(agent_name=agent_name).observe(elapsed_ms / 1000.0)
                except Exception as e:
                    logger.debug(f"Prometheus agent duration metric error: {e}")

    # =========================================================================
    # Domain Metric Recording
    # =========================================================================
    def record_submission(self, claim_id: str, claim_type: str, loss_type: str, claimed_amt: float):
        """Records initial claim submission in OpenTelemetry and Prometheus metrics."""
        self.claims_submitted_counter.add(
            1,
            attributes={"claim.type": claim_type, "claim.loss_type": loss_type}
        )
        self._metric_totals["claims_submitted"] += 1

        try:
            PROM_CLAIMS_SUBMITTED.labels(claim_type=claim_type, loss_type=loss_type).inc()
        except Exception as e:
            logger.debug(f"Prometheus claims submitted metric error: {e}")

    def record_claim_completion(self, final_state: Dict[str, Any]):
        """
        Records comprehensive outcome metrics for a completed claim run:
        - Claims processed counter (OTel + Prometheus)
        - Fraud score distribution (OTel + Prometheus)
        - Settlement payout distribution (OTel + Prometheus)
        - SIU / Policy exception flags (OTel + Prometheus)
        """
        status = final_state.get("current_status", "UNKNOWN")
        claim_type = final_state.get("claim_type", "motor")
        intake = final_state.get("intake_data", {})
        loss_type = intake.get("loss_type", "collision")
        is_stp = (status == "SETTLED_STP")

        self.claims_processed_counter.add(
            1,
            attributes={
                "claim.status": status,
                "claim.loss_type": loss_type,
                "claim.type": claim_type,
                "claim.is_stp": str(is_stp).lower(),
            }
        )
        self._metric_totals["claims_processed"] += 1
        if is_stp:
            self._metric_totals["claims_stp"] += 1

        try:
            PROM_CLAIMS_PROCESSED.labels(
                status=status,
                loss_type=loss_type,
                is_stp=str(is_stp).lower()
            ).inc()
        except Exception as e:
            logger.debug(f"Prometheus claims processed metric error: {e}")

        # Fraud metric
        fraud_rep = final_state.get("fraud_report", {})
        if fraud_rep and "fraud_score" in fraud_rep:
            fraud_score = float(fraud_rep.get("fraud_score", 0.0))
            self.fraud_score_histogram.record(
                fraud_score,
                attributes={"claim.loss_type": loss_type}
            )
            self._metric_totals["fraud_scores_recorded"] += 1

            try:
                PROM_FRAUD_SCORE.observe(fraud_score)
            except Exception as e:
                logger.debug(f"Prometheus fraud score metric error: {e}")

            if fraud_rep.get("siu_escalate"):
                self.siu_referrals_counter.add(
                    1,
                    attributes={"reason": "high_fraud_score"}
                )
                self._metric_totals["siu_referrals"] += 1
                try:
                    PROM_SIU_REFERRALS.labels(reason="high_fraud_score").inc()
                except Exception as e:
                    logger.debug(f"Prometheus SIU metric error: {e}")

        # Policy exception metric
        policy_val = final_state.get("policy_validation", {})
        if policy_val and not policy_val.get("eligible", True):
            reason = policy_val.get("exception_reason") or "coverage_exclusion"
            self.policy_exceptions_counter.add(
                1,
                attributes={"reason": reason[:60]}
            )
            self._metric_totals["policy_exceptions"] += 1
            try:
                PROM_POLICY_EXCEPTIONS.labels(reason=reason[:60]).inc()
            except Exception as e:
                logger.debug(f"Prometheus policy exception metric error: {e}")

        # Settlement payout metric
        settle_dec = final_state.get("settlement_decision", {})
        if settle_dec and "proposed_payout" in settle_dec:
            payout = float(settle_dec.get("proposed_payout", 0.0))
            if payout > 0:
                self.settlement_payout_histogram.record(
                    payout,
                    attributes={"claim.status": status, "claim.loss_type": loss_type}
                )
                self._metric_totals["total_payout_amount"] += payout
                try:
                    PROM_SETTLEMENT_PAYOUT.observe(payout)
                except Exception as e:
                    logger.debug(f"Prometheus settlement payout metric error: {e}")

    # =========================================================================
    # Telemetry Inspection & Status API
    # =========================================================================
    def get_telemetry_status(self) -> Dict[str, Any]:
        """
        Returns full telemetry diagnostics, active OpenTelemetry configuration,
        metric totals, and recent spans formatted with W3C IDs and attributes.
        """
        finished_spans = self.in_memory_exporter.get_finished_spans()
        recent_spans_summary = []

        # Return latest 30 spans formatted
        for s in reversed(finished_spans[-30:]):
            ctx = s.get_span_context()
            parent = s.parent
            parent_id = self.format_span_id(parent.span_id) if parent and parent.is_valid else None
            
            # Duration in ms
            duration_ms = 0.0
            if s.end_time and s.start_time:
                duration_ms = round((s.end_time - s.start_time) / 1_000_000, 2)

            recent_spans_summary.append({
                "name": s.name,
                "trace_id": self.format_trace_id(ctx.trace_id),
                "span_id": self.format_span_id(ctx.span_id),
                "parent_span_id": parent_id,
                "status": s.status.status_code.name,
                "status_description": s.status.description,
                "duration_ms": duration_ms,
                "attributes": dict(s.attributes or {}),
                "events_count": len(s.events),
            })

        return {
            "status": "active",
            "service_name": self.service_name,
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "poc"),
            "exporters": {
                "in_memory": True,
                "otlp_endpoint": OTEL_EXPORTER_OTLP_ENDPOINT or "none (in-memory buffer active)",
                "otlp_active": self.otlp_enabled,
                "console_logging": OTEL_TRACES_CONSOLE,
                "prometheus_metrics": "/metrics",
            },
            "spans_recorded_total": len(finished_spans),
            "metric_totals": self._metric_totals,
            "recent_spans": recent_spans_summary,
        }

    def get_prometheus_metrics(self) -> bytes:
        """Exports all Prometheus metrics in official exposition text format."""
        return generate_latest()

    def clear_spans(self):
        """Resets the in-memory span buffer (useful for unit tests)."""
        self.in_memory_exporter.clear()


# Global Singleton Telemetry Manager
telemetry_manager = TelemetryManager()

