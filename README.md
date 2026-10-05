# testreceipt

A receipt for a pull request's tests. When a coding agent writes "all tests pass", testreceipt
checks that against what the tests did at the same commit. It also checks whether the change itself
weakened the tests.

> Status: pre-alpha. The rules are measured on real agent pull requests before a first release.
> Expect breaking changes.

## Why

In 2025, agent pull requests that said "all tests pass" in their description often had failing tests
in CI at the same commit, and rather more said it about a subset they had picked. We checked 481
agent PRs from AIDev that made such a claim and had a CI result; two judges reviewed each failing case
(details: [`evals/results/`](evals/results/)).

| Agent | PRs with a CI result | Said all tests pass, tests failed | Also counting claims about a subset |
|---|---|---|---|
| Claude Code | 178 | 11.2% | 20.8% |
| Copilot | 212 | 7.1% | 10.8% |
| Devin | 68 | 4.4% | 13.2% |
| Codex (lists the commands it ran) | 68 | 0% | 0% |

CI failed about as often on PRs that claimed passing tests (18%) as on PRs that said nothing about
tests (22%). Codex differs: it lists the commands it ran and says when they failed.

## Use

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

On the 95 adjudicated cases from the study, CONTRADICTED is right 41 times out of 44. These cases
were also used to develop the rules, and a measurement on 2026 pull requests is in progress.

**Check whether the change weakens tests:**

```bash
testreceipt check --base main                          # fixed rules on the diff
testreceipt check --base main --run "python -m pytest -q"
```

`--run` also runs the tests at the base, at the head, and on the head's code with the base's tests.
A test that the change broke, and that was then skipped or loosened, becomes **caught**. The other
findings are **suspicious**: changes of the right shape that a deliberate change of behaviour can
also explain.

On agent PRs no rule saw before, caught findings were right 8 times out of 9. Two rules have caught
weakening in every batch so far:
- unconditional skip/xfail of an existing test (17 of 17);
- a lowered coverage gate.

**In GitHub Actions:**

```yaml
- run: python -m pytest --junitxml=report.xml
- uses: amos689/testreceipt@v0   # not published yet
  if: always()
  with:
    junit: report.xml
```

The action writes the receipt to the job summary and keeps it updated in one comment on the pull
request.

**In Claude Code:** add a Stop hook. When a turn ends on "tests pass" that the session's own test
runs contradict, or that no run since the last edit backs, the hook sends the agent back once to run
them:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "testreceipt hook claude-stop"}]}]}}
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

## License

MIT
