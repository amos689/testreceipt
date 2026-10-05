from __future__ import annotations

import json
from pathlib import Path

from testreceipt.sessions import check_session, runs_tests


def transcript(tmp_path: Path, steps: list[tuple[str, object]]) -> Path:
    lines = []
    for i, (kind, value) in enumerate(steps):
        if kind == "run":
            command, output = value  # type: ignore[misc]
            use = {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}
            lines.append({"type": "assistant", "message": {"content": [use]}})
            result = {"type": "tool_result", "tool_use_id": f"t{i}", "content": output}
            lines.append({"type": "user", "message": {"content": [result]}})
        elif kind == "edit":
            use = {"type": "tool_use", "id": f"e{i}", "name": "Edit", "input": {"file_path": value}}
            lines.append({"type": "assistant", "message": {"content": [use]}})
        else:
            lines.append(
                {"type": "assistant", "message": {"content": [{"type": "text", "text": value}]}}
            )
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def verdicts(tmp_path: Path, steps: list[tuple[str, object]]) -> list[str]:
    return [c.verdict for c in check_session(transcript(tmp_path, steps))]


def test_backed(tmp_path: Path) -> None:
    steps = [("run", ("uv run pytest -q", "12 passed in 0.4s")), ("say", "All 12 tests pass.")]
    assert verdicts(tmp_path, steps) == ["backed"]


def test_contradicted(tmp_path: Path) -> None:
    steps = [("run", ("pytest", "1 failed, 11 passed in 0.4s")), ("say", "All tests pass.")]
    assert verdicts(tmp_path, steps) == ["contradicted"]


def test_lint_failure_in_the_same_command_is_not_a_test_failure(tmp_path: Path) -> None:
    output = "12 passed in 0.4s\nFound 2 errors.\nExit code 1"
    steps = [("run", ("pytest -q && ruff check", output)), ("say", "All tests pass.")]
    assert verdicts(tmp_path, steps) == ["backed"]


def test_stale_after_a_code_edit_but_not_a_docs_edit(tmp_path: Path) -> None:
    run = ("run", ("pytest", "3 passed in 0.1s"))
    assert verdicts(tmp_path, [run, ("edit", "README.md"), ("say", "Tests pass.")]) == ["backed"]
    assert verdicts(tmp_path, [run, ("edit", "src/a.py"), ("say", "Tests pass.")]) == ["stale"]


def test_unverified_and_count_mismatch(tmp_path: Path) -> None:
    assert verdicts(tmp_path, [("say", "All tests pass.")]) == ["unverified"]
    steps = [("run", ("pytest", "4985 passed in 9s")), ("say", "All 4992 tests pass.")]
    assert verdicts(tmp_path, steps) == ["count mismatch"]


def test_chained_commands() -> None:
    assert runs_tests("uv sync && uv run pytest -q")
    assert not runs_tests("pip install pytest")
