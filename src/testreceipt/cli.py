"""Command line: `testreceipt check --base main`."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence

from . import __version__, census
from .changes import GitError, from_git, merge_base, resolve
from .check import check
from .model import Level, Report, Unchecked, Verdict
from .rules import TITLES

EXIT_ON = {
    "caught": {Verdict.CAUGHT},
    "suspicious": {Verdict.CAUGHT, Verdict.SUSPICIOUS},
    "never": set(),
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testreceipt",
        description="Check a change for weakened tests and test runs made to look green.",
    )
    parser.add_argument("--version", action="version", version=f"testreceipt {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("check", help="check the change from BASE to HEAD")
    run.add_argument("--repo", default=".", help="the git repository (default: .)")
    run.add_argument("--base", required=True, help="the branch or commit the change starts from")
    run.add_argument("--head", default="HEAD", help="the commit to check (default: HEAD)")
    run.add_argument(
        "--exact-base",
        action="store_true",
        help="compare with BASE itself, not with its merge base with HEAD",
    )
    run.add_argument("--json", action="store_true", help="print the report as JSON")
    run.add_argument(
        "--notes", action="store_true", help="also list notes, which never change the verdict"
    )
    run.add_argument(
        "--run",
        metavar="COMMAND",
        help="also run this pytest command at the base, the head, and the head's code with the "
        "base's tests, and use the results as evidence",
    )
    run.add_argument(
        "--fail-on",
        choices=sorted(EXIT_ON),
        default="caught",
        help="exit with status 1 on this verdict or worse (default: caught)",
    )
    return parser


def _text(report: Report, base: str, head: str, *, notes: bool) -> str:
    lines = [f"testreceipt {report.verdict.value}  {base[:12]}..{head[:12]}"]
    for f in report.sorted_findings():
        if f.level == Level.NOTE and not notes:
            continue
        where = f.path + (f":{f.line}" if f.line else "")
        test = f" [{f.test}]" if f.test else ""
        lines.append(
            f"  {f.level.value.upper():<10} {f.rule} {TITLES.get(f.rule, '')}: {where}{test}"
        )
        lines.append(f"             {f.message}")
    for u in report.unchecked:
        lines.append(f"  UNCHECKED  {u.path}: {u.reason}")
    return "\n".join(lines)


def _summary(run: census.Run) -> str:
    if run.exit_code is None:
        return f"did not run: {run.error}"
    counts = Counter(run.results.values())
    shown = ", ".join(f"{n} {outcome}" for outcome, n in sorted(counts.items()))
    return f"exit {run.exit_code}: {shown or 'no results'}"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        head = resolve(args.repo, args.head)
        base = resolve(args.repo, args.base)
        if not args.exact_base:
            base = merge_base(args.repo, base, head)
        changes = from_git(args.repo, base, head)
    except GitError as error:
        print(f"testreceipt: {error}", file=sys.stderr)
        return 2
    report = check(changes)
    runs: dict[str, object] = {}
    if args.run:
        taken = census.take(args.repo, base, head, changes, args.run)
        report.findings = census.findings(taken, report.findings)
        runs = {
            name: _summary(run)
            for name, run in (("base", taken.base), ("head", taken.head), ("cross", taken.cross))
            if run is not None
        }
        if taken.base.exit_code is None or taken.head.exit_code is None:
            report.unchecked.append(Unchecked("(runner)", taken.base.error or taken.head.error))
    if args.json:
        payload = {"base": base, "head": head, **report.to_dict(), "runs": runs}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_text(report, base, head, notes=args.notes))
        for name, summary in runs.items():
            print(f"  runner {name:<6} {summary}")
    return 1 if report.verdict in EXIT_ON[args.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
