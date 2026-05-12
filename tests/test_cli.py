import json
import subprocess

from llm_code_validator.cli import main


def test_cli_text_output_for_file(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    exit_code = main(["check", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "LCV001" in output
    assert "pinecone" in output


def test_cli_json_output_for_file(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text("import numpy as np\nx = np.bool\n", encoding="utf-8")

    exit_code = main(["check", "--format", "json", str(path)])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 1
    assert payload["checked_files"] == 1
    assert payload["diagnostics"][0]["library"] == "numpy"


def test_cli_ok_exit_code(tmp_path, capsys):
    path = tmp_path / "clean.py"
    path.write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["check", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "OK:" in output


def test_cli_github_output_for_file(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    exit_code = main(["check", "--format", "github", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert output.startswith("::error file=")
    assert "title=LCV001" in output


def test_cli_stdin(monkeypatch, capsys):
    class FakeStdin:
        def read(self):
            return "import numpy as np\nx = np.int\n"

    monkeypatch.setattr("sys.stdin", FakeStdin())
    exit_code = main(["check", "-"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "<stdin>" in output


def test_cli_directory_scan(tmp_path, capsys):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "sample.py").write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    exit_code = main(["check", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "sample.py" in output


def test_cli_explicit_requirements_removes_default_warning(tmp_path, capsys):
    req = tmp_path / "requirements.txt"
    req.write_text("openai==1.2.3\n", encoding="utf-8")
    path = tmp_path / "sample.py"
    path.write_text("import openai\nopenai.ChatCompletion.create()\n", encoding="utf-8")

    exit_code = main(["check", "--requirements", str(req), str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "openai==1.2.3" in output
    assert "No requirements file" not in output


def test_cli_validate_signatures(capsys):
    exit_code = main(["validate-signatures"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK:" in output


def test_cli_validate_signatures_missing_file(capsys):
    exit_code = main(["validate-signatures", "--path", "missing-signatures.json"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "file not found" in captured.err


def test_cli_validate_signatures_invalid_json(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")

    exit_code = main(["validate-signatures", "--path", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "invalid JSON" in captured.err


def test_cli_fix_dry_run_skips_suggested_fix(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")

    exit_code = main(["fix", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "skipped (suggested_fix)" in output
    assert "pinecone.init" in path.read_text(encoding="utf-8")


def test_cli_staged_checks_only_staged_python(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    staged = tmp_path / "staged.py"
    unstaged = tmp_path / "unstaged.py"
    staged.write_text("import pinecone\npinecone.init(api_key='x')\n", encoding="utf-8")
    unstaged.write_text("import openai\nopenai.ChatCompletion.create()\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.py"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    exit_code = main(["check", "--staged"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "staged.py" in output
    assert "unstaged.py" not in output


def test_cli_show_low_confidence_option(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text(
        "import pandas as pd\n\ndef make_df():\n    return pd.DataFrame()\n\ndf = make_df()\ndf.append({})\n",
        encoding="utf-8",
    )

    exit_code = main(["check", "--show-low-confidence", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "DataFrame.append" in output


def test_cli_ai_review_payload_is_redacted(tmp_path, capsys):
    path = tmp_path / "sample.py"
    path.write_text(
        "import openai\nOPENAI_API_KEY = 'sk-secret123456789'\nopenai.ChatCompletion.create()\n",
        encoding="utf-8",
    )

    exit_code = main(["check", "--ai-review", "--show-ai-payload", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "advisory API-drift review" in output
    assert "sk-secret" not in output
    assert "[REDACTED]" in output


def test_cli_ai_review_requires_provider_configuration(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = tmp_path / "clean.py"
    path.write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["check", "--ai-review", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "OPENAI_API_KEY" in captured.err


def test_cli_no_network_blocks_ai_provider_calls(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789")
    path = tmp_path / "clean.py"
    path.write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["check", "--ai-review", "--no-network", str(path)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--no-network" in captured.err


def test_cli_suggest_rule_outputs_candidate_json(capsys):
    exit_code = main(
        [
            "suggest-rule",
            "--library",
            "demo",
            "--symbol",
            "old_api",
            "--removed-in",
            "2.0.0",
            "--reason",
            "Removed in v2.",
            "--replacement",
            "new_api",
            "--evidence",
            "https://example.com/migration",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["demo"]["methods"]["old_api"]["fix_safety"] == "suggested_fix"
    assert payload["demo"]["methods"]["old_api"]["source_url"] == "https://example.com/migration"


def test_cli_uses_private_signature_database(tmp_path, capsys):
    signatures = tmp_path / "library_signatures.json"
    signatures.write_text(
        json.dumps(
            {
                "demo": {
                    "current_version": "2.x",
                    "methods": {
                        "old_api": {
                            "exists": False,
                            "removed_in": "2.0.0",
                            "reason": "removed",
                            "old_usage": "demo.old_api()",
                            "source_url": "https://example.com/migration",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "sample.py"
    source.write_text("import demo\ndemo.old_api()\n", encoding="utf-8")

    exit_code = main(["check", "--signatures-path", str(signatures), str(source)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "demo.old_api" in output


def test_cli_policy_can_disable_external_ai(tmp_path, capsys):
    config = tmp_path / "llm-code-validator.json"
    config.write_text(
        json.dumps({"policy": {"allow_external_ai": False, "allowed_ai_providers": ["local"]}}),
        encoding="utf-8",
    )
    source = tmp_path / "clean.py"
    source.write_text("print('ok')\n", encoding="utf-8")

    exit_code = main(["check", "--ai-review", "--show-ai-payload", "--config", str(config), str(source)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "not allowed by policy" in captured.err


def test_cli_ai_review_writes_audit_log_without_snippets(tmp_path, capsys):
    source = tmp_path / "clean.py"
    source.write_text("print('ok')\n", encoding="utf-8")
    audit = tmp_path / "audit.jsonl"

    exit_code = main(["check", "--ai-review", "--show-ai-payload", "--ai-audit-log", str(audit), str(source)])
    capsys.readouterr()
    record = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])

    assert exit_code == 0
    assert record["provider"] == "openai"
    assert record["contains_source_snippets"] is False
