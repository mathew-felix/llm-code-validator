import json

from llm_code_validator.diagnostics import CheckResult, Diagnostic
from llm_code_validator.formatting import format_github, format_json, format_text


def _result():
    diagnostic = Diagnostic(
        path="src/app.py",
        line=3,
        column=5,
        code="LCV001",
        severity="error",
        library="openai",
        symbol="ChatCompletion.create",
        message="stale API",
        replacement="client.chat.completions.create(...)",
        version_assumption="openai>=1.0.0",
    )
    return CheckResult(checked_files=1, diagnostics=[diagnostic])


def test_format_text_includes_location_and_fix():
    output = format_text(_result())
    assert "src/app.py:3" in output
    assert "fix:" in output


def test_format_json_has_stable_top_level_keys():
    payload = json.loads(format_json(_result()))
    assert sorted(payload.keys()) == ["checked_files", "diagnostics", "warnings"]


def test_format_github_annotation_has_file_line_and_title():
    output = format_github(_result())
    assert output.startswith("::error file=src/app.py,line=3,col=5,title=LCV001::")


def test_format_text_ok_output_with_warning():
    output = format_text(CheckResult(checked_files=1, warnings=["fallback"]))
    assert "OK: checked 1 file(s)" in output
    assert "warning: fallback" in output
