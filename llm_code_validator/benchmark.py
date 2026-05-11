from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from datetime import date
from pathlib import Path

from .core import check_file, check_source, iter_python_files
from .versioning import build_version_context


def run_benchmark(paths: list[str]) -> dict[str, object]:
    files = iter_python_files(paths)
    version_context = build_version_context(paths)
    timings: list[float] = []
    diagnostics = 0
    tracemalloc.start()
    start = time.perf_counter()
    for path in files:
        file_start = time.perf_counter()
        result = check_file(path, version_context)
        timings.append(time.perf_counter() - file_start)
        diagnostics += len(result.diagnostics)
    total = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    p50 = statistics.median(timings) if timings else 0.0
    p95 = statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else (max(timings) if timings else 0.0)
    files_per_second = len(files) / total if total else 0.0
    return {
        "files": len(files),
        "diagnostics": diagnostics,
        "total_seconds": total,
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
        "files_per_second": files_per_second,
        "peak_ram_mb": peak / (1024 * 1024),
        "hardware": platform.machine(),
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "precision": None,
        "recall": None,
        "false_positives": None,
        "false_negatives": None,
    }


def run_labeled_benchmark(dataset_path: str | Path) -> dict[str, object]:
    dataset_file = Path(dataset_path)
    cases = json.loads(dataset_file.read_text(encoding="utf-8"))
    timings: list[float] = []
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    false_positive_examples: list[dict[str, str]] = []
    false_negative_examples: list[dict[str, str]] = []
    total_expected = 0
    total_diagnostics = 0

    tracemalloc.start()
    start = time.perf_counter()
    for case in cases:
        case_start = time.perf_counter()
        result = check_source(case["code"], case.get("path") or f"{case['id']}.py")
        timings.append(time.perf_counter() - case_start)
        expected = {(item["library"], item["symbol"]) for item in case.get("expected_diagnostics", [])}
        actual = {(diagnostic.library, diagnostic.symbol) for diagnostic in result.diagnostics}
        total_expected += len(expected)
        total_diagnostics += len(actual)
        true_positives += len(expected & actual)
        case_false_positives = actual - expected
        case_false_negatives = expected - actual
        false_positives += len(case_false_positives)
        false_negatives += len(case_false_negatives)
        for library, symbol in sorted(case_false_positives):
            false_positive_examples.append(
                {"case_id": case["id"], "library": library, "symbol": symbol, "reason": "unexpected diagnostic"}
            )
        for library, symbol in sorted(case_false_negatives):
            false_negative_examples.append(
                {"case_id": case["id"], "library": library, "symbol": symbol, "reason": "missing rule or extraction gap"}
            )
    total = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 1.0
    recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives else 1.0
    p50 = statistics.median(timings) if timings else 0.0
    p95 = statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else (max(timings) if timings else 0.0)
    return {
        "dataset": str(dataset_file),
        "benchmark_date": date.today().isoformat(),
        "cases": len(cases),
        "files": len(cases),
        "diagnostics": total_diagnostics,
        "expected_diagnostics": total_expected,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "false_positive_examples": false_positive_examples,
        "false_negative_examples": false_negative_examples,
        "precision": precision,
        "recall": recall,
        "total_seconds": total,
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
        "files_per_second": len(cases) / total if total else 0.0,
        "peak_ram_mb": peak / (1024 * 1024),
        "hardware": platform.machine(),
        "os": platform.platform(),
        "python_version": platform.python_version(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m llm_code_validator.benchmark")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--dataset", help="Run a labeled benchmark dataset JSON file.")
    parser.add_argument("--output", help="Write JSON benchmark output to a file.")
    args = parser.parse_args(argv)
    if args.dataset:
        payload = run_labeled_benchmark(args.dataset)
    elif args.paths:
        payload = run_benchmark(args.paths)
    else:
        parser.error("provide one or more paths or --dataset")
    output = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
