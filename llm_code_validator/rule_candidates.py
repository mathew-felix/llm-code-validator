from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateRule:
    library: str
    symbol: str
    current_version: str
    reason: str
    evidence: str
    replacement: str | None = None
    removed_in: str | None = None
    changed_in: str | None = None
    fix_safety: str = "suggested_fix"

    def to_json(self) -> str:
        entry: dict[str, object] = {
            "exists": False if self.removed_in else True,
            "reason": self.reason,
            "fix_safety": self.fix_safety,
            "source_url": self.evidence,
        }
        if self.removed_in:
            entry["removed_in"] = self.removed_in
        if self.changed_in:
            entry["changed_in"] = self.changed_in
        if self.replacement:
            entry["replacement"] = self.replacement
        payload = {
            self.library: {
                "current_version": self.current_version,
                "methods": {
                    self.symbol: entry,
                },
            },
        }
        return json.dumps(payload, indent=2, sort_keys=True)
