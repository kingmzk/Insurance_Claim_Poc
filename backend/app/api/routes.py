import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response

from ..models.state import ClaimSubmissionRequest, ReviewDecisionRequest, ClaimState
from ..workflow.graph import claims_graph
from ..db.database import get_db_connection
from ..services.ledger_service import LedgerService
from ..services.observability_service import observability_service
from ..core.telemetry import telemetry_manager, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/api")


# Predefined Synthetic Demo Scenarios
SYNTHETIC_SCENARIOS = {
    "routine_stp": {
        "key": "routine_stp",
        "name": "Scenario 1: Routine Claim (Fast-Track STP)",
        "description": "Complete submission, active policy, low fraud score (12), standard rear collision repair ($2,950 approved - $500 deductible - $210 depr = $2,240 payout). Executes automated simulated STP payment.",
        "payload": {
            "claim_id": "CLM-DEMO-001",
            "policy_no": "POL-AUTO-99201",
            "claimant_name": "John Doe",
            "loss_date": "2026-03-15",
            "loss_type": "rear_collision",
            "claimed_amt": 3200.00,
            "vin": "1HGCR2F83HA001234",
            "vehicle_make_model": "2023 Honda Accord",
            "incident_description": "Rear-ended while waiting at traffic light. Rear bumper cover and ultrasonic parking sensors damaged.",
            "documents": [{"doc_type": "repair_estimate", "filename": "honda_certified_estimate.pdf"}],
            "photos": [{
                "photo_id": "photo_001",
                "filename": "honda_rear_bumper.jpg",
                "phash": "1122334455667788",
                "exif_timestamp": "2026-03-15T14:30:00",
                "reported_incident_timestamp": "2026-03-15T14:00:00",
                "is_tampered": False
            }]
        }
    },
    "missing_info": {
        "key": "missing_info",
        "name": "Scenario 2: Incomplete Submission (Needs Info)",
        "description": "Missing vehicle VIN and itemized repair estimate. Halts at Gate 1 with status NEEDS_INFO and generates document request.",
        "payload": {
            "claim_id": "CLM-DEMO-002",
            "policy_no": "POL-AUTO-99201",
            "claimant_name": "Alice Walker",
            "loss_date": "2026-03-18",
            "loss_type": "side_impact",
            "claimed_amt": 2400.00,
            "vin": None,
            "vehicle_make_model": "2021 Toyota Camry",
            "incident_description": "Side scraped in parking lot while vehicle was unattended.",
            "documents": [],
            "photos": []
        }
    },
    "excluded_policy": {
        "key": "excluded_policy",
        "name": "Scenario 3: Excluded Activity (Draft Denial)",
        "description": "Damage occurred during amateur track racing. Bypasses Fraud/Risk stages and drafts coverage denial citing Section 8.3 for human review.",
        "payload": {
            "claim_id": "CLM-DEMO-003",
            "policy_no": "POL-AUTO-99201",
            "claimant_name": "David Miller",
            "loss_date": "2026-03-19",
            "loss_type": "collision",
            "claimed_amt": 4500.00,
            "vin": "1HGCR2F83HA001234",
            "vehicle_make_model": "2023 Honda Accord Sport",
            "incident_description": "Vehicle impacted track safety barrier during weekend amateur track racing speed contest event.",
            "documents": [{"doc_type": "repair_estimate", "filename": "track_estimate.pdf"}],
            "photos": [{
                "photo_id": "photo_003",
                "filename": "track_barrier_damage.jpg",
                "phash": "9988776655443322",
                "exif_timestamp": "2026-03-19T11:00:00",
                "reported_incident_timestamp": "2026-03-19T10:45:00",
                "is_tampered": False
            }]
        }
    },
    "fraud_freeze": {
        "key": "fraud_freeze",
        "name": "Scenario 4: Potential Fraud / Duplicate Photo (SIU Freeze)",
        "description": "Photo perceptual hash matches prior settled claim CLM-2024-1102 and EXIF date predates incident by 2 months. Halts at Gate 3 for SIU investigation.",
        "payload": {
            "claim_id": "CLM-DEMO-004",
            "policy_no": "POL-AUTO-99201",
            "claimant_name": "Robert Bell",
            "loss_date": "2026-03-20",
            "loss_type": "rear_collision",
            "claimed_amt": 3400.00,
            "vin": "1HGCR2F83HA001234",
            "vehicle_make_model": "2023 Honda Accord",
            "incident_description": "Rear bumper damage reported from minor parking mishap.",
            "documents": [{"doc_type": "repair_estimate", "filename": "invoice_bell.pdf"}],
            "photos": [{
                "photo_id": "photo_004",
                "filename": "reused_bumper.jpg",
                "phash": "a8b4c9e1f203d456",
                "exif_timestamp": "2026-01-10T09:00:00",
                "reported_incident_timestamp": "2026-03-20T16:00:00",
                "is_tampered": False
            }]
        }
    },
    "high_estimate": {
        "key": "high_estimate",
        "name": "Scenario 5: High Value Claim (Adjuster Approval)",
        "description": "Luxury vehicle front collision claimed at $18,500 ($14,000 net payout). Exceeds $5,000 STP limit and High Risk Tier. Routed to Adjuster Approval Queue.",
        "payload": {
            "claim_id": "CLM-DEMO-005",
            "policy_no": "POL-AUTO-88104",
            "claimant_name": "Marcus Vance",
            "loss_date": "2026-03-21",
            "loss_type": "front_impact",
            "claimed_amt": 18500.00,
            "vin": "WAUZZZF28HA009876",
            "vehicle_make_model": "2024 Audi RS6 Avant",
            "incident_description": "Front impact with highway debris. Damaged intercooler, carbon fiber apron, and Matrix LED headlight assembly.",
            "documents": [{"doc_type": "repair_estimate", "filename": "audi_oem_quote.pdf"}],
            "photos": [{
                "photo_id": "photo_005",
                "filename": "audi_front_damage.jpg",
                "phash": "3344556677889900",
                "exif_timestamp": "2026-03-21T18:00:00",
                "reported_incident_timestamp": "2026-03-21T17:45:00",
                "is_tampered": False
            }]
        }
    }
}

