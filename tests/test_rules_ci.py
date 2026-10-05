from __future__ import annotations

from helpers import change, found

WORKFLOW = """
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ruff check
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e . pytest
      - name: Run tests
        run: pytest -q
"""
PATH = ".github/workflows/ci.yml"


def edited(old: str, new: str) -> list[tuple[str, str]]:
    assert old in WORKFLOW
    return found(change(PATH, WORKFLOW, WORKFLOW.replace(old, new)))


def test_failures_ignored() -> None:
    assert edited("run: pytest -q", "run: pytest -q || true") == [("TR401", "caught")]


def test_exit_zero() -> None:
    assert edited("run: pytest -q", "run: pytest -q; exit 0") == [("TR401", "caught")]


def test_continue_on_error_on_the_test_step() -> None:
    new = "run: pytest -q\n        continue-on-error: true"
    assert edited("run: pytest -q", new) == [("TR402", "caught")]


def test_continue_on_error_on_the_test_job() -> None:
    old = "  test:\n    runs-on: ubuntu-latest\n"
    new = "  test:\n    continue-on-error: true\n    runs-on: ubuntu-latest\n"
    assert edited(old, new) == [("TR402", "caught")]


def test_continue_on_error_on_lint_is_fine() -> None:
    assert edited("- run: ruff check", "- run: ruff check\n        continue-on-error: true") == []


def test_deselect() -> None:
    new = "run: pytest -q --deselect tests/test_api.py::test_login"
    assert edited("run: pytest -q", new) == [("TR403", "caught")]


def test_keyword_not() -> None:
    assert edited("run: pytest -q", 'run: pytest -q -k "not login"') == [("TR403", "caught")]


def test_ignore_is_suspicious() -> None:
    new = "run: pytest -q --ignore=tests/integration"
    assert edited("run: pytest -q", new) == [("TR403", "suspicious")]


def test_continued_command() -> None:
    new = "run: |\n          pytest -q \\\n            --deselect tests/test_api.py::test_login"
    assert edited("run: pytest -q", new) == [("TR403", "caught")]


def test_collect_only() -> None:
    assert edited("run: pytest -q", "run: pytest -q --collect-only") == [("TR405", "caught")]


def test_step_commented_out() -> None:
    findings = edited("        run: pytest -q", "        # run: pytest -q")
    assert ("TR405", "caught") in findings


def test_job_disabled() -> None:
    assert edited("  test:\n", "  test:\n    if: false\n") == [("TR405", "caught")]


def test_test_step_removed() -> None:
    old = "      - name: Run tests\n        run: pytest -q\n"
    assert edited(old, "") == [("TR405", "caught")]


def test_installing_pytest_is_not_running_it() -> None:
    assert edited("pip install -e . pytest", "pip install -e . pytest pytest-cov") == []


def test_other_tools_may_ignore_things() -> None:
    assert edited("run: ruff check", "run: flake8 --ignore=E501") == []


def test_adding_testreceipt_is_fine() -> None:
    new = "run: pytest -q\n      - run: testreceipt check --base origin/main"
    assert edited("run: pytest -q", new) == []


def test_removing_testreceipt_is_caught() -> None:
    with_guard = WORKFLOW + "      - run: testreceipt check --base origin/main\n"
    assert found(change(PATH, with_guard, WORKFLOW)) == [("TR406", "caught")]


def test_weakening_testreceipt_is_caught() -> None:
    with_guard = WORKFLOW + "      - run: testreceipt check --base origin/main\n"
    weakened = with_guard + "        continue-on-error: true\n"
    assert found(change(PATH, with_guard, weakened)) == [("TR406", "caught")]


def test_guard_config_changed() -> None:
    assert found(change(".testreceipt.toml", "x = 1\n", "x = 2\n")) == [("TR406", "caught")]


PYPROJECT = """
[project]
name = "calc"

[tool.pytest.ini_options]
testpaths = ["tests", "integration"]
addopts = "-ra"

[tool.coverage.report]
fail_under = 90
"""


def test_addopts_deselect() -> None:
    after = PYPROJECT.replace(
        'addopts = "-ra"', 'addopts = "-ra --deselect tests/test_a.py::test_x"'
    )
    assert found(change("pyproject.toml", PYPROJECT, after)) == [("TR403", "caught")]


def test_testpaths_narrowed() -> None:
    after = PYPROJECT.replace('testpaths = ["tests", "integration"]', 'testpaths = ["tests"]')
    assert found(change("pyproject.toml", PYPROJECT, after)) == [("TR403", "suspicious")]


def test_coverage_lowered() -> None:
    after = PYPROJECT.replace("fail_under = 90", "fail_under = 60")
    assert found(change("pyproject.toml", PYPROJECT, after)) == [("TR404", "caught")]


def test_coverage_raised_is_fine() -> None:
    after = PYPROJECT.replace("fail_under = 90", "fail_under = 95")
    assert found(change("pyproject.toml", PYPROJECT, after)) == []


def test_ruff_ignore_is_fine() -> None:
    after = PYPROJECT + '\n[tool.ruff.lint]\nignore = ["E501"]\n'
    assert found(change("pyproject.toml", PYPROJECT, after)) == []


def test_setup_cfg_addopts() -> None:
    before = "[tool:pytest]\naddopts = -ra\n"
    after = "[tool:pytest]\naddopts = -ra\n    -k 'not test_login'\n"
    assert found(change("setup.cfg", before, after)) == [("TR403", "caught")]


def test_tox_commands() -> None:
    before = "[testenv]\ncommands = pytest {posargs}\n"
    after = "[testenv]\ncommands = pytest {posargs} || true\n"
    assert found(change("tox.ini", before, after)) == [("TR401", "caught")]


def test_makefile_target() -> None:
    before = "test:\n\tpytest -q\n"
    after = "test:\n\t-pytest -q || true\n"
    assert found(change("Makefile", before, after)) == [("TR401", "caught")]


def test_new_workflow_is_only_suspicious() -> None:
    assert found(
        change(
            ".github/workflows/shots.yml",
            None,
            "jobs:\n  s:\n    steps:\n      - run: pytest || true\n",
        )
    ) == [("TR401", "suspicious")]


def test_ignoring_a_new_test_run_is_only_suspicious() -> None:
    before = "test:\n\tpython -m unittest\n"
    after = "test:\n\tpython -m unittest\n\tpytest tests/test_new.py || true\n"
    assert found(change("Makefile", before, after)) == [("TR401", "suspicious")]


def test_masking_that_was_already_there() -> None:
    before = "run: |\n  python run_tests.py || echo timed out\n"
    after = "run: |\n  pytest tests/ || echo failed\n"
    assert found(change(".github/workflows/t.yml", before, after)) == []
