from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from testreceipt.census import junit_id, split_command
from testreceipt.cli import main

PYTEST = f'"{sys.executable}" -m pytest -q'


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)


def write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "core.autocrlf", "false")
    write(root, "calc.py", "def add(a, b):\n    return a + b\n")
    write(
        root,
        "tests/test_calc.py",
        "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n\n\n"
        "def test_zero():\n    assert add(0, 0) == 0\n",
    )
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "agent")
    return root


def commit(repo: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        write(repo, path, text)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "agent")


def test_junit_ids() -> None:
    assert junit_id("tests.test_calc", "test_add") == "tests/test_calc.py::test_add"
    assert (
        junit_id("tests.test_calc.TestAdd", "test_one[2-3]")
        == "tests/test_calc.py::TestAdd::test_one"
    )


def test_split_command_keeps_windows_paths() -> None:
    assert split_command('"C:\\Program Files\\py.exe" -m pytest')[0].endswith("py.exe")


def test_weakened_test_that_the_change_broke_is_caught(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit(
        repo,
        {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n"
            "    assert add(1, 2) is not None\n\n\ndef test_zero():\n    assert add(0, 0) == 0\n",
        },
    )
    code = main(["check", "--repo", str(repo), "--base", "main", "--run", PYTEST, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "CAUGHT", payload
    caught = [f for f in payload["findings"] if f["level"] == "caught"]
    assert caught[0]["rule"] == "TR104"
    assert "failing on the new code" in caught[0]["message"]
    assert payload["runs"]["cross"].startswith("exit 1")
    assert code == 1


def test_weakening_that_the_change_did_not_need_stays_suspicious(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit(
        repo,
        {
            "tests/test_calc.py": "from calc import add\n\n\ndef test_add():\n"
            "    assert add(1, 2) is not None\n\n\ndef test_zero():\n    assert add(0, 0) == 0\n",
        },
    )
    code = main(["check", "--repo", str(repo), "--base", "main", "--run", PYTEST, "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "SUSPICIOUS", payload
    assert code == 0
