"""Runs every rule over a change."""

from __future__ import annotations

from .changes import FileChange
from .model import Report
from .rules.ci import check_ci
from .rules.code import check_code
from .rules.tests import check_tests


def check(changes: list[FileChange]) -> Report:
    report = Report()
    findings, unchecked = check_tests(changes)
    report.findings += findings
    report.unchecked += unchecked
    report.findings += check_code(changes)
    report.findings += check_ci(changes)
    return report
