from pathlib import Path
from subprocess import CompletedProcess
import json
import tempfile
import subprocess
import os
import zipfile

from harmonyos_dev_mcp.config import Config
from harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper import HvigorWrapper


def _write_file(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_hap(path: Path, entries: dict[str, str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _write_hsp(path: Path, module_name: str):
    _write_hap(
        path,
        {
            "module.json": f'{{"module":{{"name":"{module_name}","type":"shared"}}}}',
            "pack.info": json.dumps(
                {
                    "summary": {
                        "modules": [
                            {
                                "distro": {
                                    "moduleType": "shared",
                                    "moduleName": module_name,
                                    "deliveryWithInstall": True,
                                }
                            }
                        ]
                    },
                    "packages": [
                        {
                            "moduleType": "shared",
                            "name": f"{module_name}-default",
                        }
                    ],
                },
                separators=(",", ":"),
            ),
        },
    )


def _write_minimal_build_profile(project: Path):
    _write_file(project / "build-profile.json5", '{ signingConfigs: [{ profile: "./sign/default.p7b" }] }')
    _write_file(project / "sign" / "default.p7b", "ok")


def _write_declared_build_profile(project: Path):
    _write_file(
        project / "build-profile.json5",
        """
        {
          "app": {
            "products": [
              {
                "name": "default",
                "signingConfig": "default"
              }
            ],
            "buildModeSet": [
              { "name": "debug" },
              { "name": "release" }
            ],
            "signingConfigs": [
              {
                "name": "default",
                "material": {
                  "profile": "./sign/default.p7b"
                }
              }
            ]
          }
        }
        """,
    )
    _write_file(project / "sign" / "default.p7b", "ok")


def _write_full_signing_build_profile(project: Path):
    _write_file(
        project / "build-profile.json5",
        """
        {
          "app": {
            "signingConfigs": [
              {
                "name": "default",
                "material": {
                  "certpath": "./sign/application.pem",
                  "keyAlias": "openharmony application release",
                  "keyPassword": "000000167480EFDCA360901AC59CD0CC6BE9EAEE9D5AAB8213F99DD4A091C3E",
                  "profile": "./sign/default.p7b",
                  "signAlg": "SHA256withECDSA",
                  "storeFile": "./sign/application.p12",
                  "storePassword": "000000167480EFDCA360901AC59CD0CC6BE9EAEE9D5AAB8213F99DD4A091C3E"
                }
              }
            ],
            "products": [
              {
                "name": "default",
                "signingConfig": "default",
                "targetSdkVersion": "6.0.2(22)",
                "compatibleSdkVersion": "6.0.2(22)"
              }
            ],
            "buildModeSet": [
              { "name": "debug" },
              { "name": "release" }
            ]
          },
          "modules": [
            {
              "name": "entry",
              "srcPath": "./entry"
            }
          ]
        }
        """,
    )
    _write_file(project / "sign" / "application.pem", "cert")
    _write_file(project / "sign" / "default.p7b", "profile")
    _write_file(project / "sign" / "application.p12", "store")


def _write_hnp_packaging_inputs(project: Path):
    root = project / "entry" / "build" / "default"
    _write_file(root / "intermediates" / "package" / "default" / "module.json", "{}")
    _write_file(root / "intermediates" / "res" / "default" / "resources" / "rawfile.txt", "resource")
    _write_file(root / "intermediates" / "loader_out" / "default" / "ets" / "modules.abc", "abc")
    _write_file(root / "intermediates" / "libs" / "default" / "arm64-v8a" / "libentry.so", "native")
    _write_file(root / "intermediates" / "res" / "default" / "resources.index", "index")
    _write_file(root / "intermediates" / "loader" / "default" / "pkgContextInfo.json", "{}")
    _write_file(root / "outputs" / "default" / "pack.info", "{}")


def _write_shared_module_build_profile(project: Path):
    _write_full_signing_build_profile(project)
    profile = project / "build-profile.json5"
    content = profile.read_text(encoding="utf-8")
    content = content.replace(
        """
            {
              "name": "entry",
              "srcPath": "./entry"
            }
        """,
        """
            {
              "name": "entry",
              "srcPath": "./entry"
            },
            {
              "name": "library",
              "srcPath": "./library"
            }
        """,
    )
    profile.write_text(content, encoding="utf-8")
    _write_file(
        project / "library" / "src" / "main" / "module.json5",
        """
        {
          "module": {
            "name": "library",
            "type": "shared",
            "deviceTypes": ["phone"]
          }
        }
        """,
    )


def _write_two_shared_module_build_profile(project: Path):
    _write_full_signing_build_profile(project)
    profile = project / "build-profile.json5"
    content = profile.read_text(encoding="utf-8")
    content = content.replace(
        """
            {
              "name": "entry",
              "srcPath": "./entry"
            }
        """,
        """
            {
              "name": "entry",
              "srcPath": "./entry"
            },
            {
              "name": "library",
              "srcPath": "./library"
            },
            {
              "name": "feature",
              "srcPath": "./feature"
            }
        """,
    )
    profile.write_text(content, encoding="utf-8")
    for module in ("library", "feature"):
        _write_file(
            project / module / "src" / "main" / "module.json5",
            f"""
            {{
              "module": {{
                "name": "{module}",
                "type": "shared",
                "deviceTypes": ["phone"]
              }}
            }}
            """,
        )


def _write_unsigned_shared_module_build_profile(project: Path):
    _write_file(
        project / "build-profile.json5",
        """
        {
          "app": {
            "products": [
              {
                "name": "default",
                "targetSdkVersion": "6.0.2(22)",
                "compatibleSdkVersion": "6.0.2(22)"
              }
            ],
            "buildModeSet": [
              { "name": "debug" },
              { "name": "release" }
            ]
          },
          "modules": [
            {
              "name": "entry",
              "srcPath": "./entry"
            },
            {
              "name": "library",
              "srcPath": "./library"
            }
          ]
        }
        """,
    )
    _write_file(
        project / "library" / "src" / "main" / "module.json5",
        """
        {
          "module": {
            "name": "library",
            "type": "shared",
            "deviceTypes": ["phone"]
          }
        }
        """,
    )


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
        _write_minimal_build_profile(project)

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

        artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        _write_file(artifact, "ok")

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["timeout"] = timeout
            captured["env"] = env
            captured["capture_output"] = capture_output
            captured["text"] = text
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is True
        assert result["output_path"] == str(artifact)
        assert result["artifact_source"] == "logs"
        assert result["sign_status"] == "unsigned"
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
        _write_minimal_build_profile(project)

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

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            Path(env["HVIGOR_USER_HOME"], "cache.txt").write_text("ok", encoding="utf-8")
            artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
            _write_file(artifact, "ok")
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        hvigor_home = wrapper.hvigor_user_home

        result = wrapper.build()

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
        _write_minimal_build_profile(project)

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

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(
                cmd,
                0,
                stdout="COMPILE RESULT:FAIL {ERROR:5}",
                stderr="> hvigor ERROR: BUILD FAILED in 2 s 600 ms",
            )

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is False

    def test_execute_command_handles_timeout(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()
        _write_minimal_build_profile(project)

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
        result = wrapper.build()

        assert result["success"] is False
        assert result["error_code"] == "BUILD_TIMEOUT"
        assert "timed out" in result["stderr"]

    def test_build_accepts_release_mode(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()
        _write_declared_build_profile(project)

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

        captured = {}
        artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed.hap"
        _write_file(artifact, "ok")

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            captured["cmd"] = cmd
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(build_mode="release")

        assert result["success"] is True
        assert "buildMode=release" in captured["cmd"]

    def test_build_rejects_undeclared_build_mode(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()
        _write_declared_build_profile(project)

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
        result = wrapper.build(build_mode="profile")

        assert result["success"] is False
        assert result["error_code"] == "INVALID_BUILD_MODE"

    def test_build_rejects_har_without_module_name(self, tmp_path, monkeypatch):
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
        result = wrapper.build(target="har")

        assert result["success"] is False
        assert result["error_code"] == "MISSING_MODULE_NAME"

    def test_build_rejects_when_build_profile_is_missing(self, tmp_path, monkeypatch):
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
        result = wrapper.build()

        assert result["success"] is False
        assert result["error_code"] == "BUILD_PROFILE_MISSING"

    def test_build_rejects_when_signing_file_is_missing(self, tmp_path, monkeypatch):
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
        _write_file(
            project / "build-profile.json5",
            """
            {
              "app": {
                "products": [
                  {
                    "name": "default",
                    "signingConfig": "default"
                  }
                ],
                "signingConfigs": [
                  {
                    "name": "default",
                    "material": {
                      "profile": "./sign/default.p7b",
                      "certpath": "./sign/default.cer"
                    }
                  }
                ]
              }
            }
            """,
        )

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
        result = wrapper.build()

        assert result["success"] is False
        assert result["error_code"] == "SIGNING_FILE_NOT_FOUND"

    def test_build_uses_output_path_from_logs_before_file_scan(self, tmp_path, monkeypatch):
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
        _write_file(project / "build-profile.json5", "{ signingConfigs: [{ profile: \"./sign/default.p7b\" }] }")
        _write_file(project / "sign" / "default.p7b", "ok")
        artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        _write_file(artifact, "new")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is True
        assert result["output_path"] == str(artifact)

    def test_build_prefers_output_metadata_artifact(self, tmp_path, monkeypatch):
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
        _write_declared_build_profile(project)
        signed_artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed.hap"
        unsigned_artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        metadata = project / "entry" / "build" / "default" / "intermediates" / "hap_metadata" / "default" / "output_metadata.json"
        _write_file(unsigned_artifact, "unsigned")
        _write_file(signed_artifact, "signed")
        _write_file(metadata, '[{"hapName":"entry-default-signed.hap","isSigned":true}]')

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(cmd, 0, stdout=f"artifact: {unsigned_artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap", build_mode="release")

        assert result["success"] is True
        assert result["output_path"] == str(signed_artifact)
        assert result["artifact_source"] == "metadata"
        assert result["sign_status"] == "signed"

    def test_build_hnp_repackages_and_signs_without_project_script(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_full_signing_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_file(project / "entry" / "hnp" / "arm64-v8a" / "xrdp.hnp", "hnp")
        _write_hnp_packaging_inputs(project)
        unsigned_hnp = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned-hnp.hap"
        signed_hnp = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed-hnp.hap"

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        calls = []

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            calls.append((cmd, cwd, env))
            command = " ".join(str(part) for part in cmd)
            if "app_packing_tool.jar" in command:
                _write_hap(unsigned_hnp, {"module.json": "{}", "hnp/arm64-v8a/xrdp.hnp": "hnp"})
                return CompletedProcess(cmd, 0, stdout=f"packed {unsigned_hnp}", stderr="")
            if "hap-sign-tool.jar" in command:
                if "000000167480EFDCA360901AC59CD0CC6BE9EAEE9D5AAB8213F99DD4A091C3E" in command:
                    return CompletedProcess(cmd, 1, stdout="", stderr="keystore password was incorrect")
                assert "123456" in cmd
                _write_hap(signed_hnp, {"module.json": "{}", "hnp/arm64-v8a/xrdp.hnp": "hnp"})
                return CompletedProcess(cmd, 0, stdout=f"signed {signed_hnp}", stderr="")
            return CompletedProcess(cmd, 0, stdout="hvigor ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hnp")

        assert result["success"] is True
        assert result["output_path"] == str(signed_hnp)
        assert result["artifact_source"] == "hnp_direct"
        assert result["sign_status"] == "signed"
        assert len(calls) == 4
        assert calls[0][0][0] == str(node)
        assert "app_packing_tool.jar" in " ".join(str(part) for part in calls[1][0])
        assert "hap-sign-tool.jar" in " ".join(str(part) for part in calls[2][0])
        assert "hap-sign-tool.jar" in " ".join(str(part) for part in calls[3][0])
        assert all(call[0][0] not in {"cmd.exe", "powershell.exe", "bash"} for call in calls)

    def test_build_hnp_fails_when_hnp_package_is_missing(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(cmd, 0, stdout="hvigor ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hnp")

        assert result["success"] is False
        assert result["error_code"] == "HNP_PACKAGE_NOT_FOUND"
        assert result["output_path"] is None

    def test_build_hap_does_not_run_hnp_packaging_even_when_hnp_package_exists(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed.hap"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_declared_build_profile(project)
        _write_file(project / "entry" / "hnp" / "arm64-v8a" / "xrdp.hnp", "hnp")
        _write_file(artifact, "signed")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        calls = []

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            calls.append(cmd)
            command = " ".join(str(part) for part in cmd)
            assert "app_packing_tool.jar" not in command
            assert "hap-sign-tool.jar" not in command
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap")

        assert result["success"] is True
        assert result["output_path"] == str(artifact)
        assert len(calls) == 1

    def test_build_hnp_fails_when_sdk_packaging_jars_are_missing(self, tmp_path, monkeypatch):
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
        _write_full_signing_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_file(project / "entry" / "hnp" / "arm64-v8a" / "xrdp.hnp", "hnp")
        _write_hnp_packaging_inputs(project)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(cmd, 0, stdout="hvigor ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hnp")

        assert result["success"] is False
        assert result["error_code"] == "HNP_TOOLCHAIN_NOT_FOUND"
        assert "app_packing_tool.jar" in result["stderr"]
        assert "hap-sign-tool.jar" in result["stderr"]

    def test_build_hnp_fails_when_packaging_inputs_are_missing(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_full_signing_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_file(project / "entry" / "hnp" / "arm64-v8a" / "xrdp.hnp", "hnp")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            return CompletedProcess(cmd, 0, stdout="hvigor ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hnp")

        assert result["success"] is False
        assert result["error_code"] == "HNP_PACKAGING_INPUT_MISSING"
        assert "module.json" in result["stderr"]

    def test_build_hsp_requires_module_name(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)

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
        result = wrapper.build(target="hsp")

        assert result["success"] is False
        assert result["error_code"] == "MISSING_MODULE_NAME"

    def test_build_hsp_runs_assemble_hsp_and_returns_hsp_output(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        artifact = project / "library" / "build" / "default" / "outputs" / "default" / "library-default-signed.hsp"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_declared_build_profile(project)
        _write_file(artifact, "hsp")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        captured = {}

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            captured["cmd"] = cmd
            return CompletedProcess(cmd, 0, stdout=f"artifact: {artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hsp", module_name="library")

        assert result["success"] is True
        assert result["output_path"] == str(artifact)
        assert "assembleHsp" in captured["cmd"]
        assert "module=library" in captured["cmd"]

    def test_build_hap_can_repack_and_sign_with_hsp(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        hsp_artifact = project / "library" / "build" / "default" / "outputs" / "default" / "library-default-signed.hsp"
        unsigned_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned-hsp.hap"
        signed_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed-hsp.hap"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_shared_module_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_hnp_packaging_inputs(project)
        _write_hsp(hsp_artifact, "library")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        calls = []

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            calls.append(cmd)
            command = " ".join(str(part) for part in cmd)
            if "app_packing_tool.jar" in command:
                assert "--shared-libs-path" in cmd
                pack_info = Path(cmd[cmd.index("--pack-info-path") + 1])
                assert '"moduleName":"library"' in pack_info.read_text(encoding="utf-8")
                _write_hap(unsigned_hap, {"module.json": "{}", "shared_libs/library-default-signed.hsp": "hsp"})
                return CompletedProcess(cmd, 0, stdout=f"packed {unsigned_hap}", stderr="")
            if "hap-sign-tool.jar" in command:
                if "000000167480EFDCA360901AC59CD0CC6BE9EAEE9D5AAB8213F99DD4A091C3E" in command:
                    return CompletedProcess(cmd, 1, stdout="", stderr="keystore password was incorrect")
                _write_hap(signed_hap, {"module.json": "{}", "shared_libs/library-default-signed.hsp": "hsp"})
                return CompletedProcess(cmd, 0, stdout=f"signed {signed_hap}", stderr="")
            if "assembleHsp" in cmd:
                return CompletedProcess(cmd, 0, stdout=f"artifact: {hsp_artifact}", stderr="")
            return CompletedProcess(cmd, 0, stdout="hvigor hap ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap", include_hsp=True, hsp_module_name="library")

        assert result["success"] is True
        assert result["output_path"] == str(signed_hap)
        assert result["hsp_output_paths"] == [str(hsp_artifact)]
        assert result["artifact_source"] == "hsp_direct"
        assert result["sign_status"] == "signed"
        assert any("assembleHsp" in call for call in calls)
        assert any("--shared-libs-path" in call for call in calls)

    def test_build_hap_can_repack_and_sign_with_multiple_hsps(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        artifacts = {
            "library": project / "library" / "build" / "default" / "outputs" / "default" / "library-default-signed.hsp",
            "feature": project / "feature" / "build" / "default" / "outputs" / "default" / "feature-default-signed.hsp",
        }
        unsigned_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned-hsp.hap"
        signed_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed-hsp.hap"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_two_shared_module_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_hnp_packaging_inputs(project)
        for module, artifact in artifacts.items():
            _write_hsp(artifact, module)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        hsp_modules = []

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            command = " ".join(str(part) for part in cmd)
            if "app_packing_tool.jar" in command:
                assert "--shared-libs-path" in cmd
                shared_libs = Path(cmd[cmd.index("--shared-libs-path") + 1])
                pack_info = Path(cmd[cmd.index("--pack-info-path") + 1]).read_text(encoding="utf-8")
                assert (shared_libs / "library-default-signed.hsp").exists()
                assert (shared_libs / "feature-default-signed.hsp").exists()
                assert '"moduleName":"library"' in pack_info
                assert '"moduleName":"feature"' in pack_info
                _write_hap(
                    unsigned_hap,
                    {
                        "module.json": "{}",
                        "shared_libs/library-default-signed.hsp": "hsp",
                        "shared_libs/feature-default-signed.hsp": "hsp",
                    },
                )
                return CompletedProcess(cmd, 0, stdout=f"packed {unsigned_hap}", stderr="")
            if "hap-sign-tool.jar" in command:
                _write_hap(
                    signed_hap,
                    {
                        "module.json": "{}",
                        "shared_libs/library-default-signed.hsp": "hsp",
                        "shared_libs/feature-default-signed.hsp": "hsp",
                    },
                )
                return CompletedProcess(cmd, 0, stdout=f"signed {signed_hap}", stderr="")
            if "assembleHsp" in cmd:
                module = next(part.split("=", 1)[1] for part in cmd if str(part).startswith("module="))
                hsp_modules.append(module)
                return CompletedProcess(cmd, 0, stdout=f"artifact: {artifacts[module]}", stderr="")
            return CompletedProcess(cmd, 0, stdout="hvigor hap ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap", include_hsp=True, hsp_module_names=["library", "feature"])

        assert result["success"] is True
        assert result["output_path"] == str(signed_hap)
        assert result["hsp_output_paths"] == [str(artifacts["library"]), str(artifacts["feature"])]
        assert hsp_modules == ["library", "feature"]
        with zipfile.ZipFile(signed_hap) as archive:
            names = archive.namelist()
        assert "shared_libs/library-default-signed.hsp" in names
        assert "shared_libs/feature-default-signed.hsp" in names

    def test_build_hap_accepts_comma_separated_hsp_module_names(self, tmp_path, monkeypatch):
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
        _write_two_shared_module_build_profile(project)

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

        assert wrapper._resolve_hsp_module_names("library, feature;library", None) == ["library", "feature"]

    def test_build_hap_with_hsp_retries_stale_hsp_output_with_clean(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        app_packing_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "app_packing_tool.jar"
        hap_sign_tool = deveco / "sdk" / "default" / "openharmony" / "toolchains" / "lib" / "hap-sign-tool.jar"
        hsp_artifact = project / "library" / "build" / "default" / "outputs" / "default" / "library-default-signed.hsp"
        unsigned_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned-hsp.hap"
        signed_hap = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-signed-hsp.hap"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_file(app_packing_tool)
        _write_file(hap_sign_tool)
        _write_shared_module_build_profile(project)
        _write_file(project / "entry" / "src" / "main" / "module.json5", "{}")
        _write_hnp_packaging_inputs(project)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        hsp_build_count = 0
        clean_count = 0

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            nonlocal hsp_build_count, clean_count
            command = " ".join(str(part) for part in cmd)
            if "app_packing_tool.jar" in command:
                _write_hap(unsigned_hap, {"module.json": "{}", "shared_libs/library-default-signed.hsp": "hsp"})
                return CompletedProcess(cmd, 0, stdout=f"packed {unsigned_hap}", stderr="")
            if "hap-sign-tool.jar" in command:
                _write_hap(signed_hap, {"module.json": "{}", "shared_libs/library-default-signed.hsp": "hsp"})
                return CompletedProcess(cmd, 0, stdout=f"signed {signed_hap}", stderr="")
            if "clean" in cmd and "module=library" in cmd:
                clean_count += 1
                return CompletedProcess(cmd, 0, stdout="clean library", stderr="")
            if "assembleHsp" in cmd:
                hsp_build_count += 1
                if hsp_build_count == 2:
                    _write_hsp(hsp_artifact, "library")
                return CompletedProcess(cmd, 0, stdout="hsp ok", stderr="")
            return CompletedProcess(cmd, 0, stdout="hvigor hap ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap", include_hsp=True, hsp_module_name="library")

        assert result["success"] is True
        assert result["output_path"] == str(signed_hap)
        assert hsp_build_count == 2
        assert clean_count == 1

    def test_build_hap_with_hsp_uses_hsp_signing_error_prefix(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        java = deveco / "jbr" / "bin" / "java.exe"
        hsp_artifact = project / "library" / "build" / "default" / "outputs" / "default" / "library-default-signed.hsp"
        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)
        _write_unsigned_shared_module_build_profile(project)
        _write_hnp_packaging_inputs(project)
        _write_file(hsp_artifact, "hsp")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env, close_fds, **kwargs):
            if "assembleHsp" in cmd:
                return CompletedProcess(cmd, 0, stdout=f"artifact: {hsp_artifact}", stderr="")
            return CompletedProcess(cmd, 0, stdout="hvigor hap ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(target="hap", include_hsp=True, hsp_module_name="library")

        assert result["success"] is False
        assert result["error_code"] == "HSP_SIGNING_CONFIG_MISSING"

    def test_build_uses_sign_fallback_for_unsigned_hap(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)
        unsigned_artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        signed_artifact = project / "hapsigner" / "signApp.hap"
        sign_script = project / "hapsigner" / "2-debug-sign.bat"
        _write_file(unsigned_artifact, "unsigned")
        _write_file(sign_script, "@echo off")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        call_index = {"count": 0}

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env=None, close_fds=True, **kwargs):
            if cmd[0] == "cmd.exe":
                _write_file(signed_artifact, "signed")
                return CompletedProcess(cmd, 0, stdout="signed", stderr="")
            call_index["count"] += 1
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert call_index["count"] == 1
        assert result["success"] is True
        assert result["output_path"] == str(signed_artifact)
        assert result["artifact_source"] == "sign_fallback"
        assert result["sign_status"] == "signed"

    def test_build_detects_non_default_sign_fallback_output(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)
        unsigned_artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        signed_artifact = project / "hapsigner" / "custom-output.hap"
        sign_script = project / "hapsigner" / "2-debug-sign.bat"
        _write_file(unsigned_artifact, "unsigned")
        _write_file(sign_script, "@echo off")

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env=None, close_fds=True, **kwargs):
            if cmd[0] == "cmd.exe":
                _write_file(signed_artifact, "signed")
                return CompletedProcess(cmd, 0, stdout="signed", stderr="")
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is True
        assert result["output_path"] == str(signed_artifact)
        assert result["artifact_source"] == "sign_fallback"
        assert result["sign_status"] == "signed"

    def test_build_runs_clean_first_when_is_clean_enabled(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)

        unsigned_artifact = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        _write_file(unsigned_artifact, "unsigned")
        os.utime(unsigned_artifact, (600, 600))

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.time.time",
            lambda: 500.0
        )

        calls = []

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env=None, close_fds=True, **kwargs):
            calls.append(cmd)
            return CompletedProcess(cmd, 0, stdout=f"artifact: {unsigned_artifact}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build(is_clean=True)

        assert result["success"] is True
        assert len(calls) == 2
        assert "clean" in calls[0]

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

        _write_file(project / "build-profile.json5", "{ signingConfigs: [{ profile: \"./sign/default.p7b\" }] }")
        _write_file(project / "sign" / "default.p7b", "ok")
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

    def test_build_rejects_stale_logged_artifact(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)

        stale_unsigned = project / "entry" / "build" / "default" / "outputs" / "default" / "entry-default-unsigned.hap"
        _write_file(stale_unsigned, "unsigned")
        os.utime(stale_unsigned, (100, 100))

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.time.time",
            lambda: 500.0
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env=None, close_fds=True, **kwargs):
            return CompletedProcess(cmd, 0, stdout=f"artifact: {stale_unsigned}", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is False
        assert result["error_code"] == "STALE_BUILD_ARTIFACT"

    def test_build_rejects_missing_output_even_when_hvigor_succeeds(self, tmp_path, monkeypatch):
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
        _write_minimal_build_profile(project)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        def fake_run(cmd, cwd, capture_output, text, stdin, timeout, env=None, close_fds=True, **kwargs):
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.subprocess.run", fake_run)

        wrapper = HvigorWrapper(str(project))
        result = wrapper.build()

        assert result["success"] is False
        assert result["error_code"] == "BUILD_OUTPUT_NOT_FOUND"
        assert "could not locate a fresh artifact" in result["stderr"]
        assert "is_clean=true" in result["stderr"]
        assert "hapsigner directory" in result["stderr"]

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

    def test_java_home_prefers_standard_java_home_env(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DevEco Studio"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        embedded_java = deveco / "jbr" / "bin" / "java.exe"
        explicit_java_home = tmp_path / "ExplicitJbr"
        explicit_java = explicit_java_home / "bin" / "java.exe"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(embedded_java)
        _write_file(explicit_java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setenv("JAVA_HOME", str(explicit_java_home))
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.java_home == explicit_java_home

    def test_java_home_can_be_discovered_from_program_files_huawei_layout(self, tmp_path, monkeypatch):
        project = tmp_path / "MyApplication"
        project.mkdir()

        deveco = tmp_path / "DetectedDevEco"
        node = deveco / "tools" / "node" / "node.exe"
        hvigor = deveco / "tools" / "hvigor" / "bin" / "hvigorw.js"
        sdk_pkg = deveco / "sdk" / "default" / "sdk-pkg.json"
        program_files = tmp_path / "Program Files"
        huawei_java_home = program_files / "Huawei" / "DevEco Studio" / "jbr"
        java = huawei_java_home / "bin" / "java.exe"

        _write_file(node)
        _write_file(hvigor)
        _write_file(sdk_pkg, "{}")
        _write_file(java)

        monkeypatch.setattr(Config, "NODE_PATH", None)
        monkeypatch.setattr(Config, "HVIGOR_PATH", None)
        monkeypatch.setattr(Config, "HARMONYOS_SDK_PATH", None)
        monkeypatch.setattr(Config, "DEVECO_STUDIO_PATH", str(deveco))
        _isolate_discovery_env(monkeypatch, clear_path_java=True)
        monkeypatch.setenv("ProgramFiles", str(program_files))
        monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "Program Files (x86)"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
        monkeypatch.setattr(
            "harmonyos_dev_mcp.utils.wrappers.hvigor_wrapper.platform.system",
            lambda: "Windows"
        )

        wrapper = HvigorWrapper(str(project))

        assert wrapper.java_home == huawei_java_home
