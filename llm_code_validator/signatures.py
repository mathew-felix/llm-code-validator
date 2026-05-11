from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SIGNATURE_PATH = Path(__file__).with_name("library_signatures.json")
REPO_SIGNATURE_PATH = REPO_ROOT / "data" / "library_signatures.json"
DEFAULT_SIGNATURE_PATH = PACKAGE_SIGNATURE_PATH if PACKAGE_SIGNATURE_PATH.exists() else REPO_SIGNATURE_PATH


@dataclass(frozen=True)
class SignatureRule:
    library: str
    symbol: str
    message: str
    version_assumption: str
    severity: str
    replacement: str | None
    fix_safety: str
    evidence: str
    match_names: tuple[str, ...]
    match_exact_only: bool = False
    required_keywords: tuple[str, ...] = ()


class SignatureValidationError(ValueError):
    pass


def _rule_from_entry(library: str, symbol: str, entry: dict[str, Any], current_version: str) -> SignatureRule | None:
    has_issue = not entry.get("exists", True) or "module_old" in entry or "changed_in" in entry
    if not has_issue:
        return None

    removed_or_changed = entry.get("removed_in") or entry.get("changed_in") or current_version
    version_assumption = f"{library}>={removed_or_changed}" if removed_or_changed else f"{library} current"
    reason = entry.get("reason") or entry.get("note") or entry.get("common_mistake") or "Known API drift pattern."
    replacement = entry.get("replacement") or entry.get("new_import") or entry.get("correct_usage") or entry.get("new_usage")
    safety = entry.get("fix_safety") or ("suggested_fix" if replacement else "no_fix")
    severity = "error" if not entry.get("exists", True) else "warning"
    evidence = entry.get("source_url") or entry.get("source_note") or entry.get("release_note")
    display_symbol = symbol
    if symbol in {"append", "mad"} and library == "pandas":
        display_symbol = f"DataFrame.{symbol}"

    exact_only = bool(entry.get("match_exact_only", False))
    configured_match_names = entry.get("match_names", [])
    old_import = entry.get("old_import")
    if exact_only and old_import and " import " in old_import:
        match_names = set(configured_match_names)
    elif exact_only and configured_match_names:
        match_names = set(configured_match_names)
    else:
        match_names = {symbol, symbol.split(".")[-1]}
    if old_import and " import " in old_import:
        import_line = old_import.splitlines()[0]
        module, name = import_line.removeprefix("from ").rsplit(" import ", 1)
        if not exact_only:
            match_names.add(name.strip())
        match_names.add(f"{module.strip()}.{name.strip()}")
    old_usage = entry.get("old_usage") or entry.get("old_import")
    if old_usage and not (exact_only and old_import and " import " in old_import):
        token = old_usage.split("(", 1)[0].split()[-1]
        match_names.add(token)
    for extra_name in configured_match_names:
        match_names.add(extra_name)

    qualified_symbol = display_symbol if display_symbol.startswith(f"{library}.") else f"{library}.{display_symbol}"

    return SignatureRule(
        library=library,
        symbol=display_symbol,
        message=f"{qualified_symbol} is incompatible with {version_assumption}: {reason}",
        version_assumption=version_assumption,
        severity=severity,
        replacement=replacement,
        fix_safety=safety,
        evidence=evidence or "",
        match_names=tuple(sorted(name for name in match_names if name)),
        match_exact_only=exact_only,
        required_keywords=tuple(sorted(entry.get("required_keywords", []))),
    )


@lru_cache(maxsize=1)
def load_signatures(path: str | None = None) -> dict[str, list[SignatureRule]]:
    signature_path = Path(path) if path else DEFAULT_SIGNATURE_PATH
    with signature_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    rules: dict[str, list[SignatureRule]] = {}
    for library, library_data in raw.items():
        current_version = library_data.get("current_version", "current")
        for symbol, entry in library_data.get("methods", {}).items():
            rule = _rule_from_entry(library, symbol, entry, current_version)
            if rule:
                rules.setdefault(library, []).append(rule)
    return rules


def validate_signature_database(path: str | None = None, require_official_evidence: bool = False) -> list[str]:
    signature_path = Path(path) if path else DEFAULT_SIGNATURE_PATH
    with signature_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for library, library_data in raw.items():
        if not isinstance(library_data, dict):
            errors.append(f"{library}: library entry must be an object")
            continue
        methods = library_data.get("methods")
        if not isinstance(methods, dict):
            errors.append(f"{library}: missing methods object")
            continue
        for symbol, entry in methods.items():
            key = (library, symbol)
            if key in seen:
                errors.append(f"{library}.{symbol}: duplicate rule")
            seen.add(key)
            if not isinstance(entry, dict):
                errors.append(f"{library}.{symbol}: rule must be an object")
                continue
            rule = _rule_from_entry(library, symbol, entry, library_data.get("current_version", "current"))
            if not rule:
                continue
            if not rule.evidence:
                errors.append(f"{library}.{symbol}: missing evidence")
            if require_official_evidence and rule.evidence and not (
                entry.get("source_url") or entry.get("release_note")
            ):
                errors.append(f"{library}.{symbol}: production rules require source_url or release_note")
            if rule.fix_safety == "safe_fix" and not rule.replacement:
                errors.append(f"{library}.{symbol}: safe_fix requires replacement")
            if rule.fix_safety not in {"safe_fix", "suggested_fix", "no_fix"}:
                errors.append(f"{library}.{symbol}: invalid fix safety {rule.fix_safety}")
    return errors


def find_rule(
    library: str,
    symbol: str,
    rules: dict[str, list[SignatureRule]] | None = None,
    keywords: set[str] | None = None,
) -> SignatureRule | None:
    rules = rules or load_signatures()
    keywords = keywords or set()
    attr = symbol.split(".")[-1]
    candidates = {symbol, attr}
    for rule in rules.get(library, []):
        if rule.required_keywords and not set(rule.required_keywords).intersection(keywords):
            continue
        rule_names = set(rule.match_names)
        if rule.match_exact_only and symbol in rule_names:
            return rule
        if not rule.match_exact_only and candidates.intersection(rule_names):
            return rule
    return None
