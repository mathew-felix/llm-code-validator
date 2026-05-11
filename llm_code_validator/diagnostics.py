from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Fix:
    replacement: str | None = None
    safety: str = "no_fix"

    def to_dict(self) -> dict[str, Any]:
        return {"replacement": self.replacement, "safety": self.safety}


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    column: int
    code: str
    severity: str
    library: str
    symbol: str
    message: str
    evidence: str | None = None
    replacement: str | None = None
    confidence: float = 1.0
    version_assumption: str | None = None
    fix: Fix = field(default_factory=Fix)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "severity": self.severity,
            "library": self.library,
            "symbol": self.symbol,
            "message": self.message,
            "evidence": self.evidence,
            "replacement": self.replacement,
            "confidence": self.confidence,
            "version_assumption": self.version_assumption,
            "fix": self.fix.to_dict(),
        }


@dataclass(frozen=True)
class CheckResult:
    checked_files: int
    diagnostics: list[Diagnostic] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_files": self.checked_files,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "warnings": list(self.warnings),
        }
