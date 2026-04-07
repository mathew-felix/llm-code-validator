# Project Status

## Scope

`llm-code-validator` is a working validator for Python snippets. It checks imports and method calls against a curated breakage database, uses PyPI metadata for unknown packages, and returns a structured report through a FastAPI endpoint.

## Implemented

- `frontend/index.html` for the demo UI
- `api/main.py` with `POST /validate`
- `agent/graph.py` for the LangGraph workflow
- `agent/nodes/*.py` for extraction, lookup, PyPI fallback, routing, diagnosis, and report generation
- `data/library_signatures.json` as the local breakage database
- `tests/evaluate.py` and `tests/baseline.py` for benchmark runs

## Pipeline

1. `extract_imports`
2. `check_database`
3. Optional `fetch_pypi`
4. `supervisor`
5. Optional `import_specialist`
6. Optional `method_specialist`
7. `llm_diagnose`
8. `generate_report`

The validator also has a deterministic fallback path for cases where the OpenAI step is unavailable.

## Benchmarks

Latest saved full evaluation from [`validation_dataset/results.json`](validation_dataset/results.json):

- Precision: `76.6%`
- Recall: `72.0%`
- True positives: `59`
- False positives: `18`
- False negatives: `23`
- Average runtime: `7.03s` per test case

Baseline from `tests/baseline.py`:

- Precision: `86.7%`
- Recall: `80.2%`

The baseline is still stronger on raw score. The full system adds corrected code, line-level explanations, and fallback handling for packages outside the local database.

## Current Limitations

- The baseline still outperforms the full graph on precision and recall.
- Method attribution is partial; simple aliases are handled, but deeper object flow is not.
- Import-name normalization relies on a curated mapping table.
- Repo-local import filtering is heuristic.
- The API is limited to 10,000-character inputs.
- When the OpenAI step is unavailable, the fallback path returns narrower explanations than a full LLM pass.
