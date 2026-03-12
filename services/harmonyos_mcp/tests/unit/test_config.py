from pathlib import Path

from harmonyos_mcp.config import Config


class TestConfigHelpers:
    def test_get_deveco_search_paths_includes_macos_defaults(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Darwin")
        monkeypatch.setattr(Path, "home", lambda: Path("/Users/tester"))
        monkeypatch.delenv("DevEco Studio", raising=False)

        paths = Config._get_deveco_search_paths()

        assert Path("/Applications/DevEco-Studio.app") in paths
        assert Path("/Users/tester/Applications/DevEco-Studio.app") in paths

    def test_get_deveco_search_paths_prefers_env_hint(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Darwin")
        monkeypatch.setattr(Path, "home", lambda: Path("/Users/tester"))
        monkeypatch.setenv("DevEco Studio", "/custom/DevEco-Studio.app:/ignored/bin")

        paths = Config._get_deveco_search_paths()

        assert paths[0] == Path("/custom/DevEco-Studio.app")

    def test_get_deveco_search_paths_includes_windows_registry_candidates(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("LOCALAPPDATA", r"D:\Users\tester\AppData\Local")
        monkeypatch.setenv("ProgramFiles", r"D:\Apps")
        monkeypatch.setenv("ProgramFiles(x86)", r"E:\AppsX86")
        monkeypatch.delenv("DevEco Studio", raising=False)
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\tester"))
        monkeypatch.setattr(
            Config,
            "_get_windows_registry_deveco_paths",
            classmethod(lambda cls: [Path(r"F:\Huawei\DevEco Studio")]),
        )

        paths = Config._get_deveco_search_paths()

        assert paths[0] == Path(r"F:\Huawei\DevEco Studio")
        assert Path(r"D:\Users\tester\AppData\Local\Programs\Huawei\DevEco Studio") in paths
        assert Path(r"D:\Apps\Huawei\DevEco Studio") in paths
        assert Path(r"E:\AppsX86\Huawei\DevEco Studio") in paths

    def test_extract_command_path_handles_quoted_and_plain_commands(self):
        quoted = Config._extract_command_path(r'"C:\Program Files\Huawei\DevEco Studio\bin\devecostudio64.exe" "%1"')
        plain = Config._extract_command_path(r"C:\tools\devecostudio64.exe %1")

        assert quoted == Path(r"C:\Program Files\Huawei\DevEco Studio\bin\devecostudio64.exe")
        assert plain == Path(r"C:\tools\devecostudio64.exe")

    def test_unique_existing_paths_removes_duplicates_preserving_order(self):
        result = Config._unique_existing_paths([
            Path("/opt/DevEco-Studio"),
            Path("/opt/DevEco-Studio"),
            Path("/opt/DevEco Studio"),
        ])

        assert result == [Path("/opt/DevEco-Studio"), Path("/opt/DevEco Studio")]

    def test_is_valid_deveco_path_accepts_hvigor_layout(self, tmp_path, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Linux")
        deveco = tmp_path / "DevEco-Studio"
        (deveco / "tools" / "hvigor" / "bin").mkdir(parents=True)
        (deveco / "tools" / "hvigor" / "bin" / "hvigorw.js").write_text("// hvigor", encoding="utf-8")

        assert Config._is_valid_deveco_path(deveco) is True

    def test_is_valid_deveco_path_rejects_empty_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")

        assert Config._is_valid_deveco_path(tmp_path) is False


class TestDevEcoDetection:
    def test_detect_deveco_uses_valid_env_override(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("DEVECO_STUDIO_PATH", r"D:\Custom\DevEco")
        monkeypatch.delenv("DevEco Studio", raising=False)
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: str(path) == r"D:\Custom\DevEco"),
        )

        detected = Config._detect_deveco_studio_path()

        assert detected == r"D:\Custom\DevEco"

    def test_detect_deveco_falls_back_to_search_paths_when_env_invalid(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("DEVECO_STUDIO_PATH", r"D:\Broken\DevEco")
        monkeypatch.delenv("DevEco Studio", raising=False)
        monkeypatch.setattr(
            Config,
            "_get_deveco_search_paths",
            classmethod(lambda cls: [Path(r"E:\Huawei\DevEco Studio")]),
        )
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: str(path) == r"E:\Huawei\DevEco Studio"),
        )

        detected = Config._detect_deveco_studio_path()

        assert detected == r"E:\Huawei\DevEco Studio"

    def test_detect_deveco_returns_existing_env_path_as_last_resort(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("DEVECO_STUDIO_PATH", r"D:\Existing\UnknownLayout")
        monkeypatch.delenv("DevEco Studio", raising=False)
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: False),
        )
        monkeypatch.setattr(
            Config,
            "_get_deveco_search_paths",
            classmethod(lambda cls: []),
        )
        monkeypatch.setattr(Path, "exists", lambda self: str(self) == r"D:\Existing\UnknownLayout")

        detected = Config._detect_deveco_studio_path()

        assert detected == r"D:\Existing\UnknownLayout"

    def test_detect_deveco_prefers_valid_registry_path(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.delenv("DEVECO_STUDIO_PATH", raising=False)
        monkeypatch.delenv("DevEco Studio", raising=False)
        monkeypatch.setattr(
            Config,
            "_get_deveco_search_paths",
            classmethod(lambda cls: [Path(r"C:\Program Files\Huawei\DevEco Studio")]),
        )
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: str(path) == r"C:\Program Files\Huawei\DevEco Studio"),
        )

        detected = Config._detect_deveco_studio_path()

        assert detected == r"C:\Program Files\Huawei\DevEco Studio"


