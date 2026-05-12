# Security and AI Review

`llm-code-validator` is local-only by default. Normal checks parse Python files with `ast` and compare imports and calls with the bundled signature database. No API key is required, and no source code is sent to any external service.

Optional AI review is designed as an explicit opt-in workflow. It builds a minimized payload from imports, suspicious calls, and small snippets. Secret redaction runs before a payload is displayed or sent.

## Local-Only Operation

Use `--no-network` to prevent provider calls:

```bash
llm-code-validator check . --ai-review --no-network
```

Use `--show-ai-payload` to inspect the minimized, redacted payload:

```bash
llm-code-validator check . --ai-review --show-ai-payload
```

Use `--ai-audit-log` to write request metadata without storing source snippets:

```bash
llm-code-validator check . --ai-review --show-ai-payload --ai-audit-log audit.jsonl
```

## Organization Policy

Teams can add `llm-code-validator.json` or `.llm-code-validator.json`:

```json
{
  "policy": {
    "no_network": true,
    "allow_external_ai": false,
    "allowed_ai_providers": ["local"]
  }
}
```

This lets organizations require local-only behavior or restrict AI review to private endpoints.

## Private Rules

Use a private signature database without publishing internal rules:

```bash
llm-code-validator check . --signatures-path internal-library-signatures.json
```

Private rules use the same schema as `data/library_signatures.json`.
