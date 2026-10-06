# Changelog

## [0.1.0] - 2026-10-06

First public version, released with the study in `docs/study.md`. The tool is a research tool: its
claim verdicts report and never fail a build unless `--fail-on` says so.

### Added

- `docs/study.md`: agent pull requests' test claims against CI, in 2025 (AIDev) and 2026, with labels
  and judge sheets in `evals/`.

- `testreceipt claims`: checks what a pull request description says about its tests against what
  the tests did at the same commit, read from the commit's CI (`--pr`) or from a test run's JUnit
  XML (`--junit`).
  - Verdicts: CONTRADICTED, SCOPED (the claim covers a part of the suite), COUNT ("N tests pass",
    settled by a JUnit total), UNSTATED, CONSISTENT, UNVERIFIED, REPORTS FAILURES and NO CLAIM.
  - With `--base`, the same receipt also covers the change's effect on the tests.
- `testreceipt check`: fixed rules on a change's tests, test infrastructure, production code and CI
  configuration, at three levels (caught, suspicious, note).
  - `--run` adds runner evidence from the base, the head, and the head's code with the base's tests.
- `testreceipt hook claude-stop`: a Claude Code Stop hook. It sends a turn back once when it ends on
  a claim of passing tests that the session's own test runs do not back.
- A GitHub Action that posts the receipt to the job summary and to one pull request comment.
- A Claude Code plugin with the hook and a skill for reporting test results.
