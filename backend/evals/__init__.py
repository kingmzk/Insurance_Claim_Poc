"""
DeepEval Evaluation Suite for Autonomous Insurance Claims Processing.
Evaluates RAG faithfulness, answer relevancy, intake extraction fidelity, 
and regulatory denial compliance.
"""

from .config import get_eval_model, DEFAULT_EVAL_MODEL
from .metrics import (
    get_faithfulness_metric,
    get_answer_relevancy_metric,
    get_intake_extraction_metric,
    get_denial_compliance_metric,
    get_settlement_transparency_metric
)

def run_all_evaluations():
    from .runner import run_all_evaluations as _run
    return _run()

def get_latest_report():
    from .runner import get_latest_report as _get
    return _get()

__all__ = [
    "get_eval_model",
    "DEFAULT_EVAL_MODEL",
    "get_faithfulness_metric",
    "get_answer_relevancy_metric",
    "get_intake_extraction_metric",
    "get_denial_compliance_metric",
    "get_settlement_transparency_metric",
    "run_all_evaluations",
    "get_latest_report"
]
