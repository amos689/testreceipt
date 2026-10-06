from __future__ import annotations

from typing import Any

import pytest

from testreceipt import ci


def test_fetch_reads_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    head = "a" * 40
    statuses = [{"context": f"build/{i}", "state": "success"} for i in range(100)]
    statuses_page2 = [{"context": "ci/linux-test", "state": "failure"}]

    def fake_get(path: str, auth: str | None) -> Any:
        if path == "/repos/o/r/pulls/7":
            return {"body": "All tests pass.", "head": {"sha": head}}
        if path.startswith(f"/repos/o/r/commits/{head}/check-runs"):
            return {"check_runs": []}
        if path == f"/repos/o/r/commits/{head}/status?per_page=100&page=1":
            return {"statuses": statuses}
        if path == f"/repos/o/r/commits/{head}/status?per_page=100&page=2":
            return {"statuses": statuses_page2}
        raise AssertionError(path)

    monkeypatch.setattr(ci, "_get", fake_get)
    body, result = ci.fetch_pr("o/r", 7)
    assert body == "All tests pass."
    assert result.tests() == ("tests failed", "ci/linux-test")


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("owner/repo#12", ("owner/repo", 12)),
        ("https://github.com/owner/repo/pull/12", ("owner/repo", 12)),
    ],
)
def test_parse_pr(ref: str, expected: tuple[str, int]) -> None:
    assert ci.parse_pr(ref) == expected


def test_parse_pr_rejects_other_text() -> None:
    with pytest.raises(ValueError, match="not a pull request"):
        ci.parse_pr("owner/repo")
