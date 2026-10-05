# Second judge, batch B (caught findings)

Independent pass over `sheet-caught-b.md`, labelled with the rules in `evals/ADJUDICATION.md`. Each PR's full diff and description were read with `gh pr diff` / `gh pr view`. Base-branch file versions were also read where the hunk was cut or the earlier state mattered.

| # | PR | Label | Justified | Reason |
|---|---|---|---|---|
| 1 | https://github.com/quay/quay/pull/4158 | false-alarm | - | `IS_TESTING` was already quay's test-config switch, and CI already sets `TEST=true`. Adding `PYTEST_CURRENT_TEST` only widens that existing switch, so no test checks less. |
| 2 | https://github.com/swarmauri/swarmauri-sdk/pull/1450 | correct | no | Both block-scalar round-trip tests are now non-strict xfail, so failures are accepted. The "fix" in parser.py changes only comments, and the vague reason names no environment or issue. |
| 3 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/2489 | correct | no | A module-level `pytest.skip` overrides the existing `skipif(patch/openai_agents)` guards and disables the CLI test everywhere. A reason is given, despite what the tool says, but "constrained environment" is just the agent's sandbox. |
| 4 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/2489 | correct | no | The offline CLI test is skipped unconditionally (a reason is given, despite what the tool says). The reason "requires networked LLM" is wrong: the test stubs `openai` and `generate_patch` and never calls a network. |
| 5 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/2489 | correct | no | The pipeline test is skipped unconditionally at module level. "Requires full sandbox setup" is vague, and the test already monkeypatches the docker sandbox and the LLM. |
| 6 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/2489 | correct | no | The sandbox test (local LLM, stubbed docker) is skipped unconditionally at module level. The reason is vague and is about the agent's environment only; the PR's purpose was to "fix test collection". |
| 7 | https://github.com/mlflow/mlflow/pull/17903 | correct | yes | The CI step running gateway tests under pydantic<2 is commented out. The PR states this is a deliberate first step in dropping pydantic v1 support, and maintainers merged it. |
| 8 | https://github.com/getzep/graphiti/pull/997 | correct | yes | The LLM integration test (and `test_invalidate_edges_partial_update`) gets `@pytest.mark.skip`, so it no longer runs. The PR moves these tests into CI for the first time and names LLM non-determinism, which is plausible, though no tracking issue is given. |
| 9 | https://github.com/SkBlaz/py3plex/pull/90 | false-alarm | - | Failure masking was already there: the replaced line was `python run_tests.py \|\| echo "...timed out..."`. CI never failed on test failures before this PR, so it does not stop failing now. |
| 10 | https://github.com/marin-community/marin/pull/1474 | correct | no | `pytestmark = skip` disables `test_slice_cache` everywhere (a reason is given, despite what the tool says). The test was already `skip_in_ci` with the note "fine locally", so the new skip removes it from the only place it ran. |
| 11 | https://github.com/openworm/sibernetic/pull/207 | false-alarm | - | `test_torch_backend.py` is a new file, and `run_all_tests.sh` ran no pytest before this PR. The `\|\| true` is on a newly added run, so nothing that used to gate CI stops gating (the new test is toothless, but nothing was weakened). |
| 12 | https://github.com/TauricResearch/TradingAgents/pull/132 | false-alarm | - | This is a new ad-hoc script that streams from `localhost:8000` and is run by hand as `python test_extended_fix.py`, not by a test run. The `sys.exit(0)` sits in its own timeout handler and weakens no existing test; under pytest a SystemExit would count as a failure, not end the run early. |
| 13 | https://github.com/vespa-engine/pyvespa/pull/1138 | false-alarm | - | `self.assertTrue(q == expected, msg)` becomes `assert q == expected, msg`, the same check in another form. All 41 asserts are kept in `GroupingQueries`, and the new `TestQueryBuilderGrouping` still calls all 41. |
| 14 | https://github.com/browser-use/browser-use/pull/2166 | correct | yes | The CI test `test_search_google_action` is skipped unconditionally, inside an unrelated voice-feature PR. The reason is accurate: the test really navigates to live Google, and that is a dependency a maintainer could plausibly accept skipping. |

## Counts

- correct: 9 (justified yes: 3, items 7, 8 and 14; justified no: 6)
- false-alarm: 5 (items 1, 9, 11, 12 and 13)
- unclear: 0

Note: for items 3, 4, 5, 6 and 10 the tool's message says "no reason given", but each skip does give a reason. The main claim (an unconditional skip) is still right, so these were labelled `correct`.
