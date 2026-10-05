"""Runner truth: one test command on clean checkouts of the base, the head, and a cross of both.

The cross checkout is the head's code with the base's test files. A test that passes at the base,
fails on the head's code, and was then removed, skipped or loosened at the head was changed to fit
the new code: that is the evidence that turns a suspicious test change into a caught one.

Results come from JUnit XML, which pytest writes with `--junitxml` and most other runners can too.
"""

from __future__ import annotations

import contextlib
import os
import shlex
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .changes import FileChange, is_conftest, is_test_file
from .model import Finding, Level

# Rules whose suspicious findings become caught when the runner shows the test failing on the new
# code: the test was removed, skipped or loosened because the change broke it.
# A changed expected value (TR105) is how a deliberate change of behaviour updates its tests, so it
# is not upgraded; neither is a failure that is not an assertion, such as a removed API's
# AttributeError.
UPGRADABLE = frozenset({"TR102", "TR104", "TR106", "TR110", "TR111", "TR112"})


@dataclass
class Run:
    exit_code: int | None  # None when the command could not start or timed out
    results: dict[str, str] = field(default_factory=dict)  # test ID -> outcome
    error: str = ""
    assertion_failures: set[str] = field(default_factory=set)  # failed on an assertion

    def failing(self) -> set[str]:
        return {t for t, outcome in self.results.items() if outcome in {"failed", "error"}}


@dataclass
class Census:
    base: Run
    head: Run
    cross: Run | None

    def removed(self) -> list[str]:
        """Tests that ran at the base and no longer exist at the head."""
        return sorted(
            t for t, o in self.base.results.items() if o != "skipped" and t not in self.head.results
        )

    def newly_skipped(self) -> list[str]:
        return sorted(
            t
            for t, o in self.head.results.items()
            if o == "skipped" and self.base.results.get(t) in {"passed", "failed", "error"}
        )

    def broken_by_change(self) -> set[str]:
        """Tests that pass at the base but fail on the head's code (from the cross run)."""
        if self.cross is None:
            return set()
        failed = self.cross.assertion_failures
        return {t for t in failed if self.base.results.get(t) == "passed"}


def junit_results(path: Path) -> tuple[dict[str, str], set[str]]:
    """Test ID ("tests/test_x.py::TestY::test_z") -> "passed", "failed", "error" or "skipped",
    and the IDs of the tests that failed on an assertion."""
    results: dict[str, str] = {}
    assertions: set[str] = set()
    if not path.exists():
        return results, assertions
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        test_id = junit_id(case.get("classname", ""), case.get("name", ""))
        outcome = "passed"
        for child in case:
            if child.tag in {"failure", "error"}:
                outcome = "failed" if child.tag == "failure" else "error"
                message = (child.get("message") or "") + " " + (child.get("type") or "")
                if child.tag == "failure" and (
                    "AssertionError" in message or message.lstrip().startswith("assert")
                ):
                    assertions.add(test_id)
            elif child.tag == "skipped":
                outcome = "skipped"
        results[test_id] = outcome
    return results, assertions


def junit_id(classname: str, name: str) -> str:
    """pytest's node ID from JUnit's classname and name, without parameters."""
    parts = [p for p in classname.split(".") if p]
    classes: list[str] = []
    while parts and parts[-1][:1].isupper():
        classes.insert(0, parts.pop())
    module = "/".join(parts) + ".py" if parts else ""
    function = name.split("[", 1)[0]
    return "::".join([module, *classes, function]) if module else "::".join([*classes, function])


def static_id(path: str, test: str) -> str:
    return f"{PurePosixPath(path)}::{test}"


def _git(repo: str, *args: str) -> None:
    subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True)


@contextlib.contextmanager
def _worktree(repo: str, sha: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="testreceipt-") as tmp:
        target = Path(tmp) / "tree"
        _git(repo, "worktree", "add", "--detach", "--quiet", str(target), sha)
        try:
            yield target
        finally:
            subprocess.run(
                ["git", "-C", repo, "worktree", "remove", "--force", str(target)],
                capture_output=True,
                check=False,
            )


def split_command(command: str) -> list[str]:
    """A command line as arguments; on Windows, backslashes in paths are kept."""
    if os.name != "nt":
        return shlex.split(command)
    return [
        token[1:-1] if len(token) > 1 and token[0] == token[-1] and token[0] in "\"'" else token
        for token in shlex.split(command, posix=False)
    ]


