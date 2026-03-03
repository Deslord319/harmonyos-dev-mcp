from pathlib import Path
from subprocess import CompletedProcess
import platform

from harmonyos_mcp.config import Config
from harmonyos_mcp.utils.wrappers.hvigor_wrapper import HvigorWrapper


def _write_file(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestHvigorWrapper:
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

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == node
        assert wrapper.hvigorw_js == hvigor
        assert wrapper.sdk_root == deveco / "Contents" / "sdk"
        assert wrapper.java_home == deveco / "Contents" / "jbr" / "Contents" / "Home"

    def test_project_sdk_dir_is_normalized_to_sdk_root(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()
        _write_file(project / "local.properties", f"sdk.dir={tmp_path / 'sdk' / 'default'}\n")

        sdk_pkg = tmp_path / "sdk" / "default" / "sdk-pkg.json"
        _write_file(sdk_pkg, "{}")

        deveco = tmp_path / "DevEco-Studio.app"
        node = deveco / "Contents" / "tools" / "node" / "bin" / "node"
        hvigor = deveco / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js"
        java = deveco / "Contents" / "jbr" / "Contents" / "Home" / "bin" / "java"
        _write_file(node)
        _write_file(hvigor)
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))

        wrapper = HvigorWrapper(str(project))

        assert wrapper.sdk_root == tmp_path / "sdk"

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

        captured = {}

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["timeout"] = timeout
            captured["env"] = env
            captured["capture_output"] = capture_output
            captured["text"] = text
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

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
        assert captured["env"]["HVIGOR_USER_HOME"] == str(project / ".hvigor" / "mcp-user-home")
        assert captured["env"]["JAVA_HOME"] == str(deveco / "Contents" / "jbr" / "Contents" / "Home")

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

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds):
            return CompletedProcess(
                cmd,
                0,
                stdout="COMPILE RESULT:FAIL {ERROR:5}",
                stderr="> hvigor ERROR: BUILD FAILED in 2 s 600 ms",
            )

        monkeypatch.setattr("harmonyos_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build_hap()

        assert result["success"] is False

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

        # Mock platform.system() to return "Windows"
        monkeypatch.setattr(
            "harmonyos_mcp.utils.wrappers.hvigor_wrapper.platform.system",
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

        # Mock platform.system() to return "Linux"
        monkeypatch.setattr(
            "harmonyos_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Linux"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.node_exe == node
        assert wrapper.hvigorw_js == hvigor
        assert wrapper.sdk_root == deveco / "sdk"
        assert wrapper.java_home == deveco / "jbr"
