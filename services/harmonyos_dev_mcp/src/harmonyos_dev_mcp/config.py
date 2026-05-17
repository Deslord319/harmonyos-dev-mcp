"""HarmonyOS MCP configuration."""

import os
import platform
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from common.config.base import ConfigBase


class Config(ConfigBase):
    """HarmonyOS MCP configuration."""

    DEVECO_STUDIO_PATH: Optional[str] = None
    HARMONYOS_SDK_PATH: Optional[str] = None
    HDC_PATH: Optional[str] = None
    HVIGOR_PATH: Optional[str] = None
    HILOGTOOL_PATH: Optional[str] = None
    NODE_PATH: Optional[str] = None
    DEFAULT_DEVICE_ID: Optional[str] = None

    UI_OPERATION_TIMEOUT: int = 5
    UI_TREE_TIMEOUT: int = 10
    BUILD_TIMEOUT: int = 600
    INSTALL_TIMEOUT: int = 120

    @staticmethod
    def _normalize_sdk_root(path: Path) -> Optional[Path]:
        """Normalize a candidate SDK path to the root directory expected by hvigor."""
        if not path.exists():
            return None

        if any(child.is_dir() and (child / "sdk-pkg.json").exists() for child in path.iterdir()):
            return path

        if (path / "sdk-pkg.json").exists():
            return path.parent

        return None

    @classmethod
    def _is_valid_deveco_path(cls, path: Path) -> bool:
        if not path.exists() or not path.is_dir():
            return False

        system = platform.system()
        studio_names = ["devecostudio64.exe", "devecostudio.exe"] if system == "Windows" else ["devecostudio"]
        checks = [
            path / "tools" / "hvigor" / "bin" / "hvigorw.js",
            path / "sdk",
            path / "jbr",
            path / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js",
            path / "Contents" / "sdk",
            path / "Contents" / "jbr",
        ]
        checks.extend(path / "bin" / name for name in studio_names)
        checks.extend(path / "Contents" / "bin" / name for name in studio_names)
        return any(candidate.exists() for candidate in checks)

    @staticmethod
    def _extract_command_path(raw_command: str) -> Optional[Path]:
        value = raw_command.strip()
        if not value:
            return None
        if value.startswith('"'):
            end = value.find('"', 1)
            if end > 1:
                return Path(value[1:end])
        return Path(value.split()[0])

    @classmethod
    def _get_windows_registry_deveco_paths(cls) -> List[Path]:
        if platform.system() != "Windows":
            return []

        try:
            import winreg
        except ImportError:
            return []

        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Applications\devecostudio64.exe\shell\open\command"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\devecostudio\shell\open\command"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Classes\Applications\devecostudio64.exe\shell\open\command"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Classes\devecostudio\shell\open\command"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\devecostudio64.exe"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\devecostudio64.exe"),
        ]

        candidates: List[Path] = []
        for hive, key_path in registry_keys:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    for value_name in ("", "Path"):
                        try:
                            raw_value, _ = winreg.QueryValueEx(key, value_name)
                        except OSError:
                            continue
                        extracted = cls._extract_command_path(str(raw_value))
                        if not extracted:
                            continue
                        if extracted.name.lower() == "bin":
                            extracted = extracted.parent
                        elif extracted.suffix.lower() == ".exe":
                            if extracted.parent.name.lower() == "bin":
                                extracted = extracted.parent.parent
                            else:
                                extracted = extracted.parent
                        candidates.append(extracted)
            except OSError:
                continue
        return candidates

    @staticmethod
    def _unique_existing_paths(candidates: Iterable[Path]) -> List[Path]:
        seen = set()
        result: List[Path] = []
        for candidate in candidates:
            normalized = candidate.expanduser()
            key = str(normalized)
            if key in seen:
                continue
            seen.add(key)
            result.append(normalized)
        return result

    @classmethod
    def _get_deveco_search_paths(cls) -> List[Path]:
        """Return likely DevEco Studio install locations for the current platform."""
        system = platform.system()
        home = Path.home()
        candidates: List[Path] = []

        env_hint = os.getenv("DevEco Studio")
        if env_hint:
            raw_hint = env_hint.split(";" if system == "Windows" else ":")[0].strip()
            if raw_hint:
                hint_path = Path(raw_hint).expanduser()
                if hint_path.name.lower() == "bin":
                    hint_path = hint_path.parent
                candidates.append(hint_path)

        if system == "Darwin":
            candidates.extend(
                [
                    Path("/Applications/DevEco-Studio.app"),
                    Path("/Applications/DevEco Studio.app"),
                    home / "Applications" / "DevEco-Studio.app",
                    home / "Applications" / "DevEco Studio.app",
                ]
            )
        elif system == "Windows":
            local_app_data = Path(os.getenv("LOCALAPPDATA", home / "AppData" / "Local"))
            program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
            program_files_x86 = Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            candidates.extend(cls._get_windows_registry_deveco_paths())
            candidates.extend(
                [
                    local_app_data / "Programs" / "DevEco Studio",
                    local_app_data / "Programs" / "Huawei" / "DevEco Studio",
                    program_files / "DevEco Studio",
                    program_files / "Huawei" / "DevEco Studio",
                    program_files_x86 / "DevEco Studio",
                    program_files_x86 / "Huawei" / "DevEco Studio",
                ]
            )
        else:
            candidates.extend(
                [
                    Path("/opt/DevEco-Studio"),
                    Path("/opt/DevEco Studio"),
                    home / "DevEco-Studio",
                    home / "DevEco Studio",
                    home / ".local" / "share" / "DevEco-Studio",
                ]
            )

        return cls._unique_existing_paths(candidates)

    @classmethod
    def _detect_deveco_studio_path(cls) -> Optional[str]:
        env_candidates: List[Path] = []
        for env_name in ("DEVECO_STUDIO_PATH", "DevEco Studio"):
            env_value = os.getenv(env_name)
            if not env_value:
                continue
            raw_hint = env_value.split(";" if platform.system() == "Windows" else ":")[0].strip()
            if not raw_hint:
                continue
            candidate = Path(raw_hint).expanduser()
            if candidate.name.lower() == "bin":
                candidate = candidate.parent
            if cls._is_valid_deveco_path(candidate):
                return str(candidate)
            env_candidates.append(candidate)

        for candidate in cls._get_deveco_search_paths():
            if cls._is_valid_deveco_path(candidate):
                return str(candidate)

        for candidate in env_candidates:
            if candidate.exists():
                return str(candidate)

        return None

    @classmethod
    def _derive_sdk_candidates(cls, deveco_path: Optional[str]) -> List[Path]:
        user_home = Path.home()
        candidates: List[Path] = []

        for env_name in ("DEVECO_SDK_HOME", "HARMONYOS_SDK_PATH"):
            env_value = os.getenv(env_name)
            if env_value:
                candidates.append(Path(env_value).expanduser())

        if deveco_path:
            deveco = Path(deveco_path)
            candidates.extend(
                [
                    deveco / "sdk",
                    deveco / "Contents" / "sdk",
                    deveco.parent / "sdk",
                ]
            )

        candidates.extend(
            [
                user_home / "HarmonyOS" / "sdk",
                user_home / "harmonyos" / "sdk",
                user_home / "AppData" / "Local" / "HarmonyOS" / "Sdk",
                user_home / "AppData" / "Local" / "Huawei" / "Sdk",
            ]
        )

        hdc_in_path = shutil.which("hdc")
        if hdc_in_path:
            hdc_path = Path(hdc_in_path)
            for parent in hdc_path.parents:
                normalized = cls._normalize_sdk_root(parent)
                if normalized:
                    candidates.append(normalized)
                    break

        return cls._unique_existing_paths(candidates)

    @classmethod
    def _detect_sdk_root(cls, deveco_path: Optional[str]) -> Optional[str]:
        for candidate in cls._derive_sdk_candidates(deveco_path):
            normalized = cls._normalize_sdk_root(candidate)
            if normalized:
                return str(normalized)
        return None

    @classmethod
    def init(cls):
        super().init()
        system = platform.system()

        cls.DEVECO_STUDIO_PATH = os.getenv("DEVECO_STUDIO_PATH")
        cls.HARMONYOS_SDK_PATH = os.getenv("HARMONYOS_SDK_PATH")
        cls.HDC_PATH = os.getenv("HDC_PATH")
        cls.HILOGTOOL_PATH = os.getenv("HILOGTOOL_PATH")
        cls.DEFAULT_DEVICE_ID = os.getenv("HARMONYOS_DEVICE_ID")

        cls.UI_OPERATION_TIMEOUT = int(os.getenv("UI_OPERATION_TIMEOUT", str(cls.UI_OPERATION_TIMEOUT)))
        cls.UI_TREE_TIMEOUT = int(os.getenv("UI_TREE_TIMEOUT", str(cls.UI_TREE_TIMEOUT)))
        cls.BUILD_TIMEOUT = int(os.getenv("BUILD_TIMEOUT", str(cls.BUILD_TIMEOUT)))
        cls.INSTALL_TIMEOUT = int(os.getenv("INSTALL_TIMEOUT", str(cls.INSTALL_TIMEOUT)))

        if not cls.DEVECO_STUDIO_PATH or not cls._is_valid_deveco_path(Path(cls.DEVECO_STUDIO_PATH)):
            cls.DEVECO_STUDIO_PATH = cls._detect_deveco_studio_path()

        if not cls.HARMONYOS_SDK_PATH:
            cls.HARMONYOS_SDK_PATH = cls._detect_sdk_root(cls.DEVECO_STUDIO_PATH)

        if not cls.HDC_PATH and cls.HARMONYOS_SDK_PATH:
            hdc_name = "hdc.exe" if system == "Windows" else "hdc"
            sdk = Path(cls.HARMONYOS_SDK_PATH)
            for subdir in [
                "toolchains",
                "openharmony/toolchains",
                "default/toolchains",
                "default/openharmony/toolchains",
            ]:
                hdc_path = sdk / subdir / hdc_name
                if hdc_path.exists():
                    cls.HDC_PATH = str(hdc_path)
                    break

        if not cls.HDC_PATH:
            hdc_in_path = shutil.which("hdc")
            if hdc_in_path:
                cls.HDC_PATH = hdc_in_path

        if cls.DEVECO_STUDIO_PATH:
            deveco = Path(cls.DEVECO_STUDIO_PATH)
            node_name = "node.exe" if system == "Windows" else "node"
            node_candidates = [
                deveco / "tools" / "node" / node_name,
                deveco / "tools" / "node" / "bin" / node_name,
                deveco / "Contents" / "tools" / "node" / node_name,
                deveco / "Contents" / "tools" / "node" / "bin" / node_name,
            ]
            for node_path in node_candidates:
                if node_path.exists():
                    cls.NODE_PATH = str(node_path)
                    break

            hvigor_candidates = [
                deveco / "tools" / "hvigor" / "bin" / "hvigorw.js",
                deveco / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js",
            ]
            for hvigor_path in hvigor_candidates:
                if hvigor_path.exists():
                    cls.HVIGOR_PATH = str(hvigor_path)
                    break

        if not cls.HILOGTOOL_PATH and cls.HARMONYOS_SDK_PATH:
            hilogtool_name = "hilogtool.exe" if system == "Windows" else "hilogtool"
            sdk = Path(cls.HARMONYOS_SDK_PATH)
            for subdir in [
                "hms/toolchains",
                "toolchains",
                "default/hms/toolchains",
                "default/toolchains",
                "default/openharmony/toolchains",
            ]:
                candidate = sdk / subdir / hilogtool_name
                if candidate.exists():
                    cls.HILOGTOOL_PATH = str(candidate)
                    break

        if cls.HDC_PATH:
            logger.info(f"hdc path: {cls.HDC_PATH}")
        if cls.NODE_PATH:
            logger.info(f"Node.js path: {cls.NODE_PATH}")
        if cls.HVIGOR_PATH:
            logger.info(f"hvigor path: {cls.HVIGOR_PATH}")
        if cls.HILOGTOOL_PATH:
            logger.info(f"hilogtool path: {cls.HILOGTOOL_PATH}")


