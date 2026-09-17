"""DevEco and hvigor toolchain discovery."""

import os
import platform
import shutil
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from loguru import logger

from harmonyos_dev_mcp.config import Config


WhichFn = Callable[[str], Optional[str]]
WritableDirFn = Callable[[Path], bool]


def is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def has_java_executable(candidate: Path, java_names: list[str]) -> bool:
    return any((candidate / "bin" / java_exe).exists() for java_exe in java_names)


class ToolchainDiscovery:
    """Find DevEco, hvigor, SDK, Java, and writable hvigor state paths."""

    def __init__(
        self,
        project_path: Path,
        *,
        system_name: Optional[str] = None,
        which: Optional[WhichFn] = None,
        writable_dir: Optional[WritableDirFn] = None,
        temp_dir: Optional[Path] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.system_name = system_name or platform.system()
        self.which = which or shutil.which
        self.writable_dir = writable_dir or is_writable_dir
        self.temp_dir = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())

    def resolve_hvigor_user_home(self) -> Path:
        """
        Pick an isolated writable HVIGOR_USER_HOME for this wrapper instance.

        Sharing one `.hvigor` directory across concurrent builds can trigger
        Windows `EBUSY` failures while hvigor updates `dependencyMap`.
        """
        suffix = uuid.uuid4().hex[:8]
        preferred = self.project_path / ".hvigor" / f"mcp-user-home-{suffix}"
        if self.writable_dir(preferred):
            return preferred

        fallback = self.temp_dir / "harmonyos_dev_mcp" / "hvigor_home" / suffix
        if self.writable_dir(fallback):
            logger.warning(
                f"project-local HVIGOR_USER_HOME is not writable, falling back to {fallback}"
            )
            return fallback

        raise PermissionError(
            "HVIGOR_USER_HOME is not writable in either the project or temp directory: "
            f"{preferred}, {fallback}"
        )

    def find_deveco_studio(self, custom_path: Optional[str] = None) -> Optional[Path]:
        if custom_path:
            path = Path(custom_path)
            if Config._is_valid_deveco_path(path):
                return path

        if Config.DEVECO_STUDIO_PATH:
            path = Path(Config.DEVECO_STUDIO_PATH)
            if Config._is_valid_deveco_path(path):
                return path

        detected = Config._detect_deveco_studio_path()
        if detected:
            path = Path(detected)
            logger.info(f"auto-detected DevEco Studio: {path}")
            return path

        return None

    def find_node_executable(self, deveco_path: Path) -> Path:
        if Config.NODE_PATH and Path(Config.NODE_PATH).exists():
            return Path(Config.NODE_PATH)

        node_names = ["node", "node.exe"]
        if self.system_name == "Windows":
            node_names = ["node.exe", "node"]

        candidates = [
            deveco_path / "tools" / "node",
            deveco_path / "tools" / "node" / "bin",
            deveco_path / "Contents" / "tools" / "node",
            deveco_path / "Contents" / "tools" / "node" / "bin",
        ]
        for base in candidates:
            for node_name in node_names:
                candidate = base / node_name
                if candidate.exists():
                    return candidate
        return candidates[0] / node_names[0]

    @staticmethod
    def find_hvigor_wrapper(deveco_path: Path) -> Path:
        if Config.HVIGOR_PATH and Path(Config.HVIGOR_PATH).exists():
            return Path(Config.HVIGOR_PATH)

        candidates = [
            deveco_path / "tools" / "hvigor" / "bin" / "hvigorw.js",
            deveco_path / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    @staticmethod
    def find_sdk_root(deveco_path: Path) -> Path:
        # HarmonyOS: if deveco_path itself contains sdk-pkg.json,
        # the SDK home is its parent directory
        if (deveco_path / "sdk-pkg.json").exists():
            return deveco_path.parent
        # If a child of deveco_path contains sdk-pkg.json,
        # deveco_path itself is the SDK home
        try:
            for child in deveco_path.iterdir():
                if child.is_dir() and (child / "sdk-pkg.json").exists():
                    return deveco_path
        except OSError:
            pass
        candidates = [
            deveco_path / "sdk",
            deveco_path / "Contents" / "sdk",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def find_java_home(self, deveco_path: Path) -> Optional[Path]:
        java_names = ["java", "java.exe"]
        if self.system_name == "Windows":
            java_names = ["java.exe", "java"]

        for env_name in ("JAVA_HOME", "JDK_HOME"):
            env_java_home = os.getenv(env_name)
            if not env_java_home:
                continue
            candidate = Path(env_java_home).expanduser()
            if has_java_executable(candidate, java_names):
                return candidate

        java_in_path = self.which("java")
        if java_in_path:
            java_path = Path(java_in_path).resolve()
            java_home = java_path.parent.parent
            if has_java_executable(java_home, java_names):
                return java_home

        home = Path.home()
        local_app_data = Path(os.getenv("LOCALAPPDATA", home / "AppData" / "Local"))
        program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
        program_files_x86 = Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"))

        candidates = [
            deveco_path / "jbr",
            deveco_path / "jbr" / "Contents" / "Home",
            deveco_path / "Contents" / "jbr",
            deveco_path / "Contents" / "jbr" / "Contents" / "Home",
            local_app_data / "Programs" / "DevEco Studio" / "jbr",
            local_app_data / "Programs" / "Huawei" / "DevEco Studio" / "jbr",
            program_files / "DevEco Studio" / "jbr",
            program_files / "Huawei" / "DevEco Studio" / "jbr",
            program_files_x86 / "DevEco Studio" / "jbr",
            program_files_x86 / "Huawei" / "DevEco Studio" / "jbr",
        ]
        for candidate in candidates:
            if has_java_executable(candidate, java_names):
                return candidate
        return None
