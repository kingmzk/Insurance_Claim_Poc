import pytest
from deepeval import assert_test
from backend.evals.config import get_eval_model
from backend.evals.metrics import (
    get_faithfulness_metric,
    get_answer_relevancy_metric,
    get_intake_extraction_metric,
    get_denial_compliance_metric,
    get_settlement_transparency_metric
)
from backend.evals.dataset import (
    CASE_COLLISION_COVERAGE,
    CASE_RACING_EXCLUSION,
    CASE_FNOL_EXTRACTION,
    CASE_LAPSED_POLICY,
    CASE_SETTLEMENT_TRANSPARENCY
)

@pytest.fixture(scope="module")
def eval_model():
    return get_eval_model()

@pytest.mark.deepeval
def test_policy_rag_faithfulness(eval_model):
    """Evaluates whether the policy coverage explanation is strictly grounded in retrieved clauses."""
    metric = get_faithfulness_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_COLLISION_COVERAGE, [metric])

@pytest.mark.deepeval
def test_policy_answer_relevancy(eval_model):
    """Evaluates whether the coverage explanation directly and concisely answers the claim inquiry."""
    metric = get_answer_relevancy_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_COLLISION_COVERAGE, [metric])

@pytest.mark.deepeval
def test_racing_exclusion_denial_compliance(eval_model):
    """Evaluates whether track day / racing denials maintain objective tone and cite Section 8.3."""
    metric = get_denial_compliance_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_RACING_EXCLUSION, [metric])

@pytest.mark.deepeval
def test_fnol_intake_extraction_fidelity(eval_model):
    """Evaluates entity extraction accuracy from messy claimant First Notice of Loss narrative."""
    metric = get_intake_extraction_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_FNOL_EXTRACTION, [metric])

@pytest.mark.deepeval
def test_lapsed_policy_denial_notice(eval_model):
    """Evaluates draft denial notice for lapsed policy adherence to Section 2.1."""
    metric = get_denial_compliance_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_LAPSED_POLICY, [metric])

@pytest.mark.deepeval
def test_settlement_transparency(eval_model):
    """Evaluates transparency of deterministic payout math: approved - deductible - depreciation."""
    metric = get_settlement_transparency_metric(threshold=0.7, model=eval_model)
    assert_test(CASE_SETTLEMENT_TRANSPARENCY, [metric])
