from llm_code_validator.benchmark import run_benchmark, run_labeled_benchmark


def test_run_benchmark_reports_runtime_context(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("print('ok')\n", encoding="utf-8")

    payload = run_benchmark([str(tmp_path)])

    assert payload["files"] == 1
    assert "p50_ms" in payload
    assert "peak_ram_mb" in payload
    assert "python_version" in payload


def test_run_labeled_benchmark_reports_precision_and_recall():
    payload = run_labeled_benchmark("validation_dataset/cli_benchmark_cases.json")

    assert payload["cases"] == 6
    assert payload["precision"] >= 0.8
    assert payload["recall"] >= 0.8
    assert payload["false_positives"] == 0
    assert payload["false_negatives"] == 0
    assert payload["false_positive_examples"] == []
    assert payload["false_negative_examples"] == []


def test_run_ai_stack_benchmark_reports_precision_and_recall():
    payload = run_labeled_benchmark("validation_dataset/ai_stack_benchmark_cases.json")

    assert payload["cases"] == 13
    assert payload["precision"] >= 0.8
    assert payload["recall"] >= 0.8
    assert payload["false_positives"] == 0
    assert payload["false_negatives"] == 0
