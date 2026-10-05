"""
All settings for the eval in one place: paths, run limits, the models under test,
and named question subsets. Every other script imports from here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPEN_ROUTER_API_KEY")

# ---------- paths ----------
DATA_DIR = Path("data/ipl")
DB_PATH = "ipl_2026_relational.db"          # built by generate_db_relational.py
SCHEMA_PATH = "schema.sql"                  # built by generate_schema.py
ER_DIAGRAM_PATH = "schema_er.md"            # built by generate_schema.py
RESULTS_DIR = Path("results")
RESULTS_PATH = RESULTS_DIR / "model_results.csv"
REPORT_PATH = RESULTS_DIR / "eval_report.xlsx"

# ---------- run limits ----------
SQL_TIMEOUT_S = 20       # abort a generated query that runs longer than this
MAX_RESULT_ROWS = 30     # rows of each result stored in the CSV (full row count is stored too)
DEFAULT_WORKERS = 25     # questions sent in parallel for ONE model (models still run one by one)

# ---------- OpenRouter ----------
OPENROUTER_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 16000       # room for reasoning models that think before answering (4000 truncated 8% of Kimi answers)
REQUEST_TIMEOUT_S = 600  # wall-clock cap per API call (enforced in openrouter.post_with_deadline)
MAX_RETRIES = 2          # on rate limits (429), server errors (5xx) and provider failures mid-answer

# ---------- what to test ----------
# Named question subsets, for cheaper runs that still separate models.
QUESTION_SETS = {
    # the 10 questions Kimi K3 missed in its first full run (8 hard + 2 brutal)
    # + the 10 brutal questions with the most stacked traps
    "hardest20": [63, 64, 65, 69, 70, 74, 82, 85, 89, 90,
                  86, 87, 88, 91, 92, 95, 96, 98, 99, 100],
}

SELECTED_MODEL = "openai/gpt-6-luna"   # chosen for price - see README "Model selection"

MODELS = [   # (display name, OpenRouter slug)
    ("GPT-5.6 Terra",         "openai/gpt-5.6-terra-pro"),
    ("Kimi K3",               "moonshotai/kimi-k3"),
    ("Grok 4.5",              "x-ai/grok-4.5"),
    ("Claude Sonnet 5",       "anthropic/claude-sonnet-5"),
    ("MiniMax M3",            "minimax/minimax-m3"),
    # --- added from the cost-calculator list (Claude Haiku 3.5 is retired, not on OpenRouter) ---
    ("GPT-OSS-120B",          "openai/gpt-oss-120b"),
    ("GPT-6 Luna",            "openai/gpt-6-luna"),
    ("DeepSeek V4.1 Flash",   "deepseek/deepseek-v4.1-flash"),
    ("Gemini 3.1 Flash-Lite", "google/gemini-3.1-flash-lite"),
    ("Llama 4 Maverick",      "meta-llama/llama-4-maverick"),
    ("Gemini 3.8 Flash",      "google/gemini-3.8-flash"),
    ("Kimi K2.5",             "moonshotai/kimi-k2.5"),
    ("Grok Build 0.1",        "x-ai/grok-build-0.1"),
    ("GLM-4.7",               "z-ai/glm-4.7"),
    ("Qwen3.5 397B A17B",     "qwen/qwen3.5-397b-a17b"),
    ("DeepSeek V4 Pro",       "deepseek/deepseek-v4-pro"),
    ("Grok 4.3",              "x-ai/grok-4.3"),
    ("Claude Haiku 4.5",      "anthropic/claude-haiku-4.5"),
    ("Gemini 2.5 Pro",        "google/gemini-2.5-pro"),
    ("Llama 3.3 70B",         "meta-llama/llama-3.3-70b-instruct"),
]
