# testreceipt

When a coding agent's pull request says "all tests pass", do the tests pass? We checked agent pull
requests from 2025 and 2026 against CI at the same commit. This repository has the study, its data
and labels, and the tool that did the checking.

## Findings

Agent pull requests in repositories with 100+ stars that claimed passing tests and had a CI result:

| | 2025 (AIDev) | June–September 2026 |
|---|---|---|
| Pull requests | 481 | 644 |
| Said the tests pass; CI's tests failed at that commit | **8.7%** | **0.3%** (2) |
| Said a part of the suite passes; the suite failed | 7% | 4.7% |
| CI's tests failed when the description said nothing about tests | 22% | 3–12%, by agent |

- **In 2025 the claim carried little information.** CI's tests failed on 18% of pull requests
  that claimed passing tests and on 22% of those that said nothing.
- **By 2026, whole-suite claims contradicted by CI had become rare.** What remains is scope: a
  claim about one package or one command, while the suite failed somewhere else.
- **Agents changed how they report tests.**
  - Copilot went from 23% of descriptions saying tests pass to 1 of 306.
  - Cursor, Devin and Codex now say it in about 30% of their pull requests, usually naming the
    command they ran: `cargo test -p <crate>`, `pytest -k <name>`.

Every case where a claim met a failing test step was labelled by two model judges, with
disagreements settled against the evidence. Method, per-agent tables and limitations:
[docs/study.md](docs/study.md).

## The tool

testreceipt reads a pull request description, finds its claims about tests and their scope, and
reconciles them with the tests' results at the same commit. It also has fixed rules that flag a
change weakening its own tests.

**Status: research tool.** On held-out 2026 pull requests:
- CONTRADICTED was right 2 times in 12;
- SCOPED was right 23 times in 28.

The misses came from two sources:
- claims scoped by a command (`-p`, `-pl`, `-k`), which the rules read as whole-suite claims;
- CI steps named like test runs that had failed on something else.

So by default it reports and never fails a build.

```bash
uvx --from git+https://github.com/amos689/testreceipt@v0.1.0 testreceipt claims --pr owner/repo#123
```

**Check what a pull request says against its tests:**

```bash
testreceipt claims --pr owner/repo#123                       # reads its CI through the GitHub API
testreceipt claims --description pr.md --junit report.xml    # against a test run's JUnit XML
```

| Verdict | Meaning |
|---|---|
| CONTRADICTED | It says the tests pass; the tests failed at the same commit |
| SCOPED | It says some tests pass (a package, the new tests, one platform); the suite failed |
| COUNT | It says N tests pass; the tests failed, and N may not be the whole suite (a JUnit total settles it) |
| UNSTATED | It lists test commands without saying how they went; the tests failed |
| CONSISTENT, UNVERIFIED, REPORTS FAILURES, NO CLAIM | As named |

`--fail-on contradicted` or `--fail-on scoped` makes these verdicts fail the command.

**Check whether the change weakens tests:**

```bash
testreceipt check --base main                          # fixed rules on the diff
testreceipt check --base main --run "python -m pytest -q"
```

- `--run` also runs the tests at the base, at the head, and on the head's code with the base's
  tests. A test that the change broke, and that was then skipped or loosened, becomes **caught**.
- The other findings are **suspicious**: changes of the right shape that a deliberate change of
  behaviour can also explain.
- **Precision of caught findings** on three batches of agent pull requests that each rule version
  had not seen: 11 of 17, 6 of 11, then 8 of 9. The latest rules have not met a fourth batch.
- **Two rules were right every time:**
  - unconditional skip or xfail of an existing test (17 of 17);
  - a lowered coverage gate.

**In GitHub Actions:**

```yaml
- run: python -m pytest --junitxml=report.xml
- uses: amos689/testreceipt@v0.1.0
  if: always()
  with:
    junit: report.xml
```

The action writes the receipt to the job summary and keeps it updated in one comment on the pull
request.

**In Claude Code:** a Stop hook. A turn may end on "tests pass" when the session's own test runs
contradict the claim, or when no run since the last edit backs it. The hook then sends the agent
back once to run them. Its precision has not been measured.

```
/plugin marketplace add amos689/testreceipt
/plugin install testreceipt@testreceipt
```

## Rules for test changes

| ID | Finding | Level |
|---|---|---|
| TR101 | a test's checks are emptied, made always-true, cut off by an early `return`, or all removed | caught |
| TR102 | some checks removed | suspicious |
| TR103 | checks wrapped in a `try` block that swallows the failure | caught |
| TR104 | an exact check replaced by a weaker one (`==` by `is not None`, a broader exception) | suspicious |
| TR105 | a computed expected value replaced by a literal | suspicious (other changed values: note) |
| TR106 | a tolerance loosened (`approx`, `assert_allclose`, `places`, `abs(a - b) < eps`) | suspicious |
| TR110 | tests removed | suspicious |
| TR111 | a test now skipped or marked xfail | caught when unconditional, suspicious when conditional |
| TR112 | parametrized cases removed | suspicious |
| TR120 | mocks added (to an integration test) | note (suspicious) |
| TR121 | a new test that checks nothing | note |
| TR201 | a pytest hook rewrites test reports, or a test is reported without being run | caught |
| TR202 | tests dropped from collection | suspicious |
| TR203 | test code ends the process before failures are reported | caught (suspicious inside a test function, where pytest reports it as a failure) |
| TR301 | `__eq__` that always returns True | caught |
| TR302 | production code checks whether pytest is running | suspicious |
| TR303 | production code opens test files | suspicious |
| TR304 | production code branches on a test-mode switch | suspicious |
| TR401 | `\|\| true` and similar after a test command that used to fail the build | caught (a new masked run: suspicious) |
| TR402 | `continue-on-error` on a test job | caught |
| TR403 | `--deselect` and `-k "not …"` (caught), `--ignore`, `-m "not …"`, narrower `testpaths` (suspicious) | caught or suspicious |
| TR404 | coverage threshold lowered | caught |
| TR405 | test command removed, commented out, disabled or reduced to `--collect-only` | caught or suspicious |
| TR406 | testreceipt's own step or configuration weakened | caught |

## Data

- **2025:** [AIDev](https://huggingface.co/datasets/hao-li/AIDev) (CC BY 4.0), revision `c63c8a5`.
- **Rule development:** [SWE-bench](https://github.com/princeton-nlp/SWE-bench) (MIT).
- **2026:** collected from GitHub's public API by [`evals/fresh.py`](evals/fresh.py).
- **Labels and judge sheets:** [`evals/`](evals/).

The judges were models; the limitations section of the study says what that means for the numbers.

## License

MIT
