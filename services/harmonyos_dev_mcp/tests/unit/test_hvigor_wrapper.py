from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import subprocess
import os

from harmonyos_dev_mcp.config import Config
from harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper import HvigorWrapper


def _write_file(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _isolate_discovery_env(monkeypatch, *, clear_java=True, clear_path_java=False):
    for env_name in ("DEVECO_SDK_HOME", "HARMONYOS_SDK_PATH"):
        monkeypatch.delenv(env_name, raising=False)

    if clear_java:
        for env_name in ("JAVA_HOME", "JDK_HOME"):
            monkeypatch.delenv(env_name, raising=False)

    if clear_path_java:
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.shutil.which",
            lambda name: None,
        )


class TestHvigorWrapper:
    def test_custom_deveco_path_overrides_config_and_auto_detect(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "CustomDevEco"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(tmp_path / "WrongDevEco"))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            Config,
            "_detect_deveco_studio_path",
            classmethod(lambda cls: str(tmp_path / "AutoDetectedDevEco")),
        )
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: path == deveco),
        )
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project), deveco_path=str(deveco))

        assert wrapper.deveco_path == deveco

    def test_macos_bundle_layout_is_detected(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco-Studio.app"
        node = deveco / "Contents" / "tools" / "node" / "bin" / "node"
        hvigor = deveco / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "Contents" / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "Contents" / "jbr" / "Contents" / "Home" / "bin" / "java"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == node
        assert wrapper.hvigorw_js == hvigor
        assert wrapper.sdk_root == deveco / "Contents" / "sdk"
        assert wrapper.java_home == deveco / "Contents" / "jbr" / "Contents" / "Home"

    def test_config_tool_paths_are_preferred_when_present(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        config_node = tmp_path / "toolcache" / "node.exe"
        config_hvigor = tmp_path / "toolcache" / "hvigorw.js"

        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(config_node)
        _write_file(config_hvigor)

        monkeypatch.setattr(Config, "NODE_PATH", str(config_node))
        monkeypatch.setattr(Config, "HVIGOR_PATH", str(config_hvigor))
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == config_node
        assert wrapper.hvigorw_js == config_hvigor

    def test_execute_command_uses_isolated_hvigor_home(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco-Studio.app"
        node = deveco / "Contents" / "tools" / "node" / "bin" / "node"
        hvigor = deveco / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "Contents" / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "Contents" / "jbr" / "Contents" / "Home" / "bin" / "java"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        monkeypatch.setattr(Config, "BUILD_TIMEOUT", 42)
        _isolate_discovery_env(monkeypatch, clear_path_java=True)

        captured = {}

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["timeout"] = timeout
            captured["env"] = env
            captured["capture_output"] = capture_output
            captured["text"] = text
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build_hap()

        assert result["success"] is True
        assert captured["cmd"][0] == str(node)
        assert captured["cmd"][1] == str(hvigor)
        assert captured["cmd"][2] == "--no-daemon"
        assert captured["cwd"] == str(project)
        assert captured["timeout"] == 42
        assert captured["capture_output"] is True
        assert captured["text"] is True
        assert captured["env"]["DEVECO_SDK_HOME"] == str(deveco / "Contents" / "sdk")
        assert captured["env"]["HVIGOR_USER_HOME"].startswith(str(project / ".hvigor" / "mcp-user-home-"))
        assert captured["env"]["JAVA_HOME"] == str(deveco / "Contents" / "jbr" / "Contents" / "Home")

    def test_execute_command_falls_back_to_temp_hvigor_home_when_project_dir_not_writable(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_is_writable_dir(path: Path) -> bool:
            return ".hvigor" not in str(path)

        monkeypatch.setattr(HvigorWrapper, "_is_writable_dir", staticmethod(fake_is_writable_dir))
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "temp"))

        wrapper = HvigorWrapper(str(project))

        assert str(wrapper.hvigor_user_home).startswith(str(tmp_path / "temp" / "harmonyos_dev_mcp" / "hvigor_home"))

    def test_hvigor_user_home_is_unique_per_wrapper_instance(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper1 = HvigorWrapper(str(project))
        wrapper2 = HvigorWrapper(str(project))

        assert wrapper1.hvigor_user_home != wrapper2.hvigor_user_home

    def test_execute_command_cleans_up_hvigor_user_home(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds):
            Path(env["HVIGOR_USER_HOME"], "cache.txt").write_text("ok", encoding="utf-8")
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        hvigor_home = wrapper.hvigor_user_home

        result = wrapper.build_hap()

        assert result["success"] is True
        assert not hvigor_home.exists()

    def test_init_raises_when_no_writable_hvigor_home(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )
        monkeypatch.setattr(HvigorWrapper, "_is_writable_dir", staticmethod(lambda path: False))

        try:
            HvigorWrapper(str(project))
            assert False, "expected PermissionError"
        except PermissionError as exc:
            assert "HVIGOR_USER_HOME" in str(exc)

    def test_execute_command_marks_build_failed_output_as_failure(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco-Studio.app"
        node = deveco / "Contents" / "tools" / "node" / "bin" / "node"
        hvigor = deveco / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "Contents" / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "Contents" / "jbr" / "Contents" / "Home" / "bin" / "java"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds):
            return CompletedProcess(
                cmd,
                0,
                stdout="COMPILE RESULT:FAIL {ERROR:5}",
                stderr="> hvigor ERROR: BUILD FAILED in 2 s 600 ms",
            )

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build_hap()

        assert result["success"] is False

    def test_execute_command_handles_timeout(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="hvigor", timeout=kwargs["timeout"])

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build_hap()

        assert result["success"] is False
        assert result["error_code"] == "BUILD_TIMEOUT"
        assert "timed out" in result["stderr"]

    def test_build_hap_rejects_non_debug_mode(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build_hap(build_mode="release")

        assert result["success"] is False
        assert result["error_code"] == "INVALID_BUILD_MODE"

    def test_find_build_output_prefers_latest_match(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        older = project / "build" / "outputs" / "old-release.hap"
        newer = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        _write_file(older, "old")
        _write_file(newer, "new")
        os.utime(older, (100, 100))
        os.utime(newer, (200, 200))

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper._find_build_output("hap") == newer

    def test_init_raises_when_sdk_root_missing(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        java = deveco / "jbr" / "bin" / "java.exe"
        _write_file(node)
        _write_file(hvigor)
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        try:
            HvigorWrapper(str(project))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "HarmonyOS SDK" in str(exc)

    def test_windows_layout_is_detected(self, tmp_path, monkeypatch):
        """Test Windows DevEco layout: JBR directly under DevEco with java.exe"""
        project = tmp_path / "MyApplication"
        project.mkdir()

        # Windows layout: no Contents/ directory
        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)

        # Mock platform.system() to return "Windows"
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == node
        assert wrapper.hvigorw_js == hvigor
        assert wrapper.sdk_root == deveco / "sdk"
        assert wrapper.java_home == deveco / "jbr"

    def test_linux_layout_is_detected(self, tmp_path, monkeypatch):
        """Test Linux DevEco layout: similar to Windows but without .exe"""
        project = tmp_path / "MyApplication"
        project.mkdir()

        # Linux layout: similar to Windows, no Contents/ directory
        deveco = tmp_path / "DevEco-Studio"
        node = deveco / "tools" / "node" / "bin" / "node"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)

        # Mock platform.system() to return "Linux"
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Linux"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == node
        assert wrapper.hvigorw_js == hvigor
        assert wrapper.sdk_root == deveco / "sdk"
        assert wrapper.java_home == deveco / "jbr"

    def test_java_home_can_be_discovered_from_path(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        path_java_home = tmp_path / "CustomJdk"
        java = path_java_home / "bin" / "java.exe"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.shutil.which",
            lambda name: str(java) if name == "java" else None,
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.java_home == path_java_home

