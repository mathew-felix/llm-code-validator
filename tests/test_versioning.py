from llm_code_validator.core import check_source
from llm_code_validator.versioning import build_version_context, parse_dependency_file, parse_requirements


def test_parse_requirements_reads_pinned_dependency(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("openai==1.2.3\n# ignored\n", encoding="utf-8")
    assert parse_requirements(req)["openai"] == "==1.2.3"


def test_parse_requirements_tolerates_invalid_utf8_bytes(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_bytes(b"\xffopenai==1.2.3\n")
    assert parse_requirements(req)["openai"] == "==1.2.3"


def test_build_version_context_uses_explicit_requirements(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("openai>=1.0.0\n", encoding="utf-8")
    context = build_version_context(requirements=str(req))
    assert context.requirements_path == str(req)
    assert not context.used_defaults


def test_check_source_uses_requirement_version_assumption(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("openai==1.2.3\n", encoding="utf-8")
    context = build_version_context(requirements=str(req))
    result = check_source("import openai\nopenai.ChatCompletion.create()\n", "sample.py", context)
    assert result.diagnostics[0].version_assumption == "openai==1.2.3"
    assert result.warnings == []


def test_check_source_warns_when_using_defaults():
    result = check_source("import openai\nopenai.ChatCompletion.create()\n", "sample.py")
    assert result.warnings


def test_parse_pyproject_dependencies(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["openai==1.2.3", "pandas>=2.0"]\n', encoding="utf-8")

    dependencies = parse_dependency_file(pyproject)

    assert dependencies["openai"] == "==1.2.3"
    assert dependencies["pandas"] == ">=2.0"


def test_parse_poetry_lock_dependencies(tmp_path):
    lock = tmp_path / "poetry.lock"
    lock.write_text('[[package]]\nname = "openai"\nversion = "1.2.3"\n', encoding="utf-8")

    assert parse_dependency_file(lock)["openai"] == "==1.2.3"


def test_parse_uv_lock_dependencies(tmp_path):
    lock = tmp_path / "uv.lock"
    lock.write_text('[[package]]\nname = "pandas"\nversion = "2.2.0"\n', encoding="utf-8")

    assert parse_dependency_file(lock)["pandas"] == "==2.2.0"


def test_parse_pipfile_lock_dependencies(tmp_path):
    lock = tmp_path / "Pipfile.lock"
    lock.write_text('{"default": {"openai": {"version": "==1.2.3"}}}', encoding="utf-8")

    assert parse_dependency_file(lock)["openai"] == "==1.2.3"


def test_build_version_context_discovers_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["openai==1.2.3"]\n', encoding="utf-8")
    source = tmp_path / "sample.py"
    source.write_text("import openai\n", encoding="utf-8")

    context = build_version_context([str(source)])

    assert context.requirements_path == str(pyproject)
    assert context.dependencies["openai"] == "==1.2.3"
