"""
ErrorClassifier 完整测试套件

测试错误分类正确性、瞬态错误识别、边界情况
"""

import pytest
from common.utils.retry import ErrorClassifier, ErrorCategory


class TestErrorClassifierBasic:
    """测试错误分类器基本功能"""

    def test_classify_transient_timeout(self):
        """测试识别超时错误"""
        error = Exception("connection timeout")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_timed_out(self):
        """测试识别 timed out 错误"""
        error = Exception("operation timed out")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_chinese_timeout(self):
        """测试识别中文超时错误"""
        error = Exception("连接超时")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_connect(self):
        """测试识别连接错误"""
        error = Exception("cannot connect to device")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_connection_refused(self):
        """测试识别连接被拒绝错误"""
        error = Exception("connection refused")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_connection_reset(self):
        """测试识别连接重置错误"""
        error = Exception("connection reset by peer")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_device_not_respond(self):
        """测试识别设备无响应错误"""
        error = Exception("device not respond")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_device_not_found(self):
        """测试识别设备未找到错误"""
        error = Exception("device not found")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_broken_pipe(self):
        """测试识别管道破裂错误"""
        error = Exception("broken pipe")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_resource_unavailable(self):
        """测试识别资源暂时不可用错误"""
        error = Exception("resource temporarily unavailable")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_network(self):
        """测试识别网络错误"""
        error = Exception("network error occurred")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_chinese_network(self):
        """测试识别中文网络错误"""
        error = Exception("网络错误")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_temporarily(self):
        """测试识别暂时性错误"""
        error = Exception("temporarily unavailable")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_chinese_temporarily(self):
        """测试识别中文暂时性错误"""
        error = Exception("临时错误")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_unknown_syntax_error(self):
        """测试识别未知语法错误"""
        error = Exception("syntax error")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_unknown_permission_error(self):
        """测试识别权限错误"""
        error = Exception("permission denied")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_unknown_validation_error(self):
        """测试识别验证错误"""
        error = Exception("validation failed")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_empty_error(self):
        """测试识别空错误消息"""
        error = Exception("")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.UNKNOWN


class TestErrorClassifierResult:
    """测试结果错误分类"""

    def test_classify_result_success(self):
        """测试成功结果分类"""
        result = {"success": True, "data": "test"}
        category = ErrorClassifier.classify_result(result)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_result_transient_stderr(self):
        """测试结果中瞬态错误分类"""
        result = {"success": False, "stderr": "connection timeout"}
        category = ErrorClassifier.classify_result(result)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_result_unknown_stderr(self):
        """测试结果中未知错误分类"""
        result = {"success": False, "stderr": "invalid command"}
        category = ErrorClassifier.classify_result(result)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_result_no_stderr(self):
        """测试无 stderr 的结果分类"""
        result = {"success": False}
        category = ErrorClassifier.classify_result(result)
        assert category == ErrorCategory.UNKNOWN

    def test_classify_result_empty_stderr(self):
        """测试空 stderr 的结果分类"""
        result = {"success": False, "stderr": ""}
        category = ErrorClassifier.classify_result(result)
        assert category == ErrorCategory.UNKNOWN


class TestIsTransient:
    """测试瞬态错误判断"""

    def test_is_transient_exception_true(self):
        """测试异常瞬态判断（真）"""
        assert ErrorClassifier.is_transient(Exception("timeout"))
        assert ErrorClassifier.is_transient(Exception("connection refused"))
        assert ErrorClassifier.is_transient(Exception("device not found"))
        assert ErrorClassifier.is_transient(Exception("超时"))

    def test_is_transient_exception_false(self):
        """测试异常瞬态判断（假）"""
        assert not ErrorClassifier.is_transient(Exception("syntax error"))
        assert not ErrorClassifier.is_transient(Exception("permission denied"))
        assert not ErrorClassifier.is_transient(Exception(""))
        assert not ErrorClassifier.is_transient(Exception("validation failed"))

    def test_is_transient_dict_true(self):
        """测试字典瞬态判断（真）"""
        assert ErrorClassifier.is_transient({"success": False, "stderr": "timeout"})
        assert ErrorClassifier.is_transient({"success": False, "stderr": "connection reset"})
        assert ErrorClassifier.is_transient({"success": False, "stderr": "网络错误"})

    def test_is_transient_dict_false(self):
        """测试字典瞬态判断（假）"""
        assert not ErrorClassifier.is_transient({"success": True})
        assert not ErrorClassifier.is_transient({"success": False, "stderr": "syntax error"})
        assert not ErrorClassifier.is_transient({"success": False, "stderr": ""})
        assert not ErrorClassifier.is_transient({"success": False})

    def test_is_transient_invalid_type(self):
        """测试无效类型瞬态判断"""
        assert not ErrorClassifier.is_transient(None)
        assert not ErrorClassifier.is_transient("string")
        assert not ErrorClassifier.is_transient(123)
        assert not ErrorClassifier.is_transient([])


