from typing import Optional
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, GEval
from deepeval.test_case import SingleTurnParams
from deepeval.models import DeepEvalBaseLLM
from .config import get_eval_model

def get_faithfulness_metric(
    threshold: float = 0.7, 
    model: Optional[DeepEvalBaseLLM] = None
) -> FaithfulnessMetric:
    """
    RAG Faithfulness: Evaluates whether the generated policy rationale 
    is strictly grounded in the retrieved FTS5 policy clauses.
    """
    eval_model = model or get_eval_model()
    return FaithfulnessMetric(
        threshold=threshold,
        model=eval_model,
        async_mode=False
    )

def get_answer_relevancy_metric(
    threshold: float = 0.7,
    model: Optional[DeepEvalBaseLLM] = None
) -> AnswerRelevancyMetric:
    """
    RAG Answer Relevancy: Evaluates whether the policy coverage explanation 
    directly answers the claimant's loss type and incident context.
    """
    eval_model = model or get_eval_model()
    return AnswerRelevancyMetric(
        threshold=threshold,
        model=eval_model,
        async_mode=False
    )

def get_intake_extraction_metric(
    threshold: float = 0.7,
    model: Optional[DeepEvalBaseLLM] = None
) -> GEval:
    """
    Intake Extraction Fidelity: Evaluates entity extraction accuracy from 
    unstructured claimant First Notice of Loss (FNOL) narratives.
    """
    eval_model = model or get_eval_model()
    return GEval(
        name="FNOL Intake Extraction Fidelity",
        criteria=(
            "Evaluate whether the structured extraction correctly captures loss_type, "
            "damage severity, and impacted vehicle parts from the claimant's raw narrative "
            "without fabricating unmentioned damage."
        ),
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model=eval_model,
        threshold=threshold,
        async_mode=False
    )

def get_denial_compliance_metric(
    threshold: float = 0.7,
    model: Optional[DeepEvalBaseLLM] = None
) -> GEval:
    """
    Regulatory Denial Compliance: Ensures drafted coverage denials remain objective, 
    cite the exact policy exclusion clause, and avoid aggressive or binding statements.
    """
    eval_model = model or get_eval_model()
    return GEval(
        name="Insurance Denial Compliance & Tone",
        criteria=(
            "Evaluate whether the drafted denial rationale is objective and professional, "
            "explicitly cites authoritative policy exclusion sections (such as Section 8.3 "
            "for racing or Section 2.1 for lapsed policy), and clearly states that it is a "
            "draft referral for human adjuster review."
        ),
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model=eval_model,
        threshold=threshold,
        async_mode=False
    )

def get_settlement_transparency_metric(
    threshold: float = 0.7,
    model: Optional[DeepEvalBaseLLM] = None
) -> GEval:
    """
    Settlement Payout Transparency: Evaluates whether the settlement brief clearly 
    articulates the deterministic arithmetic: approved - deductible - depreciation.
    """
    eval_model = model or get_eval_model()
    return GEval(
        name="Settlement Payout Mathematical Transparency",
        criteria=(
            "Evaluate whether the settlement explanation clearly details the initial approved "
            "repair cost, the deductible deduction, depreciation adjustments, and the final net "
            "payout in a transparent manner for the policyholder."
        ),
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        model=eval_model,
        threshold=threshold,
        async_mode=False
    )
