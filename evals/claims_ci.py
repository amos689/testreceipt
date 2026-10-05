"""The gate's measurement M2: pull requests that say the tests pass, against their CI.

    uv run --group evals python evals/claims_ci.py select [--per-agent 600]
    uv run --group evals python evals/claims_ci.py fetch
    uv run --group evals python evals/claims_ci.py report

`select` reads every AIDev pull request description with `testreceipt.claims` and samples, per
agent, those that say the tests pass: in words ("All 101 tests pass"), or, for Codex, by listing
test commands under "Testing" without noting a failure. `fetch` asks the GitHub API for the check
runs on each one's head commit and, for failed GitHub Actions jobs, for the job's steps. CI logs
expire after 90 days and these pull requests are older, but job and step results are kept, so a
failed step named like a test run ("Run tests", "pytest") is the evidence used.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))

from aidev import DATA, RESULTS, GitHub

from testreceipt.claims import claims, overall

ROOT = Path(__file__).parent
CACHE = ROOT / ".cache" / "claims_ci"
SELECTED = DATA / "claims_selected.jsonl"
TEST_STEP = re.compile(
    r"\b(?:tests?|testing|pytest|py\.test|tox|nox|jest|vitest|mocha|unit|integration|e2e|spec|"
    r"check(?:s)?)\b",
    re.IGNORECASE,
)
NOT_TESTS = re.compile(
    r"\b(?:lint|linting|format|fmt|style|type ?check|mypy|pyright|eslint|prettier|ruff|flake8|"
    r"codeql|security|docs?|deploy|publish|release|label|changelog|codecov|coverage upload|"
    r"preview|vercel|netlify|cla|dco|commit ?lint|title)\b",
    re.IGNORECASE,
)


def is_test_step(name: str) -> bool:
    return bool(TEST_STEP.search(name)) and not NOT_TESTS.search(name)


def select(per_agent: int, seed: int) -> None:
    prs = pq.read_table(
        DATA / "pull_request.parquet",
        columns=["id", "number", "agent", "state", "merged_at", "repo_url", "html_url", "body"],
    ).to_pylist()
    pools: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for p in prs:
        found = claims(p["body"] or "")
        kind = overall(found)
        if kind not in {"pass", "implied pass"}:
            continue
        line = next(c.text for c in found if c.kind == "pass")
        pools[(p["agent"], kind)].append(
            {
                "pr_id": p["id"],
                "repo": p["repo_url"].removeprefix("https://api.github.com/repos/"),
                "number": p["number"],
                "agent": p["agent"],
                "claim": kind,
                "claim_line": line,
                "merged": p["merged_at"] is not None,
                "state": p["state"],
                "url": p["html_url"],
            }
        )
    rng = random.Random(seed)
    chosen = []
    for key in sorted(pools):
        pool = pools[key]
        chosen += pool if len(pool) <= per_agent else rng.sample(pool, per_agent)
        print(f"{key}: {len(pool)} claims, {min(len(pool), per_agent)} sampled", file=sys.stderr)
    rng.shuffle(chosen)
    with SELECTED.open("w", encoding="utf-8") as out:
        for row in chosen:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fetch_one(github: GitHub, row: dict[str, Any]) -> str:
    target = CACHE / f"{row['pr_id']}.json"
    if target.exists():
        return "cached"
    repo = row["repo"]
    pull = github.get(f"/repos/{repo}/pulls/{row['number']}")
    record: dict[str, Any]
    if pull is None:
        record = {"status": "gone"}
    else:
        head = pull["head"]["sha"]
        runs = github.get(f"/repos/{repo}/commits/{head}/check-runs?per_page=100") or {}
        status = github.get(f"/repos/{repo}/commits/{head}/status") or {}
        checks = []
        for run in runs.get("check_runs", []):
            check: dict[str, Any] = {
                "name": run.get("name"),
                "app": (run.get("app") or {}).get("slug"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "id": run.get("id"),
            }
            if check["app"] == "github-actions" and check["conclusion"] == "failure":
                job = github.get(f"/repos/{repo}/actions/jobs/{run['id']}") or {}
                check["steps"] = [
                    {"name": s.get("name"), "conclusion": s.get("conclusion")}
                    for s in job.get("steps", [])
                ]
            checks.append(check)
        record = {
            "status": "ok",
            "head": head,
            "checks": checks,
            "statuses": [
                {"context": s.get("context"), "state": s.get("state")}
                for s in status.get("statuses", [])
            ],
        }
    CACHE.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    return record["status"]


def fetch(workers: int) -> None:
    github = GitHub()
    rows = [json.loads(line) for line in SELECTED.read_text(encoding="utf-8").splitlines()]
    todo = [r for r in rows if not (CACHE / f"{r['pr_id']}.json").exists()]
    print(f"{len(todo)} of {len(rows)} pull requests to fetch", file=sys.stderr)
    outcomes: Counter[str] = Counter()
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(_fetch_one, github, r) for r in todo]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                outcomes[future.result()] += 1
            except RuntimeError as error:
                outcomes["failed"] += 1
                print(f"  {error}", file=sys.stderr)
            if i % 200 == 0:
                print(
                    f"  {i}/{len(todo)} {dict(outcomes)} api left {github.remaining}",
                    file=sys.stderr,
                )
    print(dict(outcomes), file=sys.stderr)


def classify(record: dict[str, Any]) -> tuple[str, str]:
    """What CI says about the head commit's tests, and the evidence."""
    if record["status"] != "ok":
        return "gone", ""
    checks = record["checks"]
    statuses = record["statuses"]
    if not checks and not statuses:
        return "no CI", ""
    failed_steps = [
        f"{c['name']} › {s['name']}"
        for c in checks
        for s in c.get("steps", [])
        if s["conclusion"] == "failure" and is_test_step(s["name"])
    ]
    if failed_steps:
        return "test step failed", failed_steps[0]
    failed_jobs = [
        c["name"]
        for c in checks
        if c["conclusion"] == "failure" and is_test_step(c["name"] or "") and "steps" not in c
    ] + [
        s["context"]
        for s in statuses
        if s["state"] in {"failure", "error"} and is_test_step(s["context"] or "")
    ]
    if failed_jobs:
        return "test job failed", failed_jobs[0]
    test_checks = [c for c in checks if is_test_step(c["name"] or "")] + [
        s for s in statuses if is_test_step(s["context"] or "")
    ]
    if not test_checks:
        others = [c for c in checks if c["conclusion"] == "failure"]
        return ("other failure" if others else "no test CI"), (others[0]["name"] if others else "")
    # consistent only when some test check actually ran and succeeded
    succeeded = [
        c for c in test_checks if c.get("conclusion") == "success" or c.get("state") == "success"
    ]
    return ("consistent", "") if succeeded else ("no result", "")


