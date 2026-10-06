# When a coding agent says "all tests pass"

*Draft, 2026-10-06. Both measurements are complete.*

Coding agents open pull requests with descriptions such as "All existing tests pass" or "✅ 42 tests
passing". Reviewers read these lines. We checked them against what CI's tests did at the same
commit.

## Summary

- **2025 (AIDev, repositories with 100+ stars):** 481 agent pull requests said in their description
  that tests pass and have a CI test result at the head commit. In 42 of them (**8.7%**) CI's tests
  failed at that commit. In another 34 (**7%**) the claim was about a subset the agent picked
  ("all 53 permission endpoint tests pass"), while the suite failed.
- **The claim carries little information:** CI's tests failed on 18% of pull requests that claimed
  passing tests, on 22% of those that said nothing about tests, and on 33% of those that reported
  failures.
- **It differs by agent.** Codex lists the commands it ran and says when they fail; none of its 68
  such pull requests with a CI result was contradicted.
- **2026 looks different.** In June–September 2026, 644 agent pull requests in such repositories
  claimed passing tests and have a CI result. Only **2 (0.3%)** were contradicted by failing tests at
  the same commit.
  - Mismatches are now mostly claims that say which part of the suite was run, while CI failed
    elsewhere: 30 cases (4.7%), often in end-to-end suites or in failures the pull request
    attributes to `main`.
  - Agents now report the exact commands they ran (`cargo test -p <crate>`, `pytest -k <name>`).
- **Copilot stopped claiming.** 23% of its 2025 descriptions said tests pass; 1 of 306 in 2026.
  Cursor, Devin and Codex now do so in about 30% of their pull requests.

## Data

- **2025.** AIDev (`hao-li/AIDev`, revision `c63c8a5`): 71,677 agent pull requests in
  repositories with more than 100 stars, opened from December 2024 to October 2025 by OpenAI Codex,
  GitHub Copilot, Devin, Cursor, Claude Code and Google Jules.
- **2026.** Agent pull requests opened from June to September 2026, found through GitHub's search
  by each agent's signature, in repositories with at least 100 stars (`evals/fresh.py`).
  - The signatures: Copilot, Devin and Jules as app authors; Codex's `codex` label; the links
    Claude Code and Cursor leave in the description.
  - Searches cover random four-hour windows of random days, paced to the search limit.
  - The unfiltered sample:

    | Agent | Pull requests |
    |---|---|
    | Claude Code | 1,153 |
    | Devin | 1,117 |
    | Cursor | 528 |
    | Copilot | 306 |
    | Codex | 281 |
    | Jules | 13 |

## Method

1. **Claims.** `testreceipt.claims` reads each description line by line and keeps lines that
   report passing tests.
   - It skips:
     - unticked template boxes;
     - merge requirements ("should not be merged until:");
     - quoted issue text;
     - plan steps;
     - pass rates below 100%;
     - "N/M passing" with N < M, which reports failures;
     - reported speech.
   - Each claim gets a scope:
     - **full**: "All tests pass", "All existing tests pass (252 tests)";
     - **part**: a named package, the new tests, a platform, a path, or a list of test files below
       the claim;
     - **count**: "All 38 tests pass", where the text cannot say whether 38 is the whole suite.
2. **CI.** For the head commit we read the check runs, the steps of GitHub Actions jobs, and commit
   statuses. CI logs expire after 90 days, so a test result is a step or job whose name says it runs
   tests ("Run tests", "pytest", "test (3.11)") and that is not lint, formatting, docs or
   deployment. Passing and failing results are read the same way.
3. **Adjudication.** Every 2025 case where a claim met a failing test step was labelled
   independently by two model judges, who read the full description and the check names on GitHub.
   - They agreed on 84 of 95 cases.
   - The author resolved the rest against the evidence.
   - Labels: contradiction, out-of-scope (a part claim), not a claim, not a test failure, unclear.
4. **The tool's precision.**
   - On those 95 cases, testreceipt's whole-description verdict CONTRADICTED is right 41 times in
     44 and finds 41 of the 45 contradictions.
   - These cases were also used to develop the rules, so this is not a held-out number.
   - **On the held-out 2026 cases it fails:** CONTRADICTED was right on 2 of 12 decided cases.
     - The 2026 descriptions name filtered commands (`mvn test -pl module`, `-k name`), which the
       scope rules did not read as narrowing the claim.
     - About one in five failing steps named like test runs failed for other reasons: stubtest,
       formatting, coverage thresholds, build. With logs available, judges could tell; names alone
       cannot.
     - SCOPED was right on 23 of 28 decided cases.

