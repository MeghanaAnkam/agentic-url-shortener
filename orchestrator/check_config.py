import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

key = os.getenv("GEMINI_API_KEY", "").strip()

if not key:
    raise SystemExit("Missing GEMINI_API_KEY. Check your .env file.")

print("Gemini API key loaded successfully.")