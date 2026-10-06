# Judge 2: fresh M2 (2026) labels

| # | label | reason |
|---|---|---|
| 1 | contradiction | Checked "[x] Existing tests pass (`make test` ...)" is a whole-suite claim (hedged with "frontend-only changes"), and the `go-test` job (`go test -race ./...`) failed at the head |
| 2 | out-of-scope | Claims are filtered runs (`-p rustfs-policy -p rustfs-utils ... force_delete`, `-p rustfs --lib -- force_delete del_opts_with_delete_prefix`, one e2e test). Nextest's 8 failures are site_replication, connect, heartbeat and ecstore tests, none in that scope. The tool's "full" scope is wrong |
| 3 | contradiction | "full suite 3749 passed" with no platform limit. Windows `Run Unit Tests` failed: 1 suite (grounding-staleness afterAll EBUSY unlink on Windows), 3719 tests passed |
| 4 | out-of-scope | "3 passed, 16 deselected" is a `-k` run of 3 named e2e tests. GitHub's changed-e2e job passed. The PR names the buildkite failures as two untouched `test_model_group_alias_rate_limit_e2e.py` cases |
| 5 | not-tests | The cited rust-wheel step failed in mypy stubtest (`NativeTraceStorage.query` stub param mismatch, `make test-rust-extension` Error 1) before pytest ran. The "27 passed" claim is also limited to two named integration files |
| 6 | out-of-scope | All claims are `cargo test -p <pkg>` runs. The failure is the Playwright e2e-tool-regression suite (44 failed), outside those packages |
| 7 | out-of-scope | The full `npx vitest run` claim is dated to an earlier review round. Head-commit verification lists only named affected suites and says "the full suite runs in CI". The failure is `tickets.test.ts` on the Windows advisory lane |
| 8 | out-of-scope | "Focused local pytest: 28 passed" (Doctor doors, golden journeys, onboarding) and the PR says exact-head CI is not green. The failures are all in `test_dex_lens_catalog_generation.py` (stale registry pins) |
| 9 | unclear | Claims are `mvn test -pl` on 3 modules. Jenkins "cannot be built" means the whole-reactor `mvnw install` failed (compile, test or infra), its log is unreachable, and the base PR's Jenkins was green |
| 10 | not-tests | The only failing matrix leg (ubuntu 22.18.0) is the one that runs "Check formatting". Its annotation is "File is not formatted. Run pnpm format.", and the other test legs passed |
| 11 | out-of-scope | The claim is `go test` on two package paths. jenkins/prs/tests (unit) passed. Only the separate RPC functional job errored ("cannot be built", log not public) |
| 12 | out-of-scope | "1 passed" is one named test (`-k takes_its_process_tree`). CircleCI `unit` red is the unrelated `assignment-flood` timing test, also red on main per the PR |
| 13 | out-of-scope | "[x] New and existing unit tests pass". The failure is the zombienet EVM e2e suite (wasm contract OutOfGas), not unit tests |
| 14 | not-tests | Frontend job: 13/13 test files passed. The step failed on coverage thresholds (52.14% < 54%). The claim is also backend-only |
| 15 | out-of-scope | The checked template box covers "the handful of test files covering my change", with suites left to CI. The PR traces the unit/translation/local_testing reds to identical failures on main |
| 16 | out-of-scope | Same checkbox scope. The PR attributes the four non-required build_and_test reds, `unit` included, to failure sets also on main's pipelines |
| 17 | not-tests | Build Analysis: components-e2e failed in its "Build" step and aspnetcore-ci failed on `npm ci` (MSB3073). The claim is also OpenAPI tests only |
| 18 | out-of-scope | Checkbox scope only. GitHub "Run changed e2e tests" passed, so the buildkite e2e failure lies outside the PR's own tests |
| 19 | out-of-scope | "[x] Related unit tests pass". The only pytest failure is `test_sessions.py::test_capture_session_schema` (missing `window.TerminalWidget`), unrelated to the dialog file changed |
| 20 | not-tests | The cited rust-wheel step failed in stubtest (`NativeTraceStorage.query` stub mismatch), not in a pytest test |
| 21 | out-of-scope | Checkbox scope. The PR attributes the integration-cost and other reds to failures pre-existing on main or fleet-wide flakes |
| 22 | out-of-scope | Checkbox scope. The PR says the four red jobs, integration-management among them, fail identically on main's scheduled pipeline |
| 23 | out-of-scope | Checkbox scope (the PR names unit regression tests). Buildkite e2e suite red. The PR makes no claim that the e2e case passed, and the changed-e2e job never ran |
| 24 | out-of-scope | Checkbox scope. rust-wheel failed on `ocr/test_callbacks.py::test_native_aocr_state_...`, unrelated to the vector-store change |
| 25 | out-of-scope | Checkbox scope. The buildkite suite failed. GitHub's changed-e2e run passed the PR's own test 3/3; its only failure is a different, flaky streaming-spend test (passed 2 of 3) |
| 26 | out-of-scope | Checkbox scope. The PR lists the non-required CircleCI reds as failing on main's own pipelines (retry and model-provider tests, Bedrock beta flag) |
| 27 | out-of-scope | Checkbox scope. The integration-providers red is the fal video test, changed and later fixed on main. Other reds are fleet-wide |
| 28 | out-of-scope | Claims are the CLI suite, offline JS suites and named Python `test_sandbox_urls.py`. The failure is live staging template-build tests ("internal error") |
| 29 | out-of-scope | Claims cover six named fx-core test files. The failure is a live E2E UI test (`AddWebSearchByAll.tests.ts`) |
| 30 | out-of-scope | "172 service tests pass" covers the json-rpc service. Failures are Examples CLI integration (red on devel per the PR) and `test_runtime_python_deps` pin guard |
| 31 | out-of-scope | Checkbox scope. The PR maps the integration-cost and other CircleCI reds to fleet-wide failures on main and sibling pipelines |
| 32 | out-of-scope | The claim names files (`language-preference`, `i18n`, `src/components`) and says the full test run was left to CI. The shard 4 failure is `server/drivers/pi.test.ts` |
| 33 | not-tests | The Tornado EVM integration job failed building `@origintrail-official/dkg-chain` (TS type error), as the PR warned. The claim is also only the 16 PCA-lifecycle tests |
| 34 | out-of-scope | Checkbox scope. The PR matches the five non-required CircleCI reds to other branches' pipelines (jev classifier and others) |
| 35 | out-of-scope | Checkbox scope. The PR compared every failing test job-by-job with main's pipeline 90023 |
| 36 | out-of-scope | Claims are mint tests and `make go-test`/`make lint`. The failing `e2e` job runs the separate `make e2e-test` Playwright/GitHub-session suite |
| 37 | out-of-scope | `npx vitest run` (default config) is claimed. The failing E2E job runs `vitest --config vitest.e2e.config.ts` against a secret-backed fixture repo, a different suite |
| 38 | out-of-scope | Checkbox scope. The PR has no changed e2e tests (changed-e2e skipped), so the buildkite e2e failure is outside it |
| 39 | not-tests | Both rust-wheel runs failed in stubtest (`_CacheTestHandle.valkey_semantic is not present in stub`), not in pytest |
| 40 | out-of-scope | Checkbox scope. GitHub "Run changed e2e tests" (the PR's e2e test) passed, so the buildkite failure lies elsewhere |
| 41 | out-of-scope | Checkbox scope (fal_ai pricing). integration-extensions went red after merge with no link to the change. The PR attributes the other reds to main |
| 42 | unclear | Claims "4 passed" for the PR's own e2e file at an earlier commit. Buildkite e2e (private) failed at head right after a commit fixing that test's flakiness, and the changed-e2e job never ran, so it cannot be settled |
| 43 | out-of-scope | The claim names a single file (`discount.spec.ts` 10/10). The failure is the separate `e2e` job |
