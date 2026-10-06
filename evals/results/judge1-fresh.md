# Judge 1: labels for sheet-fresh.md (43 cases)

| # | label | reason |
|---|---|---|
| 1 | contradiction | Checked "[x] Existing tests pass (`make test` ...)": `make test` is `go test ./...`, the same suite the failing go-test job runs (`go test -race ./...`). |
| 2 | out-of-scope | The claims cover filtered runs only (`force_delete`, `del_opts_with_delete_prefix`, `delete_authorization_test`). Workspace nextest failed 8 other tests (site_replication, ecstore init/peer/rebalance). |
| 3 | contradiction | Says "full suite 3749 passed". The Windows `Run Unit Tests` step ran vitest and a test failed (`grounding-staleness.test.ts`). |
| 4 | out-of-scope | The pass claims are the `-k`-selected spend-tracking e2e tests (3 passed). The description says Buildkite failed on two unrelated `test_model_group_alias_rate_limit_e2e.py` cases. |
| 5 | not-tests | The rust-wheel step failed in `mypy.stubtest` (stub/runtime parameter mismatch) before pytest ran. |
| 6 | out-of-scope | The claims cover specific cargo packages (smart-home, octos-cli, octos-agent). The failure is the separate Playwright e2e-tool-regression suite (44 failed). |
| 7 | contradiction | Says `npx vitest run` passed with 373 files and 4606 tests. The same vitest suite failed 1 test (`tickets.test.ts`) on the Windows lane. |
| 8 | out-of-scope | "Focused local pytest: 28 passed" covers the Doctor/door tests. Shard 2 failed only `test_dex_lens_catalog_generation.py`. |
| 9 | unclear | The claims are module-scoped (`mvn test -pl ...`). The Jenkins status only says "This commit cannot be built" and ci-maven is unreachable, so it is unknown whether tests failed or where. |
| 10 | not-tests | The ubuntu 22.18.0 leg failed only its "Check formatting" step (annotation "File is not formatted"). All other test legs passed. |
| 11 | out-of-scope | The claim covers `go test` on the transport/waku packages, and the Go `tests` Jenkins job passed. The separate functional `tests-rpc` suite failed. |
| 12 | out-of-scope | The pass claims are single tests/files (the prisma timeout test, pre_commit_lint, process helpers). The unit job failed on the unrelated `assignment-flood` timing test, which is red on main. |
| 13 | out-of-scope | The claim says "unit tests pass". The failure is the TypeScript zombienet E2E suite (wasm-contract test). |
| 14 | not-tests | The frontend job's tests all passed (103/103). The step failed on the coverage threshold. |
| 15 | out-of-scope | A template checkbox covers only "the handful of test files covering my change". The unit job failed on the fleet-wide `assignment-flood` test, outside those files. |
| 16 | out-of-scope | The same partial checkbox. The unit failure is the unrelated `assignment-flood` timing test (same on main). |
| 17 | not-tests | aspnetcore-components-e2e failed at its "Build" step (Bash exit 1), not in a test run. The claim covers OpenAPI tests only anyway. |
| 18 | out-of-scope | A partial checkbox. The PR's changed e2e tests passed in the GitHub "Run changed e2e tests" check at the head. The Buildkite e2e failure is elsewhere (its log is private). |
| 19 | out-of-scope | "Related unit tests pass" (the PR touches only `window_dialogs.py`). pytest failed in `test_sessions.py::test_capture_session_schema`. |
| 20 | not-tests | The rust-wheel step failed in `mypy.stubtest` (stub mismatch) before any pytest ran. |
| 21 | out-of-scope | A partial checkbox; the PR's tests are under tests/test_litellm. integration-cost (tests/integration) is red fleet-wide per the description. |
| 22 | out-of-scope | A partial checkbox. integration-management failed `test_saved_retry_setting...`, which the description says touches none of the PR's files. |
| 23 | out-of-scope | Only the partial template checkbox. The failure is the whole Buildkite e2e build (log private), and nothing shows the PR's own tests failed. |
| 24 | out-of-scope | A partial checkbox (vector-store tests). rust-wheel's pytest failed an unrelated OCR callback test (`tests/test_litellm_rust/ocr`). |
| 25 | out-of-scope | The claims are the checkbox plus one named e2e test (1 passed). The CI e2e failures hit other tests (e.g. `test_streaming_chat_completion_tracks_spend`). |
| 26 | out-of-scope | A partial checkbox (one responses test file). The integration-management reds are listed as failing on main too. |
| 27 | out-of-scope | A partial checkbox. integration-providers failed the fal H3 video test, which the description explains as a base/main issue. |
| 28 | out-of-scope | The claims are for named suites (CLI, JS offline suites, `test_sandbox_urls.py`). The Python SDK Windows run failed template build integration tests. |
| 29 | out-of-scope | "All affected fx-core test files pass". The failure is a separate E2E job (`AddWebSearchByAll.tests.ts`), the only failure of 24 E2E jobs. |
| 30 | out-of-scope | "172 service tests pass" covers the json-rpc service tests. The failure is the CLI examples integration test (retired `ai-cadquery` parts), which the description says is unrelated. |
| 31 | out-of-scope | A partial checkbox (streaming chunk tests). integration-cost is red fleet-wide per the description. |
| 32 | out-of-scope | The claims cover named vitest files ("full `pnpm test` left to CI"). Shard 4 failed `server/drivers/pi.test.ts`. |
| 33 | not-tests | The Tornado EVM agent job failed in the `dkg-chain` TypeScript build (type error), which the PR says will stay red. |
| 34 | out-of-scope | A partial checkbox (Slack/Teams alerting tests). integration-providers failed the fal H3 test, which the PR does not touch. |
| 35 | out-of-scope | A partial checkbox (MCP management tests). The integration-cost failures (23 `test_cost_tracking` cases) appear on main too. |
| 36 | out-of-scope | The claims are mint tests and `make go-test` (unit `go test ./...`). The failing job is the separate Playwright `make e2e-test`. |
| 37 | out-of-scope | `npx vitest run` is the unit config (1656 tests; all Lint & Test jobs passed). The failing job runs the separate `vitest.e2e.config.ts` suite. |
| 38 | out-of-scope | Only the partial template checkbox. The failure is the whole Buildkite e2e build (log private), and nothing shows the PR's own tests failed. |
| 39 | not-tests | Both rust-wheel runs failed in `mypy.stubtest` ("not present in stub") before pytest ran. |
| 40 | out-of-scope | A partial checkbox and one named e2e file. The changed-e2e GitHub check passed at the head, so the Buildkite e2e failure is elsewhere (log private). |
| 41 | out-of-scope | A partial checkbox (fal_ai tests under tests/test_litellm). integration-extensions runs tests/integration, which the PR does not touch. |
| 42 | out-of-scope | The claims are the checkbox and one e2e file (4 passed at an earlier commit). The failure is the whole Buildkite e2e build (log private), and nothing shows that file failed. |
| 43 | out-of-scope | The claim is "`discount.spec.ts` — 10/10 pass". The e2e job's merged report failed on provider e2e tests. |

Counts: contradiction 3, out-of-scope 32, not-a-claim 0, not-tests 7, unclear 1.
