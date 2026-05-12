from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_NAMES = ("llm-code-validator.json", ".llm-code-validator.json")


@dataclass(frozen=True)
class PolicyConfig:
    no_network: bool = False
    allow_external_ai: bool = True
    allowed_ai_providers: tuple[str, ...] = ("openai", "anthropic", "azure-openai", "local")


@dataclass(frozen=True)
class AppConfig:
    policy: PolicyConfig = field(default_factory=PolicyConfig)


def discover_config(start: str | Path = ".") -> Path | None:
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        for name in DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None


def load_config(path: str | Path | None = None, *, start: str | Path = ".") -> AppConfig:
    config_path = Path(path) if path else discover_config(start)
    if not config_path:
        return AppConfig()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    policy = raw.get("policy", {}) if isinstance(raw, dict) else {}
    return AppConfig(
        policy=PolicyConfig(
            no_network=bool(policy.get("no_network", False)),
            allow_external_ai=bool(policy.get("allow_external_ai", True)),
            allowed_ai_providers=tuple(policy.get("allowed_ai_providers", PolicyConfig().allowed_ai_providers)),
        )
    )


def validate_provider_allowed(provider: str, config: AppConfig) -> None:
    if provider not in config.policy.allowed_ai_providers:
        raise RuntimeError(f"AI provider {provider!r} is not allowed by policy")
    if not config.policy.allow_external_ai and provider != "local":
        raise RuntimeError("external AI providers are disabled by policy")
