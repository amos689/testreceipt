# Judge 1 — suspicious sample A

Labels per evals/ADJUDICATION.md. Source: sheet-suspicious-a.md, plus the PR page or .diff where a hunk was cut or a justification was needed.

| # | Rule | Label | Justified | Reason |
|---|---|---|---|---|
| 1 | TR110 | correct | no | Truthy non-string IdentitiesOnly parse/format test replaced by an unrelated "IdentitiesOnly no" test; the old bool/"yes" checks are gone. |
| 2 | TR104 | correct | yes | assert_called_once_with became call_count>=1 + assert_any_call; the PR adds MCP OAuth, so config is now read more than once. |
| 3 | TR102 | correct | no | list_tools now returns a dict; the `len == 1` count check was dropped though it still applied. |
| 4 | TR111 | correct | yes | Skip when the external word-list fetch is rate limited (HTTP 429), a network condition. |
| 5 | TR110 | correct | yes | V0 enc-dec scheduler test deleted; PR drops the V0 encoder-decoder runner. |
| 6 | TR110 | correct | no | test_ignore_eos ran on both engines (V1 too); deleting it with V0 removal loses V1 coverage, and it is not moved. |
| 7 | TR110 | false-alarm | - | Hard-coded soundex battery rewritten as test_soundex_against_reference, which compares against jellyfish (PR diff). |
| 8 | TR110 | correct | yes | Advanced-toggle config/options flow tests removed; the advanced options feature was removed (configure_advanced dropped). |
| 9 | TR102 | correct | yes | `__tools__` registry check dropped; PR makes _add_web_search_tool modify only body['tools'] on purpose. |
| 10 | TR102 | correct | no | Persistence test: `assert encoded` gone and the stored item's model equality weakened to a membership check. |
| 11 | TR110 | false-alarm | - | Combined HTTP test split into separate GET, 401 and SSL-auto tests; only a near-duplicate DoH-style GET was dropped. |
| 12 | TR102 | false-alarm | - | result/content non-empty checks moved into the `_parse_result` helper; the test now asserts formula, rows, is_valid and the matrix. |
| 13 | TR110 | correct | yes | V0-only prefix-caching tests deleted with the V0 engine/core removal. |
| 14 | TR110 | correct | yes | V0 core scheduler tests deleted with the V0 engine/core removal. |
| 15 | TR110 | false-alarm | - | Renamed to test_service_worker_registers, which keeps the service-worker.js existence check and adds a browser check. |
| 16 | TR102 | false-alarm | - | Output format changed from inline mask to mask_path; the checks were rewritten (mask_path present, str, file exists). |
| 17 | TR405 | correct | no | CI test workflow deleted in a closed "delete repo contents and build quiz app" PR; no replacement shown. |
| 18 | TR110 | correct | yes | test_advanced_options_step removed because advanced options are no longer supported. |
| 19 | TR110 | correct | yes | Removed with an explicit comment that advanced options are no longer supported. |
| 20 | TR112 | correct | yes | axis=None case removed; the PR moves axis=None handling out of CumOp (it now ravels at the symbolic level). |
| 21 | TR112 | correct | yes | Mllama case removed; the PR removes V0 enc-dec models, including Mllama. |
| 22 | TR112 | correct | yes | FLASHINFER case dropped; the PR removes the V0 FlashInfer backend. |
| 23 | TR102 | correct | yes | Both-required assertion became an OR; the old assertion contradicted the test's own "either" comment (PR: fix expectation logic). |
| 24 | TR110 | false-alarm | - | test_wvlet_not_found renamed to test_wvlet_initialization with the same body, plus new tests. |
| 25 | TR110 | correct | yes | V0 block manager tests deleted with the V0 core removal. |
| 26 | TR110 | false-alarm | - | run_strategy test replaced by a parametrized formatter-selection test for the new ChatStrategy logic (visible at end of diff). |
| 27 | TR403 | correct | no | testpaths=tests and norecursedirs exclude mcp_server from root collection; no reason shown in the diff. |
| 28 | TR104 | correct | yes | Default pool now loads evaluators on purpose, but the new check (`len > 0`, weights truthy) is looser than an exact one. |
| 29 | TR110 | correct | yes | Mllama tests deleted; the PR drops V0 enc-dec support. |
| 30 | TR102 | false-alarm | - | The `len == 1` check became an exact sorted-nickname list check (stronger) after aliases became separate connections. |
| 31 | TR112 | correct | yes | Mllama case removed; enc-dec models removed. |
| 32 | TR110 | false-alarm | - | Persona tests consolidated into a parametrized test_mcp_tool_calls; error test kept as test_invalid_tool_request_returns_error. |
| 33 | TR111 | correct | yes | Module skipif when the R binary is absent, an environment requirement. |
| 34 | TR110 | correct | yes | V0 enc-dec scheduler test deleted; PR removes V0 enc-dec support. |
| 35 | TR112 | false-alarm | - | check_repo_exists switched from HTTP to git ls-remote; cases rewritten for return codes, with a call-args check and new tests added. |
| 36 | TR112 | correct | yes | Tuple-axis TypeError case dropped from the pytorch dispatch test; the PR moves axis handling to the symbolic layer. |
| 37 | TR110 | correct | yes | MQLLMEngine (V0) load test deleted with the V0 engine removal. |
| 38 | TR102 | false-alarm | - | Markdown checks replaced by an exact `files` event check (PR diff); the behaviour changed to emit files. |
| 39 | TR110 | correct | yes | Mllama tests deleted; PR removes V0 enc-dec models. |
| 40 | TR110 | correct | no | Import-error test for EvaluationDataset removed in an unrelated "fix empty notebooks" PR; no reason. |
| 41 | TR111 | correct | yes | Skip only for the newly added EdgeTAM tracker, which does its own detection and cannot handle synthetic inputs (reason given). |
| 42 | TR102 | false-alarm | - | Auth changed from access/secret key pair to one API key; the check is rewritten as `api_key ==`. |
| 43 | TR110 | correct | yes | V0 sampler tests deleted with the V0 removal. |
| 44 | TR110 | correct | no | path=None default test deleted in a drag-and-drop PR; no reason or replacement. |
| 45 | TR110 | correct | yes | ModelTrainingData was removed and thinking logic moved to build_training_chat; several thinking/R1 variants were dropped, the rest refactored. |
| 46 | TR102 | false-alarm | - | make_judge tests rewritten for reserved variables; removed substring checks became full JSON or exact-equality checks. |
| 47 | TR112 | correct | no | Graph traversal cases cut from 4 to 3 (steps=10 dropped); no reason given. |
| 48 | TR102 | false-alarm | - | Helper-based warning checks replaced by filterwarnings("error") and pytest.warns(match=...), which is equivalent. |
| 49 | TR110 | correct | yes | uv runtime-env tests deleted; PR removes the old uv runtime-env plugin. |
| 50 | TR102 | correct | yes | build_user_message checks and the non-ASCII test removed; the method left the prompt builder in the chat-formatter refactor. |
| 51 | TR110 | false-alarm | - | run_integration_tests.py is a report runner, not collected by pytest; its test_* functions only print results. |
| 52 | TR110 | correct | yes | V0 ExecuteModelRequest serialization test deleted with the V0 removal. |
| 53 | TR110 | correct | yes | mBART test deleted; PR removes BART/mBART. |
| 54 | TR110 | correct | yes | V0-only metrics tests deleted with the V0 removal. |
| 55 | TR110 | correct | yes | mBART test deleted; PR drops the V0 enc-dec runner. |
| 56 | TR110 | false-alarm | - | `test_func` was a helper callable passed to patch, renamed so pytest stops collecting it; not a real test. |
| 57 | TR110 | correct | yes | LiteLLM cache tests deleted; the enable_litellm_cache feature was removed. |
| 58 | TR110 | correct | no | test_ranks ran on both engines (V1 too); deleted with V0 removal and not moved. |
| 59 | TR105 | false-alarm | - | Not a hard-coded computed value: the stop agent no longer emits a message, and the exact source list is still asserted. |
| 60 | TR110 | correct | yes | uv plugin unit test deleted; PR removes the uv runtime-env plugin. |
| 61 | TR405 | false-alarm | - | Only `--ignore` of the deleted test_mllama.py was removed; the pytest command still runs, and its selection grows. |
| 62 | TR110 | correct | no | Anthropic simple eval tests deleted in a "parallel tools" PR; not relocated, only a vague "testing strategy" reason. |
| 63 | TR110 | false-alarm | - | Three marker tests consolidated into test_marker_utils covering create/parse/extract/split. |
| 64 | TR110 | correct | yes | /synth-knobs test removed; the PR removes the synth_knobs page and route. |
| 65 | TR110 | correct | yes | MQLLMEngine (V0) abort test deleted with the V0 engine removal. |
| 66 | TR110 | correct | yes | test_litellm_cache and cache_in_memory checks removed; those options were removed from dspy. |
| 67 | TR403 | false-alarm | - | tests/e2e holds new Playwright .spec.ts tests run by their own workflow; no pytest tests are excluded. |
| 68 | TR102 | correct | no | Tracking-URI patch moved to an autouse fixture, but the `assert_called()` checks were dropped with no reason. |
| 69 | TR110 | correct | no | Include/ignore pattern scenarios deleted (a TODO left) in a closed 5k-line PR; not re-added. |
| 70 | TR110 | correct | yes | Florence-2 test deleted; PR drops V0 enc-dec support. |
| 71 | TR102 | correct | yes | V0 fallback check removed; V0 enc-dec fallback removed by the PR. |
| 72 | TR110 | false-alarm | - | Behaviour changed to default to Nwbfile; the test was rewritten to assert the new default, and more tests were added. |
| 73 | TR110 | correct | yes | MQLLMEngine (V0) error-handling tests deleted with the V0 engine removal. |
| 74 | TR110 | false-alarm | - | Generated transpiler output; test_gradient_descent is a printing program function, not a test. |
| 75 | TR110 | correct | yes | V0 enc-dec attention kernel tests deleted; PR removes V0 enc-dec. |
| 76 | TR110 | correct | yes | V0 enc-dec attention kernel tests deleted; PR drops the V0 enc-dec runner. |
| 77 | TR111 | correct | yes | skipIf PyYAML is not installed, an environment dependency. |
| 78 | TR104 | false-alarm | - | Code now uploads twice (OSS and Cloud); the OSS call keeps exact args via assert_any_call, and a Cloud check was added. |
| 79 | TR403 | correct | no | `--ignore=tests/gateway` added to the protobuf cross-test; no concrete reason (PR later split). |
| 80 | TR403 | correct | no | addopts ignores tutorial_test/test_tutorial.py; no reason shown. |
| 81 | TR102 | false-alarm | - | Error-handling subtests moved into the new test_SubtitleEditor_UpdateLine_error_handling with the same asserts. |
| 82 | TR405 | false-alarm | - | `functional:test` replaced by `functional:all` (SQLite + PostgreSQL), a broader run. |
| 83 | TR102 | false-alarm | - | Access/secret key pair replaced by one API key; the check is rewritten as `api_key ==`. |
| 84 | TR111 | correct | yes | Module skipif when the R binary is absent, an environment requirement. |
| 85 | TR102 | correct | no | Env-config tests halved (551 to 274 lines); proxy-env removal explains some, not the flagged key-normalization and edge-case checks. |
| 86 | TR110 | correct | yes | SentenceTransformersTokenTextSplitter removed along with the dependency. |
| 87 | TR102 | correct | no | Graceful-import checks replaced by expecting ModuleNotFoundError in a "fix tests" PR; the test now accepts the failure. |
| 88 | TR110 | correct | yes | V0 block table tests deleted with the V0 core removal. |
| 89 | TR112 | correct | yes | Mllama and Florence-2 cases removed; those models were removed. |
| 90 | TR106 | correct | no | Tolerance loosened 10x "to permit numerical variation"; no environment or flaky issue cited. |
| 91 | TR110 | correct | yes | Collected test file deleted with the unused models/ directory (PR: remove stale models dir). |
| 92 | TR104 | correct | no | Exact event count 48 relaxed to `> 0` to avoid API calls; the count was not updated. |
| 93 | TR110 | correct | yes | BART tests deleted; PR removes BART. |
| 94 | TR110 | correct | yes | 40 tests deleted with the unused models/ directory, which the PR removes entirely. |
| 95 | TR102 | correct | no | `assertTrue(dbfile.closed)` dropped in a Windows file-handle fix; it could have been kept on the new handle. |
| 96 | TR110 | correct | yes | V0 multiproc worker tests deleted with the V0 executor removal. |
| 97 | TR110 | correct | yes | zip_enc_dec_prompts test removed along with the function import; enc-dec support dropped. |
| 98 | TR110 | correct | yes | sanitize/parse/debug helper tests removed; PR says the helpers are deprecated in the pipeline refactor. |
| 99 | TR111 | correct | yes | Module importorskip("langchain_core"), a missing-dependency skip. |
| 100 | TR110 | false-alarm | - | `test_data_dir` was a pytest fixture, not a test; the tests themselves were renamed and expanded. |

## Counts

| Label | Count |
|---|---|
| correct | 73 (justified yes 53, no 20) |
| false-alarm | 27 |
| unclear | 0 |

| Rule | Items | correct (just. yes/no) | false-alarm | unclear |
|---|---|---|---|---|
| TR110 | 54 | 42 (35/7) | 12 | 0 |
| TR102 | 19 | 10 (4/6) | 9 | 0 |
| TR112 | 8 | 7 (6/1) | 1 | 0 |
| TR111 | 6 | 6 (6/0) | 0 | 0 |
| TR104 | 4 | 3 (2/1) | 1 | 0 |
| TR403 | 4 | 3 (0/3) | 1 | 0 |
| TR405 | 3 | 1 (0/1) | 2 | 0 |
| TR105 | 1 | 0 | 1 | 0 |
| TR106 | 1 | 1 (0/1) | 0 | 0 |
