from __future__ import annotations

import json

from .diagnostics import CheckResult


def format_text(result: CheckResult) -> str:
    lines: list[str] = []
    for diagnostic in result.diagnostics:
        qualified_symbol = (
            diagnostic.symbol
            if diagnostic.symbol.startswith(f"{diagnostic.library}.")
            else f"{diagnostic.library}.{diagnostic.symbol}"
        )
        lines.append(
            f"{diagnostic.path}:{diagnostic.line} {diagnostic.code} "
            f"{diagnostic.severity} {qualified_symbol} {diagnostic.message}"
        )
        if diagnostic.version_assumption:
            lines.append(f"  version: {diagnostic.version_assumption}")
        if diagnostic.replacement:
            lines.append(f"  fix: {diagnostic.replacement}")
    if not result.diagnostics:
        lines.append(f"OK: checked {result.checked_files} file(s), no diagnostics")
    for warning in result.warnings:
        lines.append(f"warning: {warning}")
    return "\n".join(lines)


def format_json(result: CheckResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)


def format_github(result: CheckResult) -> str:
    lines: list[str] = []
    for diagnostic in result.diagnostics:
        message = diagnostic.message.replace("\n", " ")
        lines.append(
            f"::{diagnostic.severity} file={diagnostic.path},line={diagnostic.line},"
            f"col={diagnostic.column},title={diagnostic.code}::{message}"
        )
    return "\n".join(lines)
