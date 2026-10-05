# Second judge, batch C (caught findings)

Independent labels from the full PR diffs (`gh pr diff`) and, where needed, the files and CI config at the merge base. Labels follow `evals/ADJUDICATION.md`.

| # | PR | Label | Justified | Reason |
|---|---|---|---|---|
| 1 | https://github.com/fieldsoftheworld/ftw-baselines/pull/185 | correct | yes | The new conftest `pytest_sessionfinish` calls `os._exit(0)` on darwin + py3.12 before the terminal reporter prints failures, so that run always exits 0 (also in the macos-latest/3.12 CI job this PR adds). The PR body and docstring give an environment-specific reason: a DataLoader hang on Mac silicon with py3.12. Maintainers kept it on main. |
| 2 | https://github.com/ml-struct-bio/cryodrgn/pull/457 | false-alarm | - | The `pytest --collect-only` step is newly added to style.yml as an extra check. It never replaced a test run, and tests.yml still runs the full `pytest -n2` (now with coverage). |
| 3 | https://github.com/jeshraghian/snntorch/pull/382 | correct | yes | 20 assertions on the Conv2d/AvgPool export graph were replaced by an unconditional `pytest.xfail`. The PR states that conv2d export does not work after the move to the new nir API. The owner merged it and the xfail is still on master. |
| 4 | https://github.com/scoringengine/scoringengine/pull/992 | correct | no | A module-level `pytestmark = skip` turns off every Web UI integration test. CI still runs `tests/integration/run.sh` in Docker, where these tests could run, so the stated reason ("require Docker") does not hold there. Detail: the tool says "no reason given", but a positional reason is present. The PR was closed. |
| 5 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/789 | correct | no | `test_invalid_numeric_fallback` ran at base and now always calls `pytest.skip`. The reason, "reload unstable in this environment", is a vague flakiness claim: no environment condition and no tracking issue. |
| 6 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/789 | correct | no | Same unconditional `pytest.skip`, here in `test_server_starts_with_env_port`, which ran fully at base. Same vague reason. |
| 7 | https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/789 | correct | no | Same unconditional `pytest.skip`, here in `test_build_rest_none`. The PR is titled "remove skips" but adds these three. |
| 8 | https://github.com/graphistry/pygraphistry/pull/708 | correct | no | Six schema-validation tests get `@pytest.mark.skip` after the branch removed the `schema_effects` entries that exist in the base's `call_safelist.py`, apparently through a stale cherry-pick in a docs PR. So "not yet implemented" is false relative to the base. The PR was closed. |
| 9 | https://github.com/mlflow/mlflow/pull/17454 | correct | no | `isinstance(result, Judge)` and the name check were dropped from `test_concrete_optimizer_implementation`, leaving only "does not raise". This happened in an unrelated refactor commit with no reason given. The removed asserts only touched a test double, so the impact is low. |
| 10 | https://github.com/Ziems/arbor/pull/108 | correct | yes | The unit and integration pytest steps were replaced by `echo`, coverage upload was set to `if: false`, and the whole tests/ directory was deleted. The owner authored and merged it, saying the tests are removed until the suite is rewritten. |
| 11 | https://github.com/microsoft/graphrag/pull/1944 | correct | no | `test_create_blob_storage` (no skip at base) is now skipped unconditionally. The integration workflow installs Azurite on both ubuntu and windows, so the reason ("emulator not available in this environment") describes the agent's sandbox, not CI. |

Counts: correct 10 (justified yes 3, no 7), false-alarm 1, unclear 0.
