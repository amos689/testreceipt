"""The gate's measurement M1: testreceipt on real agent pull requests from AIDev.

    uv run --group evals python evals/aidev.py select
    uv run --group evals python evals/aidev.py fetch [--limit N]
    uv run --group evals python evals/aidev.py run
    uv run --group evals python evals/aidev.py sample
    uv run --group evals python evals/aidev.py report

AIDev (hao-li/AIDev) lists pull requests that coding agents opened in repositories with more than
100 stars. `select` keeps those that touch Python test files or CI and test configuration. `fetch`
asks the GitHub API for each one's base and head and for its files, whose patches are relative to
the merge base, exactly as reviewers saw them; it then downloads each touched file at the head from
raw.githubusercontent.com and rebuilds the base version by reversing the patch. Everything lands in
`evals/.cache/aidev/` and `evals/.cache/raw/`, so `run` works offline.

The GitHub token comes from `gh auth token`; it is kept in memory and never printed or stored.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))

import patches

from testreceipt.changes import FileChange, is_conftest, is_python, is_test_file
from testreceipt.check import check
from testreceipt.rules.ci import kinds

ROOT = Path(__file__).parent
DATA = ROOT / ".data" / "aidev"
CACHE = ROOT / ".cache" / "aidev"
RAW = ROOT / ".cache" / "raw"
RESULTS = ROOT / "results"
DATASET = "hao-li/AIDev@c63c8a57a2de34fc03fa83722412824af4d8753b"
SELECTED = DATA / "selected.jsonl"
MAX_FILES = 300  # three pages of the files API
MAX_PYTHON_FILES = 80  # Python files fetched per pull request


def split(pr_id: int) -> str:
    """ "dev" for the fifth of pull requests the rules may be tuned on; "heldout" for the rest."""
    digest = hashlib.sha256(str(pr_id).encode()).digest()
    return "dev" if digest[0] % 5 == 0 else "heldout"


def relevant(path: str) -> bool:
    return is_python(path) or bool(kinds(path))


# --- select ------------------------------------------------------------------------------------


def select() -> None:
    repos = {r["id"]: r for r in pq.read_table(DATA / "repository.parquet").to_pylist()}
    prs = {
        p["id"]: p
        for p in pq.read_table(
            DATA / "pull_request.parquet",
            columns=[
                "id",
                "number",
                "agent",
                "state",
                "created_at",
                "merged_at",
                "repo_id",
                "repo_url",
                "html_url",
            ],
        ).to_pylist()
    }
    touches: dict[int, set[str]] = defaultdict(set)
    details = pq.ParquetFile(DATA / "pr_commit_details.parquet")
    for batch in details.iter_batches(batch_size=200_000, columns=["pr_id", "filename"]):
        for pr, name in zip(
            batch.column("pr_id").to_pylist(), batch.column("filename").to_pylist(), strict=True
        ):
            if not name:
                continue
            if is_test_file(name) or is_conftest(name):
                touches[pr].add("tests")
            if kinds(name):
                touches[pr].add("ci")
    chosen = []
    for pr_id, what in touches.items():
        pr = prs.get(pr_id)
        if pr is None:
            continue
        repo = repos.get(pr["repo_id"], {})
        full_name = pr["repo_url"].removeprefix("https://api.github.com/repos/")
        chosen.append(
            {
                "pr_id": pr_id,
                "repo": full_name,
                "number": pr["number"],
                "agent": pr["agent"],
                "state": pr["state"],
                "merged": pr["merged_at"] is not None,
                "created_at": str(pr["created_at"]),
                "url": pr["html_url"],
                "language": repo.get("language"),
                "stars": repo.get("stars"),
                "tests": "tests" in what,
                "ci": "ci" in what,
            }
        )
    # Python test changes first: they are what the gate measures; CI-only changes follow. Within
    # each group the order is random, so a fetch stopped early still leaves a random sample.
    random.Random(0).shuffle(chosen)
    chosen.sort(key=lambda r: not r["tests"])
    with SELECTED.open("w", encoding="utf-8") as out:
        for row in chosen:
            out.write(json.dumps(row) + "\n")
    counts = Counter((r["tests"], r["ci"]) for r in chosen)
    print(f"{len(chosen)} pull requests: {dict(counts)}", file=sys.stderr)


def selected() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SELECTED.read_text(encoding="utf-8").splitlines()]


# --- fetch -------------------------------------------------------------------------------------


class GitHub:
    def __init__(self) -> None:
        token = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        ).stdout.strip()
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "testreceipt-evals",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._lock = threading.Lock()
        self.remaining = 5000
        self.reset = 0.0

    def get(self, path: str) -> Any:
        for attempt in range(6):
            with self._lock:
                if self.remaining < 50 and time.time() < self.reset:
                    wait = self.reset - time.time() + 5
                    print(f"  rate limit: waiting {wait:.0f}s", file=sys.stderr)
                    time.sleep(wait)
                    self.remaining = 5000
            request = urllib.request.Request(f"https://api.github.com{path}", headers=self._headers)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    self._note(response.headers)
                    return json.loads(response.read())
            except urllib.error.HTTPError as error:
                self._note(error.headers)
                if error.code in {404, 410, 451}:
                    return None
                if error.code in {403, 429}:
                    retry = error.headers.get("Retry-After")
                    time.sleep(float(retry) if retry else 60 * (attempt + 1))
                    continue
                time.sleep(2**attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(2**attempt)
        raise RuntimeError(f"GitHub API failed for {path}")

    def _note(self, headers: Any) -> None:
        if headers is None:
            return
        with self._lock:
            if headers.get("X-RateLimit-Remaining") is not None:
                self.remaining = int(headers["X-RateLimit-Remaining"])
                self.reset = float(headers.get("X-RateLimit-Reset", 0))


def _raw(repo: str, sha: str, path: str) -> str | None:
    target = RAW / repo / sha / path
    missing = RAW / repo / sha / (path + ".404")
    if target.exists():
        return target.read_bytes().decode("utf-8", "replace")
    if missing.exists():
        return None
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"
    request = urllib.request.Request(url, headers={"User-Agent": "testreceipt-evals"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return data.decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                missing.parent.mkdir(parents=True, exist_ok=True)
                missing.write_bytes(b"")
                return None
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2**attempt)
    return None


def _fetch_pr(github: GitHub, row: dict[str, Any]) -> str:
    target = CACHE / f"{row['pr_id']}.json"
    if target.exists():
        return "cached"
    repo, number = row["repo"], row["number"]
    pull = github.get(f"/repos/{repo}/pulls/{number}")
    if pull is None:
        record: dict[str, Any] = {"status": "gone"}
    else:
        files: list[dict[str, Any]] = []
        for page in range(1, MAX_FILES // 100 + 1):
            batch = github.get(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}")
            if not batch:
                break
            files += batch
            if len(batch) < 100:
                break
        head = pull["head"]["sha"]
        kept = []
        python_files = 0
        for f in files:
            name = f["filename"]
            if not relevant(name):
                continue
            entry = {k: f.get(k) for k in ("filename", "status", "previous_filename", "patch")}
            if f["status"] not in {"removed", "added"} and f.get("patch") is not None:
                if is_python(name):
                    python_files += 1
                if python_files <= MAX_PYTHON_FILES or not is_python(name):
                    entry["fetched"] = _raw(repo, head, name) is not None
            kept.append(entry)
        record = {
            "status": "ok",
            "head": head,
            "base": pull["base"]["sha"],
            "merged": pull.get("merged"),
            "changed_files": pull.get("changed_files"),
            "truncated": len(files) >= MAX_FILES,
            "files": kept,
        }
    CACHE.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    return record["status"]


def fetch(limit: int | None, workers: int) -> None:
    github = GitHub()
    rows = selected()[:limit] if limit else selected()
    todo = [r for r in rows if not (CACHE / f"{r['pr_id']}.json").exists()]
    print(f"{len(todo)} of {len(rows)} pull requests to fetch", file=sys.stderr)
    outcomes: Counter[str] = Counter()
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(_fetch_pr, github, r): r for r in todo}
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


# --- run ---------------------------------------------------------------------------------------


def changes(row: dict[str, Any], record: dict[str, Any]) -> tuple[list[FileChange], list[str]]:
    """The pull request's changes, and the files that could not be rebuilt."""
    out: list[FileChange] = []
    missing: list[str] = []
    for f in record["files"]:
        name, status, patch = f["filename"], f["status"], f.get("patch")
        if patch is None:
            if status != "renamed":
                missing.append(name)
            continue
        try:
            if status == "added":
                out.append(FileChange(name, None, patches.added_text(patch, name)))
            elif status == "removed":
                out.append(FileChange(name, patches.removed_text(patch, name), None))
            else:
                if not f.get("fetched"):
                    missing.append(name)
                    continue
                after = _raw(row["repo"], record["head"], name)
                if after is None:
                    missing.append(name)
                    continue
                before = patches.reverse(after, patch, name)
                old = f.get("previous_filename")
                out.append(FileChange(name, before, after, old_path=old if old != name else None))
        except patches.PatchError:
            missing.append(name)
    return out, missing


