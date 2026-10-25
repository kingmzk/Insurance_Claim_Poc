import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env in project root or current dir
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

# Load from root first, fallback to BASE_DIR
if (ROOT_DIR / ".env").exists():
    load_dotenv(ROOT_DIR / ".env")
elif (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env")
else:
    load_dotenv()

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini" if GEMINI_API_KEY else "mock")

_raw_db_path = os.getenv("DATABASE_PATH", str(DATA_DIR / "claims.db"))
if not os.path.isabs(_raw_db_path):
    DATABASE_PATH = str((ROOT_DIR / _raw_db_path).resolve())
else:
    DATABASE_PATH = str(Path(_raw_db_path).resolve())
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
DEFAULT_AUTHORITY_LIMIT = float(os.getenv("DEFAULT_AUTHORITY_LIMIT", "5000.0"))
FRAUD_THRESHOLD_ESCALATION = int(os.getenv("FRAUD_THRESHOLD_ESCALATION", "75"))
FRAUD_THRESHOLD_LOW = int(os.getenv("FRAUD_THRESHOLD_LOW", "25"))
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Langfuse Observability
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", LANGFUSE_BASE_URL)

# Propagate to os.environ for OpenTelemetry & Langfuse internal discovery
if LANGFUSE_SECRET_KEY:
    os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
if LANGFUSE_PUBLIC_KEY:
    os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
if LANGFUSE_BASE_URL:
    os.environ["LANGFUSE_BASE_URL"] = LANGFUSE_BASE_URL
if LANGFUSE_HOST:
    os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST
# OpenTelemetry Observability Configuration
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "insurance-claims-orchestrator")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_TRACES_CONSOLE = os.getenv("OTEL_TRACES_CONSOLE", "false").lower() in ("true", "1", "yes")
