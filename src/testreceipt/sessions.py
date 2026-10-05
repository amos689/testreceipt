"""Claims in an agent's session, checked against the test runs the session itself recorded.

A Claude Code transcript (`~/.claude/projects/<project>/<session>.jsonl`) records each shell
command the agent ran with its output, each file it edited, and each message it wrote. A message
that says the tests pass is checked against the last test run before it:

- backed: the last run passed, and no file was edited after it;
- contradicted: the last run failed;
- stale: files were edited after the last run, so it does not cover the claim;
- unverified: no test run came before the claim;
- count mismatch: the claim names more passing tests than the run reported.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .claims import Claim, claims
from .rules.ci import is_test_command

EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
SHELL_TOOLS = frozenset({"Bash", "PowerShell", "shell", "exec_command"})
SUMMARY = re.compile(r"\b(\d+) (passed|failed|errors?|error)\b")
SUMMARY_LINE = re.compile(r"\b\d+ (?:passed|failed|errors?|skipped|deselected)\b.*\bin [\d.]+s\b")
NOT_CODE = (".md", ".rst", ".txt", ".html", ".csv", ".json", ".log")
EXIT = re.compile(r"\bExit code (\d+)\b|\bexited with code (\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Run:
    command: str
    output: str
    failed: bool
    passed: int | None
    index: int


@dataclass(frozen=True)
class Checked:
    claim: Claim
    verdict: str
    run: Run | None
    index: int


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""


def runs_tests(command: str) -> bool:
    """A shell command that runs tests in one of its steps (`uv sync && uv run pytest -q`)."""
    return any(is_test_command(step) for step in re.split(r"&&|\|\||;|\n|\|", command))


def _outcome(output: str, is_error: bool) -> tuple[bool, int | None]:
    counts: dict[str, int] = {}
    # only pytest's summary line ("3 failed, 12 passed in 0.41s"), not a linter's "Found 2 errors"
    for line in output.splitlines():
        if not SUMMARY_LINE.search(line):
            continue
        for number, word in SUMMARY.findall(line):
            key = "error" if word.startswith("error") else word
            counts[key] = counts.get(key, 0) + int(number)
    if counts:
        # the runner's own summary decides: a chained lint step may be what set the exit code
        return bool(counts.get("failed") or counts.get("error")), counts.get("passed")
    exit_code = next((int(a or b) for a, b in EXIT.findall(output)), None)
    return bool(exit_code) or is_error, None


def events(path: Path) -> Iterator[tuple[str, Any, int]]:
    """("run", Run) for test runs, ("edit", path) for edits and ("claim", Claim) for claims."""
    commands: dict[str, str] = {}
    index = 0
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = record.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), list):
                continue
            for block in message["content"]:
                if not isinstance(block, dict):
                    continue
                index += 1
                kind = block.get("type")
                if record.get("type") == "assistant" and kind == "tool_use":
                    name = block.get("name", "")
                    arguments = block.get("input") or {}
                    if name in SHELL_TOOLS:
                        commands[block.get("id", "")] = str(arguments.get("command", ""))
                    elif name in EDIT_TOOLS:
                        edited = str(arguments.get("file_path") or arguments.get("notebook_path"))
                        if not edited.endswith(NOT_CODE):  # documentation does not stale a run
                            yield "edit", edited, index
                elif record.get("type") == "user" and kind == "tool_result":
                    command = commands.pop(block.get("tool_use_id", ""), None)
                    if command and runs_tests(command):
                        output = _text(block.get("content"))
                        failed, passed = _outcome(output, bool(block.get("is_error")))
                        yield "run", Run(command, output, failed, passed, index), index
                elif record.get("type") == "assistant" and kind == "text":
                    for claim in claims(block.get("text", "")):
                        if claim.kind == "pass" and claim.explicit:
                            yield "claim", claim, index


def check_session(path: Path) -> list[Checked]:
    checked: list[Checked] = []
    last_run: Run | None = None
    edited_since = False
    for kind, item, index in events(path):
        if kind == "run":
            last_run, edited_since = item, False
        elif kind == "edit":
            edited_since = True
        else:
            claim: Claim = item
            if last_run is None:
                verdict = "unverified"
            elif last_run.failed:
                verdict = "contradicted"
            elif claim.count and last_run.passed is not None and claim.count > last_run.passed:
                verdict = "count mismatch"
            elif edited_since:
                verdict = "stale"
            else:
                verdict = "backed"
            checked.append(Checked(claim, verdict, last_run, index))
    return checked
