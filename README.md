# testreceipt

A receipt that a green test run was earned.

Coding agents sometimes make a failing test suite pass by changing the tests rather than the code.
They may delete or skip the failing test, loosen an assertion, end the test process early, or tell
CI to ignore the failure. testreceipt checks a change for these moves with fixed rules on the
syntax tree and the CI configuration. It does not ask a model for its opinion.

> Status: pre-alpha. The rules are being measured on real agent pull requests before a first
> release; expect breaking changes.

## Use

```bash
testreceipt check --base main            # the change from main's merge base to HEAD
testreceipt check --base main --json     # machine-readable report
testreceipt check --base main --fail-on suspicious
```

There are three levels of finding:

- **CAUGHT** needs hard evidence: either a known cheating device, or a change that can only hide failures.
- **SUSPICIOUS** marks a change of the right shape that a legitimate change of behaviour can also explain.
- **Notes** never change the verdict.

## Rules

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
| TR303 | production code refers to test files | suspicious |
| TR304 | production code branches on a test-mode switch | suspicious |
| TR401 | `\|\| true` and similar after a test command | caught |
| TR402 | `continue-on-error` on a test job | caught |
| TR403 | `--deselect` and `-k "not …"` (caught), `--ignore`, `-m "not …"`, narrower `testpaths` (suspicious) | caught or suspicious |
| TR404 | coverage threshold lowered | caught |
| TR405 | test command removed, commented out, disabled or reduced to `--collect-only` | caught or suspicious |
| TR406 | testreceipt's own step or configuration weakened | caught |

## License

MIT
