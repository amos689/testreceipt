"""What a check finds, and the verdict it adds up to."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Level(StrEnum):
    """How sure a finding is.

    CAUGHT needs hard evidence: a known cheating device, or a change that can only hide failures.
    SUSPICIOUS is a change of the right shape that a legitimate change of behaviour can explain too.
    NOTE is worth a reviewer's glance and never changes the verdict.
    """

    CAUGHT = "caught"
    SUSPICIOUS = "suspicious"
    NOTE = "note"


class Verdict(StrEnum):
    CAUGHT = "CAUGHT"
    SUSPICIOUS = "SUSPICIOUS"
    INCONCLUSIVE = "INCONCLUSIVE"
    CLEAN = "CLEAN"


@dataclass(frozen=True)
class Finding:
    rule: str
    level: Level
    path: str
    line: int | None
    message: str
    test: str | None = None


@dataclass(frozen=True)
class Unchecked:
    """A changed file the rules could not read, which keeps the verdict from being CLEAN."""

    path: str
    reason: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    unchecked: list[Unchecked] = field(default_factory=list)

    @property
    def verdict(self) -> Verdict:
        levels = {f.level for f in self.findings}
        if Level.CAUGHT in levels:
            return Verdict.CAUGHT
        if Level.SUSPICIOUS in levels:
            return Verdict.SUSPICIOUS
        if self.unchecked:
            return Verdict.INCONCLUSIVE
        return Verdict.CLEAN

    def sorted_findings(self) -> list[Finding]:
        order = {Level.CAUGHT: 0, Level.SUSPICIOUS: 1, Level.NOTE: 2}
        return sorted(self.findings, key=lambda f: (order[f.level], f.path, f.line or 0, f.rule))

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict.value,
            "findings": [
                {
                    "rule": f.rule,
                    "level": f.level.value,
                    "path": f.path,
                    "line": f.line,
                    "test": f.test,
                    "message": f.message,
                }
                for f in self.sorted_findings()
            ],
            "unchecked": [{"path": u.path, "reason": u.reason} for u in self.unchecked],
        }
