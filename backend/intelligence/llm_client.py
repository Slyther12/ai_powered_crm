"""
Groq LLM client with token tracking, latency measurement, and retry logic.
Supports risk analysis and natural language query answering.
Uses the Groq API (OpenAI-compatible) with llama-3.3-70b-versatile.
"""
import json
from typing import Optional

from backend.config import GROQ_API_KEY, GROQ_MODEL
from backend.observability.logger import get_logger
from backend.observability.metrics import record_metric, measure_latency

logger = get_logger("llm")

_client = None


def _get_client():
    """Lazy-init the Groq client."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set — LLM features will use fallback mode")
            return None
        try:
            from groq import Groq
            _client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialise Groq client: {e}")
            return None
    return _client


def generate(prompt: str, system_instruction: str = None,
             temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
    """Generate a response from Groq with metrics tracking."""
    client = _get_client()
    if client is None:
        return _fallback_response(prompt)

    with measure_latency("llm", "generate"):
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track token usage
            tokens_prompt = 0
            tokens_completion = 0
            if hasattr(response, 'usage') and response.usage:
                tokens_prompt = getattr(response.usage, 'prompt_tokens', 0) or 0
                tokens_completion = getattr(response.usage, 'completion_tokens', 0) or 0

            record_metric(
                stage="llm",
                operation="generate",
                tokens_used=tokens_prompt + tokens_completion,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            record_metric(stage="llm", operation="generate", error=str(e))
            return _fallback_response(prompt)


def generate_risk_summary(quotation_data: dict) -> str:
    """Generate a plain-language risk summary for a quotation."""
    system = """You are a procurement risk analyst for a manufacturing company.
Analyze the quotation data and identify risks, anomalies, and concerns.
Be specific — cite exact field values and data points.
Format your response as a concise risk summary (3-5 bullet points max).
If no significant risks are found, say so briefly."""

    prompt = f"""Analyze this supplier quotation for risks:

Supplier: {quotation_data.get('supplier_name', 'Unknown')}
Document: {quotation_data.get('doc_no', 'N/A')}
Date: {quotation_data.get('doc_date', 'N/A')}
Currency: {quotation_data.get('currency', 'N/A')}
Total (excl tax): {quotation_data.get('total_excl_tax', 0):,.2f}
Payment Terms: {quotation_data.get('payment_terms', 'N/A')}
Validity: {quotation_data.get('validity_days', 'N/A')} days
Anomaly Flags: {quotation_data.get('anomalies', [])}

Line Items:
{json.dumps(quotation_data.get('line_items', []), indent=2)}

Risk Flags Already Detected:
{json.dumps(quotation_data.get('risk_flags', []), indent=2)}

Provide a plain-language risk summary citing specific values."""

    return generate(prompt, system_instruction=system)


def generate_search_answer(query: str, context_docs: list[dict]) -> str:
    """Generate an answer to a natural language query using retrieved context."""
    system = """You are a procurement intelligence assistant for a manufacturing CRM.
Answer the user's question using ONLY the provided quotation data.
Always cite specific document numbers, suppliers, and values.
If the data doesn't contain enough information to answer, say so.
Format your answer clearly with specific numbers and comparisons."""

    context_text = ""
    for i, doc in enumerate(context_docs, 1):
        context_text += f"\n--- Document {i} ---\n"
        context_text += f"Doc: {doc.get('doc_no', 'N/A')} | "
        context_text += f"Supplier: {doc.get('supplier_name', 'N/A')} | "
        context_text += f"Project: {doc.get('project_name', 'N/A')} | "
        context_text += f"Date: {doc.get('doc_date', 'N/A')} | "
        context_text += f"Total: {doc.get('currency', '')} {doc.get('total_excl_tax', 0):,.2f}\n"
        if doc.get('line_items'):
            for li in doc['line_items']:
                context_text += f"  • {li.get('description', 'N/A')}: "
                context_text += f"{li.get('quantity', 0)} {li.get('unit', '')} @ "
                context_text += f"{li.get('unit_price', 0):,.2f}\n"

    prompt = f"""User Question: {query}

Retrieved Quotation Data:
{context_text}

Answer the question based on the above data. Cite document numbers and supplier names."""

    return generate(prompt, system_instruction=system, temperature=0.2)


def _fallback_response(prompt: str) -> str:
    """Fallback when Groq is unavailable — returns a helpful placeholder."""
    if "risk" in prompt.lower():
        return ("⚠️ LLM unavailable — Risk summary could not be generated. "
                "Review the rule-based risk flags for this quotation. "
                "Set GROQ_API_KEY environment variable to enable AI-powered analysis.")
    return ("⚠️ LLM unavailable — Set GROQ_API_KEY environment variable "
            "to enable AI-powered responses.")


def extract_quotation_data(text: str) -> dict:
    """Extract structured quotation data from raw text using the LLM."""
    system = """You are a data extraction bot. Your job is to extract data from quotation text and output valid JSON.
Do not output any markdown formatting, only raw JSON.
The JSON must follow this exact schema:
{
  "supplier_name": str,
  "doc_no": str,
  "doc_date": "YYYY-MM-DD" or null,
  "project_name": str or null,
  "currency": str,
  "total_excl_tax": float,
  "total_incl_tax": float or null,
  "payment_terms": str or null,
  "delivery_days": int or null,
  "validity_days": int or null,
  "freight_terms": str or null,
  "warranty": str or null,
  "line_items": [
    {
      "description": str,
      "unit": str,
      "quantity": float,
      "unit_price": float,
      "amount": float
    }
  ]
}
"""
    prompt = f"Extract the quotation data from the following text into the specified JSON schema:\n\n{text[:12000]}"
    
    response = generate(prompt, system_instruction=system, temperature=0.1)
    
    if not response or response.startswith("⚠️ LLM unavailable"):
        return {}
        
    try:
        # Clean up the response in case the LLM returned markdown
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM extraction JSON: {e}")
        return {}