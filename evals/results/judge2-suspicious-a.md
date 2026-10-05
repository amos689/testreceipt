# Judge 2: suspicious sample A

I labelled every item from `sheet-suspicious-a.md`. Where a hunk was cut or the reason for a removal mattered, I read the PR's title, description and file list on GitHub, and the test file at the PR's base and head. I did not read any labels or other judge files.

| # | rule | label | justified | reason |
|---|---|---|---|---|
| 1 | TR110 | correct | no | Test of truthy bool/"yes" IdentitiesOnly parsing and formatting replaced by an unrelated "IdentitiesOnly no" test; old checks not kept anywhere |
| 2 | TR104 | correct | yes | assert_called_once_with loosened to call_count>=1 + assert_any_call; PR stores OAuth tokens in the same config, so extra reads are intended |
| 3 | TR102 | correct | no | Registry result is now a dict; name/version still checked, but the exactly-one-tool count check was dropped although it still applies |
| 4 | TR111 | correct | yes | New pytest.skip when the external word-list URL returns HTTP 429 (network rate limit = environment) |
| 5 | TR110 | correct | yes | V0 encoder-decoder scheduler test deleted; PR "Drop V0 encoder-decoder runner" removes the feature |
| 6 | TR110 | correct | no | PR removes V0, but test_ignore_eos ran on both engines (run_with_both_engines); V1 ignore_eos coverage lost with no replacement |
| 7 | TR110 | false-alarm | - | Battery rewritten in the same file as test_soundex_against_reference (larger name list checked against jellyfish) |
| 8 | TR110 | correct | yes | Advanced config/options-flow tests removed together with the configure_advanced toggle; PR removes the Advanced option |
| 9 | TR102 | correct | yes | Check that the __tools__ registry gets web_search was removed; PR deliberately makes the filter modify only body['tools'] |
| 10 | TR102 | correct | no | Equality check on the stored item's model became a key-membership check (the cited `assert encoded` itself was redundant) |
| 11 | TR110 | false-alarm | - | Combined network test split into test_basic_get_request..., test_http_401..., test_ssl_auto_mode, etc., with the same assertions |
| 12 | TR102 | false-alarm | - | Repeated result/content asserts moved into a _parse_result helper called at each step; the rewrite adds stronger asserts (is_valid, rows>0) |
| 13 | TR110 | correct | yes | V0-only prefix-caching tests (use_v0_only) deleted in PR "Remove V0 engine and core" |
| 14 | TR110 | correct | yes | V0 core scheduler tests deleted together with vllm.core (Remove V0 engine and core) |
| 15 | TR110 | false-alarm | - | Renamed to test_service_worker_registers; keeps the service-worker.js existence assert and adds more (new module-level playwright importorskip noted) |
| 16 | TR102 | false-alarm | - | PR now returns masks as PNG files; mask-list checks replaced by checks that mask_path is a str and the file exists |
| 17 | TR405 | correct | yes | Unit-test workflow deleted together with the whole pytheus package (PR replaces the repo with a quiz app) |
| 18 | TR110 | correct | yes | test_advanced_options_step removed; PR removes the Advanced option and its step |
| 19 | TR110 | correct | yes | Advanced-options step test removed; the comment and the PR both say advanced options are no longer supported |
| 20 | TR112 | correct | yes | axis=None CumOp case removed; PR moves axis=None handling out of CumOp on purpose |
| 21 | TR112 | correct | yes | Mllama case removed; PR deletes Mllama and other V0 encoder-decoder models |
| 22 | TR112 | correct | yes | FLASHINFER backend case removed; PR removes the V0 FlashInfer backend |
| 23 | TR102 | correct | yes | Two required substrings became an OR; code comment says the message has USD or "offline data missing", depending on whether the data is present |
| 24 | TR110 | false-alarm | - | Renamed to test_wvlet_initialization with the same body plus an assert; more tests added |
| 25 | TR110 | correct | yes | V0 block-manager tests deleted with the V0 core |
| 26 | TR110 | false-alarm | - | run_strategy replaced by chat formatters; test rewritten at the end of the file as a parametrized formatter-selection test with the same cases |
| 27 | TR403 | false-alarm | - | Every mcp_server test is new in this PR and runs in a new mcp-server-tests workflow; the root run loses nothing |
| 28 | TR104 | false-alarm | - | PR auto-registers evaluators; expected default changed from [] to non-empty (disjoint, not looser); empty case kept via evaluators=[] |
| 29 | TR110 | correct | yes | Mllama generation tests deleted; PR drops encoder-decoder models |
| 30 | TR102 | false-alarm | - | Each Host label now becomes its own connection (PR intent); count still checked through sorted-nickname list equality |
| 31 | TR112 | correct | yes | Mllama registry case removed along with the model |
| 32 | TR110 | false-alarm | - | The four scenario tests reappear as parametrized test_mcp_tool_calls with the same asserts, plus test_invalid_tool_request_returns_error |
| 33 | TR111 | correct | yes | Module-level skipif (no R binary) now also skips test_tool_discovery; environment reason |
| 34 | TR110 | correct | yes | V0 encoder-decoder scheduler test deleted; PR removes V0 encoder-decoder support |
| 35 | TR112 | false-alarm | - | check_repo_exists moved from HTTP HEAD to git ls-remote; cases rewritten as return codes and a call-args assert added |
| 36 | TR112 | correct | yes | Tuple-axis TypeError case dropped; PR changes CumOp axis handling on purpose |
| 37 | TR110 | correct | yes | V0 MQLLMEngine load test deleted with the V0 engine |
| 38 | TR102 | false-alarm | - | Two markdown startswith checks replaced by one exact equality over both emitted `files` events (PR switches to files events) |
| 39 | TR110 | correct | yes | Mllama tests deleted; PR deletes Mllama, BART, etc. |
| 40 | TR110 | correct | yes | ImportError expectation removed because EvaluationDataset is now implemented in OSS (evaluation_dataset.py added) |
| 41 | TR111 | false-alarm | - | Skip only applies to EdgeTAM, a tracker added in this PR; existing tracker cases still run |
| 42 | TR102 | false-alarm | - | Access-key and secret-key fields replaced by a single api_key; the assert checks the new field |
| 43 | TR110 | correct | yes | V0 sampler tests (use_v0_only) deleted with the V0 engine |
| 44 | TR110 | correct | no | path=None default tests deleted in an unrelated drag-and-drop PR (sftp_utils also changed); nothing replaces them |
| 45 | TR110 | correct | yes | Refactor to ChatMessage lists drops the thinking/R1 variants and the no-parent-task test; some coverage moved to the chat formatter tests |
| 46 | TR102 | correct | yes | Template variables restricted to reserved names on purpose; cited example became a stronger JSON check, but the complex-template test lost its user-message and result checks |
| 47 | TR112 | correct | no | graph_traversal cases cut from 4 to 3 (steps=10 case gone) along with epoch renumbering; no reason given for dropping a case |
| 48 | TR102 | false-alarm | - | Helper-based warning checks replaced by an "error" filter (no warning) and pytest.warns(match=...) (warning); equivalent |
| 49 | TR110 | correct | yes | uv runtime-env tests deleted with the plugin (PR "Remove old uv runtime env plugin") |
| 50 | TR102 | false-alarm | - | build_user_message moved to format_user_message; its checks, including the non-ASCII test, now live in chat/test_chat_formatter.py |
| 51 | TR110 | false-alarm | - | run_integration_tests.py is a report script (not test_*.py; its functions return results without asserting); pytest never collected it |
| 52 | TR110 | correct | yes | V0 ExecuteModelRequest msgspec test deleted with the V0 core |
| 53 | TR110 | correct | yes | mBART test deleted; PR removes the BART family |
| 54 | TR110 | correct | yes | V0 metrics tests (use_v0_only) deleted with the V0 engine |
| 55 | TR110 | correct | yes | mBART test deleted with encoder-decoder support |
| 56 | TR110 | false-alarm | - | test_func was a helper passed to @patch and is now named foobar_func; it was never a real test |
| 57 | TR110 | correct | yes | LiteLLM cache tests deleted; PR removes LiteLLM caching |
| 58 | TR110 | correct | no | test_ranks ran on both engines; deleting it with the V0 removal drops V1 rank coverage |
| 59 | TR105 | false-alarm | - | PR stops _StopAgent from emitting a message; "C" is now last and the exact expected_sources list is still checked; no computed value was hardcoded |
| 60 | TR110 | correct | yes | UvProcessor unit test deleted together with uv.py |
| 61 | TR405 | false-alarm | - | pytest command still runs; only the --ignore for the deleted test_mllama.py was dropped |
| 62 | TR110 | correct | no | 9 Anthropic eval tests deleted in a PR that adds parallel tool support; unrelated to the feature |
| 63 | TR110 | false-alarm | - | Three marker tests merged into test_marker_utils, covering parse/wrap/extract/split (minor detail lost: hasattr Pipe, wrapper format) |
| 64 | TR110 | correct | yes | The /synth-knobs route and page are deleted in this PR |
| 65 | TR110 | correct | yes | V0 MQLLMEngine abort test deleted with the V0 engine |
| 66 | TR110 | correct | yes | test_litellm_cache removed along with the enable_litellm_cache and cache_in_memory options |
| 67 | TR403 | false-alarm | - | tests/e2e holds only Playwright TS specs (run by the new e2e workflow), so no pytest tests are excluded |
| 68 | TR102 | false-alarm | - | get_tracking_uri patch moved to an autouse fixture; routing is still shown by the asserts on DatabricksStore mock calls |
| 69 | TR110 | correct | no | Parametrized include/ignore pattern scenarios deleted and replaced by TODO comments; no copy elsewhere in the PR |
| 70 | TR110 | correct | yes | Florence-2 test deleted with the encoder-decoder models |
| 71 | TR102 | correct | yes | V0 fallback check removed; the V0 encoder-decoder fallback no longer exists |
| 72 | TR110 | false-alarm | - | PR makes Nwbfile the default; test rewritten as test_nwb_table_defaults_to_nwbfile plus broader tests |
| 73 | TR110 | correct | yes | V0 MQLLMEngine error-handling tests deleted |
| 74 | TR110 | false-alarm | - | Generated transpiler output; test_gradient_descent is an ordinary program function, now nested in main, not a test |
| 75 | TR110 | correct | yes | V0-only encoder-decoder attention kernel tests deleted with V0 encoder-decoder support |
| 76 | TR110 | correct | yes | Same deletion, in the PR that drops the V0 encoder-decoder runner |
| 77 | TR111 | correct | yes | Class skipped when PyYAML is not installed; environment reason |
| 78 | TR104 | correct | yes | assert_called_with became assert_any_call because a cloud-spec upload now follows the OSS one |
| 79 | TR403 | correct | no | tests/gateway newly ignored in the protobuf cross-test job; the only reason given is "avoid test conflicts" |
| 80 | TR403 | correct | no | addopts now ignores the existing tutorial_test/test_tutorial.py, with no reason given |
| 81 | TR102 | false-alarm | - | Error-handling subtest moved into the new test_SubtitleEditor_UpdateLine_error_handling with the same asserts |
| 82 | TR405 | false-alarm | - | functional:test replaced by functional:all, which runs the SQLite and the new PostgreSQL live tests |
| 83 | TR102 | false-alarm | - | Same as 42: access/secret keys replaced by api_key, and the assert follows |
| 84 | TR111 | correct | yes | Module-level skipif when R is missing; environment reason |
| 85 | TR102 | correct | no | Test file halved (74 asserts down to 33); unrelated checks (key normalization, edge cases) dropped beyond the proxy refactor |
| 86 | TR110 | correct | yes | SentenceTransformersTokenTextSplitter is removed in this PR |
| 87 | TR102 | correct | no | "fix tests" PR changes the fallback-import test to expect ModuleNotFoundError, so the fallback wiring is no longer checked |
| 88 | TR110 | correct | yes | V0 block-table tests deleted together with vllm.core |
| 89 | TR112 | correct | yes | Mllama and Florence-2 cases removed with the models |
| 90 | TR106 | correct | no | Tolerance loosened from 1e-3 to 1e-2 "to permit numerical variation"; no tracked cause |
| 91 | TR110 | correct | yes | The whole stale models/ directory is removed (rationale given in the PR) |
| 92 | TR104 | correct | no | Exact event count of 48 loosened to > 0 |
| 93 | TR110 | correct | yes | BART tests deleted; PR removes BART |
| 94 | TR110 | correct | yes | Models CLI tests deleted with the whole models/ directory |
| 95 | TR102 | correct | no | Rewritten to use named temp files; the "AddressSet closed the file" assert in test_file_update dropped, only a comment remains |
| 96 | TR110 | correct | no | Multiproc worker-utils tests deleted although multiproc_worker_utils.py stays in the PR (modified) |
| 97 | TR110 | correct | yes | zip_enc_dec_prompts removed with encoder-decoder support (its import is dropped) |
| 98 | TR110 | correct | yes | sanitize_for_log, parse_responses_sse and _MemHandler were removed from the module by an earlier refactor; this PR drops their tests |
| 99 | TR111 | correct | yes | Module-level importorskip("langchain_core"); missing-dependency environment |
| 100 | TR110 | false-alarm | - | test_data_dir was a fixture, now replaced by mock_file_factory; the real tests were renamed and extended |
