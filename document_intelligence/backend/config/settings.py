import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DI_SECRET_KEY", "poc-only-not-a-production-secret")
DEBUG = os.environ.get("DI_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "document_catalog",
    "document_extraction",
    "document_verification",
    "document_scrutiny",
    "mock_issuer_services",
    "api",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {}
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

UPLOADS_ROOT = Path(os.environ.get("DI_UPLOADS_ROOT", BASE_DIR / "uploads"))
MAX_UPLOAD_BYTES = int(os.environ.get("DI_MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
ALLOWED_UPLOAD_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")

EXTRACTION_MODE = os.environ.get("EXTRACTION_MODE", "gemini")
# When gemini mode is on, put the mock reader under it as a safety net so a demo
# does not hard-fail on a dropped network or a spent key. Off by default so tests
# and non-demo runs keep the plain gemini behaviour (ADR-013).
EXTRACTION_FALLBACK = os.environ.get("EXTRACTION_FALLBACK", "") not in ("", "0", "false")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
EXTRACTION_MODEL = os.environ.get("DI_MODEL", "gemini-3.1-pro-preview")
INVENTORY_MODEL = os.environ.get("DI_INVENTORY_MODEL", "gemini-3.1-pro-preview")
MAX_DOCUMENT_PAGES = int(os.environ.get("DI_MAX_PAGES", "150"))

# The mock issuers are served by this same Django app, so the port has to match
# whatever this process is listening on. Hardcoding 8000 made every issuer check
# come back "unavailable" on any other port, which reads like a working
# unavailable-path demo rather than a misconfiguration.
DI_SERVER_PORT = os.environ.get("DI_SERVER_PORT", "8000")
MOCK_ISSUER_BASE_URL = os.environ.get(
    "DI_MOCK_ISSUER_BASE_URL", f"http://127.0.0.1:{DI_SERVER_PORT}/mock"
)

# One URL per department, each overridable on its own so a single issuer can be
# pointed at something real without moving the rest.
ITD_PAN_VERIFY_URL = os.environ.get(
    "DI_ITD_PAN_VERIFY_URL", f"{MOCK_ISSUER_BASE_URL}/itd/pan/verify"
)
ITD_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("DI_ITD_TIMEOUT_SECONDS", "3.0"))

UIDAI_VERIFY_URL = os.environ.get(
    "DI_UIDAI_VERIFY_URL", f"{MOCK_ISSUER_BASE_URL}/uidai/aadhaar/verify"
)
UIDAI_REQUEST_TIMEOUT_SECONDS = float(
    os.environ.get("DI_UIDAI_TIMEOUT_SECONDS", "3.0")
)

SARATHI_VERIFY_URL = os.environ.get(
    "DI_SARATHI_VERIFY_URL", f"{MOCK_ISSUER_BASE_URL}/sarathi/dl"
)
SARATHI_REQUEST_TIMEOUT_SECONDS = float(
    os.environ.get("DI_SARATHI_TIMEOUT_SECONDS", "3.0")
)

IGRS_VERIFY_URL = os.environ.get(
    "DI_IGRS_VERIFY_URL", f"{MOCK_ISSUER_BASE_URL}/igrs/deeds"
)
IGRS_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("DI_IGRS_TIMEOUT_SECONDS", "3.0"))

# The date scrutiny is carried out on, injected rather than taken from the clock so
# the seeded expiry dates keep meaning what they were written to mean and a check
# run is reproducible. Matches the prototype's own DI.TODAY.
SCRUTINY_TODAY = os.environ.get("DI_SCRUTINY_TODAY", "2026-09-07")

MOCK_ISSUER_LATENCY_SECONDS = float(os.environ.get("DI_MOCK_ISSUER_LATENCY_SECONDS", "0.9"))
MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = float(
    os.environ.get("DI_MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS", "1.0")
)
MOCK_ISSUER_API_KEY = os.environ.get("DI_MOCK_ISSUER_API_KEY", "poc-itd-demo-key")
