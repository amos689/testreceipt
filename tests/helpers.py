from __future__ import annotations

from textwrap import dedent

from testreceipt.changes import FileChange
from testreceipt.check import check
from testreceipt.model import Report


def change(path: str, before: str | None, after: str | None) -> FileChange:
    return FileChange(
        path,
        dedent(before).lstrip("\n") if before is not None else None,
        dedent(after).lstrip("\n") if after is not None else None,
    )


def report(*changes: FileChange) -> Report:
    return check(list(changes))


def found(*changes: FileChange) -> list[tuple[str, str]]:
    """(rule, level) of every finding, sorted."""
    return sorted((f.rule, f.level.value) for f in report(*changes).findings)
