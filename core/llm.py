"""
LLM factory with multi-provider support:
- Groq (Ultra-fast inference, Llama 3.3 70B & 3.1 8B, ~500 tok/s)
- Google Gemini (gemini-3.5-flash-lite, multi-model fallback)
Includes exponential backoff and automatic cross-provider fallback.
"""
import time
import logging
from typing import Optional, List, Any

from config.settings import (
    GOOGLE_API_KEY, GROQ_API_KEY, GROQ_MODEL, GROQ_FALLBACK_MODELS,
    MODEL_NAME, FALLBACK_MODELS, DEFAULT_PROVIDER,
    LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_TIMEOUT, LLM_MAX_RETRIES,
    GROQ_API_KEY_VALID, API_KEY_VALID
)

logger = logging.getLogger(__name__)

ACTIVE_PROVIDER = DEFAULT_PROVIDER


def set_active_provider(provider: str):
    """Set active LLM provider ('groq' or 'gemini')."""
    global ACTIVE_PROVIDER
    if provider in ("groq", "gemini"):
        ACTIVE_PROVIDER = provider


def get_active_provider() -> str:
    """Return currently active LLM provider."""
    return ACTIVE_PROVIDER


# Errors that warrant a retry
RETRYABLE_ERRORS = (
    "504", "DEADLINE_EXCEEDED",
    "503", "SERVICE_UNAVAILABLE",
    "429", "RATE_LIMIT", "RESOURCE_EXHAUSTED",
    "500", "INTERNAL",
    "UNAVAILABLE",
    "rate_limit_exceeded",
)


def _extract_text_content(content: Any) -> str:
    """Normalize response content to string across different SDK versions."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(str(item.text))
        return "".join(parts)
    elif hasattr(content, "text"):
        return str(content.text)
    return str(content)


# ─── Groq Engine (Ultra-Fast) ─────────────────────────────────────────────────
def call_groq_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = LLM_TEMPERATURE,
    max_retries: int = LLM_MAX_RETRIES,
) -> str:
    """Call Groq API with Llama 3.3 / Llama 3.1 models."""
    from groq import Groq

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured.")

    client = Groq(api_key=GROQ_API_KEY, timeout=LLM_TIMEOUT)
    candidate_models = [GROQ_MODEL] + [m for m in GROQ_FALLBACK_MODELS if m != GROQ_MODEL]

    last_error: Optional[Exception] = None

    for model in candidate_models:
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=min(LLM_MAX_TOKENS, 4096),
                )
                text = response.choices[0].message.content or ""
                if text.strip():
                    return text
            except Exception as e:
                err_str = str(e)
                last_error = e

                is_retryable = any(code in err_str.lower() for code in RETRYABLE_ERRORS)
                if not is_retryable:
                    logger.warning(f"Groq error on {model}: {e}. Trying fallback.")
                    break

                wait = 1.0 * (2 ** attempt)
                logger.warning(f"Groq retry {attempt+1}/{max_retries} on {model}: {e}. Waiting {wait}s…")
                time.sleep(wait)

    raise RuntimeError(f"Groq call failed on all models: {last_error}")


# ─── Google Gemini Engine ─────────────────────────────────────────────────────
def call_gemini_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = LLM_TEMPERATURE,
    max_retries: int = LLM_MAX_RETRIES,
    base_delay: float = 2.0,
) -> str:
    """Call Google Gemini through LangChain with model fallback."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured.")

    candidate_models = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    last_error: Optional[Exception] = None

    for model in candidate_models:
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
            max_output_tokens=LLM_MAX_TOKENS,
            timeout=LLM_TIMEOUT,
            max_retries=0,
            convert_system_message_to_human=True,
        )

        for attempt in range(max_retries):
            try:
                response = llm.invoke(messages)
                text = _extract_text_content(response.content)
                if text.strip():
                    return text
            except Exception as e:
                err_str = str(e)
                last_error = e

                if "404" in err_str or "NOT_FOUND" in err_str:
                    logger.warning(f"Gemini {model} returned 404. Falling back.")
                    break

                is_retryable = any(code in err_str for code in RETRYABLE_ERRORS)
                if not is_retryable:
                    logger.error(f"Gemini error on {model}: {e}")
                    break

                wait = base_delay * (2 ** attempt)
                logger.warning(f"Gemini call on {model} retry {attempt+1}/{max_retries}. Waiting {wait:.1f}s…")
                time.sleep(wait)

    raise RuntimeError(f"Gemini call failed on all candidate models: {last_error}")


# ─── Unified Caller with Automatic Cross-Provider Fallback ───────────────────
def call_llm_with_retry(
    system_prompt: str,
    user_prompt: str,
    temperature: float = LLM_TEMPERATURE,
    max_retries: int = LLM_MAX_RETRIES,
    base_delay: float = 2.0,
) -> str:
    """
    Call the LLM using the active provider.
    Automatically falls back to secondary provider if primary fails.
    """
    primary = get_active_provider()

    # Route 1: Try Groq if active or configured
    if primary == "groq" and GROQ_API_KEY_VALID:
        try:
            return call_groq_llm(system_prompt, user_prompt, temperature, max_retries)
        except Exception as e:
            logger.warning(f"Groq failed ({e}). Falling back to Gemini…")
            if API_KEY_VALID:
                return call_gemini_llm(system_prompt, user_prompt, temperature, max_retries, base_delay)
            raise

    # Route 2: Try Gemini
    if API_KEY_VALID:
        try:
            return call_gemini_llm(system_prompt, user_prompt, temperature, max_retries, base_delay)
        except Exception as e:
            logger.warning(f"Gemini failed ({e}). Falling back to Groq…")
            if GROQ_API_KEY_VALID:
                return call_groq_llm(system_prompt, user_prompt, temperature, max_retries)
            raise

    # Route 3: If Groq key exists, try Groq
    if GROQ_API_KEY_VALID:
        return call_groq_llm(system_prompt, user_prompt, temperature, max_retries)

    raise RuntimeError("No valid API key found. Please configure GROQ_API_KEY or GOOGLE_API_KEY in .env.")


def test_llm_connection(provider: Optional[str] = None) -> dict:
    """Test LLM connectivity for active or specified provider."""
    target_provider = provider or get_active_provider()
    try:
        if target_provider == "groq":
            if not GROQ_API_KEY_VALID:
                return {"status": "error", "message": "GROQ_API_KEY not set in .env", "provider": "groq"}
            result = call_groq_llm(
                system_prompt="You are a test assistant.",
                user_prompt="Reply with exactly: CONNECTION_OK",
                max_retries=1,
            )
        else:
            if not API_KEY_VALID:
                return {"status": "error", "message": "GOOGLE_API_KEY not set in .env", "provider": "gemini"}
            result = call_gemini_llm(
                system_prompt="You are a test assistant.",
                user_prompt="Reply with exactly: CONNECTION_OK",
                max_retries=1,
            )

        return {
            "status": "ok",
            "message": f"{target_provider.title()} connected successfully",
            "provider": target_provider,
            "response": result[:100],
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "provider": target_provider, "response": ""}
