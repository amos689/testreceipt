"""A reading sheet for adjudication: each sampled finding with the hunks it is about.

    uv run --group evals python evals/sheet.py [--level caught] [--out FILE]

Reads `evals/results/aidev-sample.jsonl` and the cached pull request files, and prints, for each
finding, the pull request, the claim, and the hunks of the file that touch the finding's test (or
its line). Labels go into `evals/aidev_labels.toml`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache" / "aidev"
RESULTS = ROOT / "results"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def hunks(patch: str) -> list[tuple[int, int, list[str]]]:
    out: list[tuple[int, int, list[str]]] = []
    for line in patch.splitlines():
        match = HUNK.match(line)
        if match:
            start = int(match.group(1))
            out.append((start, start + int(match.group(2) or 1), [line]))
        elif out:
            out[-1][2].append(line)
    return out


def relevant(patch: str, test: str | None, line: int | None, limit: int = 80) -> list[str]:
    name = test.split("::")[-1] if test else None
    chosen: list[str] = []
    for start, end, lines in hunks(patch):
        text = "\n".join(lines)
        if (name and name in text) or (line and start - 5 <= line <= end + 5):
            chosen += lines
    if not chosen:
        chosen = patch.splitlines()
    return chosen[:limit] + (["… (cut)"] if len(chosen) > limit else [])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="caught")
    parser.add_argument("--out")
    args = parser.parse_args()
    selected = {
        json.loads(line)["url"]: json.loads(line)
        for line in (ROOT / ".data" / "aidev" / "selected.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    }
    items = [
        json.loads(line)
        for line in (RESULTS / "aidev-sample.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    out: list[str] = []
    for n, item in enumerate((i for i in items if i["level"] == args.level), 1):
        row = selected[item["pr"]]
        record = json.loads((CACHE / f"{row['pr_id']}.json").read_text(encoding="utf-8"))
        patch = next(
            (f.get("patch") or "" for f in record["files"] if f["filename"] == item["path"]), ""
        )
        line = None
        match = re.search(r"#L(\d+)$", item["file_at_head"])
        if match:
            line = int(match.group(1))
        out += [
            f"## {n}. {item['rule']} {item['level']} — {item['agent']}, merged={item['merged']}",
            f"{item['pr']}  `{item['path']}` {item['test'] or ''}",
            f"> {item['message']}",
            "```diff",
            *relevant(patch, item["test"], line),
            "```",
            "",
        ]
    text = "\n".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"{args.out}: {len(out)} lines", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