def persist_claim_run(final_state: ClaimState):
    """Saves final claim state, audit trail, and creates review tasks in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    claim_id = final_state.get("claim_id")
    status = final_state.get("current_status", "UNKNOWN")
    claim_type = final_state.get("claim_type", "motor")
    now = datetime.now(timezone.utc).isoformat()
    state_json = json.dumps(final_state)
    
    trace_id = final_state.get("trace_id")
    trace_url = final_state.get("trace_url")
    otel_trace_id = final_state.get("otel_trace_id")
    
    # 1. Insert or update claims
    cursor.execute("""
    INSERT INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json, trace_id, trace_url, otel_trace_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(claim_id) DO UPDATE SET
        status = excluded.status,
        updated_at = excluded.updated_at,
        state_json = excluded.state_json,
        trace_id = excluded.trace_id,
        trace_url = excluded.trace_url,
        otel_trace_id = excluded.otel_trace_id;
    """, (claim_id, status, claim_type, now, now, state_json, trace_id, trace_url, otel_trace_id))

    
    # 2. Insert audit events
    audit_events = final_state.get("audit_events", [])
    for event in audit_events:
        cursor.execute("""
        INSERT INTO audit_events (claim_id, stage, event_type, route_reason, evidence_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (
            claim_id,
            event.get("stage", "UNKNOWN"),
            event.get("event_type", "EVENT"),
            event.get("route_reason", ""),
            json.dumps(event.get("evidence", {})),
            event.get("timestamp", now)
        ))
        
    # 3. Create Review Task if Human action is required
    if status == "NEEDS_INFO":
        task_id = f"TSK-INFO-{claim_id}"
        cursor.execute("""
        INSERT OR IGNORE INTO review_tasks (task_id, claim_id, task_type, priority, status, details_json, created_at)
        VALUES (?, ?, 'NEEDS_INFO', 'MEDIUM', 'PENDING', ?, ?);
        """, (task_id, claim_id, json.dumps({"missing": final_state.get("missing_fields", [])}), now))
    elif status == "PENDING_REVIEW":
        fraud_rep = final_state.get("fraud_report", {})
        policy_val = final_state.get("policy_validation", {})
        settle_dec = final_state.get("settlement_decision", {})
        
        if fraud_rep.get("siu_escalate"):
            task_id = f"TSK-SIU-{claim_id}"
            task_type = "SIU_FRAUD"
            priority = "URGENT"
            details = {"score": fraud_rep.get("fraud_score"), "flags": fraud_rep.get("flags")}
        elif not policy_val.get("eligible", True):
            task_id = f"TSK-COV-{claim_id}"
            task_type = "COVERAGE_EXCEPTION"
            priority = "HIGH"
            details = {"reason": policy_val.get("exception_reason"), "citations": policy_val.get("citations")}
        else:
            task_id = f"TSK-ADJ-{claim_id}"
            task_type = "ADJUSTER_APPROVAL"
            priority = "MEDIUM"
            details = {
                "proposed_payout": settle_dec.get("proposed_payout"),
                "reasons": settle_dec.get("approval_reasons", [])
            }
            
        cursor.execute("""
        INSERT OR IGNORE INTO review_tasks (task_id, claim_id, task_type, priority, status, details_json, created_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?);
        """, (task_id, claim_id, task_type, priority, json.dumps(details), now))

    conn.commit()
    conn.close()

