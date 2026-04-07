import json
import sys
import os
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph import validate_code


def evaluate():
    """Run all test cases through the agent and compute precision/recall.

    Compares agent output against labeled known_issues to measure
    true positives, false positives, and false negatives.
    """

    # Use os.path.join for cross-platform path resolution
    test_path = os.path.join(
        os.path.dirname(__file__), "..", "validation_dataset", "test_cases.json"
    )
    results_path = os.path.join(
        os.path.dirname(__file__), "..", "validation_dataset", "results.json"
    )

    with open(test_path, "r") as f:
        test_cases = json.load(f)

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    total_issues = 0

    # Per-library tracking
    lib_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    results = []
    total_start = time.time()

    for i, test in enumerate(test_cases):
        print(f"\nRunning test {i+1}/{len(test_cases)}: {test['id']} — {test['description']}")
        test_start = time.time()

        try:
            result = validate_code(test["code"])
            report = result.get("report", {})

            # Handle both dict and Pydantic model output
            if hasattr(report, "model_dump"):
                report = report.model_dump()

            found_issues = report.get("issues", []) if isinstance(report, dict) else []
            known_issues = test["known_issues"]

            total_issues += len(known_issues)

            test_tp = 0
            test_fn = 0

            # Check each known issue — did the agent find it?
            for known in known_issues:
                library = known.get("library", "unknown")
                found = any(
                    issue["line_number"] == known["line"] and
                    issue["issue_type"] == known["type"]
                    for issue in found_issues
                )
                if found:
                    true_positives += 1
                    test_tp += 1
                    lib_stats[library]["tp"] += 1
                else:
                    false_negatives += 1
                    test_fn += 1
                    lib_stats[library]["fn"] += 1

            # Check for false positives (agent flagged something not in known_issues)
            test_fp = 0
            for found in found_issues:
                is_real = any(
                    found["line_number"] == known["line"]
                    for known in known_issues
                )
                if not is_real:
                    false_positives += 1
                    test_fp += 1

            elapsed = time.time() - test_start
            status = "✓" if test_fn == 0 and test_fp == 0 else "✗"
            print(f"  {status} TP:{test_tp} FP:{test_fp} FN:{test_fn} ({elapsed:.1f}s)")

            results.append({
                "id": test["id"],
                "description": test["description"],
                "expected": len(known_issues),
                "found": len(found_issues),
                "true_positives": test_tp,
                "false_positives": test_fp,
                "false_negatives": test_fn,
                "time_seconds": round(elapsed, 2)
            })

        except Exception as e:
            elapsed = time.time() - test_start
            print(f"  ERROR: {e} ({elapsed:.1f}s)")
            results.append({
                "id": test["id"],
                "description": test["description"],
                "error": str(e),
                "time_seconds": round(elapsed, 2)
            })

    total_elapsed = time.time() - total_start

    # Calculate metrics
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0 else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0 else 0
    )

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total test cases:    {len(test_cases)}")
    print(f"Total known issues:  {total_issues}")
    print(f"True positives:      {true_positives}")
    print(f"False positives:     {false_positives}")
    print(f"False negatives:     {false_negatives}")
    print(f"Precision:           {precision:.1%}")
    print(f"Recall (TPR):        {recall:.1%}")
    print(f"Total time:          {total_elapsed:.1f}s")
    print(f"Avg time per test:   {total_elapsed/len(test_cases):.1f}s")

    # Per-library breakdown
    print("\n" + "-" * 60)
    print("PER-LIBRARY BREAKDOWN")
    print("-" * 60)
    print(f"{'Library':<20} {'TP':>4} {'FP':>4} {'FN':>4} {'Precision':>10} {'Recall':>8}")
    print("-" * 60)
    for lib in sorted(lib_stats.keys()):
        s = lib_stats[lib]
        lib_precision = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) > 0 else 0
        lib_recall = s["tp"] / (s["tp"] + s["fn"]) if (s["tp"] + s["fn"]) > 0 else 0
        print(f"{lib:<20} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} {lib_precision:>9.0%} {lib_recall:>7.0%}")

    # Save results
    with open(results_path, "w") as f:
        json.dump({
            "summary": {
                "total_tests": len(test_cases),
                "total_known_issues": total_issues,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "total_time_seconds": round(total_elapsed, 2),
                "avg_time_per_test": round(total_elapsed / len(test_cases), 2)
            },
            "per_library": {
                lib: lib_stats[lib] for lib in sorted(lib_stats.keys())
            },
            "per_test": results
        }, f, indent=2)

    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    evaluate()
