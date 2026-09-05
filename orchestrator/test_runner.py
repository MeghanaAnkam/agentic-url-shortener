import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_api_tests():
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "app/tests/test_api.py",
                "-q",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "output": "Tests exceeded the 60-second limit.",
        }
    except OSError as error:
        return {"status": "failed", "output": str(error)}

    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "output": result.stdout + result.stderr,
    }


if __name__ == "__main__":
    report = run_api_tests()
    print(report["output"])
    print("Runner result:", report["status"])
    sys.exit(0 if report["status"] == "passed" else 1)