class LogSecurityConfig:
    """Log security configuration."""

    _ALLOWED_SAVE_PATHS_RELATIVE: List[str] = ["./hm_logs", "./hilog_files"]
    _ALLOWED_SAVE_PATHS_ABS: List[str] = []

    MAX_LOG_LINES: int = int(os.getenv("MAX_LOG_LINES", "50000"))
    MAX_OUTPUT_SIZE_MB: int = int(os.getenv("MAX_OUTPUT_SIZE_MB", "100"))
    DEFAULT_TIMEOUT: int = int(os.getenv("LOG_DEFAULT_TIMEOUT", "30"))
    MAX_TIMEOUT: int = int(os.getenv("LOG_MAX_TIMEOUT", "300"))
    FETCH_MULTIPLIER: int = int(os.getenv("LOG_FETCH_MULTIPLIER", "5"))
    ENABLE_NOISE_FILTER: bool = os.getenv("LOG_ENABLE_NOISE_FILTER", "true").lower() == "true"
    AUTO_CLEANUP_DAYS: int = int(os.getenv("LOG_AUTO_CLEANUP_DAYS", "7"))
    MAX_CACHE_SIZE_MB: int = int(os.getenv("LOG_MAX_CACHE_SIZE_MB", "500"))
    TIME_PARSE_STRATEGY: str = os.getenv("LOG_TIME_PARSE_STRATEGY", "auto")

    @classmethod
    def get_allowed_save_paths(cls) -> List[str]:
        if not cls._ALLOWED_SAVE_PATHS_ABS:
            cls._ALLOWED_SAVE_PATHS_ABS = [os.path.abspath(path) for path in cls._ALLOWED_SAVE_PATHS_RELATIVE]
        return cls._ALLOWED_SAVE_PATHS_ABS

    @classmethod
    def validate_save_path(cls, path: str) -> tuple:
        try:
            real_path = os.path.realpath(os.path.abspath(path))
            for allowed in cls.get_allowed_save_paths():
                if real_path.startswith(allowed + os.sep) or real_path == allowed:
                    target = os.path.dirname(real_path) if os.path.splitext(real_path)[1] else real_path
                    os.makedirs(target, exist_ok=True)
                    return True, real_path
            return False, f"path is not in the allowlist: {cls.get_allowed_save_paths()}"
        except Exception as exc:
            return False, f"path validation failed: {exc}"

    @classmethod
    def validate_timeout(cls, timeout: int) -> int:
        if timeout is None:
            return cls.DEFAULT_TIMEOUT
        return min(max(timeout, 1), cls.MAX_TIMEOUT)
