import os
import json
import time

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agent.graph import validate_code

THESIS_CODE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "neural-edge-video-compression")
)
SKIP_DIRECTORIES = {
    ".git",
    "venv",
    "__pycache__",
    "node_modules",
    "DCVC",
    "_third_party_amt",
    "tests",
}
MAX_CODE_CHARS = 10_000
MAX_VALIDATION_ATTEMPTS = 2

if not os.path.isdir(THESIS_CODE_PATH):
    raise FileNotFoundError(
        f"Expected thesis repo at {THESIS_CODE_PATH}, but the directory does not exist."
    )


def scan_thesis_codebase() -> list[dict]:
    """
    Run the validator across every Python file in the thesis repo.
    Returns only files where the validator found at least one issue.
    """
    results = []

    for root, dirs, files in os.walk(THESIS_CODE_PATH):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES]
        for filename in files:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            relative_path = os.path.relpath(filepath, THESIS_CODE_PATH)

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()

            if not code.strip():
                continue

            if len(code) > MAX_CODE_CHARS:
                print(
                    f"[SKIP] {relative_path}: {len(code)} chars exceeds "
                    f"{MAX_CODE_CHARS}-char validator limit"
                )
                continue

            try:
                report = {}
                for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
                    result = validate_code(code)
                    report = result.get("report", {})
                    if hasattr(report, "model_dump"):
                        report = report.model_dump()

                    summary = report.get("summary", "")
                    if not str(summary).startswith("Validation failed due to LLM error:"):
                        break

                    if attempt < MAX_VALIDATION_ATTEMPTS:
                        print(f"[RETRY] {relative_path}: transient LLM failure, retrying")
                        time.sleep(1.0)

                if report.get("total_issues_found", 0) > 0:
                    results.append({
                        "file": relative_path,
                        "issues_found": report["total_issues_found"],
                        "issues": report.get("issues", []),
                    })
                    print(f"[FOUND] {relative_path}: {report['total_issues_found']} issue(s)")
            except Exception as e:
                print(f"[ERROR] {relative_path}: {e}")

    return results


def main() -> None:
    """
    Execute the thesis scan and persist the findings to JSON.
    Keeps thesis validation reproducible from a single script entry point.
    """
    results = scan_thesis_codebase()

    output_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nTotal files with issues: {len(results)}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
