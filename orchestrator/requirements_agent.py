import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


def analyze_requirement(requirement: str) -> str:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")

    if not key or not model:
        raise ValueError("Missing Gemini configuration in .env.")

    prompt = f"""
You are a requirements analyst. Do not write code.

Current system:
- FastAPI and SQLite.
- Creates short links and redirects visitors.
- Stores total clicks per link and link creation time.
- Provides an analytics API.
- No dashboard, login, or individual click records.

Analyze this request:
<request>
{requirement}
</request>

Rules:
- Current system facts are context, not requested changes.
- Only explicitly requested changes are confirmed.
- "Improve analytics" does not confirm event tracking,
  database changes, dashboards, or new metrics.
- Ask what outcome the user wants before proposing architecture.
- Do not assume migrations or personal-data collection.
- Do not invent acceptance criteria or numerical targets.

Return:
1. Status: NEEDS_CLARIFICATION or READY_FOR_REVIEW
2. Explicitly requested outcome
3. Up to three clarification questions, if needed
4. Optional suggestions, clearly marked as unapproved

For vague requests, use NEEDS_CLARIFICATION.
"""

    with genai.Client(
        api_key=key,
        http_options={"timeout": 60000},
    ) as client:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

    if not response.text:
        raise ValueError("The model returned no text.")

    return response.text


if __name__ == "__main__":
    request = input("Enter your requirement: ").strip()

    if not request:
        raise SystemExit("Please enter a requirement.")

    try:
        print(analyze_requirement(request))
    except Exception as error:
        print("Analysis failed:", type(error).__name__)
        print("Status code:", getattr(error, "code", "unavailable"))