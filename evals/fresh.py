"""M2 on 2026 pull requests: agent pull requests that say their tests pass, against their CI.

    uv run --group evals python evals/fresh.py collect [--per-agent 400]
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


# GitHub's search allows about 30 queries a minute across REST and GraphQL; more gets 403s
PACE = 2.5
_last_search = [0.0]


def _search(github: GitHub, query: str, after: str | None) -> dict[str, Any]:
    body = json.dumps({"query": SEARCH, "variables": {"q": query, "after": after}}).encode()
    for attempt in range(8):
        wait = _last_search[0] + PACE - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_search[0] = time.time()
        request = urllib.request.Request(
            "https://api.github.com/graphql", data=body, headers=github._headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
            if payload.get("errors") and not payload.get("data"):
                raise RuntimeError(str(payload["errors"])[:200])
            return payload["data"]["search"]  # type: ignore[no-any-return]
        except urllib.error.HTTPError as error:
            retry = error.headers.get("Retry-After") if error.headers else None
            pause = float(retry) if retry else 60.0 * (attempt + 1)
            print(f"  search {error.code}, waiting {pause:.0f}s", file=sys.stderr, flush=True)
            time.sleep(pause)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            print(f"  search error, retrying: {error}", file=sys.stderr, flush=True)
            time.sleep(30.0 * (attempt + 1))
    raise RuntimeError(f"search failed: {query}")


def _windows(day: dt.date) -> list[str]:
    stamp = day.isoformat()
    return [f"{stamp}T{h:02d}:00:00Z..{stamp}T{h + 3:02d}:59:59Z" for h in range(0, 24, 4)]


def _pages(github: GitHub, query: str, pages: int) -> tuple[int, list[dict[str, Any]]]:
    """The query's total count and the pull requests on its first pages."""
    found: list[dict[str, Any]] = []
    after = None
    count = 0
    for _ in range(pages):
        result = _search(github, query, after)
        count = result["issueCount"]
        found += [n for n in result["nodes"] if n]
        if not result["pageInfo"]["hasNextPage"]:
            break
        after = result["pageInfo"]["endCursor"]
    return count, found


# text the description must contain for agents found through it, since search matches loosely
SIGNATURE_TEXT = {"Claude_Code": "claude code", "Cursor": "cursor.com/"}


def _keep(node: dict[str, Any], agent: str) -> bool:
    repo = node.get("repository") or {}
    if repo.get("stargazerCount", 0) < MIN_STARS or repo.get("isFork"):
        return False
    needed = SIGNATURE_TEXT.get(agent)
    return needed is None or needed in (node.get("body") or "").lower()


def _sample_window(
    github: GitHub, base: str, day: dt.date, w: int, busy: bool
) -> tuple[list[dict[str, Any]], bool]:
    """Pull requests of the w-th four-hour window of a day (two pages at most), and whether the
    day is quiet enough to have been taken whole instead."""
    if not busy:
        count, found = _pages(github, f"{base} created:{day.isoformat()} sort:created-asc", 2)
        if count <= 200:
            return found, True
    window = _windows(day)[w]
    return _pages(github, f"{base} created:{window} sort:created-asc", 2)[1], False


def collect(
    per_agent: int,
    seed: int,
    agents: list[str] | None = None,
    control_target: int | None = None,
) -> None:
    """Samples days for every agent in turn, until each has `per_agent` pull requests that mention
    tests passing and half as many unfiltered ones. Finished days are remembered in
    `progress.json`, so a stopped run picks up where it left off."""
    github = GitHub()
    DATA.mkdir(parents=True, exist_ok=True)
    progress_path = DATA / "progress.json"
    done: set[str] = set(json.loads(progress_path.read_text())) if progress_path.exists() else set()
    days = [START + dt.timedelta(days=i) for i in range((END - START).days + 1)]
    # the phrase search matches loosely (about one in ten of its pull requests has a claim), so the
    # unfiltered sample is the main source of claims; `per_agent` caps the phrase population
    targets = {
        "claims": per_agent,
        "control": control_target if control_target is not None else per_agent // 2,
    }
    state = {}
    for agent in AGENTS:
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
        # a step is a four-hour window of a day; a quiet day is taken whole by its first step
        steps = [(day, population, w) for day in days for population in targets for w in range(6)]
        random.Random(f"{seed}:{agent}").shuffle(steps)
        state[agent] = (seen, counts, iter(steps))
    active = list(state)
    while active:
        for agent in list(active):
            seen, counts, steps = state[agent]
            step = None
            for day, population, w in steps:
                stem = f"{agent}|{population}|{day.isoformat()}"
                key = f"{stem}|{w}"
                wanted = counts[population] < targets[population]
                if wanted and key not in done and f"{stem}|quiet" not in done:
                    step = (day, population, w, stem)
                    break
            if step is None:
                active.remove(agent)
                print(f"{agent}: {dict(counts)}", file=sys.stderr, flush=True)
                continue
            day, population, w, stem = step
            terms = CLAIM_TERMS if population == "claims" else ""
            base = f"is:pr {AGENTS[agent]} {terms}".strip()
            busy = f"{stem}|busy" in done
            found, quiet = _sample_window(github, base, day, w, busy)
            done.add(f"{stem}|quiet" if quiet else f"{stem}|busy")
            key = f"{stem}|{w}"
            with (DATA / f"{agent}.jsonl").open("a", encoding="utf-8") as out:
                for node in found:
                    if node["databaseId"] in seen or not _keep(node, agent):
                        continue
                    seen.add(node["databaseId"])
                    counts[population] += 1
                    out.write(json.dumps(_row(node, agent, population)) + "\n")
            done.add(key)
            progress_path.write_text(json.dumps(sorted(done)))
            print(f"  {agent} {population} {day} {dict(counts)}", file=sys.stderr, flush=True)


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
    for path in sorted(DATA / f"{agent}.jsonl" for agent in AGENTS):
        if not path.exists():
            continue
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


def prefetch() -> None:
    """CI results for every collected pull request not fetched yet (not limited by search)."""
    _use_fresh_files()
    github = GitHub()
    todo = [
        {**r, "claim": r["population"], "claim_line": ""}
        for r in rows()
        if not (CACHE / f"{r['pr_id']}.json").exists()
    ]
    print(f"{len(todo)} pull requests to fetch", file=sys.stderr, flush=True)
    for start in range(0, len(todo), 10):
        try:
            claims_ci._graphql_batch(github, todo[start : start + 10])
        except RuntimeError as error:
            print(f"  {error}", file=sys.stderr, flush=True)
        if (start // 10) % 20 == 0:
            print(f"  {start + 10}/{len(todo)}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["collect", "prefetch", "select", "fetch", "report", "verdicts", "sheet"],
    )
    parser.add_argument("--per-agent", type=int, default=400)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--agents", nargs="*", help="collect only these agents")
    parser.add_argument(
        "--control-target", type=int, help="how many unfiltered pull requests to collect per agent"
    )
    args = parser.parse_args()
    if args.command == "collect":
        collect(args.per_agent, args.seed, args.agents, args.control_target)
    elif args.command == "prefetch":
        prefetch()
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
