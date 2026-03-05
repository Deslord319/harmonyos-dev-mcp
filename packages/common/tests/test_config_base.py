"""
ConfigBase 完整测试套件

测试配置文件加载、优先级、重新加载、错误处理
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from common.config.base import ConfigBase


class TestConfigFileLoading:
    """测试配置文件加载"""

    def test_load_yaml_config(self):
        """测试加载 YAML 配置文件"""
        yaml_content = """
LOG_LEVEL: DEBUG
MAX_RETRIES: 5
RETRY_DELAY: 3
COMMAND_TIMEOUT: 60
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "DEBUG"
            assert ConfigBase.MAX_RETRIES == 5
            assert ConfigBase.RETRY_DELAY == 3
            assert ConfigBase.COMMAND_TIMEOUT == 60
        finally:
            os.unlink(config_path)

    def test_load_json_config(self):
        """测试加载 JSON 配置文件"""
        json_content = {
            "LOG_LEVEL": "WARNING",
            "MAX_RETRIES": 10,
            "RETRY_DELAY": 5,
            "COMMAND_TIMEOUT": 120,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(json_content, f)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "WARNING"
            assert ConfigBase.MAX_RETRIES == 10
            assert ConfigBase.RETRY_DELAY == 5
            assert ConfigBase.COMMAND_TIMEOUT == 120
        finally:
            os.unlink(config_path)

    def test_load_yml_extension(self):
        """测试加载 .yml 扩展名配置文件"""
        yaml_content = """
LOG_LEVEL: ERROR
MAX_RETRIES: 2
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "ERROR"
            assert ConfigBase.MAX_RETRIES == 2
        finally:
            os.unlink(config_path)

    def test_unsupported_file_format(self):
        """测试不支持的配置文件格式"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid format")
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase._config_file = None
            ConfigBase.LOG_LEVEL = "INFO"
            ConfigBase.MAX_RETRIES = 3
            ConfigBase.RETRY_DELAY = 2
            ConfigBase.COMMAND_TIMEOUT = 30
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "INFO"
            assert ConfigBase.MAX_RETRIES == 3
        finally:
            os.unlink(config_path)
            ConfigBase._initialized = False
            ConfigBase._config_file = None


class TestConfigPriority:
    """测试配置优先级"""

    def test_priority_env_over_config(self):
        """测试环境变量优先级最高"""
        yaml_content = """
MAX_RETRIES: 5
RETRY_DELAY: 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            original_max = os.getenv("MAX_RETRIES")
            original_delay = os.getenv("RETRY_DELAY")

            os.environ["MAX_RETRIES"] = "10"
            os.environ["RETRY_DELAY"] = "8"

            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.MAX_RETRIES == 10
            assert ConfigBase.RETRY_DELAY == 8

            if original_max:
                os.environ["MAX_RETRIES"] = original_max
            else:
                os.environ.pop("MAX_RETRIES", None)

            if original_delay:
                os.environ["RETRY_DELAY"] = original_delay
            else:
                os.environ.pop("RETRY_DELAY", None)
        finally:
            os.unlink(config_path)

    def test_priority_config_over_default(self):
        """测试配置文件优先级高于默认值"""
        yaml_content = """
LOG_LEVEL: DEBUG
MAX_RETRIES: 7
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase._config_file = None
            ConfigBase.LOG_LEVEL = "INFO"
            ConfigBase.MAX_RETRIES = 3
            ConfigBase.RETRY_DELAY = 2
            ConfigBase.COMMAND_TIMEOUT = 30
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "DEBUG"
            assert ConfigBase.MAX_RETRIES == 7
            assert ConfigBase.RETRY_DELAY == 2
            assert ConfigBase.COMMAND_TIMEOUT == 30
        finally:
            os.unlink(config_path)
            ConfigBase._initialized = False
            ConfigBase._config_file = None

    def test_priority_without_config_file(self):
        """测试无配置文件时使用默认值"""
        ConfigBase._initialized = False
        ConfigBase._config_file = None
        ConfigBase.LOG_LEVEL = "INFO"
        ConfigBase.MAX_RETRIES = 3
        ConfigBase.RETRY_DELAY = 2
        ConfigBase.COMMAND_TIMEOUT = 30
        ConfigBase.init()

        assert ConfigBase.LOG_LEVEL == "INFO"
        assert ConfigBase.MAX_RETRIES == 3
        assert ConfigBase.RETRY_DELAY == 2
        assert ConfigBase.COMMAND_TIMEOUT == 30

    def test_env_var_string_to_int_conversion(self):
        """测试环境变量字符串到整数的转换"""
        original = os.getenv("MAX_RETRIES")
        os.environ["MAX_RETRIES"] = "15"

        try:
            ConfigBase._initialized = False
            ConfigBase.init()

            assert isinstance(ConfigBase.MAX_RETRIES, int)
            assert ConfigBase.MAX_RETRIES == 15
        finally:
            if original:
                os.environ["MAX_RETRIES"] = original
            else:
                os.environ.pop("MAX_RETRIES", None)


class TestConfigReload:
    """测试配置重新加载"""

    def test_reload_config(self):
        """测试重新加载配置"""
        yaml_content = """
LOG_LEVEL: DEBUG
MAX_RETRIES: 5
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.MAX_RETRIES == 5

            yaml_content_new = """