## Results

### 2025

| Agent | PRs with a claim and a CI result | Contradicted | Also counting part claims |
|---|---|---|---|
| Claude Code | 178 | 20 (11.2%, 95% CI 7–17) | 37 (20.8%) |
| Copilot | 212 | 15 (7.1%) | 23 (10.8%) |
| Devin | 68 | 3 (4.4%) | 9 (13.2%) |
| Cursor | 17 | 3 (18%) | 6 (35%) |
| Codex (claims implied by listed commands) | 68 | 0 | 0 |

Excluding the one repository with the most cases (oven-sh/bun) gives 38 of 465 (8.2%). The 42
contradictions come from 32 repositories.

CI test failure rate by what the description says (automatic classification, all agents):

| The description | CI's tests failed |
|---|---|
| claims passing tests | 18.1% [14.9, 21.8] |
| says nothing about tests | 21.8% [17.1, 27.3] |
| reports failing tests | 33.3% [26.8, 40.6] |

### 2026

The unfiltered sample. Every case where a claim met a failing test step was labelled by two judges,
who agreed on 41 of 43; the judges could read CI logs where they still existed.

| Agent | Claim passing tests | Claimers with a CI result | Contradicted | Part claim, suite failed |
|---|---|---|---|---|
| Devin | 32.1% | 290 | 1 | 18 |
| Claude Code | 22.5% | 189 | 1 | 8 |
| Cursor | 30.7% | 113 | 0 | 4 |
| Codex | 29.9% | 51 | 0 | 0 |
| Copilot | 0.3% | 1 | 0 | 0 |
| **All** | | **644** | **2 (0.3%, 95% CI 0.1–1.1)** | **30 (4.7%)** |

CI's tests failed on 2.6–11.6% of pull requests whose description said nothing about tests,
depending on the agent, against 22% in 2025.

### 2025 and 2026 compared

| Agent | Explicit "tests pass" in descriptions, 2025 | 2026 |
|---|---|---|
| Copilot | 23.4% | 0.3% |
| Claude Code | 27.8% | 22.5% |
| Devin | 10.3% | 32.1% |
| Cursor | 1.6% | 30.7% |
| Codex | 0.2% (it listed commands instead) | 29.9% |

The 2025 contradiction rate is an upper bound: logs had expired, and in 2026 about one in five
failing steps named like test runs had not failed on tests. Even so, whole-suite claims contradicted
by CI went from about one in eleven to about one in three hundred.

## Limitations

- **The judges are models.** A person spot-checked the disagreements, but not every label.
- **CI logs had expired for 2025.** A failing step named like a test run is taken as failing tests;
  when the claim covers what that step runs, it is counted as a contradiction.
- **"Tests pass" may refer to the agent's own environment.** A contradiction means the claim and CI
  disagree at the same commit. It does not mean the agent lied.
- **Only explicit claims are counted.** An agent that never claims anything is never contradicted.
- **The two years were sampled differently.**
  - 2025 is AIDev's collection.
  - 2026 comes from GitHub search on each agent's signature. Agents whose pull requests carry no
    signature, and repositories under 100 stars, are missing from both.
- **The 2026 tool verdicts were frozen before measurement,** and the 2026 cases were not used to
  change the rules.

## Data and licenses

- AIDev (CC BY 4.0): Hao Li et al., <https://huggingface.co/datasets/hao-li/AIDev>.
- SWE-bench (MIT), used for rule development only.
- The 2026 pull requests and CI results are public GitHub data, fetched in October 2026. Only
  labels, identifiers and short excerpts are kept in this repository.

## Reproduce

```bash
uv run --group evals python evals/claims_ci.py select && uv run --group evals python evals/claims_ci.py fetch-graphql
uv run --group evals python evals/claims_dev.py
uv run --group evals python evals/fresh.py collect && uv run --group evals python evals/fresh.py select
uv run --group evals python evals/fresh.py fetch && uv run --group evals python evals/fresh.py verdicts
```
