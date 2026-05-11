# Accuracy Notes

This project keeps the public accuracy notes limited to curated benchmark data.

## Labeled Benchmarks

The labeled benchmark files are curated test cases with known expected diagnostics:

```text
validation_dataset/cli_benchmark_cases.json
validation_dataset/ai_stack_benchmark_cases.json
```

Current saved results:

- CLI dataset: precision `1.0`, recall `1.0`
- AI-stack dataset: precision `1.0`, recall `1.0`

These results measure the current rule set against the included labeled cases. They do not claim broad accuracy across all Python projects.

## External Repository Scans

External repository scans were used during development to find noisy rules and scanner edge cases.

- 40 repositories configured
- 39 repositories scanned
- 2,073 Python files scanned
- 121 candidate diagnostics

Raw external scan output is not part of the public release docs because those findings require dependency and source-context review before being treated as confirmed.
