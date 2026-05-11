# llm-code-validator

Python CLI for checking dependency-heavy Python projects for stale or version-incompatible third-party API usage before commit or CI.

It parses Python files with `ast`, checks imports and calls against a maintained API-drift rule database, and reports issues before runtime.

Current local validation: 74 tests passing, 68 API-drift rules, and PyPI install verified.

PyPI: https://pypi.org/project/llm-code-validator/

![Terminal demo showing API drift diagnostics and safe fix preview](docs/demo.gif)

## Install

```bash
pip install llm-code-validator
```

For local development:

```bash
git clone https://github.com/mathew-felix/llm-code-validator
cd llm-code-validator
pip install -e ".[dev]"
```

## Quick Use

```bash
llm-code-validator check file.py
llm-code-validator check src/
llm-code-validator check --staged
llm-code-validator check src/ --format json
llm-code-validator check src/ --format github
```

Exit codes:

- `0`: no diagnostics
- `1`: diagnostics found
- `2`: tool error

## Example

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

```bash
llm-code-validator check app.py
```

```text
app.py:1 LCV001 warning sqlalchemy.declarative_base sqlalchemy.declarative_base is incompatible with sqlalchemy>=2.0.0
  fix: from sqlalchemy.orm import declarative_base
```

Preview or apply safe fixes:

```bash
llm-code-validator fix app.py
llm-code-validator fix app.py --write
```

## What It Checks

Current rule database:

- 68 API-drift rules
- 15 safe fixes
- Rules for OpenAI, Anthropic, LangChain, LangGraph, LlamaIndex, Pinecone, ChromaDB, FastAPI, Pydantic, pandas, NumPy, SQLAlchemy, Torch, and Transformers

Validate the rule database:

```bash
llm-code-validator validate-signatures
```

This checks source-level API migration patterns. It does not replace Ruff for linting, mypy for type checking, pip-audit for vulnerability checks, or Dependabot for dependency updates.

## Limitations

- Detects known API-drift rules only.
- Does not prove full program correctness.
- Complex dynamic imports may be missed.
- Dependency checks depend on available project metadata.
- Suggested fixes require review before applying.
- External repository findings are treated as candidates until manually reviewed.

## Integrations

Pre-commit:

```yaml
repos:
  - repo: https://github.com/mathew-felix/llm-code-validator
    rev: v0.1.0
    hooks:
      - id: llm-code-validator
```

GitHub Actions:

```yaml
- run: pip install llm-code-validator
- run: llm-code-validator check . --format github
```

## Development

Run tests:

```bash
pytest -q
```

Current local result:

```text
74 passed
```

Run benchmarks:

```bash
python -m llm_code_validator.benchmark --dataset validation_dataset/cli_benchmark_cases.json
python -m llm_code_validator.benchmark --dataset validation_dataset/ai_stack_benchmark_cases.json
```

## More Details

- `docs/demo.md`: command walkthrough
- `docs/accuracy.md`: benchmark and external-review notes
- `docs/rules.md`: rule database notes
- `docs/release.md`: release steps
