from pathlib import Path

from llm_code_validator.ai_review import build_ai_payload, is_secret_path, redact_secrets


def test_redact_secrets_removes_common_secret_values():
    text = "OPENAI_API_KEY = 'sk-secret123456789'\nAuthorization: Bearer abc.def.ghi\n"

    redacted = redact_secrets(text)

    assert "sk-secret" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "[REDACTED]" in redacted


def test_secret_paths_are_excluded():
    assert is_secret_path(Path(".env"))
    assert is_secret_path(Path("config/secrets/settings.py"))


def test_build_ai_payload_uses_minimized_snippet_and_excludes_secret_paths(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("import openai\nx = 1\nopenai.ChatCompletion.create(api_key='sk-secret123456789')\n", encoding="utf-8")
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "hidden.py"
    secret_file.write_text("import openai\n", encoding="utf-8")

    payload = build_ai_payload([str(tmp_path)], max_snippet_lines=5)
    files = payload["files"]

    assert isinstance(files, list)
    assert len(files) == 1
    assert files[0]["path"].endswith("app.py")
    assert "x = 1" not in files[0]["snippet"]
    assert "sk-secret" not in files[0]["snippet"]
