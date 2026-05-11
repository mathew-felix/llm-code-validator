from pathlib import Path

import yaml


def test_github_action_uses_checkout_setup_python_install_and_github_format():
    workflow = yaml.safe_load(Path(".github/workflows/api-drift-check.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["api-drift"]["steps"]
    serialized = "\n".join(str(step) for step in steps)

    assert "actions/checkout@v4" in serialized
    assert "actions/setup-python@v5" in serialized
    assert "pip install -e ." in serialized
    assert "llm-code-validator check . --format github" in serialized


def test_pre_commit_hook_points_to_cli_check_command():
    hooks = yaml.safe_load(Path(".pre-commit-hooks.yaml").read_text(encoding="utf-8"))
    hook = hooks[0]

    assert hook["id"] == "llm-code-validator"
    assert hook["entry"] == "llm-code-validator check"
    assert hook["types"] == ["python"]