class TestSdkDetection:
    def test_derive_sdk_candidates_includes_env_deveco_and_hdc_sources(self, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\tester"))
        monkeypatch.setenv("DEVECO_SDK_HOME", r"D:\sdk")
        monkeypatch.delenv("HARMONYOS_SDK_PATH", raising=False)
        monkeypatch.setattr(
            "harmonyos_mcp.config.shutil.which",
            lambda name: r"F:\DevEco\sdk\default\openharmony\toolchains\hdc.exe" if name == "hdc" else None,
        )
        monkeypatch.setattr(
            Config,
            "_normalize_sdk_root",
            staticmethod(
                lambda path: (
                    Path(r"F:\DevEco\sdk") if str(path) == r"F:\DevEco\sdk\default\openharmony\toolchains"
                    else path if str(path) in {r"D:\sdk", r"E:\DevEco\sdk", r"C:\Users\tester\HarmonyOS\sdk"}
                    else None
                )
            ),
        )

        candidates = Config._derive_sdk_candidates(r"E:\DevEco")

        assert Path(r"D:\sdk") in candidates
        assert Path(r"E:\DevEco\sdk") in candidates
        assert Path(r"C:\Users\tester\HarmonyOS\sdk") in candidates
        assert Path(r"F:\DevEco\sdk") in candidates

    def test_detect_sdk_root_prefers_first_normalized_candidate(self, monkeypatch):
        monkeypatch.setattr(
            Config,
            "_derive_sdk_candidates",
            classmethod(lambda cls, deveco_path: [Path(r"D:\sdk"), Path(r"E:\sdk")]),
        )
        monkeypatch.setattr(
            Config,
            "_normalize_sdk_root",
            staticmethod(lambda path: path if str(path) == r"E:\sdk" else None),
        )

        detected = Config._detect_sdk_root(r"C:\DevEco")

        assert detected == r"E:\sdk"

    def test_detect_sdk_root_can_derive_from_hdc_on_path(self, monkeypatch):
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setattr(
            "harmonyos_mcp.config.shutil.which",
            lambda name: r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe" if name == "hdc" else None,
        )
        monkeypatch.setattr(
            Config,
            "_normalize_sdk_root",
            staticmethod(
                lambda path: Path(r"C:\Program Files\Huawei\DevEco Studio\sdk")
                if str(path) in {
                    r"C:\Program Files\Huawei\DevEco Studio\sdk",
                    r"C:\Program Files\Huawei\DevEco Studio\sdk\default",
                    r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony",
                    r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains",
                }
                else None
            ),
        )

        detected = Config._detect_sdk_root(None)

        assert detected == r"C:\Program Files\Huawei\DevEco Studio\sdk"


class TestConfigInit:
    def test_init_uses_auto_detected_paths_and_derives_toolchain(self, monkeypatch):
        original_values = {
            "DEVECO_STUDIO_PATH": Config.DEVECO_STUDIO_PATH,
            "HARMONYOS_SDK_PATH": Config.HARMONYOS_SDK_PATH,
            "HDC_PATH": Config.HDC_PATH,
            "HVIGOR_PATH": Config.HVIGOR_PATH,
            "HILOGTOOL_PATH": Config.HILOGTOOL_PATH,
            "NODE_PATH": Config.NODE_PATH,
            "BUILD_TIMEOUT": Config.BUILD_TIMEOUT,
            "INSTALL_TIMEOUT": Config.INSTALL_TIMEOUT,
        }
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("BUILD_TIMEOUT", "321")
        monkeypatch.setenv("INSTALL_TIMEOUT", "123")
        monkeypatch.delenv("DEVECO_STUDIO_PATH", raising=False)
        monkeypatch.delenv("HARMONYOS_SDK_PATH", raising=False)
        monkeypatch.delenv("HDC_PATH", raising=False)
        monkeypatch.delenv("HILOGTOOL_PATH", raising=False)
        monkeypatch.setattr("harmonyos_mcp.config.ConfigBase.init", classmethod(lambda cls: None))
        monkeypatch.setattr(
            Config,
            "_detect_deveco_studio_path",
            classmethod(lambda cls: r"C:\DevEco"),
        )
        monkeypatch.setattr(
            Config,
            "_detect_sdk_root",
            classmethod(lambda cls, deveco_path: r"C:\DevEco\sdk"),
        )
        monkeypatch.setattr(
            "harmonyos_mcp.config.Path.exists",
            lambda self: str(self) in {
                r"C:\DevEco\sdk\openharmony\toolchains\hdc.exe",
                r"C:\DevEco\tools\node\node.exe",
                r"C:\DevEco\tools\hvigor\bin\hvigorw.js",
                r"C:\DevEco\sdk\toolchains\hilogtool.exe",
            },
        )
        monkeypatch.setattr("harmonyos_mcp.config.shutil.which", lambda name: None)

        try:
            Config.init()

            assert Config.DEVECO_STUDIO_PATH == r"C:\DevEco"
            assert Config.HARMONYOS_SDK_PATH == r"C:\DevEco\sdk"
            assert Config.HDC_PATH == r"C:\DevEco\sdk\openharmony\toolchains\hdc.exe"
            assert Config.NODE_PATH == r"C:\DevEco\tools\node\node.exe"
            assert Config.HVIGOR_PATH == r"C:\DevEco\tools\hvigor\bin\hvigorw.js"
            assert Config.HILOGTOOL_PATH == r"C:\DevEco\sdk\toolchains\hilogtool.exe"
            assert Config.BUILD_TIMEOUT == 321
            assert Config.INSTALL_TIMEOUT == 123
        finally:
            for key, value in original_values.items():
                setattr(Config, key, value)

    def test_init_preserves_explicit_valid_deveco_env(self, monkeypatch):
        original_values = {
            "DEVECO_STUDIO_PATH": Config.DEVECO_STUDIO_PATH,
            "HARMONYOS_SDK_PATH": Config.HARMONYOS_SDK_PATH,
            "HDC_PATH": Config.HDC_PATH,
            "HVIGOR_PATH": Config.HVIGOR_PATH,
            "HILOGTOOL_PATH": Config.HILOGTOOL_PATH,
            "NODE_PATH": Config.NODE_PATH,
        }
        monkeypatch.setattr("harmonyos_mcp.config.platform.system", lambda: "Windows")
        monkeypatch.setenv("DEVECO_STUDIO_PATH", r"D:\Explicit\DevEco")
        monkeypatch.setenv("HARMONYOS_SDK_PATH", r"D:\Explicit\DevEco\sdk")
        monkeypatch.setenv("HDC_PATH", r"D:\Explicit\DevEco\sdk\toolchains\hdc.exe")
        monkeypatch.setattr("harmonyos_mcp.config.ConfigBase.init", classmethod(lambda cls: None))
        monkeypatch.setattr(
            Config,
            "_is_valid_deveco_path",
            classmethod(lambda cls, path: str(path) == r"D:\Explicit\DevEco"),
        )
        monkeypatch.setattr("harmonyos_mcp.config.shutil.which", lambda name: None)
        monkeypatch.setattr("harmonyos_mcp.config.Path.exists", lambda self: False)

        try:
            Config.init()

            assert Config.DEVECO_STUDIO_PATH == r"D:\Explicit\DevEco"
            assert Config.HARMONYOS_SDK_PATH == r"D:\Explicit\DevEco\sdk"
            assert Config.HDC_PATH == r"D:\Explicit\DevEco\sdk\toolchains\hdc.exe"
        finally:
            for key, value in original_values.items():
                setattr(Config, key, value)
