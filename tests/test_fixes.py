from llm_code_validator.diagnostics import CheckResult, Diagnostic, Fix
from llm_code_validator.fixes import fix_file


def _diagnostic(safety: str, replacement: str | None = None):
    return Diagnostic(
        path="sample.py",
        line=1,
        column=1,
        code="LCV001",
        severity="error",
        library="demo",
        symbol="old_api",
        message="old api",
        replacement=replacement,
        fix=Fix(replacement=replacement, safety=safety),
    )


def test_fix_dry_run_does_not_modify_file(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("old_api()\n", encoding="utf-8")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [_diagnostic("safe_fix", "new_api")]))

    result = fix_file(path, write=False)

    assert result.previews
    assert not result.changed
    assert path.read_text(encoding="utf-8") == "old_api()\n"


def test_fix_write_applies_safe_fix_and_preserves_final_newline(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("old_api()\n", encoding="utf-8")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [_diagnostic("safe_fix", "new_api")]))

    result = fix_file(path, write=True)

    assert result.changed
    assert path.read_text(encoding="utf-8") == "new_api()\n"


def test_fix_skips_suggested_fix(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("old_api()\n", encoding="utf-8")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [_diagnostic("suggested_fix", "new_api")]))

    result = fix_file(path, write=True)

    assert result.skipped
    assert not result.changed
    assert path.read_text(encoding="utf-8") == "old_api()\n"


def test_fix_skips_no_fix(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("old_api()\n", encoding="utf-8")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [_diagnostic("no_fix")]))

    result = fix_file(path, write=True)

    assert result.skipped
    assert not result.changed


def test_fix_replaces_exact_dotted_symbol(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("value = np.bool\n", encoding="utf-8")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [_diagnostic("safe_fix", "bool")]))
    diagnostic = _diagnostic("safe_fix", "bool")
    object.__setattr__(diagnostic, "symbol", "np.bool")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [diagnostic]))

    result = fix_file(path, write=True)

    assert result.changed
    assert path.read_text(encoding="utf-8") == "value = bool\n"


def test_fix_replaces_safe_from_import_line(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text("from langchain.memory import ConversationBufferMemory\n", encoding="utf-8")
    diagnostic = _diagnostic("safe_fix", "from langchain_community.memory import ConversationBufferMemory")
    object.__setattr__(diagnostic, "symbol", "ConversationBufferMemory")
    monkeypatch.setattr("llm_code_validator.fixes.check_file", lambda *_: CheckResult(1, [diagnostic]))

    result = fix_file(path, write=True)

    assert result.changed
    assert path.read_text(encoding="utf-8") == (
        "from langchain_community.memory import ConversationBufferMemory\n"
    )


def test_real_safe_fix_replaces_langchain_memory_import(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("from langchain.memory import ConversationBufferMemory\n", encoding="utf-8")

    result = fix_file(path, write=True)

    assert result.changed
    assert path.read_text(encoding="utf-8") == (
        "from langchain_community.memory import ConversationBufferMemory\n"
    )


def test_real_safe_fix_replaces_sqlalchemy_declarative_import(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(
        "from sqlalchemy.ext.declarative import declarative_base\nBase = declarative_base()\n",
        encoding="utf-8",
    )

    result = fix_file(path, write=True)

    assert result.changed
    assert path.read_text(encoding="utf-8") == (
        "from sqlalchemy.orm import declarative_base\nBase = declarative_base()\n"
    )
