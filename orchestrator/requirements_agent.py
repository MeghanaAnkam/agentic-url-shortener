from pathlib import Path

from orchestrator.gemini_client import GeminiResult, generate_with_fallback, load_gemini_config


def analyze_requirement(requirement: str) -> GeminiResult:
    project_root = Path(__file__).resolve().parents[1]
    config = load_gemini_config(project_root)

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

    return generate_with_fallback(config, prompt)


if __name__ == "__main__":
    request = input("Enter your requirement: ").strip()

    if not request:
        raise SystemExit("Please enter a requirement.")

    try:
        result = analyze_requirement(request)
        print(result.text)

        if result.fallback_used:
            print(f"\n(Note: fallback model '{result.model_used}' was used.)")
    except Exception as error:
        print("Analysis failed:", type(error).__name__)
        print("Status code:", getattr(error, "code", "unavailable"))