@router.post("/claims/submit")
def submit_claim(request: ClaimSubmissionRequest):
    """Submits a claim and triggers the LangGraph multi-agent pipeline."""
    claim_id = request.claim_id or f"CLM-{uuid.uuid4().hex[:6].upper()}"
    
    initial_state: ClaimState = {
        "claim_id": claim_id,
        "claim_type": request.claim_type,
        "intake_data": {
            "policy_no": request.policy_no,
            "claimant_name": request.claimant_name,
            "loss_date": request.loss_date,
            "loss_type": request.loss_type,
            "claimed_amt": request.claimed_amt,
            "vin": request.vin,
            "vehicle_make_model": request.vehicle_make_model,
            "incident_description": request.incident_description,
            "documents": [d.model_dump() for d in request.documents],
            "photos": [p.model_dump() for p in request.photos]
        },
        "completeness": 0.0,
        "missing_fields": [],
        "policy_validation": {},
        "fraud_report": {},
        "risk_assessment": {},
        "settlement_decision": {},
        "current_status": "INTAKE_STARTED",
        "route_reason": "Initiated multi-agent claims adjudication.",
        "audit_events": [],
        "errors": []
    }
    
    # Insert initial claim record so foreign keys in ledger and tasks are valid
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO claims (claim_id, status, claim_type, created_at, updated_at, state_json)
    VALUES (?, 'IN_PROGRESS', ?, ?, ?, ?)
    ON CONFLICT(claim_id) DO UPDATE SET
        status = 'IN_PROGRESS',
        updated_at = excluded.updated_at,
        state_json = excluded.state_json;
    """, (claim_id, request.claim_type, now, now, json.dumps(initial_state)))
    conn.commit()
    conn.close()

    # Configure Langfuse Observability Callback & Trace Context
    langfuse_handler = observability_service.get_langchain_callback(
        claim_id=claim_id,
        claimant_name=request.claimant_name,
        loss_type=request.loss_type,
        tags=["motor_claims", request.loss_type, "poc"]
    )
    
    config = {
        "run_name": f"ClaimWorkflow-{claim_id}",
        "tags": ["motor_claims", "langgraph", request.loss_type],
        "metadata": {
            "langfuse_trace_name": f"Insurance Claim Workflow: {claim_id}",
            "langfuse_session_id": claim_id,
            "langfuse_user_id": request.claimant_name,
            "langfuse_tags": ["insurance_claim", "langgraph", request.loss_type],
            "claim_id": claim_id,
            "claimant_name": request.claimant_name,
            "policy_no": request.policy_no,
            "claimed_amt": request.claimed_amt,
            "loss_type": request.loss_type,
        }
    }
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    # OpenTelemetry Metric: Record submission
    telemetry_manager.record_submission(
        claim_id=claim_id,
        claim_type=request.claim_type,
        loss_type=request.loss_type,
        claimed_amt=request.claimed_amt
    )

    # Execute LangGraph state machine inside root OpenTelemetry span
    with telemetry_manager.tracer.start_as_current_span("insurance.claim.adjudication") as root_span:
        root_span.set_attribute("insurance.claim.id", claim_id)
        root_span.set_attribute("claim.type", request.claim_type)
        root_span.set_attribute("claim.loss_type", request.loss_type)
        root_span.set_attribute("claim.claimed_amt", request.claimed_amt)
        root_span.set_attribute("claim.policy_no", request.policy_no)
        root_span.set_attribute("claimant.name", request.claimant_name)

        try:
            final_state = claims_graph.invoke(initial_state, config=config)
        except Exception as e:
            root_span.record_exception(e)
            raise HTTPException(status_code=500, detail=f"Orchestration failure: {str(e)}")

        otel_ctx = root_span.get_span_context()
        otel_trace_id = telemetry_manager.format_trace_id(otel_ctx.trace_id)
        root_span.set_attribute("claim.status", final_state.get("current_status", "UNKNOWN"))

    # Extract trace ID and generate direct Langfuse Trace URL
    trace_id = getattr(langfuse_handler, "last_trace_id", None) if langfuse_handler else None
    trace_url = observability_service.get_trace_url(trace_id) if trace_id else None
    
    final_state["trace_id"] = trace_id or otel_trace_id
    final_state["otel_trace_id"] = otel_trace_id
    final_state["trace_url"] = trace_url

    # Record domain evaluation scores to Langfuse session
    observability_service.record_claim_metrics(final_state, trace_id=trace_id)
    observability_service.flush()

    # Record OpenTelemetry completion metrics & counter increments
    telemetry_manager.record_claim_completion(final_state)
        
    # Persist in SQLite
    persist_claim_run(final_state)
    return final_state


@router.get("/claims")
def list_claims(limit: int = 20):
    """Lists submitted claims with current state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM claims ORDER BY updated_at DESC LIMIT ?;", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        st = json.loads(r["state_json"])
        trace_id = r["trace_id"] if "trace_id" in r.keys() else st.get("trace_id")
        trace_url = r["trace_url"] if "trace_url" in r.keys() else st.get("trace_url")
        otel_trace_id = r["otel_trace_id"] if "otel_trace_id" in r.keys() else st.get("otel_trace_id")
        results.append({
            "claim_id": r["claim_id"],
            "status": r["status"],
            "claim_type": r["claim_type"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "trace_id": trace_id,
            "otel_trace_id": otel_trace_id,
            "trace_url": trace_url,
            "state": st
        })
    return results

@router.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    """Retrieves full claim state and any associated review tasks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM claims WHERE claim_id = ?;", (claim_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Claim not found")
        
    cursor.execute("SELECT * FROM review_tasks WHERE claim_id = ? ORDER BY created_at DESC;", (claim_id,))
    tasks = [dict(t) for t in cursor.fetchall()]
    conn.close()
    
    st = json.loads(row["state_json"])
    trace_id = row["trace_id"] if "trace_id" in row.keys() else st.get("trace_id")
    trace_url = row["trace_url"] if "trace_url" in row.keys() else st.get("trace_url")
    otel_trace_id = row["otel_trace_id"] if "otel_trace_id" in row.keys() else st.get("otel_trace_id")
    return {
        "claim_id": row["claim_id"],
        "status": row["status"],
        "trace_id": trace_id,
        "otel_trace_id": otel_trace_id,
        "trace_url": trace_url,
        "state": st,
        "review_tasks": tasks
    }


@router.get("/claims/{claim_id}/audit")
def get_claim_audit(claim_id: str):
    """Retrieves chronological audit events for a claim."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_events WHERE claim_id = ? ORDER BY event_id ASC;", (claim_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/reviews")
def list_review_tasks(status: str = Query("PENDING")):
    """Lists human review tasks (Adjuster or SIU)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT r.*, c.state_json 
    FROM review_tasks r
    JOIN claims c ON r.claim_id = c.claim_id
    WHERE r.status = ?
    ORDER BY r.created_at DESC;
    """, (status,))
    rows = cursor.fetchall()
    conn.close()
    
    tasks = []
    for r in rows:
        tasks.append({
            "task_id": r["task_id"],
            "claim_id": r["claim_id"],
            "task_type": r["task_type"],
            "priority": r["priority"],
            "status": r["status"],
            "details": json.loads(r["details_json"]),
            "decision_note": r["decision_note"],
            "created_at": r["created_at"],
            "claim_state": json.loads(r["state_json"])
        })
    return tasks

@router.post("/reviews/{task_id}/decision")
def record_review_decision(task_id: str, request: ReviewDecisionRequest):
    """Adjuster or SIU investigator records a decision on a queued review task."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM review_tasks WHERE task_id = ?;", (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Review task not found")
        
    claim_id = task["claim_id"]
    cursor.execute("SELECT state_json FROM claims WHERE claim_id = ?;", (claim_id,))
    claim_row = cursor.fetchone()
    if not claim_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Associated claim not found")
        
    claim_state = json.loads(claim_row["state_json"])
    now = datetime.now(timezone.utc).isoformat()
    
    # Process human decision
    if request.decision == "APPROVED":
        payout = request.adjusted_payout if request.adjusted_payout is not None else claim_state.get("settlement_decision", {}).get("proposed_payout", 0.0)
        
        # Disburse payment in ledger
        disbursement = LedgerService.disburse_settlement(
            claim_id=claim_id,
            amount=payout,
            recipient=claim_state.get("intake_data", {}).get("claimant_name", "Claimant")
        )
        
        claim_state["current_status"] = "SETTLED_MANUAL"
        claim_state["settlement_decision"] = {
            **claim_state.get("settlement_decision", {}),
            "status": "APPROVED_BY_ADJUSTER",
            "net_payout": payout,
            "txn_ref": disbursement.get("txn_id"),
            "adjuster_notes": request.notes
        }
        claim_state["route_reason"] = f"Adjuster approved payout of ${payout:,.2f}. Txn: {disbursement.get('txn_id')}"
        
    elif request.decision == "REJECTED":
        claim_state["current_status"] = "DENIED_BY_ADJUSTER"
        claim_state["settlement_decision"] = {
            **claim_state.get("settlement_decision", {}),
            "status": "DENIED",
            "net_payout": 0.0,
            "denial_notes": request.notes
        }
        claim_state["route_reason"] = f"Adjuster confirmed claim denial: {request.notes}"
    else: # REQUEST_INFO
        claim_state["current_status"] = "NEEDS_INFO"
        claim_state["route_reason"] = f"Adjuster requested additional information: {request.notes}"
        
    # Update review task
    cursor.execute("""
    UPDATE review_tasks 
    SET status = ?, decision_note = ?, resolved_at = ?
    WHERE task_id = ?;
    """, (request.decision, request.notes, now, task_id))
    
    # Update claim state
    cursor.execute("""
    UPDATE claims 
    SET status = ?, updated_at = ?, state_json = ?
    WHERE claim_id = ?;
    """, (claim_state["current_status"], now, json.dumps(claim_state), claim_id))
    
    # Log audit event
    cursor.execute("""
    INSERT INTO audit_events (claim_id, stage, event_type, route_reason, evidence_json, created_at)
    VALUES (?, 'HUMAN_REVIEW', ?, ?, ?, ?);
    """, (
        claim_id,
        f"REVIEW_{request.decision}",
        claim_state["route_reason"],
        json.dumps({"reviewer": request.reviewer_id, "notes": request.notes}),
        now
    ))
    
    conn.commit()
    conn.close()
    
    # Record human-in-the-loop decision score in Langfuse
    observability_service.record_human_review(
        claim_id=claim_id,
        decision=request.decision,
        reviewer_id=request.reviewer_id,
        adjusted_payout=request.adjusted_payout,
        notes=request.notes,
        trace_id=claim_state.get("trace_id")
    )
    observability_service.flush()
    
    return {
        "task_id": task_id,
        "decision": request.decision,
        "updated_claim_status": claim_state["current_status"],
        "claim_state": claim_state
    }

@router.get("/scenarios")
def list_scenarios():
    """Lists pre-packaged synthetic scenarios for 1-click execution."""
    return list(SYNTHETIC_SCENARIOS.values())

@router.post("/scenarios/run/{scenario_key}")
def run_scenario(scenario_key: str):
    """Executes a pre-packaged synthetic scenario immediately."""
    scenario = SYNTHETIC_SCENARIOS.get(scenario_key)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario key not found")
        
    req = ClaimSubmissionRequest(**scenario["payload"])
    return submit_claim(req)

@router.post("/database/reset")
def reset_database():
    """Resets claims, review tasks, audit logs, and simulated ledger to clean demo state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM review_tasks;")
    cursor.execute("DELETE FROM audit_events;")
    cursor.execute("DELETE FROM simulated_ledger;")
    cursor.execute("DELETE FROM claims;")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Demo database cleared and reset successfully."}

@router.get("/evals/report")
def get_eval_report():
    """Returns the latest DeepEval LLM evaluation report and metrics."""
    from backend.evals import get_latest_report
    return get_latest_report()

@router.post("/evals/run")
def trigger_eval_suite():
    """Triggers an on-demand DeepEval test run across all insurance agent nodes."""
    from backend.evals import run_all_evaluations
    return run_all_evaluations()

@router.get("/observability/status")
def get_observability_status():
    """Returns Langfuse observability connectivity status and configuration."""
    return {
        "enabled": observability_service.is_enabled,
        "base_url": "https://us.cloud.langfuse.com",
        "has_keys": bool(observability_service.client is not None)
    }

# ==============================================================================
# OpenTelemetry Endpoints
# ==============================================================================
@router.get("/telemetry/status")
def get_telemetry_status():
    """
    Returns full OpenTelemetry runtime diagnostics, active Tracer/Meter providers,
    exporter states, metric counters, and formatted recent spans.
    """
    return telemetry_manager.get_telemetry_status()

@router.get("/telemetry/spans")
def list_telemetry_spans(claim_id: Optional[str] = None, limit: int = 50):
    """
    Retrieves recent OpenTelemetry spans captured by the in-memory exporter.
    Optionally filters by claim_id.
    """
    status = telemetry_manager.get_telemetry_status()
    spans = status.get("recent_spans", [])
    if claim_id:
        spans = [s for s in spans if s.get("attributes", {}).get("insurance.claim.id") == claim_id or s.get("attributes", {}).get("claim.id") == claim_id]
    return spans[:limit]

@router.post("/telemetry/reset")
def reset_telemetry():
    """Clears in-memory OpenTelemetry span buffer."""
    telemetry_manager.clear_spans()
    return {"status": "success", "message": "In-memory OpenTelemetry span buffer cleared."}

@router.get("/metrics")
def get_prometheus_metrics():
    """Returns official Prometheus exposition metrics on /api/metrics."""
    return Response(content=telemetry_manager.get_prometheus_metrics(), media_type=CONTENT_TYPE_LATEST)



