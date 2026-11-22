"""
Configuration settings for Multi-Agent Research Intelligence Platform.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys & Providers ─────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Groq Configuration (Ultra-fast inference ~500 tok/s)
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_FALLBACK_MODELS = [
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]
GROQ_API_KEY_VALID = bool(GROQ_API_KEY and len(GROQ_API_KEY) > 10)

# Gemini Configuration
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-4-hydrogen"]
API_KEY_VALID = bool(GOOGLE_API_KEY and len(GOOGLE_API_KEY) > 10)

# Default active provider
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "groq" if GROQ_API_KEY_VALID else "gemini")

# ─── Application Metadata ─────────────────────────────────────────────────────
APP_NAME = "Multi-Agent Research Intelligence Platform"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Agentic AI Research Lab"

# ─── LLM Parameters ───────────────────────────────────────────────────────────
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# ─── Research Configuration ───────────────────────────────────────────────────
MAX_REVIEW_ITERATIONS = int(os.getenv("MAX_REVIEW_ITERATIONS", "3"))
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "75"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "6"))

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "research_history.db")

# ─── Output Directories ───────────────────────────────────────────────────────
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
