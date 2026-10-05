"""M2 on 2026 pull requests: agent pull requests that say their tests pass, against their CI.

    uv run --group evals python evals/fresh.py collect [--per-agent 1500]
    uv run --group evals python evals/fresh.py select [--per-agent 600]
    uv run --group evals python evals/fresh.py fetch
    uv run --group evals python evals/fresh.py report

AIDev stops in October 2025. `collect` finds agent pull requests opened from June to September 2026
through GitHub's GraphQL search, by each agent's signature (the Copilot, Devin and Jules apps as
authors; Codex's `codex` label; the links Claude Code and Cursor leave in descriptions). Days are
taken in a random order (seeded); a busy day is split into four-hour windows so that no query hits
the search's 1,000-result cap. Two populations are kept per agent: descriptions that mention tests
passing ("tests pass", "tests passing", "tests passed"), and an unfiltered sample as the control.
Only repositories with at least 100 stars are kept, as in AIDev-pop.

`select`, `fetch` and `report` reuse `claims_ci.py` on this data, with their own files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import claims_ci
from aidev import GitHub

from testreceipt.reconcile import reconcile

ROOT = Path(__file__).parent
DATA = ROOT / ".data" / "fresh"
CACHE = ROOT / ".cache" / "fresh_ci"
RESULTS = ROOT / "results"
MIN_STARS = 100
START, END = dt.date(2026, 6, 1), dt.date(2026, 9, 30)
AGENTS = {
    "Copilot": "author:app/copilot-swe-agent",
    "Claude_Code": '"Generated with Claude Code" in:body',
    "Cursor": '"cursor.com/background-agent" in:body',
    "Devin": "author:app/devin-ai-integration",
    "Google_Jules": "author:app/google-labs-jules",
    "OpenAI_Codex": "label:codex",
}
CLAIM_TERMS = '("tests pass" OR "tests passing" OR "tests passed")'
SEARCH = """query($q: String!, $after: String) {
  search(type: ISSUE, query: $q, first: 100, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      databaseId number url createdAt merged state body
      repository { nameWithOwner stargazerCount isFork }
    } }
  }
}"""


def _search(github: GitHub, query: str, after: str | None) -> dict[str, Any]:
    body = json.dumps({"query": SEARCH, "variables": {"q": query, "after": after}}).encode()
    for attempt in range(6):
        request = urllib.request.Request(
            "https://api.github.com/graphql", data=body, headers=github._headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
            if payload.get("errors") and not payload.get("data"):
                raise RuntimeError(str(payload["errors"])[:200])
            return payload["data"]["search"]  # type: ignore[no-any-return]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as error:
            wait = 60 * (attempt + 1)
            print(f"  search retry in {wait}s: {error}", file=sys.stderr, flush=True)
            time.sleep(wait)
    raise RuntimeError(f"search failed: {query}")


def _windows(day: dt.date) -> list[str]:
    stamp = day.isoformat()
    return [f"{stamp}T{h:02d}:00:00Z..{stamp}T{h + 3:02d}:59:59Z" for h in range(0, 24, 4)]


def _collect_window(github: GitHub, query: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    after = None
    for _ in range(10):  # the search returns at most 1,000 results
        result = _search(github, query, after)
        found += [n for n in result["nodes"] if n]
        if not result["pageInfo"]["hasNextPage"]:
            break
        after = result["pageInfo"]["endCursor"]
    return found


# text the description must contain for agents found through it, since search matches loosely
SIGNATURE_TEXT = {"Claude_Code": "claude code", "Cursor": "cursor.com/"}


def _keep(node: dict[str, Any], agent: str) -> bool:
    repo = node.get("repository") or {}
    if repo.get("stargazerCount", 0) < MIN_STARS or repo.get("isFork"):
        return False
    needed = SIGNATURE_TEXT.get(agent)
    return needed is None or needed in (node.get("body") or "").lower()


def collect(per_agent: int, seed: int, agents: list[str] | None = None) -> None:
    github = GitHub()
    DATA.mkdir(parents=True, exist_ok=True)
    days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
    for agent, signature in AGENTS.items():
        if agents and agent not in agents:
            continue
        target = DATA / f"{agent}.jsonl"
        seen: set[int] = set()
        counts: Counter[str] = Counter()
        if target.exists():
            for line in target.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                seen.add(row["pr_id"])
                counts[row["population"]] += 1
        order = list(days)
        random.Random(f"{seed}:{agent}").shuffle(order)
        with target.open("a", encoding="utf-8") as out:
            for day in order:
                if counts["claims"] >= per_agent and counts["control"] >= per_agent // 2:
                    break
                for population, terms in (("claims", CLAIM_TERMS), ("control", "")):
                    if population == "claims" and counts["claims"] >= per_agent:
                        continue
                    if population == "control" and counts["control"] >= per_agent // 2:
                        continue
                    base = f"is:pr {signature} {terms}".strip()
                    probe = _search(github, f"{base} created:{day.isoformat()}", None)
                    windows = _windows(day) if probe["issueCount"] > 1000 else [day.isoformat()]
                    # the control takes one window a day, to spread it over more days
                    if population == "control":
                        windows = [random.Random(f"{seed}:{agent}:{day}").choice(windows)]
                    for window in windows:
                        for node in _collect_window(github, f"{base} created:{window}"):
                            if node["databaseId"] in seen or not _keep(node, agent):
                                continue
                            seen.add(node["databaseId"])
                            counts[population] += 1
                            out.write(json.dumps(_row(node, agent, population)) + "\n")
                print(f"  {agent} {day} {dict(counts)}", file=sys.stderr, flush=True)
        print(f"{agent}: {dict(counts)}", file=sys.stderr, flush=True)


def _row(node: dict[str, Any], agent: str, population: str) -> dict[str, Any]:
    return {
        "pr_id": node["databaseId"],
        "repo": node["repository"]["nameWithOwner"],
        "stars": node["repository"]["stargazerCount"],
        "number": node["number"],
        "url": node["url"],
        "created_at": node["createdAt"],
        "merged": node["merged"],
        "state": node["state"].lower(),
        "agent": agent,
        "population": population,
        "body": node["body"] or "",
    }


def rows() -> list[dict[str, Any]]:
    out = []
    for path in sorted(DATA.glob("*.jsonl")):
        out += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return out


def _use_fresh_files() -> None:
    claims_ci.CACHE = CACHE
    claims_ci.SELECTED = DATA / "selected.jsonl"
    claims_ci.CASES = RESULTS / "fresh-claims-ci-cases.jsonl"


def select(per_agent: int, seed: int) -> None:
    """Pass claims from the claim population, and the control population as it is."""
    _use_fresh_files()
    rng = random.Random(seed)
    chosen = []
    for agent in AGENTS:
        mine = [r for r in rows() if r["agent"] == agent]
        pools: dict[str, list[dict[str, Any]]] = {"pass": [], "implied pass": [], "control": []}
        for r in mine:
            found = claims_ci.claims(r["body"])
            kind = claims_ci.overall(found)
            line = next((c.text for c in found if c.kind == "pass"), "")
            entry = {
                k: r[k] for k in ("pr_id", "repo", "number", "agent", "merged", "state", "url")
            }
            if r["population"] == "claims" and kind in {"pass", "implied pass"}:
                pools[kind].append({**entry, "claim": kind, "claim_line": line})
            elif r["population"] == "control":
                pools["control"].append({**entry, "claim": f"control: {kind}", "claim_line": line})
        for name, pool in pools.items():
            take = pool if len(pool) <= per_agent else rng.sample(pool, per_agent)
            chosen += take
            print(f"{agent} {name}: {len(pool)}, {len(take)} sampled", file=sys.stderr)
    rng.shuffle(chosen)
    with claims_ci.SELECTED.open("w", encoding="utf-8") as out:
        for row in chosen:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


OUTCOME = {
    "tests failed": "tests failed",
    "consistent": "tests passed",
    "no result": "no test result",
    "no test CI": "no test result",
    "other failure": "no test result",
    "no CI": "no CI",
    "gone": "no CI",
}


def verdicts() -> str:
    """testreceipt's own verdict for each selected pull request, and the rates per agent."""
    _use_fresh_files()
    bodies = {r["pr_id"]: r["body"] for r in rows()}
    selected = [
        json.loads(line) for line in claims_ci.SELECTED.read_text(encoding="utf-8").splitlines()
    ]
    out = []
    table: dict[tuple[str, str], Counter[str]] = {}
    for row in selected:
        target = CACHE / f"{row['pr_id']}.json"
        if not target.exists():
            continue
        found, evidence = claims_ci.classify(json.loads(target.read_text(encoding="utf-8")))
        result = reconcile(bodies[row["pr_id"]], OUTCOME[found], evidence)
        group = "control" if row["claim"].startswith("control") else "claims"
        table.setdefault((row["agent"], group), Counter())[result.verdict] += 1
        table[(row["agent"], group)]["ci: " + OUTCOME[found]] += 1
        out.append({**row, "ci": found, "evidence": evidence, **result.to_dict()})
    with (RESULTS / "fresh-verdicts.jsonl").open("w", encoding="utf-8") as handle:
        for item in out:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    lines = [
        "| Agent | PRs that claim passing tests, with a CI result | CONTRADICTED | SCOPED | COUNT |"
        " Control: CI tests failed |",
        "|---|---|---|---|---|---|",
    ]
    for agent in AGENTS:
        c = table.get((agent, "claims"), Counter())
        decided = c["ci: tests failed"] + c["ci: tests passed"]
        k = table.get((agent, "control"), Counter())
        k_decided = k["ci: tests failed"] + k["ci: tests passed"]

        def share(n: int, d: int) -> str:
            return f"{n} ({100 * n / d:.1f}%)" if d else "–"

        lines.append(
            f"| {agent} | {decided} | {share(c['CONTRADICTED'], decided)} | "
            f"{share(c['SCOPED'], decided)} | {share(c['COUNT'], decided)} | "
            f"{share(k['ci: tests failed'], k_decided)} of {k_decided} |"
        )
    return "\n".join(lines) + "\n"