def run() -> None:
    RESULTS.mkdir(exist_ok=True)
    counts: Counter[str] = Counter()
    with (RESULTS / "aidev.jsonl").open("w", encoding="utf-8") as out:
        for row in selected():
            target = CACHE / f"{row['pr_id']}.json"
            if not target.exists():
                continue
            record = json.loads(target.read_text(encoding="utf-8"))
            if record["status"] != "ok":
                counts["gone"] += 1
                continue
            found, missing = changes(row, record)
            report = check(found)
            verdict = report.verdict.value
            if missing and verdict == "CLEAN":
                verdict = "INCONCLUSIVE"
            counts[verdict] += 1
            out.write(
                json.dumps(
                    {
                        **row,
                        "split": split(row["pr_id"]),
                        "head": record["head"],
                        "verdict": verdict,
                        "missing": missing,
                        "truncated": record["truncated"],
                        "findings": [
                            {
                                "rule": f.rule,
                                "level": f.level.value,
                                "path": f.path,
                                "line": f.line,
                                "test": f.test,
                                "message": f.message,
                            }
                            for f in report.sorted_findings()
                        ],
                        "unchecked": [u.path for u in report.unchecked],
                    }
                )
                + "\n"
            )
    print(dict(counts), file=sys.stderr)


# --- sample for adjudication -------------------------------------------------------------------


