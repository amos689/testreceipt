# Judge 1: M2 labels

| # | label | reason |
|---|---|---|
| 1 | contradiction | "All existing tests pass" under Tests, not scoped; test-bun jobs fail on 14 platforms |
| 2 | out-of-scope | Claim limited to "on Windows"; failing test jobs are darwin and ubuntu only |
| 3 | contradiction | "All existing tests pass" in Testing section, not scoped; test-on-macos/windows/ubuntu fail |
| 4 | unclear | Codex bare command with no stated result; failing Proto.Remote.Tests is listed bare too, so it can't be settled whether the line claims a pass |
| 5 | out-of-scope | Claim limited to the 39+ CDC tests; AppVeyor job runs `go test ./...` repo-wide on Windows and doesn't show a CDC failure |
| 6 | out-of-scope | Limited to the 51 parser + agent_utils tests (the description says the full suite was not run); failing job is the full suite |
| 7 | not-a-claim | Listed under "This PR should not be merged until:", so it is a merge requirement |
| 8 | not-a-claim | About the pass rate of red-team eval test cases, not test results |
| 9 | not-a-claim | Checked box from the LiteLLM PR template's pre-submission checklist |
| 10 | contradiction | "All existing tests continue to pass" under Testing; Run Unit Tests fails |
| 11 | contradiction | "All 42 tests pass" (NLopt PR) is not named as a subset; test (OptimizationNLopt, 1) and Core test jobs fail |
| 12 | contradiction | "All existing tests continue to pass"; Run tests / storage tests / MongoStorage tests fail |
| 13 | out-of-scope | Limited to WebSocket tests (test/js/web/websocket/); failure is the whole-suite darwin test-bun job |
| 14 | out-of-scope | Limited to existing Playwright tests; failing check is the playground CLI tests |
| 15 | out-of-scope | Commit-message line limited to "comprehensive scenario tests"; failing job is the whole Go test suite |
| 16 | contradiction | "All existing tests pass (252 tests)" is the full suite; test (alldeps, 1.10) fails |
| 17 | out-of-scope | Agent's own checklist "[x] Tests added and passing" covers only the added compression tests; failures are whole-suite test-bun jobs |
| 18 | out-of-scope | Limited to the myaudio package tests; failing unit-tests job is repo-wide |
| 19 | contradiction | "All 423 tests pass" is not scoped (likely the CLI tests); Tests / Integrations Linux (Cli) fails |
| 20 | not-a-claim | Line lists a dependency version (`vitest`: 3.2.4) |
| 21 | contradiction | "All tests pass successfully:" with a list of scenarios, no explicit scope; unit-tests job fails |
| 22 | not-a-claim | Reports that 0 tests ran ("No tests here; Use browser tests") |
| 23 | out-of-scope | Limited to 53 permission endpoint tests; failures are the whole-suite test matrix |
| 24 | not-a-claim | Says only that cargo test was run on one crate, with no result |
| 25 | contradiction | Plain "All tests pass ✅" with no scope; integration-app-harness and reflex-web tests fail |
| 26 | contradiction | "74 automated tests with 100% pass rate" are the board_compare tool's tests; their CI job test-board-compare fails |
| 27 | out-of-scope | Limited to 39 DNS-related tests; failing test (3.9) is the full suite |
| 28 | contradiction | "All tests pass successfully." with no explicit scope; darwin-14-aarch64 test-bun fails |
| 29 | out-of-scope | Pasted output covering only 2 demo test files; failures are the macOS Build&Test runs of the repo suite |
| 30 | contradiction | "Unit tests pass" (and the next line: all existing tests pass); the unit test jobs fail on every Python version |
| 31 | out-of-scope | "All tests pass:" lists exactly two test files (server.spec.ts, 04459.test.ts); failure is whole-suite test-bun |
| 32 | unclear | Codex bare `cargo test` with no stated result; tool-tests fails, but whether the line asserts a pass can't be settled |
| 33 | out-of-scope | 42 tests = realtime package (34 existing + 8 new); failing check is the framework-express example tests |
| 34 | contradiction | "All existing tests continue to pass", not scoped; React 18 / v8 Integration (integration test job) fails |
| 35 | contradiction | "All existing tests continue to pass", not scoped; Testing Pods (xcodebuild test workflow) fails |
| 36 | contradiction | "All existing tests continue to pass (57 passed...)"; the whole pytest matrix fails |
| 37 | contradiction | "All existing tests continue to pass."; CircleCI test_even/test_odd/end_to_end jobs fail |
| 38 | contradiction | Agent-written "[x] All tests passing" (not a template); test (3.11) fails |
| 39 | unclear | Claim already reports 772/773 RSpec with 1 failing; the evidence is the JS suite (outside RSpec); the RSpec job failure can't be told apart from the admitted one |
| 40 | contradiction | "All tests pass locally ✅" ("locally" names no subset); contracts-bedrock fuzz test job on the modified tests fails |
| 41 | not-a-claim | LiteLLM template checkbox about adding a screenshot |
| 42 | unclear | Limited to "existing parser tests"; Test Linux is broad, but the failing Conformance job is largely parser conformance, so it could be in scope |
| 43 | out-of-scope | 38/38 = cyrus-adapter-anthropic package tests (pnpm --filter); failing test (22.x) is the monorepo suite |
| 44 | unclear | Codex bare `go test -short ./...` with no result; the PR moves heavy tests out of -short, and the CI test command is unknown |
| 45 | not-a-claim | LiteLLM template checkbox about adding a screenshot |
| 46 | contradiction | "All existing tests pass (252 tests)" is the full suite; test (alldeps, 1.10) fails |
| 47 | contradiction | "All tests pass including the new test coverage", not scoped; tests (3.10) fails |
| 48 | contradiction | "All existing tests pass."; Core and lib test jobs fail |
| 49 | contradiction | "All existing tests pass + new watchdog suite"; unit-tests fails |
| 50 | out-of-scope | Limited to 12 bundler worker tests (command shown); failures are whole-suite test-bun jobs |
| 51 | contradiction | "All existing tests continue to pass"; CircleCI linux and windows test jobs fail |
| 52 | not-a-claim | Copilot plan checklist item done before implementation; "[ ] Verify all tests pass" is unchecked |
| 53 | contradiction | "All unit tests passing with race detector"; unit-tests fails |
| 54 | unclear | Claim admits 2/2116 failing ("pre-existing"); the AppVeyor Windows test run errored and can't be told apart from those |
| 55 | contradiction | "All existing tests continue to pass"; Run unit tests and integration tests fail |
| 56 | contradiction | "All existing tests pass (6870 tests)"; Core and many lib test jobs fail |
| 57 | out-of-scope | 68 tests = new lock-component tests only; one PHP/Swoole leg of the full suite fails, not shown to be in them |
| 58 | contradiction | Agent-written checklist "[x] All tests pass"; test (18.x) and Test Suite fail |
| 59 | contradiction | "All existing tests pass", not scoped; darwin/ubuntu test-bun jobs fail |
| 60 | not-a-claim | Lists a changed file (jest.config.js), not a test result |
| 61 | contradiction | "135 tests passing (6 new)" is the full suite (the current body says all 129 existing pass); Test job fails |
| 62 | out-of-scope | Limited to the seed test for one fixture; failing "test" is fern's unit test job |
| 63 | not-a-claim | Quoted issue text giving a requirement ("make all tests passed") |
| 64 | contradiction | "All unit and integration tests pass"; Run Unit Tests fails |
| 65 | out-of-scope | Limited to existing telemetry tests; failing tests (3.13) is the full suite |
| 66 | out-of-scope | "All 15 tests" are the 15 numbered smart-stub scenario tests listed above it; failing test (3.11) is the pytest suite |
| 67 | contradiction | "All existing tests continue to pass"; the Test Results check and the build/verify job fail |
| 68 | contradiction | "All tests pass successfully.", not scoped; Test on windows-latest fails |
| 69 | not-a-claim | LiteLLM template checkbox about adding a screenshot |
| 70 | not-a-claim | trufflehog PR template checkbox ("Tests passing (`make test-community`)?") |
| 71 | out-of-scope | Limited to 23 ProcessPoolTaskRunner tests; failures are Integration tests @main and client compatibility tests |
| 72 | out-of-scope | Limited to existing cache tests; failing check is the whole Node 20 macOS test run |
| 73 | out-of-scope | Limited to 20 tests in tests/rag/embeddings/; failing tests (3.11) is the full suite |
| 74 | contradiction | "all tests continue to pass"; every test matrix job fails |
| 75 | contradiction | "24,529+ tests passed across net8.0 and net9.0" (whole suite); many test jobs fail |
| 76 | contradiction | "npm test # ✓ All existing tests pass", not limited by Node version; Run tests on Node.js 6 fails |
| 77 | out-of-scope | Limited to AWS cloudprovider tests; failing test-and-verify is repo-wide |
| 78 | contradiction | 340+ tests are in UnitTestsParallelizable, which the failing Parallel Unit Tests job runs; Testing also claims all 12,800+ pass |
| 79 | unclear | Codex bare command (one TestDummy) with no stated result; failing job is repo-wide, so either not a claim or out of scope |
| 80 | out-of-scope | Limited to 63 ForkId tests; failures are repo-wide unit/integration/reference/acceptance jobs |
| 81 | out-of-scope | Limited to bundler tests; failures are whole-suite test-bun jobs |
| 82 | out-of-scope | Limited to the unit tests of two packages (5/5, 4/4); failures are e2e, integration, bundle and screenshots |
| 83 | out-of-scope | Limited to 16 v1/v2 validation test cases; failing "Run tests" is the broader suite |
| 84 | out-of-scope | 24/24 = the specific Blob/File serialization test file; failure is whole-suite test-bun |
| 85 | contradiction | "All 261 tests pass" is the full suite; test (alldeps, 1.10) fails |
| 86 | out-of-scope | "All Tests Pass:" lists only the new env-var/CLI/platform/integration test groups; failures are whole-suite test-bun jobs |
| 87 | contradiction | Agent-written "[x] All tests pass locally", not scoped; Interface1/Interface2 test jobs fail |
| 88 | not-a-claim | Checkbox from kodit's PR template ("New and existing unit tests pass locally") |
| 89 | out-of-scope | One grep-selected unit test; failing check is test-integration |
| 90 | out-of-scope | Limited to the new/unit/QA tests for one command; AppVeyor runs a hand-picked set of debug resource integration tests |
| 91 | unclear | Codex bare `pytest -v tests/` with no stated result; tests job fails, but whether the line asserts a pass can't be settled |
| 92 | contradiction | "All tests pass ✅", not scoped; test-bun fails on all 20 platforms |
| 93 | out-of-scope | Limited to the 5 new unit tests; failures are smoke tests and the full Rust build/test |
| 94 | out-of-scope | Limited to the new tests and existing thread-safety tests; failing tests (3.12) is the full suite |
| 95 | contradiction | "All 64 tests pass (62 existing + 2 new)" is the full suite; Run Tests for linux and windows fail |