def _environment(directory: Path) -> dict[str, str]:
    """The environment with the checkout's own code first on the import path.

    In CI the project is usually installed from the main checkout, so without this the base and
    cross runs would import the head's code instead of their own.
    """
    env = dict(os.environ)
    paths = [str(directory / "src")] if (directory / "src").is_dir() else []
    paths.append(str(directory))
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _run(directory: Path, command: str, timeout: int) -> Run:
    junit = directory.parent / "junit.xml"
    # each run gets its own temporary directory: runs must not share pytest's, which may also be
    # unwritable for the CI user
    args = [
        *split_command(command),
        f"--junitxml={junit}",
        f"--basetemp={directory.parent / 'basetemp'}",
        "-p",
        "no:cacheprovider",
    ]
    try:
        completed = subprocess.run(
            args,
            cwd=directory,
            env=_environment(directory),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Run(None, error=str(error))
    try:
        results, assertions = junit_results(junit)
    except ET.ParseError as error:
        return Run(completed.returncode, error=f"unreadable JUnit XML: {error}")
    tail = completed.stdout.strip().splitlines()[-1:] if not results else []
    return Run(completed.returncode, results, tail[0] if tail else "", assertions)


def take(
    repo: str, base: str, head: str, changes: list[FileChange], command: str, timeout: int = 1800
) -> Census:
    """Runs `command` (a pytest command line) at the base, the head and the cross checkout."""
    with _worktree(repo, base) as tree:
        base_run = _run(tree, command, timeout)
    with _worktree(repo, head) as tree:
        head_run = _run(tree, command, timeout)
    test_files = [
        c
        for c in changes
        if is_test_file(c.path) or is_conftest(c.path) or (c.old_path and is_test_file(c.old_path))
    ]
    cross_run = None
    if test_files:
        with _worktree(repo, head) as tree:
            for change in test_files:
                if change.after is not None:
                    (tree / change.path).unlink(missing_ok=True)
                if change.before is not None:
                    target = tree / change.before_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(change.before.encode("utf-8"))
            cross_run = _run(tree, command, timeout)
    return Census(base_run, head_run, cross_run)


def findings(census: Census, static: list[Finding]) -> list[Finding]:
    """Findings from the runner, and static findings upgraded by it."""
    out: list[Finding] = []
    broken = census.broken_by_change()
    upgraded: set[int] = set()
    for i, f in enumerate(static):
        if f.level != Level.SUSPICIOUS or f.rule not in UPGRADABLE:
            continue
        hit = _broken_tests_of(f, broken)
        if hit:
            upgraded.add(i)
            out.append(
                Finding(
                    f.rule,
                    Level.CAUGHT,
                    f.path,
                    f.line,
                    f"{f.message}; the runner shows {_names(hit)} passing before the change and "
                    "failing on the new code, so the test was changed to fit the code",
                    f.test,
                )
            )
    out += [f for i, f in enumerate(static) if i not in upgraded]
    removed = census.removed()
    # removals the static rules already report get the runner's word added, not a second finding
    static_files = {f"{PurePosixPath(f.path)}::" for f in out if f.rule == "TR110"}
    for i, f in enumerate(out):
        if f.rule != "TR110" or f.level != Level.SUSPICIOUS:
            continue
        mine = [t for t in removed if t.startswith(f"{PurePosixPath(f.path)}::")]
        still = [t for t in mine if census.cross and census.cross.results.get(t) == "passed"]
        if still:
            note = f"; the runner shows {_names(still)} still passing on the new code"
            out[i] = Finding(f.rule, f.level, f.path, f.line, f.message + note, f.test)
    unreported = [t for t in removed if not any(t.startswith(prefix) for prefix in static_files)]
    if unreported:
        out.append(
            Finding(
                "TR110",
                Level.SUSPICIOUS,
                "(runner)",
                None,
                f"{len(unreported)} tests no longer run: {_names(unreported)}",
            )
        )
    skipped = census.newly_skipped()
    if skipped:
        out.append(
            Finding(
                "TR111",
                Level.SUSPICIOUS,
                "(runner)",
                None,
                f"{len(skipped)} tests now skipped: {_names(skipped)}",
            )
        )
    return out


def _broken_tests_of(finding: Finding, broken: set[str]) -> list[str]:
    if finding.test:
        wanted = static_id(finding.path, finding.test)
        return [t for t in broken if t == wanted]
    # a file-level finding, such as removed tests: any broken test in that file
    prefix = f"{PurePosixPath(finding.path)}::"
    return sorted(t for t in broken if t.startswith(prefix))


def _names(tests: list[str], limit: int = 3) -> str:
    shown = ", ".join(f"`{t}`" for t in tests[:limit])
    return shown + (f" and {len(tests) - limit} more" if len(tests) > limit else "")
