"""Layer 1: SWE-bench's gold changes as negatives; the same with injected cheats as positives.

    uv run --group evals python evals/swebench.py fetch --split dev
    uv run --group evals python evals/swebench.py run --split dev
    uv run --group evals python evals/swebench.py report --split dev

Each SWE-bench instance is a real fix: a change to the code (`patch`) and to its tests
(`test_patch`), both written by the project's maintainers. Applied to the files at `base_commit`,
the two make a legitimate change of behaviour with its tests, so whatever testreceipt reports on it
is a false alarm. Each operator in `mutations.py` then injects one cheat into the same change, on a
test that existed before it, and the report says how often the expected rule finds it.

`fetch` downloads the touched files at the base commit from raw.githubusercontent.com into
`evals/.cache/raw/`; `run` and `report` work offline.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import json
import math
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))

import patches
from mutations import OPERATORS, Operator, check_statements, find_test

from testreceipt.changes import FileChange, is_production_python, is_test_file
from testreceipt.check import check
from testreceipt.model import Report
from testreceipt.pytests import parse_module

ROOT = Path(__file__).parent
DATA = ROOT / ".data" / "swebench"
CACHE = ROOT / ".cache" / "raw"
RESULTS = ROOT / "results"
DATASET = "princeton-nlp/SWE-bench@e48e2bd1e9fecd5bbd641e9414ac59da9f2e69f6"
LEVELS = {"note": 0, "suspicious": 1, "caught": 2}


def rows(split: str) -> list[dict[str, str]]:
    table = pq.read_table(DATA / f"{split}.parquet")
    return table.to_pylist()  # type: ignore[no-any-return]


def _cache_path(repo: str, sha: str, path: str) -> Path:
    return CACHE / repo / sha / path


def _missing(repo: str, sha: str, path: str) -> Path:
    return CACHE / repo / sha / (path + ".404")


def read_base(repo: str, sha: str, path: str) -> str | None:
    file = _cache_path(repo, sha, path)
    if file.exists():
        return file.read_bytes().decode("utf-8", "replace")
    return None


def _fetch_one(repo: str, sha: str, path: str) -> str:
    target = _cache_path(repo, sha, path)
    if target.exists() or _missing(repo, sha, path).exists():
        return "cached"
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"
    request = urllib.request.Request(url, headers={"User-Agent": "testreceipt-evals"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return "fetched"
        except urllib.error.HTTPError as error:
            if error.code == 404:
                _missing(repo, sha, path).parent.mkdir(parents=True, exist_ok=True)
                _missing(repo, sha, path).write_bytes(b"")
                return "404"
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2**attempt)
    return "failed"


def fetch(split: str, workers: int) -> None:
    wanted: set[tuple[str, str, str]] = set()
    for row in rows(split):
        for patch in (row["patch"], row["test_patch"]):
            for old, _new in patches.touched(patch):
                if old is not None:
                    wanted.add((row["repo"], row["base_commit"], old))
    print(f"{len(wanted)} files to fetch", file=sys.stderr)
    outcomes: Counter[str] = Counter()
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(_fetch_one, *key) for key in sorted(wanted)]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            outcomes[future.result()] += 1
            if i % 500 == 0:
                print(f"  {i}/{len(wanted)} {dict(outcomes)}", file=sys.stderr)
    print(dict(outcomes), file=sys.stderr)


# --- building cases ----------------------------------------------------------------------------


def instance_files(
    row: dict[str, str],
) -> tuple[dict[str, str | None], dict[str, str | None]] | None:
    """The touched files before and after the gold change; None when a file is missing."""
    base: dict[str, str | None] = {}
    for patch in (row["patch"], row["test_patch"]):
        for old, _new in patches.touched(patch):
            if old is not None and old not in base:
                text = read_base(row["repo"], row["base_commit"], old)
                if text is None:
                    return None
                base[old] = text
    try:
        after = patches.apply(patches.apply(base, row["patch"]), row["test_patch"])
    except patches.PatchError:
        return None
    return base, after


def changes_of(base: dict[str, str | None], after: dict[str, str | None]) -> list[FileChange]:
    out = []
    for path in sorted(set(base) | set(after)):
        before, now = base.get(path), after.get(path)
        if before != now:
            out.append(FileChange(path, before, now))
    return out


def _changed_lines(before: str | None, after: str) -> set[int]:
    old, new = (before or "").splitlines(), after.splitlines()
    lines: set[int] = set()
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if tag in {"replace", "insert"}:
            lines.update(range(j1 + 1, j2 + 1))
    return lines


def candidate_tests(
    base: dict[str, str | None], after: dict[str, str | None]
) -> list[tuple[str, str]]:
    """(path, node ID) of tests that exist before and after the change and check something."""
    found = []
    for path, text in sorted(after.items()):
        old = base.get(path)
        if text is None or old is None or not is_test_file(path):
            continue
        try:
            old_tests, new_tests = parse_module(old), parse_module(text)
            import ast

            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            continue
        for node_id, case in new_tests.items():
            if case.helper or node_id not in old_tests:
                continue
            fn = find_test(tree, node_id)
            if fn is not None and check_statements(fn):
                found.append((path, node_id))
    return found


def _summary(report: Report) -> list[dict[str, object]]:
    return [
        {
            "rule": f.rule,
            "level": f.level.value,
            "path": f.path,
            "test": f.test,
            "message": f.message,
        }
        for f in report.findings
    ]


def _detected(
    report: Report, op: Operator, path: str, node_id: str | None, *, any_rule: bool = False
) -> str:
    """The best level at which the expected rule (or any rule) reports the injected cheat."""
    best = ""
    for f in report.findings:
        if (f.rule != op.rule and not any_rule) or f.path != path:
            continue
        if node_id is not None and f.test not in {node_id, None}:
            continue
        if not best or LEVELS[f.level.value] > LEVELS[best]:
            best = f.level.value
    return best


def cases(row: dict[str, str], seed: int) -> list[dict[str, object]] | None:
    """The gold case and one case per operator for an instance; None when it cannot be rebuilt."""
    files = instance_files(row)
    if files is None:
        return None
    base, after = files
    report = check(changes_of(base, after))
    record = {"instance": row["instance_id"], "repo": row["repo"]}
    out: list[dict[str, object]] = [
        {**record, "case": "gold", "verdict": report.verdict.value, "findings": _summary(report)}
    ]
    rng = random.Random(f"{seed}:{row['instance_id']}")
    tests = candidate_tests(base, after)
    production = [p for p, t in after.items() if t is not None and is_production_python(p)]
    for op in OPERATORS:
        mutated = dict(after)
        target_path: str | None = None
        node_id: str | None = None
        if op.kind == "test":
            for path, candidate in rng.sample(tests, min(len(tests), 6)):
                text = after[path]
                assert text is not None
                new_text = op.apply(text, candidate)
                if new_text is not None:
                    mutated[path], target_path, node_id = new_text, path, candidate
                    break
        elif op.kind == "conftest" and tests:
            directory = PurePosixPath(tests[0][0]).parent
            target_path = str(directory / "conftest.py")
            mutated[target_path] = op.apply(after.get(target_path))
        elif op.kind == "production":
            for path in production:
                text = after[path]
                assert text is not None
                new_text = op.apply(text, _changed_lines(base.get(path), text))
                if new_text is not None:
                    mutated[path], target_path = new_text, path
                    break
        if target_path is None:
            continue
        report = check(changes_of(base, mutated))
        detected = _detected(report, op, target_path, node_id)
        out.append(
            {
                **record,
                "case": op.name,
                "path": target_path,
                "test": node_id,
                "detected": detected,
                "anything": _detected(report, op, target_path, node_id, any_rule=True),
                "verdict": report.verdict.value,
                "findings": _summary(report) if not detected else [],
            }
        )
    return out


def run(split: str, seed: int, workers: int) -> None:
    RESULTS.mkdir(exist_ok=True)
    skipped = 0
    with (
        (RESULTS / f"swebench-{split}.jsonl").open("w", encoding="utf-8") as out,
        concurrent.futures.ProcessPoolExecutor(workers) as pool,
    ):
        for records in pool.map(cases, rows(split), [seed] * 100_000, chunksize=4):
            if records is None:
                skipped += 1
                continue
            for record in records:
                out.write(json.dumps(record) + "\n")
    print(f"skipped {skipped} instances whose files could not be rebuilt", file=sys.stderr)


# --- report ------------------------------------------------------------------------------------


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def _pct(k: int, n: int) -> str:
    if n == 0:
        return "–"
    low, high = wilson(k, n)
    return f"{100 * k / n:.1f}% [{100 * low:.0f}, {100 * high:.0f}]"


def report(split: str) -> str:
    records = [
        json.loads(line)
        for line in (RESULTS / f"swebench-{split}.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    gold = [r for r in records if r["case"] == "gold"]
    lines = [
        f"# Layer 1 on SWE-bench `{split}`",
        "",
        f"Dataset: `{DATASET}`, {len(gold)} instances rebuilt "
        f"from {len({r['repo'] for r in gold})} repositories.",
        "",
        "## Negatives: the maintainers' own fixes",
        "",
        "| Verdict | Instances | Share |",
        "|---|---|---|",
    ]
    verdicts = Counter(r["verdict"] for r in gold)
    for verdict in ("CAUGHT", "SUSPICIOUS", "INCONCLUSIVE", "CLEAN"):
        lines.append(f"| {verdict} | {verdicts[verdict]} | {_pct(verdicts[verdict], len(gold))} |")
    by_rule: dict[str, Counter[str]] = defaultdict(Counter)
    for r in gold:
        for rule, level in {(f["rule"], f["level"]) for f in r["findings"]}:
            by_rule[rule][level] += 1
    lines += [
        "",
        "Instances with each finding:",
        "",
        "| Rule | caught | suspicious | note |",
        "|---|---|---|---|",
    ]
    for rule in sorted(by_rule):
        c = by_rule[rule]
        lines.append(f"| {rule} | {c['caught']} | {c['suspicious']} | {c['note']} |")

    lines += [
        "",
        "## Positives: one injected cheat per operator and instance",
        "",
        "| Operator | Expected | Cases | Expected rule at its level | Any rule |",
        "|---|---|---|---|---|",
    ]
    for op in OPERATORS:
        cases = [r for r in records if r["case"] == op.name]
        at_level = sum(
            1 for r in cases if r["detected"] and LEVELS[r["detected"]] >= LEVELS[op.level]
        )
        at_all = sum(1 for r in cases if r["anything"] in {"caught", "suspicious"})
        lines.append(
            f"| {op.name} | {op.rule} {op.level} | {len(cases)} | {_pct(at_level, len(cases))} "
            f"| {_pct(at_all, len(cases))} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["fetch", "run", "report"])
    parser.add_argument("--split", default="dev")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.split, args.workers)
    elif args.command == "run":
        run(args.split, args.seed, args.workers)
    else:
        text = report(args.split)
        (RESULTS / f"swebench-{args.split}.md").write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
