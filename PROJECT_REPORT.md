# Project Report: llm-code-validator

## Project Overview

`llm-code-validator` is a Python command-line tool for detecting stale or version-incompatible third-party API usage in Python source code.

The tool scans Python files without executing them, identifies known API-drift patterns, and reports where code may no longer work with modern versions of common libraries. It is designed to run locally from the command line, in pre-commit hooks, or in CI pipelines.

The project currently focuses on Python libraries that commonly change APIs across versions, including:

- OpenAI
- Anthropic
- LangChain
- LangGraph
- LlamaIndex
- Pinecone
- ChromaDB
- FastAPI
- Pydantic
- pandas
- NumPy
- SQLAlchemy
- Torch
- Transformers

## Main Purpose

The purpose of the project is to catch API usage that is valid Python syntax but invalid for a target library version.

For example, a file can parse correctly but still contain calls or imports that were removed, renamed, moved, or changed in newer package versions.

The validator helps identify these problems earlier by checking source code against a maintained rule database.

## What the Tool Does

`llm-code-validator` can:

- Scan one Python file.
- Scan a directory recursively.
- Scan code from standard input.
- Scan staged Git files.
- Read dependency information from common Python project files.
- Report diagnostics in terminal text format.
- Report diagnostics as JSON.
- Report diagnostics as GitHub Actions annotations.
- Preview safe fixes.
- Apply safe fixes only when explicitly requested.
- Validate the internal rule database.
- Run benchmark datasets.
- Run external repository evaluation scripts.

## Command-Line Interface

Main commands:

```bash
llm-code-validator check file.py
llm-code-validator check src/
llm-code-validator check -
llm-code-validator check --staged
llm-code-validator check --format json src/
llm-code-validator check --format github src/
llm-code-validator check --requirements requirements.txt src/
llm-code-validator check --show-low-confidence src/
llm-code-validator fix file.py
llm-code-validator fix file.py --write
llm-code-validator validate-signatures
```

Exit codes:

- `0`: no diagnostics found
- `1`: diagnostics found
- `2`: tool error

## Supported Input Sources

The checker supports:

- Direct file paths
- Directory paths
- Standard input
- Git staged files

When scanning directories, the tool excludes directories that should not normally be analyzed as project source, including virtual environments and site-packages-style directories.

## Dependency Version Support

The tool can use dependency metadata to decide whether a rule applies to the target project.

Supported dependency sources:

- `requirements.txt`
- explicit `--requirements` file
- `pyproject.toml`
- `poetry.lock`
- `uv.lock`
- `Pipfile.lock`

If no dependency file is available, the checker uses default version assumptions from the maintained signature database and includes a warning in the output.

## Static Analysis Engine

The scanner is implemented with Python's built-in `ast` module.

It detects and tracks:

- direct imports
- aliased imports
- `from ... import ...` imports
- constructor assignments
- method calls
- attribute calls
- decorators
- simple object origins
- dynamic import patterns

The scanner does not execute user code. This keeps checks local, deterministic, and safe to run in CI.

## Rule Database

API-drift rules are stored in:

```text
data/library_signatures.json
```

The packaged wheel includes a copy at:

```text
llm_code_validator/library_signatures.json
```

Current rule database summary:

- 68 total API-drift rules
- 15 `safe_fix` rules
- 51 `suggested_fix` rules
- 2 `no_fix` rules

Each rule can include:

- library name
- stale API pattern
- affected version range
- diagnostic message
- severity
- replacement guidance
- fix safety level
- evidence metadata

## Rule Validation

The project includes validation for the rule database.

Validation checks include:

- JSON structure correctness
- required fields
- duplicate rule detection
- evidence presence
- safe-fix metadata
- deterministic replacement data for automatic fixes

The command is:

```bash
llm-code-validator validate-signatures
```

## Diagnostics

Diagnostics include:

- file path
- line number
- rule code
- severity
- matched API
- compatibility message
- affected version assumption
- suggested replacement when available

Example output shape:

```text
src/app.py:12 LCV001 error pandas.DataFrame.append pandas.DataFrame.append is incompatible with pandas>=2.0.0
  fix: pd.concat([df1, df2])
```

## Output Formats

The tool supports three output formats.

Text output:

```bash
llm-code-validator check src/
```

JSON output:

```bash
llm-code-validator check src/ --format json
```

GitHub Actions annotation output:

```bash
llm-code-validator check src/ --format github
```

## Safe Fix Mode

Fix mode is conservative.

Preview fixes:

```bash
llm-code-validator fix file.py
```

Write fixes:

```bash
llm-code-validator fix file.py --write
```

The tool only writes changes for rules marked `safe_fix`.

Rules marked `suggested_fix` or `no_fix` are reported but not automatically changed.

Safe fixes are currently used for deterministic replacements such as direct import migrations.

## Project Architecture

Main package files:

