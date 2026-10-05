"""Apply git-style unified diffs to files held in memory."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchError(ValueError):
    pass


@dataclass
class FilePatch:
    old_path: str | None  # None for a new file
    new_path: str | None  # None for a deleted file
    hunks: list[tuple[int, list[str]]] = field(default_factory=list)  # (old start, lines)


def _strip(path: str) -> str | None:
    path = path.strip().split("\t")[0]
    if path == "/dev/null":
        return None
    return path[2:] if path.startswith(("a/", "b/")) else path


def parse(patch: str) -> list[FilePatch]:
    """The patch's files and hunks. Hunk lengths in the `@@` headers say where each hunk ends."""
    files: list[FilePatch] = []
    current: FilePatch | None = None
    lines = patch.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            current = FilePatch(_strip(line[4:]), _strip(lines[i + 1][4:]))
            files.append(current)
            i += 2
            continue
        match = HUNK.match(line)
        if match and current is not None:
            old_left = int(match.group(2) or 1)
            new_left = int(match.group(4) or 1)
            hunk: list[str] = []
            i += 1
            while i < len(lines) and (old_left > 0 or new_left > 0):
                body = lines[i]
                tag = body[:1]
                if tag == "\\":  # "\ No newline at end of file"
                    i += 1
                    continue
                if tag in {"", " "}:
                    old_left -= 1
                    new_left -= 1
                    hunk.append(" " + body[1:])
                elif tag == "-":
                    old_left -= 1
                    hunk.append(body)
                elif tag == "+":
                    new_left -= 1
                    hunk.append(body)
                else:
                    break
                i += 1
            current.hunks.append((int(match.group(1)), hunk))
            continue
        i += 1
    return files


def _find(lines: list[str], old: list[str], guess: int, floor: int) -> int | None:
    def matches(at: int) -> bool:
        return all(lines[at + i].rstrip("\r") == old[i].rstrip("\r") for i in range(len(old)))

    if not old:
        return max(guess, floor)
    for delta in range(0, 400):
        for at in (guess + delta, guess - delta):
            if floor <= at <= len(lines) - len(old) and matches(at):
                return at
    return None


def _apply_one(text: str, fp: FilePatch) -> str:
    lines = text.splitlines()
    out: list[str] = []
    cursor = 0
    for start, hunk in fp.hunks:
        old = [h[1:] for h in hunk if h[:1] in {" ", "-"}]
        new = [h[1:] for h in hunk if h[:1] in {" ", "+"}]
        at = _find(lines, old, max(start - 1, 0), cursor)
        if at is None:
            raise PatchError(f"a hunk at line {start} does not apply to {fp.old_path}")
        out += lines[cursor:at]
        out += new
        cursor = at + len(old)
    out += lines[cursor:]
    return "\n".join(out) + "\n" if out else ""


def apply(files: dict[str, str | None], patch: str) -> dict[str, str | None]:
    """The files after the patch; a path maps to None when the patch deletes the file."""
    result = dict(files)
    for fp in parse(patch):
        if fp.old_path is None:
            if fp.new_path is not None:
                result[fp.new_path] = _apply_one("", fp)
            continue
        source = result.get(fp.old_path)
        if source is None:
            raise PatchError(f"no text for {fp.old_path}")
        if fp.new_path is None:
            result[fp.old_path] = None
            continue
        patched = _apply_one(source, fp)
        if fp.new_path != fp.old_path:
            result[fp.old_path] = None
        result[fp.new_path] = patched
    return result


def touched(patch: str) -> list[tuple[str | None, str | None]]:
    return [(fp.old_path, fp.new_path) for fp in parse(patch)]


def hunks_only(patch: str, path: str) -> FilePatch:
    """A file's hunks as the GitHub API gives them: no `---`/`+++` header, just `@@` hunks."""
    return parse(f"--- a/{path}\n+++ b/{path}\n{patch}")[0]


def reverse(text: str, patch: str, path: str) -> str:
    """The file before a change, from the file after it and the change's hunks."""
    fp = hunks_only(patch, path)
    flipped = FilePatch(path, path)
    for _start, hunk in fp.hunks:
        lines = ["-" + h[1:] if h[:1] == "+" else "+" + h[1:] if h[:1] == "-" else h for h in hunk]
        new_start = _new_start(patch, len(flipped.hunks))
        flipped.hunks.append((new_start, lines))
    return _apply_one(text, flipped)


def _new_start(patch: str, index: int) -> int:
    headers = [HUNK.match(line) for line in patch.splitlines() if line.startswith("@@")]
    match = headers[index]
    assert match is not None
    return int(match.group(3))


def added_text(patch: str, path: str) -> str:
    """A new file's text from its hunks."""
    return _apply_one("", hunks_only(patch, path))


def removed_text(patch: str, path: str) -> str:
    """A deleted file's text from its hunks."""
    fp = hunks_only(patch, path)
    lines = [h[1:] for _start, hunk in fp.hunks for h in hunk if h[:1] in {"-", " "}]
    return "\n".join(lines) + "\n" if lines else ""
