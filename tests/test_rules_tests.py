from __future__ import annotations

import pytest

from helpers import change, found, report
from testreceipt.model import Verdict

PATH = "tests/test_calc.py"

BEFORE = """
import pytest
from calc import add, compute


def test_add():
    result = add(1, 2)
    assert result == 3


def test_other():
    assert add(0, 0) == 0
"""


def after(test_add: str) -> str:
    return (
        "import pytest\nfrom calc import add, compute\n\n\n"
        + test_add.strip("\n")
        + "\n\n\ndef test_other():\n    assert add(0, 0) == 0\n"
    )


@pytest.mark.parametrize(
    ("new_test", "expected"),
    [
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n",
            [("TR101", "caught")],
            id="assertion-deleted",
        ),
        pytest.param("def test_add():\n    pass\n", [("TR101", "caught")], id="emptied"),
        pytest.param(
            "def test_add():\n    '''Adds.'''\n    ...\n", [("TR101", "caught")], id="ellipsis"
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert True\n",
            [("TR101", "caught")],
            id="always-true",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert result == result\n",
            [("TR101", "caught")],
            id="reflexive",
        ),
        pytest.param(
            "def test_add():\n    return\n    result = add(1, 2)\n    assert result == 3\n",
            [("TR101", "caught")],
            id="early-return",
        ),
        pytest.param(
            "def test_add():\n    check_sum(add(1, 2), 3)\n",
            [("TR102", "note")],
            id="moved-into-helper",
        ),
        pytest.param(
            "@pytest.mark.skip(reason='flaky')\n"
            "def test_add():\n    result = add(1, 2)\n    assert result == 3\n",
            [("TR111", "caught")],
            id="skip",
        ),
        pytest.param(
            "@pytest.mark.xfail\ndef test_add():\n    result = add(1, 2)\n    assert result == 3\n",
            [("TR111", "caught")],
            id="xfail",
        ),
        pytest.param(
            "@pytest.mark.skipif(True, reason='later')\n"
            "def test_add():\n    result = add(1, 2)\n    assert result == 3\n",
            [("TR111", "caught")],
            id="skipif-true",
        ),
        pytest.param(
            "@pytest.mark.skipif(sys.platform == 'win32', reason='posix')\n"
            "def test_add():\n    result = add(1, 2)\n    assert result == 3\n",
            [("TR111", "suspicious")],
            id="skipif-condition",
        ),
        pytest.param(
            "def test_add():\n    pytest.skip('broken')\n    result = add(1, 2)\n"
            "    assert result == 3\n",
            [("TR111", "caught")],
            id="skip-call",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert result is not None\n",
            [("TR104", "suspicious")],
            id="weakened",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert result\n",
            [("TR104", "suspicious")],
            id="truthiness",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert result == 4\n",
            [("TR105", "note")],
            id="expected-changed",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    try:\n        assert result == 3\n"
            "    except AssertionError:\n        pass\n",
            [("TR103", "caught")],
            id="swallowed",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)\n    assert result == 3\n"
            "    assert result > 0\n",
            [],
            id="assertion-added",
        ),
        pytest.param(
            "def test_add():\n    result = add(1, 2)  # one plus two\n\n    assert result == 3\n",
            [],
            id="formatting-only",
        ),
    ],
)
def test_one_test_changed(new_test: str, expected: list[tuple[str, str]]) -> None:
    assert found(change(PATH, BEFORE, after(new_test))) == expected


def test_hardcoded_expected_value() -> None:
    before = "def test_add():\n    assert add(2, 2) == compute(2)\n"
    after_ = "def test_add():\n    assert add(2, 2) == 4\n"
    assert found(change(PATH, before, after_)) == [("TR105", "suspicious")]


def test_tolerance_loosened() -> None:
    before = "def test_mean():\n    assert mean(xs) == pytest.approx(1.5)\n"
    after_ = "def test_mean():\n    assert mean(xs) == pytest.approx(1.5, rel=0.1)\n"
    assert found(change(PATH, before, after_)) == [("TR106", "suspicious")]


def test_tolerance_tightened_is_fine() -> None:
    before = "def test_mean():\n    np.testing.assert_allclose(a, b, rtol=1e-3)\n"
    after_ = "def test_mean():\n    np.testing.assert_allclose(a, b, rtol=1e-6)\n"
    assert found(change(PATH, before, after_)) == []


UNITTEST = "class TestX(unittest.TestCase):\n    def test_a(self):\n        {}\n"


def test_places_lowered() -> None:
    before = UNITTEST.format("self.assertAlmostEqual(a, b, places=6)")
    after_ = UNITTEST.format("self.assertAlmostEqual(a, b, places=2)")
    assert found(change(PATH, before, after_)) == [("TR106", "suspicious")]


