import os
import json
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from .config import get_eval_model, DEFAULT_EVAL_MODEL
from .metrics import (
    get_faithfulness_metric,
    get_answer_relevancy_metric,
    get_intake_extraction_metric,
    get_denial_compliance_metric,
    get_settlement_transparency_metric
)
from .dataset import (
    CASE_COLLISION_COVERAGE,
    CASE_RACING_EXCLUSION,
    CASE_FNOL_EXTRACTION,
    CASE_LAPSED_POLICY,
    CASE_SETTLEMENT_TRANSPARENCY
)
from backend.app.core.config import DATA_DIR

REPORT_FILE = Path(DATA_DIR) / "deepeval_report.json"

def run_all_evaluations() -> Dict[str, Any]:
    """
    Executes the comprehensive DeepEval evaluation suite across all 
    insurance claims agent reasoning nodes and RAG pipelines.
    """
    eval_model = get_eval_model()
    model_name = eval_model.get_model_name() if hasattr(eval_model, "get_model_name") else DEFAULT_EVAL_MODEL

    def safe_measure(metric, test_case, retries: int = 2):
        for attempt in range(retries + 1):
            try:
                time.sleep(2)
                metric.measure(test_case)
                return
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < retries:
                    print("    [!] Free-tier rate limit reached. Pausing 26s for quota reset...")
                    time.sleep(26)
                else:
                    raise

    print(f"\n==================================================")
    print(f"[*] Running DeepEval AI Evaluation Suite")
    print(f"Evaluation Model: {model_name}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"==================================================\n")

    results: List[Dict[str, Any]] = []

    # 1. RAG Faithfulness Metric on Collision Policy
    print("Evaluating Test 1: Policy RAG Faithfulness...")
    m_faith = get_faithfulness_metric(threshold=0.7, model=eval_model)
    safe_measure(m_faith, CASE_COLLISION_COVERAGE)
    results.append({
        "id": "EVAL-001",
        "name": "Policy RAG Faithfulness",
        "category": "RAG_GROUNDING",
        "metric": "FaithfulnessMetric",
        "score": round(float(m_faith.score), 4),
        "threshold": m_faith.threshold,
        "passed": bool(m_faith.is_successful()),
        "reason": m_faith.reason
    })

    # 2. RAG Answer Relevancy Metric
    print("Evaluating Test 2: Policy Answer Relevancy...")
    m_rel = get_answer_relevancy_metric(threshold=0.7, model=eval_model)
    safe_measure(m_rel, CASE_COLLISION_COVERAGE)

    results.append({
        "id": "EVAL-002",
        "name": "Policy Answer Relevancy",
        "category": "RAG_RELEVANCY",
        "metric": "AnswerRelevancyMetric",
        "score": round(float(m_rel.score), 4),
        "threshold": m_rel.threshold,
        "passed": bool(m_rel.is_successful()),
        "reason": m_rel.reason
    })

    # 3. Denial Regulatory Compliance (Racing Exclusion)
    print("Evaluating Test 3: Racing Exclusion Denial Compliance...")
    m_racing = get_denial_compliance_metric(threshold=0.7, model=eval_model)
    safe_measure(m_racing, CASE_RACING_EXCLUSION)
    results.append({
        "id": "EVAL-003",
        "name": "Racing Exclusion Denial Compliance",
        "category": "REGULATORY_COMPLIANCE",
        "metric": "GEval_DenialCompliance",
        "score": round(float(m_racing.score), 4),
        "threshold": m_racing.threshold,
        "passed": bool(m_racing.is_successful()),
        "reason": m_racing.reason
    })

    # 4. FNOL Intake Extraction Fidelity
    print("Evaluating Test 4: FNOL Entity Extraction Fidelity...")
    m_extract = get_intake_extraction_metric(threshold=0.7, model=eval_model)
    safe_measure(m_extract, CASE_FNOL_EXTRACTION)
    results.append({
        "id": "EVAL-004",
        "name": "FNOL Intake Entity Extraction",
        "category": "EXTRACTION_FIDELITY",
        "metric": "GEval_IntakeExtraction",
        "score": round(float(m_extract.score), 4),
        "threshold": m_extract.threshold,
        "passed": bool(m_extract.is_successful()),
        "reason": m_extract.reason
    })

    # 5. Lapsed Policy Coverage Denial Notice
    print("Evaluating Test 5: Lapsed Policy Denial Notice...")
    m_lapsed = get_denial_compliance_metric(threshold=0.7, model=eval_model)
    safe_measure(m_lapsed, CASE_LAPSED_POLICY)
    results.append({
        "id": "EVAL-005",
        "name": "Lapsed Policy Notice Compliance",
        "category": "REGULATORY_COMPLIANCE",
        "metric": "GEval_DenialCompliance",
        "score": round(float(m_lapsed.score), 4),
        "threshold": m_lapsed.threshold,
        "passed": bool(m_lapsed.is_successful()),
        "reason": m_lapsed.reason
    })

    # 6. Settlement Mathematical Transparency
    print("Evaluating Test 6: Settlement Payout Mathematical Transparency...")
    m_settle = get_settlement_transparency_metric(threshold=0.7, model=eval_model)
    safe_measure(m_settle, CASE_SETTLEMENT_TRANSPARENCY)

    results.append({
        "id": "EVAL-006",
        "name": "Settlement Payout Mathematical Transparency",
        "category": "SETTLEMENT_TRANSPARENCY",
        "metric": "GEval_SettlementTransparency",
        "score": round(float(m_settle.score), 4),
        "threshold": m_settle.threshold,
        "passed": bool(m_settle.is_successful()),
        "reason": m_settle.reason
    })

    # Compute Summary Statistics
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    pass_rate = round((passed_tests / total_tests) * 100, 1)
    avg_score = round(sum(r["score"] for r in results) / total_tests, 4)

    # Category breakdowns
    rag_scores = [r["score"] for r in results if "RAG" in r["category"]]
    rag_avg = round(sum(rag_scores) / len(rag_scores), 4) if rag_scores else 1.0

    compliance_scores = [r["score"] for r in results if r["category"] == "REGULATORY_COMPLIANCE"]
    compliance_avg = round(sum(compliance_scores) / len(compliance_scores), 4) if compliance_scores else 1.0

    extraction_scores = [r["score"] for r in results if r["category"] == "EXTRACTION_FIDELITY"]
    extraction_avg = round(sum(extraction_scores) / len(extraction_scores), 4) if extraction_scores else 1.0

    settlement_scores = [r["score"] for r in results if r["category"] == "SETTLEMENT_TRANSPARENCY"]
    settlement_avg = round(sum(settlement_scores) / len(settlement_scores), 4) if settlement_scores else 1.0

    report = {
        "status": "COMPLETED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_model": model_name,
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate_pct": pass_rate,
            "overall_avg_score": avg_score,
            "category_averages": {
                "rag_grounding_relevancy": rag_avg,
                "regulatory_compliance": compliance_avg,
                "intake_extraction_fidelity": extraction_avg,
                "settlement_math_transparency": settlement_avg
            }
        },
        "test_results": results
    }

    # Save to disk
    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n[OK] DeepEval report saved to {REPORT_FILE}")
    except Exception as e:
        print(f"Warning: Failed to save report file: {e}")

    # Synchronize DeepEval scores and metrics to Langfuse
    try:
        from backend.app.services.observability_service import observability_service
        if observability_service.is_enabled and observability_service.client:
            for r in results:
                metric_key = f"eval_{r['id'].lower().replace('-', '_')}"
                observability_service.record_score(
                    name=metric_key,
                    value=float(r["score"]),
                    session_id="deepeval_benchmarks",
                    comment=f"{r['name']} ({r['metric']}) - Passed: {r['passed']}. Reason: {str(r.get('reason', ''))[:120]}"
                )
            observability_service.record_score(
                name="deepeval_pass_rate",
                value=float(pass_rate),
                session_id="deepeval_benchmarks",
                comment=f"DeepEval Benchmark Suite ({passed_tests}/{total_tests} passed, {pass_rate}%)"
            )
            observability_service.flush()
            report["langfuse_synced"] = True
            report["langfuse_session_id"] = "deepeval_benchmarks"
            print("[OK] DeepEval benchmark scores synchronized with Langfuse.")
        else:
            report["langfuse_synced"] = False
    except Exception as e:
        print(f"Warning: Failed to sync DeepEval metrics to Langfuse: {e}")
        report["langfuse_synced"] = False

    # Terminal summary print
    print(f"\n==================== DeepEval Results ====================")
    print(f"Total Tests: {total_tests} | Passed: {passed_tests} | Pass Rate: {pass_rate}% | Avg Score: {avg_score}")
    print(f"RAG Grounding & Relevancy: {rag_avg * 100}%")
    print(f"Regulatory & Denial Compliance: {compliance_avg * 100}%")
    print(f"Intake Extraction Fidelity: {extraction_avg * 100}%")
    print(f"Settlement Transparency: {settlement_avg * 100}%")
    print(f"==========================================================\n")

    return report

def get_latest_report() -> Dict[str, Any]:
    """Retrieves the latest persisted DeepEval report or runs the suite if not found."""
    if REPORT_FILE.exists():
        try:
            with open(REPORT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return run_all_evaluations()

if __name__ == "__main__":
    run_all_evaluations()
