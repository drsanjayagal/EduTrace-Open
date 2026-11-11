"""Result types shared across validators."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from edutrace.exceptions import ValidationError


@dataclass
class CheckResult:
    """The outcome of one validation check."""

    name: str
    status: str  # "pass" | "fail" | "skip"
    message: str
    severity: str = "error"  # "info" | "warning" | "error"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Collection of :class:`CheckResult` items from one run."""

    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    def extend(self, results: list[CheckResult]) -> None:
        self.results.extend(results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == "fail"]

    @property
    def skipped(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == "skip"]

    @property
    def passed(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == "pass"]

    @property
    def ok(self) -> bool:
        return not self.failures

    def raise_if_failed(self) -> None:
        if self.failures:
            summary = "; ".join(f"{r.name}: {r.message}" for r in self.failures[:5])
            raise ValidationError(
                f"{len(self.failures)} validation check(s) failed: {summary}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": len(self.results),
            "passed": len(self.passed),
            "failed": len(self.failures),
            "skipped": len(self.skipped),
            "results": [r.to_dict() for r in self.results],
        }

    def write_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return p
