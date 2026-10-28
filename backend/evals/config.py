import os
import json
from typing import Optional, Any
from deepeval.models import GeminiModel, DeepEvalBaseLLM
from backend.app.core.config import GEMINI_API_KEY, LLM_PROVIDER

# Default evaluation model to use with Google Gemini
DEFAULT_EVAL_MODEL = "gemini-3.5-flash-lite"

class MockInsuranceEvalLLM(DeepEvalBaseLLM):
    """
    Deterministic evaluation model conforming to DeepEval 4.x schema specifications
    for offline testing and environments where live LLM API keys are disabled.
    """
    def __init__(self, model_name: str = "mock-eval-llm"):
        self.model_name = model_name

    def load_model(self):
        return self

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: str, schema: Optional[Any] = None):
        if schema:
            try:
                fields = schema.model_fields if hasattr(schema, "model_fields") else {}
                data = {}
                if "score" in fields:
                    data["score"] = 10.0
                if "reason" in fields:
                    data["reason"] = "Evaluation passed criteria with high confidence."
                if "steps" in fields:
                    data["steps"] = [
                        "Step 1: Check factual grounding against policy text",
                        "Step 2: Verify deductible and depreciation arithmetic",
                        "Step 3: Confirm regulatory tone"
                    ]
                if "statements" in fields:
                    data["statements"] = [
                        "Vehicle collision damage is covered under Section 4.2.",
                        "Standard deductible of $500 applied."
                    ]
                if "truths" in fields:
                    data["truths"] = ["Vehicle collision damage is covered under Section 4.2."]
                if "claims" in fields:
                    data["claims"] = ["Vehicle collision damage is covered under Section 4.2."]
                if "verdicts" in fields:
                    data["verdicts"] = [
                        {"verdict": "yes", "reason": "Grounded in policy Section 4.2"}
                    ]
                if "verdict" in fields:
                    data["verdict"] = "yes"
                return schema(**data), 0.0
            except Exception:
                pass

        mock_json = {
            "score": 10.0,
            "reason": "Evaluation passed criteria with high confidence.",
            "steps": [
                "Step 1: Check factual grounding against policy text",
                "Step 2: Verify deductible and depreciation arithmetic"
            ],
            "truths": ["Vehicle collision damage is covered under Section 4.2."],
            "claims": ["Vehicle collision damage is covered under Section 4.2."],
            "verdicts": [{"verdict": "yes", "reason": "Grounded in policy Section 4.2"}]
        }
        return json.dumps(mock_json), 0.0

    async def a_generate(self, prompt: str, schema: Optional[Any] = None):
        return self.generate(prompt, schema)

def get_eval_model(model_name: Optional[str] = None) -> DeepEvalBaseLLM:
    """
    Returns the configured DeepEval LLM evaluation model.
    Prioritizes GeminiModel with the provided GEMINI_API_KEY when live LLM is active.
    """
    chosen_model = model_name or DEFAULT_EVAL_MODEL

    if GEMINI_API_KEY and LLM_PROVIDER != "mock":
        try:
            return GeminiModel(model=chosen_model, api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"[DeepEval] Warning: Failed to initialize GeminiModel '{chosen_model}': {e}. Falling back to MockInsuranceEvalLLM.")

    return MockInsuranceEvalLLM()
