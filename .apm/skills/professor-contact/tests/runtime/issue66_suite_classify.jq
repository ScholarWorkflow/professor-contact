# 产品断言与测试程序能力检查有不同归属；异常、加载错误和空套件保留无效终态。
def has_executed_items:
  (.tests_run | type) == "number"
  and .tests_run > 0
  and (.tests | type) == "array"
  and .tests_run == (.tests | length);
if (has_executed_items | not) then "INVALID_TEST_EXECUTION"
elif .classification == "PRODUCT_FAIL" and $owner == "test_program"
then "INVALID_TEST_EXECUTION"
else .classification
end
