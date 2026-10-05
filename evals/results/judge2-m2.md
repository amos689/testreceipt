# Judge 2: M2 cases (sheet-m2.md)

I labelled each parsed claim line, reading it in the context of the full PR description (the AIDev `body` snapshot, which is the text the parser read). I judged failing checks by their names, using the cached check and status lists for the head commit. Where the description makes a broader claim elsewhere than the parsed line does, the reason notes it in "(description elsewhere: ...)".

| Case | Label | Reason |
|---:|---|---|
| 1 | contradiction | Unqualified "All existing tests pass", but 14 test-bun jobs failed (alpine/debian/ubuntu/darwin-14). |
| 2 | out-of-scope | The claim covers Windows only. Both Windows test-bun jobs passed; the failures are darwin and ubuntu only. |
| 3 | contradiction | Unqualified "All existing tests pass", but test-on-macos, test-on-windows and test-on-ubuntu all failed. |
| 4 | unclear | Bare Codex command with no stated result. The failing job is Proto.Remote.Tests (also a bare line, the next one); Proto.Actor.Tests itself was cancelled, not failed. |
| 5 | not-tests | The AppVeyor PR status is 'error', yet the same commit's AppVeyor branch build passed, as did every CircleCI test job (including end_to_end_cdc). No test failure is shown. |
| 6 | out-of-scope | The claim covers 51 parser+agent_utils tests, and the author says the full suite was not run. One whole-suite tests (3.10) shard failed; where is unknown. |
| 7 | not-a-claim | Listed under "This PR should not be merged until:" as a precondition, not a report. |
| 8 | not-a-claim | About the red-team prompt pass rate (8-15%), not software tests. |
| 9 | contradiction | Template box "passes all unit tests on make test-unit" was ticked selectively, but the unit "test" job failed. |
| 10 | contradiction | "All existing tests continue to pass", but Run Unit Tests failed. |
| 11 | contradiction | "All 42 tests pass" names no scope, and Core plus nearly every sublibrary test job (including OptimizationNLopt) failed. |
| 12 | contradiction | "All existing tests continue to pass", but the Run tests, storage and MongoStorage test jobs failed. |
| 13 | out-of-scope | The claim covers test/js/web/websocket/ only. Only one whole-suite job (darwin-14-aarch64) failed, and nothing places the failure in the websocket tests. |
| 14 | out-of-scope | The claim covers Playwright/e2e tests only; the failing job is test-playground-cli (CLI tests). |
| 15 | not-a-claim | This backport PR's body is the copied commit log of #886. The line comes from an intermediate commit message ("Ready for CI validation") about local syslog scenario tests. |
| 16 | contradiction | "All existing tests pass (252 tests)", but test (alldeps, 1.10) failed. |
| 17 | out-of-scope | "Tests added and passing" refers to the added compression tests. The failures are whole-suite test-bun jobs on 6 platforms, and nothing places them in those files. |
| 18 | out-of-scope | The claim covers the myaudio package only. The failing unit-tests job covers the whole repo; where it failed is unknown. |
| 19 | contradiction | "All 423 tests pass", but the CLI test job (Tests / Integrations Linux (Cli)) failed. |
| 20 | not-a-claim | A dependency version line (`vitest`: 3.2.4). |
| 21 | contradiction | "All tests pass successfully" (the list under it is behaviours, not a scope), but unit-tests failed. |
| 22 | not-a-claim | The line says 0 tests ran ("No tests here; Use browser tests"). |
| 23 | out-of-scope | The claim covers 53 permission endpoint tests. All matrix test jobs failed, but nothing shows the failures are in those tests. |
| 24 | unclear | Says the crate's tests were run but gives no result. The scope is one crate; the failing job is the whole rust-unit suite. |
| 25 | contradiction | Unqualified "All tests pass ✅", but the integration jobs failed (integration-app-harness memory/3.11, reflex-web, rx-shout-from-template). Note that all unit-tests jobs passed. |
| 26 | contradiction | Claims "74 automated tests with 100% pass rate" for the board-compare tool, but the tool's own test-board-compare job failed. |
| 27 | out-of-scope | The claim covers 39 DNS-related tests. Whole-suite test (3.9) failed; where is unknown. |
| 28 | contradiction | Unqualified "All tests pass successfully.", but darwin-14-aarch64-test-bun failed (the other platforms passed). |
| 29 | not-a-claim | Sample "Demonstrated Functionality" output from 2 example test files in a docs-only PR, not a report on this PR's tests. |
| 30 | contradiction | "Unit tests pass" (and "All existing tests continue to pass"), but the unit test jobs on py3.9-3.12 all failed. |
| 31 | out-of-scope | "All tests pass:" lists exactly two files (server.spec.ts, 04459.test.ts). Only the darwin-14-aarch64 whole-suite job failed. |
| 32 | unclear | Bare `cargo test` with no stated result; tool-tests failed. |
| 33 | out-of-scope | The 42 tests are the realtime package's (34+8). The failing job is Test examples (framework-express), and realtime: Test was cancelled. (description elsewhere: "All existing tests pass") |
| 34 | contradiction | Unqualified "All existing tests continue to pass", but the React 18 / v8 Integration test job failed (v9 integration and e2e passed). |
| 35 | contradiction | "All existing tests continue to pass", but Testing Pods (the iOS test job) failed. |
| 36 | contradiction | "All existing tests continue to pass", but every test matrix job failed. |
| 37 | contradiction | "All existing tests continue to pass", but CircleCI test_even/test_odd/end_to_end and AppVeyor all failed. |
| 38 | contradiction | The agent ticked its own "[x] All tests passing", but test (3.11) failed. |
| 39 | unclear | The claim itself reports 772/773 with one known failure. The evidence job is the Node (JS) run, outside the RSpec scope, and the failing RSpec jobs may be that admitted failure. |
| 40 | contradiction | "All tests pass locally", but the CI heavy-fuzz job on the modified test files (SafeSend) failed. |
| 41 | out-of-scope | Ticked template box about a screenshot of the new test, and no screenshot is attached. The failing job is the full unit suite. (description elsewhere: blanket-ticked "passes all unit tests") |
| 42 | unclear | The claim covers parser tests. Conformance (parser plus other conformance snapshots) and Test Linux failed; whether parser tests caused it can't be told. |
| 43 | out-of-scope | 38/38 is the new cyrus-adapter-anthropic package (the category counts sum to 38). test (22.x) covers the whole monorepo; where it failed is unknown. |
| 44 | unclear | Bare `go test -short ./...` with no stated result; -short skips tests the CI test job may run. |
| 45 | out-of-scope | Same as 41: blanket-ticked screenshot box (no screenshot) about the new test only, while the full-suite test job failed. |
| 46 | contradiction | "All existing tests pass (252 tests)", but test (alldeps, 1.10) failed. |
| 47 | contradiction | "All tests pass including the new test coverage", but tests (3.10) failed. |
| 48 | contradiction | "All existing tests pass", but Core and several sublibrary test jobs failed. |
| 49 | contradiction | "All existing tests pass + new watchdog suite", but unit-tests failed. |
| 50 | out-of-scope | The claim covers 12 bundler_worker tests. Whole-suite test-bun failed on 13 platforms, and nothing places the failures in those files. |
| 51 | contradiction | "All existing tests continue to pass", but CircleCI test-amd_linux_test and test-windows_test failed. |
| 52 | not-a-claim | A ticked step in Copilot's plan checklist (a baseline check before changes); "Verify all tests pass" is still unticked. |
| 53 | contradiction | "All unit tests passing with race detector", but unit-tests failed. |
| 54 | unclear | The line itself admits 2 failures. The only evidence is an AppVeyor status of 'error' (not 'failure'), and all GitHub Actions build/test jobs passed. |
| 55 | contradiction | "All existing tests continue to pass", but Run unit tests and the integration tests failed (the release build also failed). |
| 56 | contradiction | "All existing tests pass (6870 tests)", but nearly every test job failed. |
| 57 | out-of-scope | The 68 tests are the new lock-component tests. Only one matrix job (PHP 8.3/Swoole 6.0.2) failed; where is unknown. |
| 58 | contradiction | The agent's own release checklist ticks "[x] All tests pass", but test (18.x) and Test Suite failed. |
| 59 | contradiction | "All existing tests pass", but test-bun failed on darwin-13/14 aarch64 and ubuntu baseline. |
| 60 | not-a-claim | The line is a file-list entry (`jest.config.js` - Improved configuration). (description elsewhere: "Unit Tests (Jest): ✅ Passing", which the failed jest (20/21) jobs contradict) |
| 61 | contradiction | "135 tests passing" for the whole yarn test run, but Test failed. |
| 62 | out-of-scope | The claim covers one seed fixture. The failing "test" is the unit test job (compile and test-ete passed). |
| 63 | not-a-claim | Quoted issue text: the task requirement "make all tests passed". |
| 64 | contradiction | "All unit and integration tests pass", but Run Unit Tests failed. |
| 65 | out-of-scope | The claim covers telemetry tests. One whole-suite tests (3.13) shard failed; where is unknown. |
| 66 | out-of-scope | The "15 tests" are the PR's manual mode/stub scenarios; the failing job is the pytest suite test (3.11). |
| 67 | contradiction | "All existing tests continue to pass", but the Test Results report and build (ubuntu-latest) failed. |
| 68 | contradiction | Unqualified "All tests pass successfully.", but Test on windows-latest failed. |
| 69 | out-of-scope | Same as 41: blanket-ticked screenshot box (no screenshot) about the new test only, while the full unit test job failed. |
| 70 | contradiction | Ticked template "[x] Tests passing (make test-community)", but the test job failed. |
| 71 | out-of-scope | The claim covers 23 ProcessPoolTaskRunner tests. All unit suites passed; only Integration tests @main and Client Compatibility failed. |
| 72 | out-of-scope | The claim covers cache tests. Only the whole-suite Node 20 macOS job failed; where is unknown. |
| 73 | out-of-scope | The claim covers 20 tests in tests/rag/embeddings/. One whole-suite tests (3.11) shard failed. |
| 74 | contradiction | "all tests continue to pass", but every test matrix job failed. |
| 75 | contradiction | "24,529+ tests passed across net8.0 and net9.0", but many net8.0 test jobs failed. |
| 76 | contradiction | "npm test ✓ All existing tests pass" with no Node version limit, but Run tests on Node.js 6 failed. |
| 77 | out-of-scope | The claim covers AWS cloudprovider tests; the failing test-and-verify job covers the whole repo (tests plus verify checks). |
| 78 | out-of-scope | The 340+ are the mouse tests (per the Testing section); the failing Parallel Unit Tests job covers the whole project. (description elsewhere: "All tests pass ... Total 12,800+") |
| 79 | unclear | Bare Codex command with no result, and it runs only TestDummy; the failing job is the whole test run. |
| 80 | out-of-scope | The claim covers 63 ForkId tests. The failing gates (unittests/integration/acceptance) cover the whole repo; buildDocker and spotless also failed. |
| 81 | out-of-scope | The claim covers bundler tests. Whole-suite test-bun failed on 4 platforms; where is unknown. |
| 82 | out-of-scope | The claim covers react-monaco-editor and react-docsite-components unit tests; the failing jobs are e2e, integration, bundle and screenshots. |
| 83 | out-of-scope | The claim covers 16 validation unit tests. The failing "Run tests" is an API test job, and the parameterised Run tests jobs passed. |
| 84 | out-of-scope | 24/24 are the new structuredClone tests; only the darwin-13-aarch64 whole-suite job failed. |
| 85 | contradiction | "All 261 tests pass", but test (alldeps, 1.10) failed. |
| 86 | out-of-scope | "All Tests Pass:" lists the PR's own groups (4/4, 5/5, 4/4). test-bun failed on all platforms, but nothing places the failures in those tests. |
| 87 | contradiction | The agent ticked its own "[x] All tests pass locally", but the Interface1/Interface2 test jobs failed. |
| 88 | contradiction | Template box "New and existing unit tests pass locally" was ticked selectively, but the test job failed. |
| 89 | out-of-scope | Covers a single unit test run via --grep, and the unit "test" job passed; the failing job is test-integration. |
| 90 | out-of-scope | The claimed suites (unit, QA/HQRM, SQL Server integration) all passed on Azure Pipelines; only AppVeyor (error/failure) failed. |
| 91 | unclear | Bare `pytest -v tests/` with no stated result; tests failed. |
| 92 | contradiction | Unqualified "All tests pass ✅", but test-bun failed on all 20 platforms. |
| 93 | out-of-scope | The claim covers the 5 new unit tests; the failing jobs are the whole Rust build/test, the smoke tests and the format check. |
| 94 | out-of-scope | The claim covers the new tests and the thread-safety tests. One whole-suite tests (3.12) shard failed. |
| 95 | contradiction | "All 64 tests pass (62 existing + 2 new)", which is the full suite, but Run Tests for linux and windows failed. |

## Counts

| Label | Count |
|---|---:|
| contradiction | 42 |
| out-of-scope | 34 |
| not-a-claim | 9 |
| not-tests | 1 |
| unclear | 9 |
| total | 95 |
