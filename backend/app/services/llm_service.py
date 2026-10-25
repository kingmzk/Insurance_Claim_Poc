import json
import httpx
from typing import Dict, Any, List, Optional
from ..core.config import GEMINI_API_KEY, LLM_PROVIDER

try:
    from langfuse import observe, get_client
except ImportError:
    def observe(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    def get_client():
        return None

GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash"
]
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

class LLMService:
    @staticmethod
    @observe(as_type="generation", name="gemini_generate_content")
    def call_gemini(prompt: str, json_mode: bool = False) -> Optional[str]:
        """Calls Google Gemini REST API using httpx with Langfuse generation tracing."""
        if not GEMINI_API_KEY or LLM_PROVIDER == "mock":
            return None


        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}
        body: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        for model_name in GEMINI_MODELS:
            url = GEMINI_BASE_URL.format(model=model_name)
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, headers=headers, params=params, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                text_result = parts[0].get("text", "")
                                try:
                                    lf_client = get_client()
                                    if lf_client:
                                        usage = data.get("usageMetadata", {})
                                        usage_kwargs = {}
                                        if usage:
                                            usage_kwargs["usage_details"] = {
                                                "input": usage.get("promptTokenCount", 0),
                                                "output": usage.get("candidatesTokenCount", 0),
                                                "total": usage.get("totalTokenCount", 0),
                                            }
                                        lf_client.update_current_generation(
                                            model=model_name,
                                            metadata={"finish_reason": candidates[0].get("finishReason", "STOP")},
                                            **usage_kwargs
                                        )
                                except Exception:
                                    pass
                                return text_result

            except Exception:
                continue
        return None

    @classmethod
    def extract_fnol(cls, text: str, fallback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts structured entities from First Notice of Loss narrative."""
        prompt = f"""
You are an insurance claims intake AI. Extract key entities from the following claim narrative into JSON.
Return keys: loss_type, estimated_damage_severity, primary_impact_area, summary.

Narrative:
{text}
"""
        response_text = cls.call_gemini(prompt, json_mode=True)
        if response_text:
            try:
                extracted = json.loads(response_text)
                return {**fallback_data, **extracted, "extraction_method": "GEMINI_2.5_FLASH"}
            except Exception:
                pass

        # Deterministic fallback
        return {
            **fallback_data,
            "extraction_method": "RULE_BASED_FALLBACK"
        }

    @classmethod
    def generate_coverage_rationale(cls, policy_clauses: List[Dict[str, Any]], claim_info: Dict[str, Any]) -> str:
        """Generates evidence-backed coverage rationale citing specific clauses."""
        citations = "\n".join([f"- [{c.get('section_title')}] (Page {c.get('page_number')}): {c.get('chunk_text')}" for c in policy_clauses])
        prompt = f"""
You are a senior insurance claims policy specialist.
Draft a concise coverage determination brief for Claim {claim_info.get('claim_id')}.
Cite the exact policy section titles and explain why the damage is covered or excluded.

Policy Evidence:
{citations}

Claim Details:
Loss Type: {claim_info.get('loss_type')}
Claimed Amount: ${claim_info.get('claimed_amt')}
Incident Summary: {claim_info.get('incident_description', 'Collision incident')}
"""
        result = cls.call_gemini(prompt, json_mode=False)
        if result:
            return result.strip()

        # Deterministic fallback explanation
        if any("Exclusions" in c.get("section_title", "") for c in policy_clauses):
            return f"Coverage exception: Damage relates to excluded activities under Section 8.3 (General Exclusions). Referral to human adjuster recommended."
        return f"Coverage confirmed under Section 4.2 (Collision & Comprehensive Coverage). Standard deductible applied as per Section 4.2."
