import json
import os

# Load test cases
TEST_CASES_PATH = os.path.join(os.path.dirname(__file__),
                               "../validation_dataset/test_cases.json")
DATABASE_PATH = os.path.join(os.path.dirname(__file__),
                             "../data/library_signatures.json")

with open(TEST_CASES_PATH) as f:
    test_cases = json.load(f)

with open(DATABASE_PATH) as f:
    database = json.load(f)

def baseline_check(code: str) -> set:
    """Pure dictionary lookup — no LLM, no LangGraph."""
    detected = set()
    for library_name, library_data in database.items():
        if library_name in code:
            for method_name, method_data in library_data.get("methods", {}).items():
                if method_name in code:
                    detected.add(f"{library_name}.{method_name}")
    return detected

tp_total, fp_total, fn_total = 0, 0, 0

for case in test_cases:
    expected = set(
        f"{issue['library']}.{issue['method']}"
        for issue in case["known_issues"]
    )
    detected = baseline_check(case["code"])

    tp = len(detected & expected)
    fp = len(detected - expected)
    fn = len(expected - detected)

    tp_total += tp
    fp_total += fp
    fn_total += fn

precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0
recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0

print(f"Baseline (dictionary only)")
print(f"Precision: {precision:.1%}")
print(f"Recall:    {recall:.1%}")
