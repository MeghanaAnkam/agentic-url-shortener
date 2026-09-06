import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

if not key or not model:
    raise SystemExit("Add GEMINI_API_KEY and GEMINI_MODEL to .env.")

try:
    with genai.Client(
        api_key=key,
        http_options={"timeout": 60000},
    ) as client:
        response = client.models.generate_content(
            model=model,
            contents="Reply with only: Connection successful",
        )

    print(response.text or "No text returned.")
except Exception as error:
    print("Request failed:", type(error).__name__)
    print("Status code:", getattr(error, "code", "unavailable"))