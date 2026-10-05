from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from testreceipt.cli import main


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calc.py").write_bytes(
        b"def test_add():\n    assert 1 + 2 == 3\n\n\ndef test_sub():\n    assert 2 - 1 == 1\n"
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "tests")
    git(tmp_path, "checkout", "-q", "-b", "agent")
    return tmp_path


def commit(repo: Path, path: str, text: str) -> None:
    (repo / path).write_bytes(text.encode())
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "change")


def test_caught_change_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(
        repo,
        "tests/test_calc.py",
        "def test_add():\n    pass\n\n\ndef test_sub():\n    assert 2 - 1 == 1\n",
    )
    assert main(["check", "--repo", str(repo), "--base", "main"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("testreceipt CAUGHT")
    assert "TR101" in out
    assert "tests/test_calc.py:1 [test_add]" in out


def test_clean_change_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(
        repo,
        "tests/test_calc.py",
        "def test_add():\n    assert 1 + 2 == 3\n    assert 2 + 2 == 4\n\n\n"
        "def test_sub():\n    assert 2 - 1 == 1\n",
    )
    assert main(["check", "--repo", str(repo), "--base", "main"]) == 0
    assert capsys.readouterr().out.startswith("testreceipt CLEAN")


def test_json_and_fail_on(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, "tests/test_calc.py", "def test_add():\n    assert 1 + 2 == 3\n")
    code = main(["check", "--repo", str(repo), "--base", "main", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["verdict"] == "SUSPICIOUS"
    assert payload["findings"][0]["rule"] == "TR110"
    assert main(["check", "--repo", str(repo), "--base", "main", "--fail-on", "suspicious"]) == 1


def test_bad_revision(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--repo", str(repo), "--base", "nope"]) == 2
    assert "testreceipt:" in capsys.readouterr().err
