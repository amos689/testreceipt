"""Whole-description verdicts against the adjudicated M2 cases (the claims development set).

    uv run --group evals python evals/claims_dev.py

Each of the 95 cases is a pull request whose description claims passing tests while CI failed a
test step at the head commit. Two judges labelled each one (evals/results/judge*-m2.md); see
evals/aidev_labels.toml for resolutions. The script compares testreceipt's verdict for the whole
description with those labels.
"""

from __future__ import annotations

import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from testreceipt.claims import claims

ROOT = Path(__file__).parent


def labels(path: Path) -> dict[int, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0].isdigit():
            out[int(cells[0])] = cells[1]
    return out


def truth() -> dict[int, str]:
    a = labels(ROOT / "results" / "judge1-m2.md")
    b = labels(ROOT / "results" / "judge2-m2.md")
    doc = tomllib.loads((ROOT / "aidev_labels.toml").read_text(encoding="utf-8"))
    resolved = {int(k): v for k, v in doc["m2_resolved"].items()}
    pr_level = {int(k): v for k, v in doc.get("m2_pr_level", {}).items()}
    return {k: pr_level.get(k) or (a[k] if a[k] == b[k] else resolved[k]) for k in a}


def verdict(body: str) -> str:
    found = claims(body)
    explicit = [c for c in found if c.kind == "pass" and c.explicit]
    if not explicit:
        return "none"
    if any(c.kind == "fail" for c in found):
        return "mixed"
    scopes = {c.scope for c in explicit}
    if "full" in scopes:
        return "CONTRADICTED"
    return "COUNT" if "count" in scopes else "SCOPED"


def main() -> None:
    final = truth()
    cases = [
        json.loads(line)
        for line in (ROOT / "results" / "claims-ci-cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    wanted = {c["pr_id"] for c in cases}
    bodies = {
        p["id"]: p["body"] or ""
        for p in pq.read_table(
            ROOT / ".data" / "aidev" / "pull_request.parquet", columns=["id", "body"]
        ).to_pylist()
        if p["id"] in wanted
    }
    table: Counter[tuple[str, str]] = Counter()
    for n, case in enumerate(cases, 1):
        auto = verdict(bodies[case["pr_id"]])
        table[(final[n], auto)] += 1
        if (final[n] == "contradiction") != (auto == "CONTRADICTED") and "-v" in sys.argv:
            print(f"  {n:3} truth={final[n]:14} auto={auto}")
    for key, count in sorted(table.items()):
        print(f"{key[0]:15} -> {key[1]:13} {count}")
    said = sum(v for (t, a), v in table.items() if a == "CONTRADICTED")
    right = table[("contradiction", "CONTRADICTED")]
    total = sum(v for (t, a), v in table.items() if t == "contradiction")
    print(f"CONTRADICTED: precision {right}/{said}, recall {right}/{total}")


if __name__ == "__main__":
    main()
