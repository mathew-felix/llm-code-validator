from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import check_file
from .diagnostics import Diagnostic
from .versioning import VersionContext


@dataclass(frozen=True)
class FixResult:
    path: str
    changed: bool
    previews: list[str]
    skipped: list[str]


def _line_replacement(line: str, diagnostic: Diagnostic) -> str | None:
    if diagnostic.fix.safety != "safe_fix" or not diagnostic.replacement:
        return None
    if line.lstrip().startswith("from ") and diagnostic.replacement.startswith("from "):
        indent = line[: len(line) - len(line.lstrip())]
        return indent + diagnostic.replacement
    if diagnostic.symbol in line:
        return line.replace(diagnostic.symbol, diagnostic.replacement, 1)
    old_token = diagnostic.symbol.split(".")[-1]
    if old_token not in line:
        return None
    return line.replace(old_token, diagnostic.replacement, 1)


def fix_file(path: str | Path, write: bool = False, version_context: VersionContext | None = None) -> FixResult:
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8")
    keep_final_newline = source.endswith("\n")
    lines = source.splitlines()
    result = check_file(file_path, version_context)
    previews: list[str] = []
    skipped: list[str] = []
    changed = False

    for diagnostic in result.diagnostics:
        if diagnostic.line < 1 or diagnostic.line > len(lines):
            skipped.append(f"{diagnostic.path}:{diagnostic.line} {diagnostic.code} cannot locate line")
            continue
        old_line = lines[diagnostic.line - 1]
        new_line = _line_replacement(old_line, diagnostic)
        if new_line is None:
            skipped.append(
                f"{diagnostic.path}:{diagnostic.line} {diagnostic.code} skipped "
                f"({diagnostic.fix.safety})"
            )
            continue
        previews.append(f"{diagnostic.path}:{diagnostic.line}\n  old: {old_line}\n  new: {new_line}")
        if write:
            lines[diagnostic.line - 1] = new_line
            changed = True

    if write and changed:
        updated = "\n".join(lines)
        if keep_final_newline:
            updated += "\n"
        file_path.write_text(updated, encoding="utf-8")

    return FixResult(str(file_path), changed, previews, skipped)
