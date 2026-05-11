# Rule Evidence and Review

Every diagnostic-producing rule in `data/library_signatures.json` must explain why the API is stale.

Accepted evidence, in priority order:

1. Official release notes or migration guides.
2. Official API documentation.
3. Maintainer issue or discussion when official docs are unavailable.

Do not use blog posts, Stack Overflow answers, or generic notes for production rules.

Run strict validation before release:

```bash
llm-code-validator validate-signatures --require-official-evidence
```

Use `safe_fix` only when all of these are true:

- The replacement is deterministic.
- The behavior is officially supported.
- Tests cover the replacement.

Use `suggested_fix` when the migration requires review. Use `no_fix` when no mechanical replacement is safe.

## Missed API Workflow

When the benchmark or a user report finds stale API usage that was missed:

1. Add a failing labeled benchmark case that reproduces the miss.
2. Classify the root cause:
   - missing rule
   - alias tracking gap
   - constructor tracking gap
   - dynamic import
   - wrapper function
   - unsupported syntax
3. If the root cause is a missing rule, add an entry to `data/library_signatures.json`.
4. Add official evidence with `source_url` or `release_note`.
5. Mark the fix safety:
   - `safe_fix` only for deterministic direct renames or import-path replacements with tests
   - `suggested_fix` for migrations requiring review
   - `no_fix` when no mechanical replacement is safe
6. Run:

```bash
llm-code-validator validate-signatures
pytest -q
python -m llm_code_validator.benchmark --dataset validation_dataset/ai_stack_benchmark_cases.json
```
