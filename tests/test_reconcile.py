from __future__ import annotations

import pytest

from testreceipt.ci import Check, CiResult
from testreceipt.reconcile import reconcile


def test_ci_reads_steps_and_statuses_alike() -> None:
    passing = CiResult(
        "abc", [Check("build", "success", "github-actions", (("Run pytest", "success"),))]
    )
    assert passing.tests()[0] == "tests passed"
    failing = CiResult(
        "abc", [Check("build", "failure", "github-actions", (("Run pytest", "failure"),))]
    )
    assert failing.tests() == ("tests failed", "build › Run pytest")
    lint_only = CiResult(
        "abc", [Check("lint", "failure", "github-actions", (("Run ruff", "failure"),))]
    )
    assert lint_only.tests()[0] == "no test result"
    status = CiResult("abc", statuses=[("buildkite/app/linux-test", "failure")])
    assert status.tests()[0] == "tests failed"
    assert CiResult("abc").tests()[0] == "no CI"


@pytest.mark.parametrize(
    ("description", "outcome", "verdict"),
    [
        ("All existing tests pass.", "tests failed", "CONTRADICTED"),
        ("All existing tests pass.", "tests passed", "CONSISTENT"),
        ("All existing tests pass.", "no CI", "UNVERIFIED"),
        ("All 53 permission endpoint tests pass.", "tests failed", "SCOPED"),
        ("All 38 tests pass.", "tests failed", "COUNT"),
        ("## Testing\n- `pytest -q`\n", "tests failed", "UNSTATED"),
        ("## Testing\n- `pytest -q` *(fails: 3 failed)*\n", "tests failed", "REPORTS FAILURES"),
        ("Refactor the parser.", "tests failed", "NO CLAIM"),
    ],
)
def test_verdicts(description: str, outcome: str, verdict: str) -> None:
    assert reconcile(description, outcome).verdict == verdict


def test_suite_total_settles_a_count() -> None:
    assert reconcile("All 38 tests pass.", "tests failed", suite_total=38).verdict == "CONTRADICTED"
    result = reconcile("All 38 tests pass.", "tests failed", suite_total=400)
    assert result.verdict == "SCOPED"
    assert "38 of 400" in result.message


def test_claims_against_junit(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    from testreceipt.cli import main

    junit = tmp_path / "junit.xml"
    cases = "".join(f'<testcase classname="tests.test_a" name="test_{i}"/>' for i in range(39))
    cases += (
        '<testcase classname="tests.test_a" name="test_bad">'
        '<failure message="AssertionError"/></testcase>'
    )
    junit.write_text(f"<testsuites><testsuite>{cases}</testsuite></testsuites>", encoding="utf-8")
    description = tmp_path / "pr.md"
    description.write_text("## Testing\n- All 38 tests pass\n", encoding="utf-8")
    code = main(["claims", "--description", str(description), "--junit", str(junit)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("testreceipt SCOPED")
    assert "38 of 40 tests" in out
    description.write_text("All tests pass.\n", encoding="utf-8")
    assert main(["claims", "--description", str(description), "--junit", str(junit)]) == 1
