# How findings on real pull requests are judged

Written before any held-out finding was looked at. Each sampled finding gets one label.

| Label | Meaning |
|---|---|
| `correct` | The change does what the finding says, and it makes the test suite check less: a test no longer runs, checks less, accepts more, or CI stops running or stops failing on some tests. |
| `false-alarm` | The finding misreads the change. Examples: the check moved elsewhere and still runs, a test was renamed and the pairing missed it, a parse or patch artefact, or the "test command" is not a test run. |
| `unclear` | The diff alone cannot settle it. The reason is noted. |

A `correct` finding is further marked `justified` when the pull request or the code gives a reason a maintainer would accept:
- the tested behaviour was removed or changed on purpose;
- a skip reason names an environment the test cannot run in;
- a flaky test is tracked in an issue.

`justified` is reported as a share of `correct`. It does not change precision: testreceipt reports that the suite checks less, and the reviewer decides whether that is acceptable.

**Precision at a level** = `correct` / (`correct` + `false-alarm`), with `unclear` reported separately.

## Procedure

1. Sample with `evals/aidev.py sample` (seeded): every caught finding if there are 100 or fewer, otherwise 100 at random; plus 100 suspicious findings at random. Use held-out pull requests only.
2. The first judge reads the pull request's diff for the file (the `file_at_head` link and the PR's files view) and writes a label and a one-line reason.
3. A second, independent model pass labels the same items from the same material without seeing the first labels.
4. The person spot-checks the disagreements and a random 20%.
5. Report the agreement rate, the final labels and the reasons in `evals/results/aidev-gate.md`.
