"""The receipt as Markdown, for a pull request comment or a job summary."""

from __future__ import annotations

from . import __version__
from .model import Level, Report
from .reconcile import Reconciled
from .rules import TITLES

ICONS = {
    "CONTRADICTED": "🔴",
    "SCOPED": "🟠",
    "COUNT": "🟠",
    "UNSTATED": "🟡",
    "UNVERIFIED": "🟡",
    "CONSISTENT": "🟢",
    "REPORTS FAILURES": "🟢",
    "NO CLAIM": "⚪",
    "CAUGHT": "🔴",
    "SUSPICIOUS": "🟠",
    "INCONCLUSIVE": "🟡",
    "CLEAN": "🟢",
}


def _cell(text: str, limit: int = 160) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def claims_section(result: Reconciled, where: str) -> str:
    lines = [
        f"**What the description says about the tests: {ICONS.get(result.verdict, '')} "
        f"{result.verdict}**",
        "",
        result.message[:1].upper() + result.message[1:] + ".",
    ]
    if result.evidence:
        lines += ["", f"Evidence: `{_cell(result.evidence, 120)}` ({_cell(where, 80)})"]
    return "\n".join(lines)


def check_section(report: Report, base: str, head: str, *, notes: bool = False) -> str:
    verdict = report.verdict.value
    shown = [f for f in report.sorted_findings() if notes or f.level != Level.NOTE]
    lines = [
        f"**What the change does to the tests: {ICONS.get(verdict, '')} {verdict}** "
        f"(`{base[:7]}..{head[:7]}`)",
    ]
    if shown:
        lines += ["", "| Level | Rule | Where | What |", "|---|---|---|---|"]
        for f in shown:
            where = f.path + (f":{f.line}" if f.line else "") + (f" `{f.test}`" if f.test else "")
            rule = f"{f.rule} {TITLES.get(f.rule, '')}"
            lines.append(f"| {f.level.value} | {rule} | {_cell(where, 80)} | {_cell(f.message)} |")
    else:
        lines += ["", "No test was removed, skipped or weakened."]
    for u in report.unchecked:
        lines.append(f"\nNot checked: `{u.path}` ({_cell(u.reason, 100)})")
    return "\n".join(lines)


def receipt(*sections: str) -> str:
    body = "\n\n".join(s for s in sections if s)
    footer = (
        f"<sub>testreceipt {__version__}: fixed rules, no model; "
        "caught means hard evidence, suspicious means worth a look.</sub>"
    )
    return f"### 🧾 testreceipt\n\n{body}\n\n{footer}\n"