LOG_LEVEL: WARNING
MAX_RETRIES: 8
"""
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(yaml_content_new)

            ConfigBase.reload()

            assert ConfigBase.MAX_RETRIES == 8
            assert ConfigBase.LOG_LEVEL == "WARNING"
        finally:
            os.unlink(config_path)

    def test_reload_preserves_config_file_path(self):
        """测试重新加载保持配置文件路径"""
        yaml_content = "MAX_RETRIES: 5"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            original_path = ConfigBase._config_file
            ConfigBase.reload()

            assert ConfigBase._config_file == original_path
        finally:
            os.unlink(config_path)


class TestConfigErrorHandling:
    """测试配置错误处理"""

    def test_file_not_exists(self):
        """测试配置文件不存在"""
        ConfigBase._initialized = False
        ConfigBase._config_file = None
        ConfigBase.LOG_LEVEL = "INFO"
        ConfigBase.MAX_RETRIES = 3
        ConfigBase.set_config_file("/nonexistent/config.yaml")
        ConfigBase.init()

        assert ConfigBase.LOG_LEVEL == "INFO"
        assert ConfigBase.MAX_RETRIES == 3

    def test_invalid_yaml_format(self):
        """测试无效的 YAML 格式"""
        invalid_yaml = """
LOG_LEVEL: DEBUG
MAX_RETRIES: [invalid
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(invalid_yaml)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase._config_file = None
            ConfigBase.LOG_LEVEL = "INFO"
            ConfigBase.MAX_RETRIES = 3
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "INFO"
            assert ConfigBase.MAX_RETRIES == 3
        finally:
            os.unlink(config_path)
            ConfigBase._initialized = False
            ConfigBase._config_file = None

    def test_invalid_json_format(self):
        """测试无效的 JSON 格式"""
        invalid_json = "{LOG_LEVEL: DEBUG}"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(invalid_json)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase._config_file = None
            ConfigBase.LOG_LEVEL = "INFO"
            ConfigBase.MAX_RETRIES = 3
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "INFO"
            assert ConfigBase.MAX_RETRIES == 3
        finally:
            os.unlink(config_path)
            ConfigBase._initialized = False
            ConfigBase._config_file = None

    def test_empty_config_file(self):
        """测试空配置文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase._config_file = None
            ConfigBase.LOG_LEVEL = "INFO"
            ConfigBase.MAX_RETRIES = 3
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            assert ConfigBase.LOG_LEVEL == "INFO"
            assert ConfigBase.MAX_RETRIES == 3
        finally:
            os.unlink(config_path)
            ConfigBase._initialized = False
            ConfigBase._config_file = None

    def test_yaml_without_pyyaml(self):
        """测试没有 PyYAML 时加载 YAML"""
        import common.config.base as config_module

        original_yaml = config_module.yaml

        config_module.yaml = None

        try:
            yaml_content = "MAX_RETRIES: 5"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            ) as f:
                f.write(yaml_content)
                config_path = f.name

            try:
                ConfigBase._initialized = False
                ConfigBase._config_file = None
                ConfigBase.MAX_RETRIES = 3
                ConfigBase.set_config_file(config_path)
                ConfigBase.init()

                assert ConfigBase.MAX_RETRIES == 3
            finally:
                os.unlink(config_path)
                ConfigBase._initialized = False
                ConfigBase._config_file = None
        finally:
            config_module.yaml = original_yaml


class TestConfigUtilityMethods:
    """测试配置工具方法"""

    def test_ensure_init(self):
        """测试 ensure_init 方法"""
        ConfigBase._initialized = False
        ConfigBase.ensure_init()

        assert ConfigBase._initialized

    def test_get_config_info(self):
        """测试获取配置信息"""
        ConfigBase._initialized = False
        ConfigBase._config_file = None
        ConfigBase.LOG_LEVEL = "INFO"
        ConfigBase.MAX_RETRIES = 3
        ConfigBase.RETRY_DELAY = 2
        ConfigBase.COMMAND_TIMEOUT = 30
        ConfigBase.init()

        info = ConfigBase.get_config_info()

        assert "LOG_LEVEL" in info
        assert "MAX_RETRIES" in info
        assert "RETRY_DELAY" in info
        assert "COMMAND_TIMEOUT" in info
        assert info["LOG_LEVEL"] == "INFO"
        assert info["MAX_RETRIES"] == 3

    def test_get_config_info_with_file(self):
        """测试获取配置信息（包含文件路径）"""
        yaml_content = "MAX_RETRIES: 5"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            ConfigBase._initialized = False
            ConfigBase.set_config_file(config_path)
            ConfigBase.init()

            info = ConfigBase.get_config_info()

            assert "config_file" in info
            assert Path(info["config_file"]) == Path(config_path)
        finally:
            os.unlink(config_path)

    def test_set_config_file(self):
        """测试设置配置文件路径"""
        ConfigBase._initialized = False
        ConfigBase.set_config_file("test_config.yaml")

        assert ConfigBase._config_file == "test_config.yaml"


class TestConfigMultipleInstances:
    """测试多实例配置隔离"""

    def test_subclass_isolation(self):
        """测试子类配置隔离"""

        class ConfigA(ConfigBase):
            LOG_LEVEL: str = "DEBUG"

        class ConfigB(ConfigBase):
            LOG_LEVEL: str = "ERROR"

        ConfigA._initialized = False
        ConfigB._initialized = False

        ConfigA.init()
        ConfigB.init()

        assert ConfigA.LOG_LEVEL == "DEBUG"
        assert ConfigB.LOG_LEVEL == "ERROR"
