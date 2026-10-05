"""The files a change touches, with their text before and after."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath

# Files larger than this are not read: rules work on source code and configuration, not data.
MAX_BYTES = 2_000_000

TEST_DIRS = frozenset({"test", "tests", "testing"})
# Top-level directories of tooling and documentation, not of the code under test.
NOT_PRODUCTION = frozenset(
    {
        "docs",
        "doc",
        "examples",
        "example",
        "benchmarks",
        "bench",
        "scripts",
        "tools",
        "evals",
        "ci",
        "dev",
        ".github",
    }
)


@dataclass(frozen=True)
class FileChange:
    path: str
    before: str | None  # None when the change adds the file
    after: str | None  # None when the change deletes the file
    old_path: str | None = None  # the path before a rename

    @property
    def before_path(self) -> str:
        return self.old_path or self.path


def is_python(path: str) -> bool:
    return path.endswith((".py", ".pyi"))


def is_conftest(path: str) -> bool:
    return PurePosixPath(path).name == "conftest.py"


def is_test_file(path: str) -> bool:
    """A Python file that holds tests or test helpers, by pytest's and common layouts."""
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    name = p.name
    if name.startswith("test_") or name.endswith("_test.py") or name in {"tests.py", "test.py"}:
        return True
    return any(part in TEST_DIRS for part in p.parts[:-1])


def is_test_support(path: str) -> bool:
    """A module of a test framework or test harness the project ships, such as `pkg/testing.py`,
    a pytest plugin, or pytest itself: handling the test run is its job."""
    p = PurePosixPath(path)
    if p.stem in {"testing", "pytest_plugin", "testutils", "test_utils", "testing_utils"}:
        return True
    return p.stem.startswith("pytest_") or any(
        part == "_pytest" or part.startswith("pytest_") for part in p.parts[:-1]
    )


def is_production_python(path: str) -> bool:
    p = PurePosixPath(path)
    if not is_python(path) or is_test_file(path) or is_conftest(path):
        return False
    if p.name in {"setup.py", "noxfile.py", "conftest.py"}:
        return False
    top = p.parts[0] if len(p.parts) > 1 else ""
    return top not in NOT_PRODUCTION


class GitError(RuntimeError):
    pass


def _git(repo: str, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, check=False)
    if result.returncode != 0:
        raise GitError(result.stderr.decode("utf-8", "replace").strip() or f"git {args[0]} failed")
    return result.stdout


def _read(repo: str, rev: str, path: str) -> str | None:
    """The file's text at a revision; None when it is binary or too large."""
    size = int(_git(repo, "cat-file", "-s", f"{rev}:{path}").strip() or 0)
    if size > MAX_BYTES:
        return None
    data = _git(repo, "show", f"{rev}:{path}")
    if b"\0" in data[:8000]:
        return None
    return data.decode("utf-8", "replace")


def merge_base(repo: str, base: str, head: str) -> str:
    return _git(repo, "merge-base", base, head).decode().strip()


def resolve(repo: str, rev: str) -> str:
    return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()


def from_git(repo: str, base: str, head: str) -> list[FileChange]:
    """The changes from `base` to `head`, both commits of the repository at `repo`."""
    out = _git(repo, "diff", "--name-status", "-z", "-M", base, head)
    fields = out.decode("utf-8", "replace").split("\0")
    changes: list[FileChange] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        if status.startswith(("R", "C")):
            old, new = fields[i + 1], fields[i + 2]
            i += 3
        else:
            old = new = fields[i + 1]
            i += 2
        kind = status[0]
        if kind == "C":  # a copy leaves its source in place: the new file is simply added
            kind, old = "A", new
        before = after = None
        if kind != "A":
            before = _read(repo, base, old)
            if before is None:
                continue
        if kind != "D":
            after = _read(repo, head, new)
            if after is None:
                continue
        changes.append(
            FileChange(path=new, before=before, after=after, old_path=old if old != new else None)
        )
    return changes
