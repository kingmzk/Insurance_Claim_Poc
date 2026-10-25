import os
from typing import Optional
from deepeval.models import GeminiModel, DeepEvalBaseLLM
from backend.app.core.config import GEMINI_API_KEY, LLM_PROVIDER

# Default evaluation model to use with Google Gemini
DEFAULT_EVAL_MODEL = "gemini-3.5-flash-lite"

class MockInsuranceEvalLLM(DeepEvalBaseLLM):
    """Deterministic fallback model for offline testing or environments without API keys."""
    def __init__(self, model_name: str = "mock-eval-llm"):
        self.model_name = model_name

    def load_model(self):
        return self

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: str, schema=None):
        return ("Evaluation passed with mock deterministic score.", 0.0)

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt, schema)

def get_eval_model(model_name: Optional[str] = None) -> DeepEvalBaseLLM:
    """
    Returns the configured DeepEval LLM evaluation model.
    Prioritizes GeminiModel with the provided GEMINI_API_KEY.
    """
    chosen_model = model_name or DEFAULT_EVAL_MODEL

    if GEMINI_API_KEY and LLM_PROVIDER != "mock":
        try:
            return GeminiModel(model=chosen_model, api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"[DeepEval] Warning: Failed to initialize GeminiModel '{chosen_model}': {e}. Falling back to MockInsuranceEvalLLM.")

    return MockInsuranceEvalLLM()
