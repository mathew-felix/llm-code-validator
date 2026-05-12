from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from .core import EXCLUDED_DIR_NAMES, iter_python_files


SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}
SECRET_NAME_PARTS = {"secret", "secrets", "credential", "credentials", "token", "private-key"}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
]


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key_env: str | None
    endpoint: str | None = None

    @property
    def configured(self) -> bool:
        if self.provider == "local":
            return bool(self.endpoint)
        return bool(self.api_key_env and os.getenv(self.api_key_env))


def default_key_env(provider: str) -> str | None:
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    if provider == "azure-openai":
        return "AZURE_OPENAI_API_KEY"
    return None


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_redaction, redacted)
    return redacted


def _redaction(match: re.Match[str]) -> str:
    value = match.group(0)
    if value.lower().startswith("authorization:"):
        return f"{match.group(1)}[REDACTED]"
    if "=" in value:
        name = value.split("=", 1)[0].strip()
        return f"{name} = \"[REDACTED]\""
    return "[REDACTED]"


def is_secret_path(path: Path) -> bool:
    lowered = {part.lower() for part in path.parts}
    if lowered.intersection(EXCLUDED_DIR_NAMES):
        return True
    if path.name.lower() in SECRET_FILE_NAMES:
        return True
    return bool(lowered.intersection(SECRET_NAME_PARTS))


def _extract_relevant_lines(source: str, max_snippet_lines: int) -> list[str]:
    relevant: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("import ")
            or stripped.startswith("from ")
            or any(name in stripped.lower() for name in ("key", "secret", "token", "password", "authorization"))
            or "(" in stripped
            or "." in stripped
            or "@" in stripped
        ):
            relevant.append(line)
        if len(relevant) >= max_snippet_lines:
            break
    return relevant


def build_ai_payload(
    paths: list[str],
    *,
    max_snippet_lines: int = 30,
    redact: bool = True,
) -> dict[str, object]:
    files = []
    for file_path in iter_python_files(paths):
        if is_secret_path(file_path):
            continue
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        snippet = "\n".join(_extract_relevant_lines(source, max_snippet_lines))
        if redact:
            snippet = redact_secrets(snippet)
        files.append({"path": str(file_path), "snippet": snippet})
    return {
        "purpose": "advisory API-drift review",
        "files": files,
        "instructions": (
            "Review only the provided minimized snippets for stale third-party API usage. "
            "Return advisory findings and candidate rules; do not assume full program context."
        ),
    }


def render_ai_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def write_ai_audit_log(path: str | Path, provider: str, payload: dict[str, object]) -> None:
    files = payload.get("files", [])
    file_count = len(files) if isinstance(files, list) else 0
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "file_count": file_count,
        "payload_type": payload.get("purpose", "advisory API-drift review"),
        "contains_source_snippets": False,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def validate_ai_provider(config: ProviderConfig, no_network: bool) -> None:
    if no_network:
        raise RuntimeError("--no-network prevents AI review provider calls")
    if not config.configured:
        if config.provider == "local":
            raise RuntimeError("--ai-provider local requires --ai-endpoint")
        env_name = config.api_key_env or "provider API key environment variable"
        raise RuntimeError(f"--ai-review requires {env_name} to be set")
