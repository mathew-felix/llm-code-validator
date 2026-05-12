## Summary

- 

## Rule Changes

- [ ] New or changed production rules include `source_url` or `release_note`.
- [ ] New or changed rules include a benchmark or test case.
- [ ] `safe_fix` is used only for deterministic replacements covered by tests.
- [ ] `suggested_fix` or `no_fix` is used when migration needs user review.
- [ ] `data/library_signatures.json` and `llm_code_validator/library_signatures.json` are synced when public rules change.

## Verification

- [ ] `llm-code-validator validate-signatures --require-official-evidence`
- [ ] `pytest -q`
- [ ] Relevant benchmark command, if rules changed:

```bash
python -m llm_code_validator.benchmark --dataset validation_dataset/ai_stack_benchmark_cases.json
```
