from __future__ import annotations

import pytest

from testreceipt.claims import claims, overall


@pytest.mark.parametrize(
    ("text", "kind", "count"),
    [
        ("All 101 tests pass with no regressions", "pass", 101),
        ("- All tests pass successfully", "pass", None),
        (
            "Verified all existing System.IO.Compression tests continue to pass"
            " (1327 tests, 0 failures)",
            "pass",
            1327,
        ),
        ("All tests are now passing.", "pass", None),
        ("pytest: 12 passed in 0.41s", "pass", 12),
        ("✅ `pytest -q`", "pass", None),
        ("- [x] Unit tests pass", "pass", None),
        ("所有测试全部通过", "pass", None),
        ("- `pytest -q` *(fails: 265 failed, 511 passed, 73 skipped, 18 errors)*", "fail", None),
        ("- ❌ `npm test`", "fail", None),
        ("Some tests are still failing on Windows", "fail", None),
    ],
)
def test_one_line(text: str, kind: str, count: int | None) -> None:
    found = claims(text)
    assert [(c.kind, c.count) for c in found] == [(kind, count)]


@pytest.mark.parametrize(
    "text",
    [
        "- [ ] My PR passes all unit tests on `make test-unit`",
        "Please make sure all tests pass before merging.",
        "This change should make the flaky tests pass.",
        "It also includes the changes needed to ensure that all tests pass.",
        "Added a test for the parser.",
        "<!-- - [x] tests pass -->",
        "Tests could not be run in this environment.",
    ],
)
def test_not_a_claim(text: str) -> None:
    assert [c for c in claims(text) if c.kind == "pass"] == []


def test_commands_listed_under_testing_imply_a_pass() -> None:
    body = "## Summary\n- add health checks\n\n## Testing\n- `ruff check`\n- `pytest -q`\n"
    found = claims(body)
    assert [(c.kind, c.explicit) for c in found] == [("pass", False)]
    assert overall(found) == "implied pass"


def test_commands_listed_elsewhere_are_not_claims() -> None:
    assert claims("## Usage\n- `pytest -q` runs the suite\n") == []


def test_overall() -> None:
    assert overall(claims("All tests pass.\n")) == "pass"
    assert overall(claims("## Testing\n- `pytest` *(fails: 2 failed)*\n")) == "fail"
    assert (
        overall(claims("All unit tests pass.\nIntegration tests fail without a database.\n"))
        == "mixed"
    )
    assert overall(claims("Refactor the parser.\n")) == "none"


@pytest.mark.parametrize(
    "text",
    [
        "- ✅ Added comprehensive unit test coverage",
        "- [x] Add tests to verify extended function signatures work correctly",
        "- [x] Unit Test",
        "- regenerate golden test outputs for passing programs",
        "- scale the metrics test batch axis with the number of devices so it passes everywhere",
        "- [x] Test the implementation compiles and builds successfully",
    ],
)
def test_work_done_is_not_a_test_run(text: str) -> None:
    assert [c for c in claims(text) if c.kind == "pass"] == []


def test_ticked_box_with_a_pass_verb() -> None:
    assert [c.kind for c in claims("- [x] Existing tests pass")] == ["pass"]
