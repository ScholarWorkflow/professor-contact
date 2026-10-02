# 只确认完整有效通过；不重新分类非通过结果，也不读取日志文字。
type == "object" and
.schema_version == 2 and
.verdict == "PASS" and
(.tests_run | type == "number") and
(.tests_run > 0) and
(.started | type == "array") and
(.started | all(type == "string")) and
(.started | length) == .tests_run and
(.started | unique | length) == .tests_run and
.completed == .started and
.load_errors == [] and
.interruption == null and
.missing_required_prefixes == [] and
.events == [] and
.failures == [] and
.errors == [] and
.skipped == [] and
.expected_failures == [] and
.unexpected_successes == [] and
($required | length) == 1 and
($required[0] | type == "array") and
($required[0] | length) > 0 and
($required[0] | all(type == "string")) and
(($required[0] - .started) | length) == 0