def sample(per_level: int, seed: int) -> None:
    results = [
        json.loads(line)
        for line in (RESULTS / "aidev.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    results = [r for r in results if r["split"] == "heldout"]  # dev findings shaped the rules
    rng = random.Random(seed)
    sheet = []
    for level in ("caught", "suspicious"):
        items = [(r, f) for r in results for f in r["findings"] if f["level"] == level]
        picked = items if len(items) <= per_level else rng.sample(items, per_level)
        for r, f in picked:
            line = f"#L{f['line']}" if f["line"] else ""
            sheet.append(
                {
                    "pr": r["url"],
                    "agent": r["agent"],
                    "merged": r["merged"],
                    "rule": f["rule"],
                    "level": level,
                    "path": f["path"],
                    "test": f["test"],
                    "message": f["message"],
                    "file_at_head": f"https://github.com/{r['repo']}/blob/{r['head']}/{f['path']}{line}",
                    "population": len(items),
                }
            )
    target = RESULTS / "aidev-sample.jsonl"
    with target.open("w", encoding="utf-8") as out:
        for item in sheet:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"{len(sheet)} findings to adjudicate in {target}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["select", "fetch", "run", "sample"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--per-level", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.command == "select":
        select()
    elif args.command == "fetch":
        fetch(args.limit, args.workers)
    elif args.command == "run":
        run()
    else:
        sample(args.per_level, args.seed)


if __name__ == "__main__":
    main()