def sheet(seed: int) -> None:
    """The cases for the judges: every CONTRADICTED (up to 100), 50 SCOPED and 50 COUNT."""
    items = [
        json.loads(line)
        for line in (RESULTS / "fresh-verdicts.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rng = random.Random(seed)
    picked = []
    for verdict, limit in (("CONTRADICTED", 100), ("SCOPED", 50), ("COUNT", 50)):
        pool = [
            i for i in items if i["verdict"] == verdict and not i["claim"].startswith("control")
        ]
        picked += pool if len(pool) <= limit else rng.sample(pool, limit)
    lines = ["# Fresh M2 (2026): testreceipt's verdicts for the judges", ""]
    for n, item in enumerate(picked, 1):
        claims_text = "\n".join(
            f"  - [{c['kind']}, {c['scope']}] {c['text'][:200]}" for c in item["claims"][:6]
        )
        lines += [
            f"## {n}. {item['verdict']} — {item['agent']}, merged={item['merged']}",
            item["url"],
            f"- testreceipt says: {item['message']}",
            f"- CI evidence at the head commit: {item['evidence'] or '(none)'}",
            "- claims it read from the description:",
            claims_text,
            "",
        ]
    (RESULTS / "sheet-fresh.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(picked)} cases in {RESULTS / 'sheet-fresh.md'}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["collect", "select", "fetch", "report", "verdicts", "sheet"]
    )
    parser.add_argument("--per-agent", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--agents", nargs="*", help="collect only these agents")
    args = parser.parse_args()
    if args.command == "collect":
        collect(args.per_agent, args.seed, args.agents)
    elif args.command == "select":
        select(args.per_agent, args.seed)
    elif args.command == "fetch":
        _use_fresh_files()
        claims_ci.fetch_graphql(10)
    elif args.command == "verdicts":
        text = verdicts()
        (RESULTS / "fresh-verdicts.md").write_text(text, encoding="utf-8")
        print(text)
    elif args.command == "sheet":
        sheet(args.seed)
    else:
        _use_fresh_files()
        text = claims_ci.report()
        (RESULTS / "fresh-claims-ci.md").write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
