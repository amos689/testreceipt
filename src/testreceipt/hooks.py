"""Agent hooks: stop a turn that ends on a "tests pass" the session's own runs do not back.

Claude Code calls a Stop hook with JSON on stdin that names the session's transcript. When the last
turn claims passing tests that the last test run contradicts, that edits after the run made stale,
or that no run backs at all, the hook answers with `{"decision": "block", "reason": ...}`, and
Claude Code continues the turn with that reason. It blocks once: when Claude Code reports that a
stop hook is already active, the hook lets the turn end.

    {"hooks": {"Stop": [{"hooks": [
        {"type": "command", "command": "testreceipt hook claude-stop"}
    ]}]}}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .sessions import UNBACKED, last_turn

ADVICE = {
    "contradicted": "the last test run failed",
    "stale": "code changed after the last test run",
    "unverified": "no test run in this session backs it",
    "count mismatch": "the last test run reported fewer passing tests",
}


def claude_stop(raw: str) -> str | None:
    """The hook's answer for one Stop event, or None to let the turn end."""
    try:
        event = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None
    if event.get("stop_hook_active"):
        return None
    transcript = event.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return None
    unbacked = [c for c in last_turn(Path(transcript)) if c.verdict in UNBACKED]
    if not unbacked:
        return None
    first = unbacked[0]
    claim = " ".join(first.claim.text.split())[:160]
    reason = (
        f'testreceipt: you said "{claim}", but {ADVICE[first.verdict]}. Run the tests now and '
        "report what they show, quoting the summary line, or correct the statement."
    )
    return json.dumps({"decision": "block", "reason": reason})


def main(argv: list[str]) -> int:
    if argv[:1] != ["claude-stop"]:
        print(
            "usage: testreceipt hook claude-stop  (reads the hook event on stdin)", file=sys.stderr
        )
        return 2
    answer = claude_stop(sys.stdin.read())
    if answer:
        print(answer)
    return 0
