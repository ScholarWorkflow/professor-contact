#!/bin/sh
# 在仓库根执行；只验证结构化通过检查，不执行产品用例。
set -eu
out=$1
mkdir "$out"
jq -n --slurpfile required test-plan/issue-74-required-cases.json \
  -f test-plan/issue-74-check-samples.jq > "$out/samples.json"
for name in valid-success valid-success-reordered valid-product-failure invalid-empty-execution missing-required-method conflicting-pass-evidence
do
  jq --arg name "$name" '.[] | select(.name == $name) | .evidence' \
    "$out/samples.json" > "$out/$name.input.json"
  jq --slurpfile required test-plan/issue-74-required-cases.json \
    -f test-plan/issue-74-pass-check.jq "$out/$name.input.json" > "$out/$name.actual.json"
  jq -n --arg name "$name" --slurpfile samples "$out/samples.json" \
    --slurpfile actual "$out/$name.actual.json" \
    '{name: $name, expected: ($samples[0][] | select(.name == $name) | .expected),
      actual: $actual[0]} | . + {matched: (.actual == .expected)}' > "$out/$name.result.json"
  jq -e '.matched == true' "$out/$name.result.json" > /dev/null
done
jq -s '.' "$out/valid-success.result.json" "$out/valid-success-reordered.result.json" \
  "$out/valid-product-failure.result.json" "$out/invalid-empty-execution.result.json" \
  "$out/missing-required-method.result.json" "$out/conflicting-pass-evidence.result.json" > "$out/results.json"
