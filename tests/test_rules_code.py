from __future__ import annotations

from helpers import change, found

MAKEREPORT = """
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        rep.outcome = "passed"
"""


def test_report_rewritten_in_conftest() -> None:
    assert found(change("tests/conftest.py", "", MAKEREPORT)) == [("TR201", "caught")]


def test_existing_device_is_not_reported_again() -> None:
    edited = MAKEREPORT + "\n\ndef pytest_configure(config):\n    pass\n"
    assert found(change("tests/conftest.py", MAKEREPORT, edited)) == []


def test_tests_never_called() -> None:
    hook = "def pytest_pyfunc_call(pyfuncitem):\n    return True\n"
    assert found(change("conftest.py", None, hook)) == [("TR201", "caught")]


def test_exit_status_overwritten() -> None:
    hook = "def pytest_sessionfinish(session, exitstatus):\n    session.exitstatus = 0\n"
    assert found(change("conftest.py", None, hook)) == [("TR203", "caught")]


def test_os_exit_in_test_code() -> None:
    hook = "import os\n\n\ndef pytest_sessionfinish(session):\n    os._exit(0)\n"
    assert found(change("conftest.py", "", hook)) == [("TR203", "caught")]


def test_sys_exit_success_in_a_test() -> None:
    before = "def test_a():\n    assert f() == 1\n"
    after = "import sys\n\n\ndef test_a():\n    sys.exit(0)\n    assert f() == 1\n"
    assert ("TR203", "caught") in found(change("tests/test_a.py", before, after))


def test_expected_exits_are_fine() -> None:
    after = (
        "import sys\nimport pytest\n\n\ndef test_cli():\n"
        "    with pytest.raises(SystemExit):\n        sys.exit(0)\n\n\n"
        "if __name__ == '__main__':\n    sys.exit(pytest.main())\n"
    )
    assert found(change("tests/test_cli.py", None, after)) == []


def test_exit_with_failure_status_inside_a_test_is_fine() -> None:
    after = (
        "import sys\n\n\ndef test_handler():\n    def boom():\n        sys.exit(2)\n"
        "    assert run(boom) == 2\n"
    )
    assert found(change("tests/test_cli.py", None, after)) == []


def test_collection_narrowed() -> None:
    hook = (
        "def pytest_collection_modifyitems(config, items):\n"
        "    items[:] = [i for i in items if 'slow' not in i.name]\n"
    )
    assert found(change("conftest.py", None, hook)) == [("TR202", "suspicious")]


def test_collect_ignore_grows() -> None:
    before = "collect_ignore = ['setup.py']\n"
    after = "collect_ignore = ['setup.py', 'tests/test_parser.py']\n"
    assert found(change("conftest.py", before, after)) == [("TR202", "suspicious")]


def test_eq_always_true() -> None:
    before = "class Result:\n    def __init__(self, v):\n        self.v = v\n"
    after = before + "\n    def __eq__(self, other):\n        return True\n"
    assert found(change("src/app/result.py", before, after)) == [("TR301", "caught")]


def test_pytest_detected_in_production_code() -> None:
    before = "def total(xs):\n    return sum(xs)\n"
    after = (
        "import sys\n\n\ndef total(xs):\n    if 'pytest' in sys.modules:\n"
        "        return 42\n    return sum(xs)\n"
    )
    assert found(change("src/app/calc.py", before, after)) == [("TR302", "caught")]


def test_pytest_env_in_production_code() -> None:
    after = "import os\n\nFAKE = bool(os.environ.get('PYTEST_CURRENT_TEST'))\n"
    assert found(change("app/calc.py", "", after)) == [("TR302", "caught")]


def test_production_reads_test_files() -> None:
    after = "def expected():\n    return open('tests/fixtures/out.json').read()\n"
    assert found(change("src/app/io.py", "", after)) == [("TR303", "suspicious")]


def test_test_mode_switch() -> None:
    after = (
        "import os\n\n\ndef rate():\n    if os.getenv('TESTING'):\n        return 0\n    return 5\n"
    )
    assert found(change("src/app/rate.py", "", after)) == [("TR304", "suspicious")]


def test_lower_case_attributes_are_not_switches() -> None:
    after = "def run(args):\n    if args.test:\n        return 0\n    return 5\n"
    assert found(change("src/app/cli.py", "", after)) == []


def test_os_exit_in_production_code() -> None:
    after = "import os\n\n\ndef main():\n    os._exit(0)\n"
    assert found(change("src/app/main.py", "", after)) == [("TR203", "suspicious")]


def test_docs_and_examples_are_not_production() -> None:
    after = "import sys\n\nif 'pytest' in sys.modules:\n    pass\n"
    assert found(change("docs/conf.py", "", after)) == []


def test_docstrings_mentioning_tests_are_fine() -> None:
    after = '"""Writes fixtures into tests/fixtures/ for the test suite."""\n\nX = 1\n'
    assert found(change("src/app/fixtures.py", "", after)) == []


def test_tooling_is_not_production() -> None:
    after = "def run():\n    return open('tests/data/a.json')\n"
    assert found(change("evals/run.py", "", after)) == []


def test_help_text_naming_a_test_file_is_fine() -> None:
    after = "def hint():\n    return 'run `python test_video.py` for a full report'\n"
    assert found(change("src/app/hints.py", "", after)) == []


def test_scripts_under_tests_may_exit() -> None:
    script = (
        "import sys\n\n\ndef main():\n    if missing():\n        sys.exit()\n\n\n"
        "if __name__ == '__main__':\n    main()\n"
    )
    assert found(change("tests/data/tool.py", None, script)) == []
    assert found(change(".github/scripts/run_examples_integration_test.py", None, script)) == []


def test_test_harness_modules_may_detect_pytest() -> None:
    after = "import os\n\nRUNNING = os.environ.get('PYTEST_CURRENT_TEST')\n"
    assert found(change("reflex/testing.py", "", after)) == []
    assert found(change("src/_pytest/tmpdir.py", "", after)) == []
    assert found(change("src/pytest_timeout.py", "", after)) == []
