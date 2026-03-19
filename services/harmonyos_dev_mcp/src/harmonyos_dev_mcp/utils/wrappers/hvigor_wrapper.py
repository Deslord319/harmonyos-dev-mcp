"""Wrapper around the DevEco hvigor build toolchain."""

import os
import platform
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from harmonyos_dev_mcp.config import Config


class HvigorWrapper:
    """Run hvigor commands for a HarmonyOS project."""

    def __init__(self, project_path: str, deveco_path: Optional[str] = None):
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise ValueError(f"project path does not exist: {project_path}")

        self.deveco_path = self._find_deveco_studio(deveco_path)
        if not self.deveco_path:
            raise ValueError(
                "unable to locate DevEco Studio; install it or pass deveco_path explicitly"
            )

        self.node_exe = self._find_node_executable()
        self.hvigorw_js = self._find_hvigor_wrapper()
        self.sdk_root = self._find_sdk_root()
        self.java_home = self._find_java_home()
        self.hvigor_user_home = self._resolve_hvigor_user_home()

        if not self.node_exe.exists():
            raise ValueError(f"node executable not found: {self.node_exe}")
        if not self.hvigorw_js.exists():
            raise ValueError(f"hvigor wrapper not found: {self.hvigorw_js}")
        if not self.sdk_root.exists():
            raise ValueError(f"HarmonyOS SDK root not found: {self.sdk_root}")
        if self.java_home and not self.java_home.exists():
            raise ValueError(f"JAVA_HOME not found: {self.java_home}")

        logger.info("Initialized HvigorWrapper")
        logger.info(f"  project_path: {self.project_path}")
        logger.info(f"  deveco_path: {self.deveco_path}")
        logger.info(f"  node_exe: {self.node_exe}")
        logger.info(f"  hvigorw_js: {self.hvigorw_js}")
        logger.info(f"  sdk_root: {self.sdk_root}")
        if self.java_home:
            logger.info(f"  java_home: {self.java_home}")
        logger.info(f"  hvigor_user_home: {self.hvigor_user_home}")

    @staticmethod
    def _is_writable_dir(path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def _resolve_hvigor_user_home(self) -> Path:
        """
        Pick an isolated writable HVIGOR_USER_HOME for this wrapper instance.

        Sharing one `.hvigor` directory across concurrent builds can trigger
        Windows `EBUSY` failures while hvigor updates `dependencyMap`.
        """
        suffix = uuid.uuid4().hex[:8]
        preferred = self.project_path / ".hvigor" / f"mcp-user-home-{suffix}"
        if self._is_writable_dir(preferred):
            return preferred

        fallback = Path(tempfile.gettempdir()) / "harmonyos_dev_mcp" / "hvigor_home" / suffix
        if self._is_writable_dir(fallback):
            logger.warning(
                f"project-local HVIGOR_USER_HOME is not writable, falling back to {fallback}"
            )
            return fallback

        raise PermissionError(
            "HVIGOR_USER_HOME is not writable in either the project or temp directory: "
            f"{preferred}, {fallback}"
        )

    def _find_deveco_studio(self, custom_path: Optional[str] = None) -> Optional[Path]:
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

        for path in Config._get_deveco_search_paths():
            if Config._is_valid_deveco_path(path):
                logger.info(f"auto-detected DevEco Studio: {path}")
                return path

        return None

    def _find_node_executable(self) -> Path:
        if Config.NODE_PATH and Path(Config.NODE_PATH).exists():
            return Path(Config.NODE_PATH)

        node_names = ["node", "node.exe"]
        if platform.system() == "Windows":
            node_names = ["node.exe", "node"]

        candidates = [
            self.deveco_path / "tools" / "node",
            self.deveco_path / "tools" / "node" / "bin",
            self.deveco_path / "Contents" / "tools" / "node",
            self.deveco_path / "Contents" / "tools" / "node" / "bin",
        ]
        for base in candidates:
            for node_name in node_names:
                candidate = base / node_name
                if candidate.exists():
                    return candidate
        return candidates[0] / node_names[0]

    def _find_hvigor_wrapper(self) -> Path:
        if Config.HVIGOR_PATH and Path(Config.HVIGOR_PATH).exists():
            return Path(Config.HVIGOR_PATH)

        candidates = [
            self.deveco_path / "tools" / "hvigor" / "bin" / "hvigorw.js",
            self.deveco_path / "Contents" / "tools" / "hvigor" / "bin" / "hvigorw.js",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _find_sdk_root(self) -> Path:
        candidates = [
            self.deveco_path / "sdk",
            self.deveco_path / "Contents" / "sdk",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _find_java_home(self) -> Optional[Path]:
        java_names = ["java", "java.exe"]
        if platform.system() == "Windows":
            java_names = ["java.exe", "java"]

        for env_name in ("JAVA_HOME", "JDK_HOME"):
            env_java_home = os.getenv(env_name)
            if not env_java_home:
                continue
            candidate = Path(env_java_home).expanduser()
            for java_exe in java_names:
                if (candidate / "bin" / java_exe).exists():
                    return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            java_path = Path(java_in_path).resolve()
            java_home = java_path.parent.parent
            for java_exe in java_names:
                if (java_home / "bin" / java_exe).exists():
                    return java_home

        candidates = [
            self.deveco_path / "jbr",
            self.deveco_path / "jbr" / "Contents" / "Home",
            self.deveco_path / "Contents" / "jbr",
            self.deveco_path / "Contents" / "jbr" / "Contents" / "Home",
            Path.home() / "AppData" / "Local" / "Programs" / "DevEco Studio" / "jbr",
            Path.home() / "AppData" / "Local" / "Programs" / "Huawei" / "DevEco Studio" / "jbr",
        ]
        for candidate in candidates:
            for java_exe in java_names:
                if (candidate / "bin" / java_exe).exists():
                    return candidate
        return None

    def _ensure_local_properties(self) -> None:
        """
        Keep local.properties aligned for projects that still read it.

        HarmonyOS projects normally resolve SDK paths through DEVECO_SDK_HOME,
        but keeping this file correct is harmless and helps mixed setups.
        """
        local_props = self.project_path / "local.properties"
        sdk_dir = self.deveco_path / "sdk" / "default"
        nodejs_dir = self.deveco_path / "tools" / "node"

        existing_config: Dict[str, str] = {}
        if local_props.exists():
            with open(local_props, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        existing_config[key.strip()] = value.strip()

        needs_update = False
        if existing_config.get("sdk.dir") != str(sdk_dir).replace("\\", "\\\\"):
            needs_update = True
        if existing_config.get("nodejs.dir") != str(nodejs_dir).replace("\\", "\\\\"):
            needs_update = True

        if needs_update:
            logger.info("updating local.properties")
            with open(local_props, "w", encoding="utf-8") as handle:
                handle.write("# This file is automatically generated by HarmonyOS MCP Server\n")
                handle.write("# Do not modify this file manually\n\n")
                handle.write(f"sdk.dir={str(sdk_dir).replace('\\', '/')}\n")
                handle.write(f"nodejs.dir={str(nodejs_dir).replace('\\', '/')}\n")

    def _execute_command(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """Execute hvigor with the resolved toolchain and environment."""
        effective_args = list(args)
        if (
            platform.system() == "Windows"
            and "--no-daemon" not in effective_args
            and "--daemon" not in effective_args
        ):
            effective_args.append("--no-daemon")

        cmd = [str(self.node_exe), str(self.hvigorw_js)] + effective_args
        timeout = timeout or Config.BUILD_TIMEOUT

        logger.debug(f"running hvigor command: {' '.join(cmd)}")

        env = os.environ.copy()
        env["DEVECO_SDK_HOME"] = str(self.sdk_root)
        env["HVIGOR_USER_HOME"] = str(self.hvigor_user_home)
        if self.java_home:
            env["JAVA_HOME"] = str(self.java_home)
            env["PATH"] = f"{self.java_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"

        self.hvigor_user_home.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                env=env,
                close_fds=True,
            )
            command_success = result.returncode == 0 and not self._has_build_failure_output(
                result.stdout, result.stderr
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": command_success,
            }
        except subprocess.TimeoutExpired:
            logger.error(f"hvigor command timed out after {timeout}s")
            return {
                "error_code": "BUILD_TIMEOUT",
                "returncode": -1,
                "stdout": "",
                "stderr": f"build timed out after {timeout}s",
                "success": False,
            }
        except Exception as exc:
            logger.error(f"failed to execute hvigor command: {exc}")
            return {
                "error_code": "BUILD_COMMAND_ERROR",
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "success": False,
            }
        finally:
            self._cleanup_hvigor_user_home()

    @staticmethod
    def _has_build_failure_output(stdout: str, stderr: str) -> bool:
        combined = f"{stdout}\n{stderr}".upper()
        return "BUILD FAILED" in combined or "COMPILE RESULT:FAIL" in combined

    def _kill_process_tree(self, pid: int) -> None:
        """Terminate a process and its children."""
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                import signal

                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception as exc:
            logger.error(f"failed to terminate process tree: {exc}")

    def _cleanup_hvigor_user_home(self) -> None:
        """Remove the per-build HVIGOR_USER_HOME directory."""
        try:
            shutil.rmtree(self.hvigor_user_home, ignore_errors=False)
        except FileNotFoundError:
            return
        except Exception as exc:
            logger.warning(f"failed to remove hvigor_user_home {self.hvigor_user_home}: {exc}")

    def clean(self, product: str = "default") -> Dict[str, Any]:
        logger.info(f"clean build outputs for product={product}")
        args = [
            "--no-daemon",
            "--sync",
            "-p",
            f"product={product}",
            "--analyze=normal",
            "--parallel",
            "--incremental",
        ]
        result = self._execute_command(args)
        if result["success"]:
            logger.info("clean succeeded")
        else:
            logger.error(f"clean failed: {result['stderr']}")
        return result

    def build_har(self, module_name: str, product: str = "default") -> Dict[str, Any]:
        logger.info(f"build HAR for module={module_name}, product={product}")
        args = [
            "--no-daemon",
            "--mode",
            "module",
            "-p",
            f"product={product}",
            "-p",
            f"module={module_name}",
            "assembleHar",
            "--analyze=normal",
            "--parallel",
            "--incremental",
        ]
        result = self._execute_command(args)
        if result["success"]:
            har_path = self._find_build_output("har", module_name)
            result["har_path"] = str(har_path) if har_path else None
            logger.info(f"HAR build succeeded: {result['har_path']}")
        else:
            logger.error(f"HAR build failed: {result['stderr']}")
        return result

    def build_hap(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        if build_mode != "debug":
            return {
                "error_code": "INVALID_BUILD_MODE",
                "returncode": -1,
                "stdout": "",
                "stderr": 'only build_mode="debug" is currently supported',
                "success": False,
                "hap_path": None,
            }

        logger.info(f"build HAP for product={product}")
        args = [
            "--no-daemon",
            "--mode",
            "module",
            "-p",
            f"product={product}",
            "assembleHap",
            "--analyze=normal",
            "--parallel",
            "--incremental",
        ]
        result = self._execute_command(args)
        if result["success"]:
            hap_path = self._find_build_output("hap")
            result["hap_path"] = str(hap_path) if hap_path else None
            logger.info(f"HAP build succeeded: {result['hap_path']}")
        else:
            logger.error(f"HAP build failed: {result['stderr']}")
        return result

    def build_app(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        if build_mode != "debug":
            return {
                "error_code": "INVALID_BUILD_MODE",
                "returncode": -1,
                "stdout": "",
                "stderr": 'only build_mode="debug" is currently supported',
                "success": False,
                "app_path": None,
            }

        logger.info(f"build APP for product={product}")
        args = [
            "--no-daemon",
            "-p",
            f"product={product}",
            "assembleApp",
            "--analyze=normal",
            "--parallel",
            "--incremental",
        ]
        result = self._execute_command(args)
        if result["success"]:
            app_path = self._find_build_output("app")
            result["app_path"] = str(app_path) if app_path else None
            logger.info(f"APP build succeeded: {result['app_path']}")
        else:
            logger.error(f"APP build failed: {result['stderr']}")
        return result

    def _find_build_output(self, output_type: str, search_key: str = "") -> Optional[Path]:
        """Return the newest build artifact for the requested output type."""
        output_dirs = [
            self.project_path / "build",
            self.project_path / "entry" / "build",
        ]
        if output_type == "har" and search_key:
            output_dirs.append(self.project_path / search_key / "build")

        matches: List[Path] = []
        extension = f".{output_type}"
        for output_dir in output_dirs:
            if not output_dir.exists():
                continue
            matches.extend(output_dir.rglob(f"*{extension}"))

        if not matches:
            return None

        if search_key:
            narrowed = [
                path
                for path in matches
                if search_key.lower() in path.name.lower()
                or search_key.lower() in str(path.parent).lower()
            ]
            if narrowed:
                matches = narrowed

        matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0]

    def get_build_info(self) -> Dict[str, Any]:
        return {
            "project_path": str(self.project_path),
            "deveco_path": str(self.deveco_path),
            "node_exe": str(self.node_exe),
            "hvigorw_js": str(self.hvigorw_js),
            "has_build_profile": (self.project_path / "build-profile.json5").exists(),
            "has_local_properties": (self.project_path / "local.properties").exists(),
        }
