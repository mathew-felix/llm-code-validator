from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from llm_code_validator.benchmark import run_benchmark
from llm_code_validator.core import check_paths


DEFAULT_REPOS_FILE = Path("validation_dataset/external_ai_repos.txt")
DEFAULT_WORKDIR = Path(".external_repos")
DEFAULT_OUTPUT_DIR = Path("validation_dataset/external_repo_runs")


def repo_slug(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").removesuffix(".git")
    return path.replace("/", "__") or parsed.netloc.replace(".", "-")


def load_repo_urls(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def clone_or_update(url: str, workdir: Path, update: bool) -> tuple[Path, str, str | None]:
    destination = workdir / repo_slug(url)
    if (destination / ".git").exists():
        if not update:
            return destination, "existing", None
        proc = run_git(["pull", "--ff-only"], cwd=destination)
        if proc.returncode != 0:
            return destination, "update_failed", (proc.stderr or proc.stdout).strip()
        return destination, "updated", None

    destination.parent.mkdir(parents=True, exist_ok=True)
    proc = run_git(["clone", "--depth", "1", url, str(destination)])
    if proc.returncode != 0:
        return destination, "clone_failed", (proc.stderr or proc.stdout).strip()
    return destination, "cloned", None


def summarize_diagnostics(diagnostics: list[dict[str, object]]) -> dict[str, object]:
    by_library = Counter(str(item["library"]) for item in diagnostics)
    by_code = Counter(str(item["code"]) for item in diagnostics)
    by_symbol = Counter(f"{item['library']}.{item['symbol']}" for item in diagnostics)
    return {
        "by_library": dict(by_library.most_common()),
        "by_code": dict(by_code.most_common()),
        "top_symbols": dict(by_symbol.most_common(10)),
    }


def evaluate_repo(url: str, workdir: Path, update: bool) -> dict[str, object]:
    destination, clone_status, clone_error = clone_or_update(url, workdir, update)
    result: dict[str, object] = {
        "repo": url,
        "slug": repo_slug(url),
        "path": str(destination),
        "clone_status": clone_status,
    }
    if clone_error:
        result["status"] = "failed"
        result["error"] = clone_error
        return result

    check_result = check_paths([str(destination)], show_low_confidence=True)
    diagnostics = [diagnostic.to_dict() for diagnostic in check_result.diagnostics]
    benchmark = run_benchmark([str(destination)])
    result.update(
        {
            "status": "scanned",
            "checked_files": check_result.checked_files,
            "diagnostics": diagnostics,
            "diagnostic_count": len(diagnostics),
            "warnings": check_result.warnings,
            "diagnostic_summary": summarize_diagnostics(diagnostics),
            "benchmark": benchmark,
        }
    )
    return result


def write_outputs(results: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "External repo evaluation is an unlabeled smoke test; diagnostics require human review.",
        "results": results,
    }
    (output_dir / "external_ai_repo_results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "external_ai_repo_summary.md").write_text(render_markdown(payload), encoding="utf-8")


def render_markdown(payload: dict[str, object]) -> str:
    results = list(payload["results"])  # type: ignore[index]
    scanned = [item for item in results if item.get("status") == "scanned"]
    failed = [item for item in results if item.get("status") == "failed"]
    total_files = sum(int(item.get("checked_files", 0)) for item in scanned)
    total_diagnostics = sum(int(item.get("diagnostic_count", 0)) for item in scanned)

    lines = [
        "# External AI Repo Evaluation",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "This is an unlabeled external smoke test. It shows what the tool finds in real AI-stack repositories, but it does not prove precision or recall until findings are manually labeled.",
        "",
        f"- Repositories attempted: {len(results)}",
        f"- Repositories scanned: {len(scanned)}",
        f"- Repositories failed: {len(failed)}",
        f"- Python files scanned: {total_files}",
        f"- Diagnostics found: {total_diagnostics}",
        "",
        "| Repository | Status | Files | Diagnostics | Top findings | p95 ms | Files/sec |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for item in results:
        repo = str(item["repo"])
        status = str(item["status"])
        if status != "scanned":
            error = str(item.get("error", "")).splitlines()[0][:80]
            lines.append(f"| {repo} | {status} | 0 | 0 | {error} | 0.00 | 0.00 |")
            continue
        summary = item.get("diagnostic_summary", {})
        top_symbols = summary.get("top_symbols", {}) if isinstance(summary, dict) else {}
        top = ", ".join(f"{symbol} ({count})" for symbol, count in list(top_symbols.items())[:3]) or "none"
        benchmark = item.get("benchmark", {})
        p95 = float(benchmark.get("p95_ms", 0.0)) if isinstance(benchmark, dict) else 0.0
        fps = float(benchmark.get("files_per_second", 0.0)) if isinstance(benchmark, dict) else 0.0
        lines.append(
            f"| {repo} | {status} | {item.get('checked_files', 0)} | {item.get('diagnostic_count', 0)} | {top} | {p95:.2f} | {fps:.1f} |"
        )

    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Treat findings as candidates until a developer checks the target dependency versions and the source context.",
            "- A repo with zero diagnostics is not guaranteed clean; unsupported libraries, dynamic imports, and deeper type inference remain known limits.",
            "- Clone or update failures are recorded so the run is repeatable instead of silently skipping repositories.",
            "",
            "## Rerun",
            "",
            "```bash",
            "python scripts/evaluate_external_repos.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clone public AI-stack repos and run llm-code-validator on them.")
    parser.add_argument("--repos-file", type=Path, default=DEFAULT_REPOS_FILE)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, help="Only evaluate the first N repositories.")
    parser.add_argument("--no-update", action="store_true", help="Do not run git pull for repositories already cloned.")
    args = parser.parse_args(argv)

    urls = load_repo_urls(args.repos_file)
    if args.limit is not None:
        urls = urls[: args.limit]
    results = [evaluate_repo(url, args.workdir, update=not args.no_update) for url in urls]
    write_outputs(results, args.output_dir)
    print(f"Wrote {args.output_dir / 'external_ai_repo_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
