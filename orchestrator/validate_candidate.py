import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
from datetime import datetime, timezone


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the candidate_main.py path.")

    candidate = Path(sys.argv[1]).resolve()
    project = Path(__file__).resolve().parents[1]

    if not candidate.is_file():
        raise SystemExit("Candidate file not found.")

    with TemporaryDirectory() as directory:
        workspace = Path(directory)
        app_folder = workspace / "app"
        tests_folder = app_folder / "tests"
        tests_folder.mkdir(parents=True)

        (app_folder / "__init__.py").touch()
        shutil.copy2(candidate, app_folder / "main.py")
        shutil.copy2(
            project / "app/tests/test_api.py",
            tests_folder / "test_api.py",
        )
        shutil.copy2(
            candidate.parent / "test_daily_counts.py",
            tests_folder / "test_daily_counts.py",
        )
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("GEMINI_API_KEY", None)
        environment.pop("GOOGLE_API_KEY", None)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "app/tests",
                    "-q",
                ],
                cwd=workspace,
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise SystemExit("Candidate tests exceeded 60 seconds.")

        def file_hash(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        report = {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "candidate_sha256": file_hash(app_folder / "main.py"),
            "api_tests_sha256": file_hash(tests_folder / "test_api.py"),
            "daily_tests_sha256": file_hash(
                tests_folder / "test_daily_counts.py"
            ),
            "output": result.stdout + result.stderr,
        }

        report_path = candidate.parent / "validation.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        print("Validation report saved:", report_path)

        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()