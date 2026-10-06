# 先判断完整候选证据，再保留不依赖无效材料的局部产品失败。
def source_present: type == "string" and length > 0;
def suite_valid:
  .evidence_validity == "VALID"
  and (.owner == "product" or .owner == "test_program")
  and (.structured_status_source | source_present)
  and (.raw_event_source | source_present)
  and (.failures | type) == "array"
  and (.result == "PASS" or .result == "PRODUCT_FAIL")
  and (if .result == "PRODUCT_FAIL" then .owner == "product"
       and any(.failures[]; .status == "failure" or .status == "unexpected_success")
       else (.failures | length) == 0 end);
. as $input
| ([
    (if .candidate.validity != "VALID" or (.candidate.source | source_present | not) then
      {kind:"candidate", source:.candidate.source, reason:"候选版本或摘要无效"}
    else empty end),
    (if .ledger.validity != "VALID" or (.ledger.source | source_present | not) then
      {kind:"ledger", source:.ledger.source, reason:"样例账本或候选汇总自测记录无效",
       sample_ledger_exit_code:.ledger.sample_ledger_exit_code,
       combination_check_exit_code:.ledger.combination_check_exit_code}
    else empty end),
    (if (.suites | type) != "array" or (.suites | length) == 0 then
      {kind:"suites", source:"suites.jsonl", reason:"套件记录缺失"}
    else empty end),
    (.suites[]? | if (suite_valid | not) then
      {kind:"suite", suite:.suite, source:.structured_status_source,
       reason:"套件记录无效或测试程序检查未通过"}
    else empty end)
  ]) as $gaps
| ([.suites[]?
    | select($input.candidate.validity == "VALID"
        and ($input.candidate.source | source_present)
        and suite_valid and .owner == "product"
        and (.structured_status_source | source_present)
        and (.raw_event_source | source_present))
    | . as $suite | .failures[]?
    | select(.status == "failure" or .status == "unexpected_success")
    | {suite:$suite.suite, test_id:.test_id, status:.status,
       structured_status_source:$suite.structured_status_source,
       raw_event_source:$suite.raw_event_source, events:.events}
  ]) as $failures
| (if ($gaps | length) > 0 then "INVALID_TEST_EXECUTION"
   elif ($failures | length) > 0 then "FAIL" else "PASS" end) as $overall
| {schema:"issue66-candidate-result-v1",
   evidence_validity:(if ($gaps | length) == 0 then "VALID" else "INVALID" end),
   overall:$overall,
   exit_code:(if $overall == "PASS" then 0 elif $overall == "FAIL" then 1 else 2 end),
   local_product_failures:$failures, gaps:$gaps,
   runner_execution:"COMPLETE",
   runner_execution_meaning:"仅表示运行器已执行完全部步骤；不表示证据有效、候选通过或正式验收通过",
   evidence_sources:{candidate:$input.candidate.source, ledger:$input.ledger.source,
                     suites:[$input.suites[]? | .structured_status_source]}}
