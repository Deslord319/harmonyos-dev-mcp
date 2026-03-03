from pathlib import Path

from harmonyos_mcp.config import Config


class TestConfig:
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