class TestErrorClassifierEdgeCases:
    """测试边界情况"""

    def test_case_sensitivity(self):
        """测试大小写敏感性（转换为小写后匹配）"""
        error_lower = Exception("timeout")
        error_upper = Exception("TIMEOUT")
        error_mixed = Exception("Connection Timeout")

        assert ErrorClassifier.classify_error(error_lower) == ErrorCategory.TRANSIENT
        assert ErrorClassifier.classify_error(error_upper) == ErrorCategory.TRANSIENT
        assert ErrorClassifier.classify_error(error_mixed) == ErrorCategory.TRANSIENT

    def test_partial_match(self):
        """测试部分匹配"""
        error = Exception("operation timed out after 30 seconds")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_multiple_patterns(self):
        """测试多个模式匹配"""
        error = Exception("connection timeout and network error")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        error = Exception("  timeout  ")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_special_characters(self):
        """测试特殊字符"""
        error = Exception("timeout!@#$%^&*()")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_unicode_characters(self):
        """测试 Unicode 字符"""
        error = Exception("超时错误")
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_very_long_error_message(self):
        """测试超长错误消息"""
        long_msg = "a" * 10000 + "timeout" + "b" * 10000
        error = Exception(long_msg)
        category = ErrorClassifier.classify_error(error)
        assert category == ErrorCategory.TRANSIENT


class TestErrorClassifierPatterns:
    """测试错误模式集合"""

    def test_all_transient_patterns(self):
        """测试所有瞬态模式"""
        patterns = [
            "timeout",
            "timed out",
            "超时",
            "connect",
            "connection refused",
            "connection reset",
            "device not respond",
            "device not found",
            "cannot connect",
            "broken pipe",
            "resource temporarily unavailable",
            "network",
            "网络",
            "temporarily",
            "临时",
        ]

        for pattern in patterns:
            error = Exception(pattern)
            category = ErrorClassifier.classify_error(error)
            assert category == ErrorCategory.TRANSIENT, f"Pattern '{pattern}' should be transient"

    def test_patterns_are_lowercase(self):
        """测试模式都是小写"""
        for pattern in ErrorClassifier.TRANSIENT_PATTERNS:
            assert pattern.islower() or any(ord(c) > 127 for c in pattern), (
                f"Pattern '{pattern}' should be lowercase or contain non-ASCII"
            )

    def test_patterns_not_empty(self):
        """测试模式集合不为空"""
        assert len(ErrorClassifier.TRANSIENT_PATTERNS) > 0

    def test_patterns_are_unique(self):
        """测试模式唯一性"""
        patterns_list = list(ErrorClassifier.TRANSIENT_PATTERNS)
        assert len(patterns_list) == len(set(patterns_list))


class TestErrorCategoryEnum:
    """测试错误分类枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_enum_comparison(self):
        """测试枚举比较"""
        assert ErrorCategory.TRANSIENT == ErrorCategory.TRANSIENT
        assert ErrorCategory.TRANSIENT != ErrorCategory.UNKNOWN
        assert ErrorCategory.UNKNOWN != ErrorCategory.PERMANENT

    def test_enum_members(self):
        """测试枚举成员"""
        assert hasattr(ErrorCategory, "TRANSIENT")
        assert hasattr(ErrorCategory, "PERMANENT")
        assert hasattr(ErrorCategory, "UNKNOWN")