- `llm_code_validator/cli.py`: command-line interface
- `llm_code_validator/core.py`: AST scanner and rule matching
- `llm_code_validator/diagnostics.py`: diagnostic data model
- `llm_code_validator/formatting.py`: text, JSON, and GitHub output
- `llm_code_validator/signatures.py`: rule loading and validation
- `llm_code_validator/fixes.py`: fix preview and write behavior
- `llm_code_validator/versioning.py`: dependency file parsing
- `llm_code_validator/benchmark.py`: benchmark runner

Supporting files:

- `data/library_signatures.json`: source rule database
- `pyproject.toml`: package metadata
- `.pre-commit-hooks.yaml`: pre-commit integration
- `.github/workflows/api-drift-check.yml`: GitHub Actions workflow
- `docs/rules.md`: rule documentation
- `docs/release.md`: release workflow
- `docs/demo.md`: demo workflow
- `examples/stale_ai_code.py`: example file with stale APIs
- `tests/`: test suite
- `validation_dataset/`: benchmark and evaluation data

## Packaging

The package is configured in `pyproject.toml`.

The console script is:

```bash
llm-code-validator
```

The package builds successfully into:

- source distribution
- wheel distribution

The wheel includes the packaged signature database so the installed command can run without needing the repository source tree.

## Testing

Current test result:

```text
74 passed
```

Test coverage includes:

- CLI behavior
- scanner behavior
- rule matching
- output formatting
- safe fixes
- dependency version parsing
- signature validation
- benchmark runner behavior
- workflow configuration
- external repository evaluation script behavior

## Benchmarking

The project includes a benchmark runner:

```bash
python -m llm_code_validator.benchmark --dataset validation_dataset/cli_benchmark_cases.json
python -m llm_code_validator.benchmark --dataset validation_dataset/ai_stack_benchmark_cases.json
```

### CLI Benchmark

Current saved result:

- 6 cases
- 5 expected diagnostics
- precision: 1.0
- recall: 1.0
- false positives: 0
- false negatives: 0
- p50: 0.243 ms
- p95: 6.199 ms
- throughput: 786 files/sec

### AI-Stack Benchmark

Current saved result:

- 13 cases
- 12 expected diagnostics
- precision: 1.0
- recall: 1.0
- false positives: 0
- false negatives: 0
- p50: 0.444 ms
- p95: 4.939 ms
- throughput: 1295 files/sec

## External Repository Evaluation

The project includes a script for scanning public repositories during validation:

```text
scripts/evaluate_external_repos.py
```

Combined external evaluation summary:

- 40 repositories configured
- 39 repositories scanned
- 2,073 Python files scanned
- 121 candidate diagnostics

The external evaluation runs helped identify and fix scanner issues, including:

- overly broad rule matches
- alias matching edge cases
- ChromaDB parameter over-reporting
- invalid UTF-8 file handling
- unnecessary scanning of committed virtual environments

Raw external scan output is kept out of the public release docs because those findings need dependency and source-context review before being treated as confirmed defects.

## Documentation

Current documentation includes:

- `README.md`: usage, commands, integrations, benchmarks, limitations
- `docs/rules.md`: rule database and evidence workflow
- `docs/release.md`: package build and release workflow
- `docs/demo.md`: short demo with stale imports and safe fixes
- `docs/accuracy.md`: benchmark and external-scan notes
- `PROJECT_REPORT.md`: project-level report

## Current Status

Completed:

- CLI implementation
- AST scanner
- rule database
- rule validation
- dependency parsing
- output formatting
- safe fix preview and write mode
- benchmark runner
- benchmark datasets
- external repository evaluation script
- pre-commit integration
- GitHub Actions integration
- README documentation
- demo documentation
- local wheel build
- source distribution build
- package metadata validation
- clean wheel install verification

Verified commands:

```bash
pytest -q
python -m build
twine check dist/*
llm-code-validator validate-signatures
```

## Remaining Work

Completed release work:

- Uploaded version `0.1.0` to PyPI.
- Verified install from PyPI in a clean virtual environment.
- Verified the installed `llm-code-validator validate-signatures` command can read the packaged signature database.
- Updated README install instructions to use `pip install llm-code-validator`.

Remaining release work:

- Add a PyPI badge if badges are wanted.

Remaining validation work:

- Continue adding labeled benchmark cases when new false positives or false negatives are found.
- Keep rule evidence updated as supported libraries change.
- Manually review external scan findings before making confirmed-defect claims.

## Limitations

Current limitations:

- The tool only detects known API-drift patterns.
- It does not prove full program correctness.
- Complex dynamic Python patterns may not be fully resolved.
- Dependency version detection depends on available project metadata.
- Some findings require manual review when dependency versions are unknown.
- External repository diagnostics are candidate findings until manually labeled.
- Automatic fixes are limited to deterministic `safe_fix` rules.

## Final Summary

`llm-code-validator` is a working Python CLI package for static detection of stale third-party API usage. It includes a maintained rule database, AST-based scanning, dependency-version awareness, multiple output formats, conservative safe fixes, benchmark datasets, external evaluation tooling, CI integration, pre-commit support, and package release preparation.

The project is published on PyPI as `llm-code-validator` and can be installed with `pip install llm-code-validator`.