def test_exception_broadened() -> None:
    before = (
        "def test_bad():\n    with pytest.raises(ValueError, match='bad'):\n        parse('x')\n"
    )
    after_ = "def test_bad():\n    with pytest.raises(Exception):\n        parse('x')\n"
    assert found(change(PATH, before, after_)) == [("TR104", "suspicious")]


def test_unittest_assertion_weakened() -> None:
    before = UNITTEST.format("self.assertEqual(f(), 3)")
    after_ = UNITTEST.format("self.assertIsNotNone(f())")
    assert found(change(PATH, before, after_)) == [("TR104", "suspicious")]


def test_test_removed() -> None:
    after_ = (
        "import pytest\nfrom calc import add\n\n\ndef test_other():\n    assert add(0, 0) == 0\n"
    )
    assert found(change(PATH, BEFORE, after_)) == [("TR110", "suspicious")]


def test_file_deleted() -> None:
    assert found(change(PATH, BEFORE, None)) == [("TR110", "suspicious")]


def test_test_renamed() -> None:
    renamed = BEFORE.replace("def test_add():", "def test_add_two_numbers():")
    assert found(change(PATH, BEFORE, renamed)) == []


def test_test_moved_to_another_file() -> None:
    stays = "def test_other():\n    assert add(0, 0) == 0\n"
    moved = "def test_add():\n    result = add(1, 2)\n    assert result == 3\n"
    assert found(change(PATH, BEFORE, stays), change("tests/test_add.py", None, moved)) == []


def test_moved_and_weakened() -> None:
    stays = "def test_other():\n    assert add(0, 0) == 0\n"
    moved = "def test_add():\n    result = add(1, 2)\n"
    findings = found(change(PATH, BEFORE, stays), change("tests/test_add.py", None, moved))
    assert findings == [("TR101", "caught")]


def test_module_skipped() -> None:
    skipped = BEFORE.replace("import pytest\n", "import pytest\n\npytestmark = pytest.mark.skip\n")
    assert found(change(PATH, BEFORE, skipped)) == [("TR111", "caught"), ("TR111", "caught")]


def test_class_tests_skipped_are_collapsed() -> None:
    methods = "".join(f"    def test_{i}(self):\n        assert f({i}) == {i}\n" for i in range(8))
    before = "class TestF:\n" + methods
    after_ = "@pytest.mark.skip\nclass TestF:\n" + methods
    findings = report(change(PATH, before, after_)).findings
    assert [(f.rule, f.level.value) for f in findings] == [("TR111", "caught")]
    assert findings[0].message.startswith("8 tests")


def test_parametrized_cases_removed() -> None:
    before = "@pytest.mark.parametrize('n', [1, 2, 3])\ndef test_n(n):\n    assert f(n) == n\n"
    after_ = "@pytest.mark.parametrize('n', [1, 2])\ndef test_n(n):\n    assert f(n) == n\n"
    assert found(change(PATH, before, after_)) == [("TR112", "suspicious")]


def test_new_hollow_test_is_a_note() -> None:
    after_ = BEFORE + "\n\ndef test_runs():\n    add(1, 1)\n"
    assert found(change(PATH, BEFORE, after_)) == [("TR121", "note")]


def test_mocks_in_integration_tests() -> None:
    before = "def test_api(client):\n    assert client.get('/').status == 200\n"
    after_ = (
        "def test_api(client, mocker):\n    mocker.patch('app.db.query')\n"
        "    assert client.get('/').status == 200\n"
    )
    assert found(change("tests/integration/test_api.py", before, after_)) == [
        ("TR120", "suspicious")
    ]
    assert found(change("tests/unit/test_api.py", before, after_)) == [("TR120", "note")]


def test_helper_emptied() -> None:
    before = (
        "def assert_valid(doc):\n    assert doc.ok\n\n\ndef test_a():\n    assert_valid(load())\n"
    )
    after_ = "def assert_valid(doc):\n    pass\n\n\ndef test_a():\n    assert_valid(load())\n"
    assert found(change(PATH, before, after_)) == [("TR101", "caught")]


def test_unparseable_file_is_inconclusive() -> None:
    result = report(change(PATH, BEFORE, "def test_add(:\n"))
    assert result.verdict == Verdict.INCONCLUSIVE
    assert result.unchecked[0].path == PATH


def test_non_test_files_are_ignored_by_test_rules() -> None:
    assert (
        found(
            change(
                "src/calc.py",
                "def add(a, b):\n    return a + b\n",
                "def add(a, b):\n    return 3\n",
            )
        )
        == []
    )