def report() -> str:
    rows = [json.loads(line) for line in SELECTED.read_text(encoding="utf-8").splitlines()]
    table: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    cases = []
    for row in rows:
        target = CACHE / f"{row['pr_id']}.json"
        if not target.exists():
            continue
        outcome, evidence = classify(json.loads(target.read_text(encoding="utf-8")))
        table[(row["agent"], row["claim"])][outcome] += 1
        if outcome in {"test step failed", "test job failed"}:
            cases.append({**row, "outcome": outcome, "evidence": evidence})
    lines = [
        "| Agent | Claim | Sampled | Undecided | Consistent | Tests failed in CI"
        " | Share of decided |",
        "|---|---|---|---|---|---|---|",
    ]
    for (agent, claim), c in sorted(table.items()):
        n = sum(c.values())
        undecided = c["no CI"] + c["no result"] + c["no test CI"] + c["gone"] + c["other failure"]
        failed = c["test step failed"] + c["test job failed"]
        decided = failed + c["consistent"]
        share = f"{100 * failed / decided:.1f}%" if decided else "–"
        lines.append(
            f"| {agent} | {claim} | {n} | {undecided} | {c['consistent']} | {failed} | {share} |"
        )
    with (RESULTS / "claims-ci-cases.jsonl").open("w", encoding="utf-8") as out:
        for case in cases:
            out.write(json.dumps(case, ensure_ascii=False) + "\n")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["select", "fetch", "report"])
    parser.add_argument("--per-agent", type=int, default=600)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "select":
        select(args.per_agent, args.seed)
    elif args.command == "fetch":
        fetch(args.workers)
    else:
        text = report()
        (RESULTS / "claims-ci.md").write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
