from typing import List, Dict, Any
from deepeval.test_case import LLMTestCase

# 1. Collision Coverage Faithfulness & Relevancy Test Case
CASE_COLLISION_COVERAGE = LLMTestCase(
    input="Is collision damage to the front bumper covered under Policy POL-AUTO-99201?",
    actual_output=(
        "Coverage confirmed under Section 4.2 (Collision & Comprehensive Coverage). "
        "The damage sustained in the front impact collision is covered up to the policy limit "
        "of $50,000, subject to a $500 standard deductible applied under Section 4.5."
    ),
    retrieval_context=[
        (
            "Section 4.2: Collision and Comprehensive Coverage. The insurer pays for direct and "
            "accidental collision loss to the insured vehicle. Maximum single incident limit is $50,000."
        ),
        (
            "Section 4.5: Deductible Application. Under Section 4.5, a standard deductible of $500 applies to all direct "
            "collision losses and is subtracted from the approved repair cost."
        )
    ],
    expected_output="Coverage confirmed under Section 4.2 with $500 deductible applied under Section 4.5 up to $50,000 limit."
)


# 2. Racing / Track Day Exclusion Compliance Test Case
CASE_RACING_EXCLUSION = LLMTestCase(
    input=(
        "Claimant Marcus Vance crashed his 2024 Audi RS6 Avant while participating in an amateur "
        "weekend speed contest and track day at the local motor raceway."
    ),
    actual_output=(
        "Coverage exception: Damage relates to excluded activities under Section 8.3 (General Exclusions). "
        "Section 8.3 explicitly excludes losses arising from speed contests, racing, and track day events. "
        "Draft denial generated and referred to human adjuster for formal confirmation."
    ),
    retrieval_context=[
        (
            "Section 8.3: General Exclusions. Coverage does not apply to any loss or damage arising from "
            "racing, speed contests, track day competitions, or stunting on closed or open courses."
        ),
        (
            "Section 11.1: Human Adjuster Governance. Automated rejection of any claim is prohibited. "
            "Claims involving policy exclusions shall be routed to the Human Adjuster Review Queue with drafted rationale."
        )
    ],
    expected_output="Denial drafted under Section 8.3 due to speed contest exclusion, referred to human review."
)

# 3. FNOL Intake Extraction Fidelity Test Case
CASE_FNOL_EXTRACTION = LLMTestCase(
    input=(
        "I was backing out of my garage this morning when I accidentally scraped the entire right rear "
        "quarter panel against the concrete pillar. The taillight is shattered and the rear bumper is pushed in. "
        "The car is still drivable but the repair shop quoted $2,400."
    ),
    actual_output=(
        '{"loss_type": "collision", "primary_impact_area": "rear right quarter panel and bumper", '
        '"estimated_damage_severity": "moderate", "summary": "Claimant scraped rear right quarter panel '
        'and taillight against garage pillar while reversing; drivable with $2,400 repair quote."}'
    ),
    expected_output="Collision loss type, rear right impact area, moderate severity without fabricated damage."
)

# 4. Lapsed Policy Coverage Denial Test Case
CASE_LAPSED_POLICY = LLMTestCase(
    input=(
        "Claimant Sarah Jenkins filed a claim for parking lot collision damage under Policy POL-AUTO-77002 "
        "which expired on 2025-12-31 without premium renewal."
    ),
    actual_output=(
        "Coverage exception: Policy POL-AUTO-77002 lapsed on 2025-12-31 prior to the date of loss. "
        "Under Section 2.1 (Policy Period and Inception), coverage ceases immediately upon expiration without payment. "
        "Draft denial notice generated and routed to human review."
    ),
    retrieval_context=[
        (
            "Section 2.1: Policy Period and Inception. Coverage is active only during the policy period "
            "specified on the declarations page. Unrenewed or lapsed policies terminate at 12:01 AM on the stated expiration date."
        ),
        (
            "Section 2.4: Notice of Termination. In the event of a lapsed policy, claims reported after "
            "expiration cannot be authorized for automated payout."
        )
    ],
    expected_output="Draft denial generated citing Section 2.1 for lapsed policy prior to incident."
)

# 5. Settlement Mathematical Transparency Test Case
CASE_SETTLEMENT_TRANSPARENCY = LLMTestCase(
    input=(
        "Claim CLM-99201 approved for $3,500.00 repair cost. Standard deductible is $500.00. "
        "Depreciation adjustment on aftermarket replacement parts is $150.00."
    ),
    actual_output=(
        "Settlement calculation breakdown: Total approved repair cost is $3,500.00. "
        "Applying the policyholder standard deductible of -$500.00 and depreciation adjustment of -$150.00 "
        "yields a net authorized settlement payout of $2,850.00 as per deterministic formula."
    ),
    expected_output="Approved $3,500 - $500 deductible - $150 depreciation = $2,850 net payout."
)

ALL_EVAL_TEST_CASES = [
    {"id": "EVAL-001", "name": "Policy Collision Faithfulness", "case": CASE_COLLISION_COVERAGE, "category": "RAG_FAITHFULNESS"},
    {"id": "EVAL-002", "name": "Policy Answer Relevancy", "case": CASE_COLLISION_COVERAGE, "category": "RAG_RELEVANCY"},
    {"id": "EVAL-003", "name": "Racing Exclusion Compliance", "case": CASE_RACING_EXCLUSION, "category": "DENIAL_COMPLIANCE"},
    {"id": "EVAL-004", "name": "FNOL Intake Entity Extraction", "case": CASE_FNOL_EXTRACTION, "category": "INTAKE_EXTRACTION"},
    {"id": "EVAL-005", "name": "Lapsed Policy Denial Notice", "case": CASE_LAPSED_POLICY, "category": "DENIAL_COMPLIANCE"},
    {"id": "EVAL-006", "name": "Settlement Payout Transparency", "case": CASE_SETTLEMENT_TRANSPARENCY, "category": "SETTLEMENT_MATH"}
]
