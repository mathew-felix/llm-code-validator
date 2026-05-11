# Release Checklist

Use this checklist when publishing `llm-code-validator`.

1. Update the version in `pyproject.toml` and `llm_code_validator/__init__.py`.
2. Run `pytest -q`.
3. Run `llm-code-validator validate-signatures --require-official-evidence`.
4. Run `python -m llm_code_validator.benchmark --dataset validation_dataset/cli_benchmark_cases.json --output validation_dataset/cli_benchmark_results.json`.
5. Build the package with `python -m build`.
6. Test the wheel in a clean virtual environment:

```bash
python -m venv .venv-release-test
.venv-release-test\Scripts\python -m pip install dist\llm_code_validator-*.whl
.venv-release-test\Scripts\llm-code-validator check tests\fixtures\sample_project
```

7. Publish with `python -m twine upload dist/*`.
8. Verify external install:

```bash
python -m venv .venv-pypi-test
.venv-pypi-test\Scripts\python -m pip install llm-code-validator
.venv-pypi-test\Scripts\llm-code-validator --help
```

Do not treat PyPI distribution as complete until step 8 succeeds against the public package.
