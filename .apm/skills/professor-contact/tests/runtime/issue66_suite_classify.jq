# 产品断言与测试程序能力检查有不同归属；异常、加载错误保留无效终态。
if .classification == "PRODUCT_FAIL" and $owner == "test_program"
then "INVALID_TEST_EXECUTION"
else .classification
end
