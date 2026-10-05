"""Command line: `testreceipt check --base main` and `testreceipt claims --pr owner/repo#12`."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from . import __version__, census, receipt
from .changes import GitError, from_git, merge_base, resolve
from .check import check
from .ci import GitHubError, fetch_pr, parse_pr, token
from .model import Level, Report, Unchecked, Verdict
from .reconcile import reconcile
from .rules import TITLES

EXIT_ON = {
    "caught": {Verdict.CAUGHT},
    "suspicious": {Verdict.CAUGHT, Verdict.SUSPICIOUS},
    "never": set(),
}
CLAIMS_EXIT_ON = {
    "contradicted": {"CONTRADICTED"},
    "scoped": {"CONTRADICTED", "COUNT", "SCOPED"},
    "never": set(),
}
OUTCOMES = ("tests failed", "tests passed", "no test result", "no CI")


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
    run.add_argument("--markdown", action="store_true", help="print the receipt as Markdown")
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
    said = commands.add_parser(
        "claims", help="check what a pull request says about its tests against its CI"
    )
    source = said.add_mutually_exclusive_group(required=True)
    source.add_argument("--pr", help="owner/repo#123 or the pull request's URL")
    source.add_argument("--description", type=Path, help="a file with the description to check")
    said.add_argument(
        "--outcome",
        choices=OUTCOMES,
        help="with --description: what the tests did at the same commit",
    )
    said.add_argument(
        "--suite-total", type=int, help="how many tests the suite has, to settle 'N tests pass'"
    )
    said.add_argument(
        "--junit",
        type=Path,
        action="append",
        help="JUnit XML from the test run at the same commit: its results decide the outcome "
        "and its total settles 'N tests pass' (may be given more than once)",
    )
    said.add_argument("--json", action="store_true", help="print the result as JSON")
    said.add_argument("--markdown", action="store_true", help="print the receipt as Markdown")
    said.add_argument("--out", type=Path, help="also write the Markdown receipt to this file")
    said.add_argument("--base", help="also check the change from BASE to --head for weakened tests")
    said.add_argument("--repo", default=".", help="with --base: the git repository (default: .)")
    said.add_argument("--head", default="HEAD", help="with --base: the commit (default: HEAD)")
    said.add_argument(
        "--fail-on-changes",
        choices=sorted(EXIT_ON),
        default="caught",
        help="with --base: exit with status 1 on this change verdict or worse (default: caught)",
    )
    said.add_argument(
        "--fail-on",
        choices=sorted(CLAIMS_EXIT_ON),
        default="contradicted",
        help="exit with status 1 on these verdicts (default: contradicted)",
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
    given = list(sys.argv[1:] if argv is None else argv)
    if given[:1] == ["hook"]:
        from .hooks import main as hook_main

        return hook_main(given[1:])
    args = _parser().parse_args(given)
    if args.command == "claims":
        return _claims(args)
    return _check(args)


def _claims(args: argparse.Namespace) -> int:
    evidence = ""
    if args.pr:
        try:
            repo, number = parse_pr(args.pr)
            description, ci = fetch_pr(repo, number, token())
        except (ValueError, GitHubError) as error:
            print(f"testreceipt: {error}", file=sys.stderr)
            return 2
        outcome, evidence = ci.tests()
        where = f"{repo}#{number} at {ci.head[:12]}"
    else:
        if not args.outcome and not args.junit:
            print("testreceipt: --description needs --outcome or --junit", file=sys.stderr)
            return 2
        description = args.description.read_text(encoding="utf-8")
        outcome, where = args.outcome or "no test result", str(args.description)
    total = args.suite_total
    if args.junit:
        outcome, evidence, total = _from_junit(args.junit, total)
    result = reconcile(description, outcome, evidence, total)
    sections = [receipt.claims_section(result, where)]
    report: Report | None = None
    if args.base:
        try:
            head = resolve(args.repo, args.head)
            base = merge_base(args.repo, resolve(args.repo, args.base), head)
            report = check(from_git(args.repo, base, head))
        except GitError as error:
            print(f"testreceipt: {error}", file=sys.stderr)
            return 2
        sections.append(receipt.check_section(report, base, head))
    markdown = receipt.receipt(*sections)
    if args.out:
        args.out.write_text(markdown, encoding="utf-8")
    if args.json:
        payload = {"pull_request": where, "tests": outcome, **result.to_dict()}
        if report is not None:
            payload["changes"] = report.to_dict()
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif args.markdown:
        print(markdown)
    else:
        print(f"testreceipt {result.verdict}  {where}")
        print(f"  {result.message}")
        if result.evidence:
            print(f"  evidence: {result.evidence}")
        if report is not None:
            print(f"  changes: {report.verdict.value}")
    failed = result.verdict in CLAIMS_EXIT_ON[args.fail_on]
    if report is not None and report.verdict in EXIT_ON[args.fail_on_changes]:
        failed = True
    return 1 if failed else 0


def _from_junit(paths: list[Path], total: int | None) -> tuple[str, str, int | None]:
    """The outcome, evidence and test count of a run, from its JUnit XML."""
    results: dict[str, str] = {}
    for path in paths:
        found, _ = census.junit_results(path)
        results.update({f"{path}:{k}": v for k, v in found.items()})
    if not results:
        return "no test result", "", total
    failed = sorted(k for k, v in results.items() if v in {"failed", "error"})
    ran = [v for v in results.values() if v != "skipped"]
    count = total if total is not None else len(ran)
    if failed:
        name = failed[0].split(":", 1)[1]
        return "tests failed", f"{len(failed)} of {len(ran)} tests failed, e.g. {name}", count
    return "tests passed", f"{len(ran)} tests passed", count


def _check(args: argparse.Namespace) -> int:
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
    elif args.markdown:
        section = receipt.check_section(report, base, head, notes=args.notes)
        print(receipt.receipt(section))
    else:
        print(_text(report, base, head, notes=args.notes))
        for name, summary in runs.items():
            print(f"  runner {name:<6} {summary}")
    return 1 if report.verdict in EXIT_ON[args.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
