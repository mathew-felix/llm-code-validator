# llm-code-validator

Validates AI-generated Python code against real library APIs — catches hallucinated methods and deprecated imports before they waste your debugging time.

![Demo](assets/demo.gif)

## The Problem

LLMs generate Python code using APIs that no longer exist. `pinecone.init()` was removed in v3. `langchain.chat_models` was restructured. `pandas.DataFrame.append()` was dropped in 2.0. Models trained before these changes don't know — and they generate broken code with complete confidence.

This problem showed up repeatedly while building `neural-edge-video-compression`, my thesis project for ROI-aware edge video compression, where a broken dependency discovered late can mean a full redeployment cycle on constrained hardware.

## How It Works

![Architecture](assets/architecture.svg)

1. Paste AI-generated Python code into the web UI
2. The AST node extracts imports, aliases, and attribute calls without executing the code
3. Extracted calls are matched against a curated database of 75+ known breaking changes
4. Unknown libraries trigger a live PyPI metadata fetch before any diagnosis happens
5. A supervisor node decides whether import and/or method specialists should run
6. Specialist findings are merged with the broad LLM diagnosis pass, deduplicated, and filtered by confidence
7. The final report is returned as structured JSON and rendered as issue cards in the UI

## Why LangGraph, Not a LangChain Chain

Two LangGraph patterns matter in this project:

**1. Conditional routing:** if all imported libraries exist in the local database,
the PyPI network call is skipped entirely. LangGraph's `add_conditional_edges`
keeps that routing explicit and cost-aware.

**2. Supervisor routing:** after parsing and database lookup, a supervisor node
decides whether import and method specialists should run before the broad
diagnosis pass. That is still explicit graph routing, but the decision is based
on the current state instead of a fixed linear pipeline.

A LangChain chain would force every step to run every time. This graph can skip
irrelevant work while still preserving a broad diagnosis pass for recall.

## Validation Results

Evaluated against 50 real broken Python scripts sourced from Stack Overflow questions, GitHub issues, and migration guides. Test cases were collected externally — not written to match the database.

| Approach | Precision | Recall | Notes |
|---|---|---|---|
| Dictionary lookup (`tests/baseline.py`) | 86.7% | 80.2% | Exact string matching only |
| `llm-code-validator` | 76.6% | 72.0% | AST + supervisor + specialists + LLM |

The exact-match baseline still has higher raw precision on this benchmark because
the test cases are weighted toward explicit import and method-name matches, which
string matching handles well. The LLM layer's value is qualitative: it produces
corrected code suggestions, plain-English explanations of what broke and why,
and line-specific fix output that the baseline cannot generate.

## Real-World Test: Thesis Codebase

I also ran the validator against the project-owned Python files in
[`neural-edge-video-compression`](neural-edge-video-compression) using
[`thesis_validation/run_on_thesis.py`](thesis_validation/run_on_thesis.py).
The thesis repo is tracked as a Git submodule so the same real-world test corpus
can be checked out in a fresh clone. Because that thesis repo is private, the
submodule fetch requires GitHub access to `mathew-felix/neural-edge-video-compression`.
That scan skips vendored directories, test suites, and files above the current
10,000-character validator limit so the run matches the product's supported input size.

After adding the local-module filter and import-name normalization, the thesis scan
dropped from 7 flagged files to 1.

| File | Example flag | Manual verdict |
|---|---|---|
| `src/decompression/interpolation_amt.py` | `torch.autocast` flagged as deprecated | Plausible real migration issue |

The previous false positives from local modules, relative imports, and import-name
vs distribution-name mismatches (`yaml`/`PyYAML`, `cv2`/`opencv-python`) are now
filtered before the PyPI fallback can mislabel them.

## Known Limitations

These are the documented cases where the validator does not work:

- **Import name normalization is heuristic**: Common mismatches like `yaml`/`PyYAML`, `cv2`/`opencv-python`, and `PIL`/`Pillow` are normalized, but uncommon import-to-distribution mismatches still need to be added to the lookup table.
- **Repo-local imports**: Relative, private, and many snake_case local modules are now filtered before PyPI, but repo-scale validation can still hit edge cases for internal package layouts.
- **Large files**: The API currently caps input at 10,000 characters; the thesis runner skips larger files to stay within the supported request size.
- **Aliased imports**: Deeply chained aliases are partially supported but sometimes missed if the alias tracking is broken or convoluted.
- **Star imports**: `from langchain import *` cannot be analyzed statically.
- **Dynamic imports**: `importlib.import_module('pandas')` is not detected.
- **Libraries outside the 20**: Falls back to PyPI metadata, which confirms the package exists but cannot validate specific method signatures, limiting its effectiveness for rare packages.
- **Method-level versus Import-level tracking**: Calls lacking an explicit library imported caller (`df.append()`) can be harder to attribute to a specific python package natively without type-checking.
- **LLM availability still matters**: When OpenAI times out or quota is unavailable, the agent now falls back to deterministic database/PyPI evidence, but the richer explanation and correction path is narrower than a successful full LLM pass.

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Agent framework | LangGraph 0.2.x | Conditional routing between nodes |
| LLM | GPT-4o-mini (temp=0.1) | Low temperature for deterministic diagnosis |
| Import parsing | Python `ast` module | Static analysis — no code execution |
| API validation | PyPI JSON API | Free, no auth, live package metadata |
| Backend | FastAPI | Async, fast, Pydantic-native |
| Output schema | Pydantic v2 | Strict typing guarantees on LLM output |
| Frontend | Vanilla HTML/JS | Zero build-tool dependencies |

## Running Locally

```bash
git clone --recurse-submodules https://github.com/mathew-felix/llm-code-validator
cd llm-code-validator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn api.main:app --reload
```
Open `frontend/index.html` in your browser.

If you already cloned the repo without submodules, run:

```bash
git submodule update --init --recursive
```

To run the thesis scan after the API key is configured:

```bash
venv/bin/python thesis_validation/run_on_thesis.py
```
