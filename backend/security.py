"""
Centralized security utilities: environment validation, sanitization, and safe filenames.
"""

import os
import re
import sys

REQUIRED_ENV_VARS = ["GROQ_API_KEY", "APP_API_KEY"]

INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (the )?(system|above) prompt",
    r"you are now",
    r"act as (an? )?(admin|root|system)",
    r"reveal (your|the) (system prompt|instructions|api key)",
]


def validate_environment() -> None:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        print(f"FATAL: Missing required environment variables: {missing}")
        sys.exit(1)

    env = os.getenv("ENVIRONMENT", "development")
    debug = os.getenv("DEBUG_MODE", "false").lower() == "true"
    if env == "production" and debug:
        print("FATAL: DEBUG_MODE must be false in production.")
        sys.exit(1)


def sanitize_question(text: str, max_len: int = 1000) -> str:
    cleaned = (text or "").strip()[:max_len]
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValueError("Question contains disallowed instruction patterns.")
    return cleaned


def sanitize_pdf_text(text: str) -> str:
    if text is None:
        return ""
    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    return cleaned


def safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "document.pdf")
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:200]
