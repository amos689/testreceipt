"""Command line: `testreceipt check --base main`."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .changes import GitError, from_git, merge_base, resolve
from .check import check
from .model import Level, Report, Verdict
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
    if args.json:
        payload = {"base": base, "head": head, **report.to_dict()}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_text(report, base, head, notes=args.notes))
    return 1 if report.verdict in EXIT_ON[args.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
