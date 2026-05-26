"""Wrapper around the DevEco hvigor build toolchain."""

import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
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

    @staticmethod
    def _has_java_executable(candidate: Path, java_names: List[str]) -> bool:
        return any((candidate / "bin" / java_exe).exists() for java_exe in java_names)

    def _find_java_home(self) -> Optional[Path]:
        java_names = ["java", "java.exe"]
        if platform.system() == "Windows":
            java_names = ["java.exe", "java"]

        for env_name in ("JAVA_HOME", "JDK_HOME"):
            env_java_home = os.getenv(env_name)
            if not env_java_home:
                continue
            candidate = Path(env_java_home).expanduser()
            if self._has_java_executable(candidate, java_names):
                return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            java_path = Path(java_in_path).resolve()
            java_home = java_path.parent.parent
            if self._has_java_executable(java_home, java_names):
                return java_home

        home = Path.home()
        local_app_data = Path(os.getenv("LOCALAPPDATA", home / "AppData" / "Local"))
        program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
        program_files_x86 = Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"))

        candidates = [
            self.deveco_path / "jbr",
            self.deveco_path / "jbr" / "Contents" / "Home",
            self.deveco_path / "Contents" / "jbr",
            self.deveco_path / "Contents" / "jbr" / "Contents" / "Home",
            local_app_data / "Programs" / "DevEco Studio" / "jbr",
            local_app_data / "Programs" / "Huawei" / "DevEco Studio" / "jbr",
            program_files / "DevEco Studio" / "jbr",
            program_files / "Huawei" / "DevEco Studio" / "jbr",
            program_files_x86 / "DevEco Studio" / "jbr",
            program_files_x86 / "Huawei" / "DevEco Studio" / "jbr",
        ]
        for candidate in candidates:
            if self._has_java_executable(candidate, java_names):
                return candidate
        return None

    def _build_command_env(self, include_hvigor_home: bool = False) -> Dict[str, str]:
        env = os.environ.copy()
        env["DEVECO_SDK_HOME"] = str(self.sdk_root)
        if include_hvigor_home:
            env["HVIGOR_USER_HOME"] = str(self.hvigor_user_home)
        if self.java_home:
            env["JAVA_HOME"] = str(self.java_home)
            env["PATH"] = f"{self.java_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        return env

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

        env = self._build_command_env(include_hvigor_home=True)

        self.hvigor_user_home.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                env=env,
                close_fds=True,
            )
            command_success = result.returncode == 0 and not self._has_build_failure_output(
                result.stdout, result.stderr
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": command_success,
            }
        except subprocess.TimeoutExpired:
            logger.error(f"hvigor command timed out after {timeout}s")
            return {
                "error_code": "BUILD_TIMEOUT",
                "stdout": "",
                "stderr": f"build timed out after {timeout}s",
                "success": False,
            }
        except Exception as exc:
            logger.error(f"failed to execute hvigor command: {exc}")
            return {
                "error_code": "BUILD_COMMAND_ERROR",
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

    def _cleanup_hvigor_user_home(self) -> None:
        """Remove the per-build HVIGOR_USER_HOME directory."""
        try:
            shutil.rmtree(self.hvigor_user_home, ignore_errors=False)
        except FileNotFoundError:
            return
        except Exception as exc:
            logger.warning(f"failed to remove hvigor_user_home {self.hvigor_user_home}: {exc}")

    def clean(self, product: str = "default", module_name: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"clean build outputs for product={product}")
        args = [
            "--no-daemon",
            "clean",
            "-p",
            f"product={product}",
            "--analyze=normal",
            "--parallel",
        ]
        if module_name:
            args.extend(["--mode", "module", "-p", f"module={module_name}"])
        result = self._execute_command(args)
        if result["success"]:
            logger.info("clean succeeded")
        else:
            logger.error(f"clean failed: {result['stderr']}")
        return result

    @staticmethod
    def _is_fresh_output(path: Optional[Path], not_before: Optional[float]) -> bool:
        if path is None or not path.exists():
            return False
        if not_before is None:
            return True
        try:
            return path.stat().st_mtime >= (not_before - 1.0)
        except OSError:
            return False

    def _build_profile_paths(self) -> List[Path]:
        profiles: List[Path] = []
        root_profile = self.project_path / "build-profile.json5"
        if root_profile.exists():
            profiles.append(root_profile)

        for path in self.project_path.rglob("build-profile.json5"):
            if path == root_profile:
                continue
            lowered_parts = {part.lower() for part in path.parts}
            if lowered_parts & {"build", ".git", ".venv", "__pycache__"}:
                continue
            profiles.append(path)
        return profiles

    @staticmethod
    def _looks_like_signing_path(value: str) -> bool:
        lowered = value.lower()
        if lowered.startswith(("http://", "https://")):
            return False
        if "\\" in value or "/" in value:
            return True
        return lowered.endswith(
            (".p7b", ".p12", ".cer", ".jks", ".keystore", ".pfx", ".pem", ".der", ".mobileprovision")
        )

    def _find_missing_signing_files(self, profile_paths: List[Path]) -> List[str]:
        missing: List[str] = []
        key_pattern = re.compile(
            r'(?i)["\']?(storefile|keystorefile|keystore|storepath|certpath|certfile|profile)["\']?\s*:\s*["\']([^"\']+)["\']'
        )
        for profile_path in profile_paths:
            try:
                content = profile_path.read_text(encoding="utf-8")
            except OSError:
                continue
            for _, raw_value in key_pattern.findall(content):
                value = raw_value.strip()
                if not self._looks_like_signing_path(value):
                    continue
                candidates = []
                path_value = Path(value)
                if path_value.is_absolute():
                    candidates.append(path_value)
                else:
                    candidates.append((profile_path.parent / path_value).resolve())
                    candidates.append((self.project_path / path_value).resolve())
                if any(candidate.exists() for candidate in candidates):
                    continue
                missing.append(value)
        return sorted(set(missing))

    def _validate_build_config(
        self,
        target: str,
        build_mode: str,
        product: str,
        module_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        profile_paths = self._build_profile_paths()
        if not profile_paths:
            return {
                "error_code": "BUILD_PROFILE_MISSING",
                "stdout": "",
                "stderr": "build-profile.json5 not found in project",
                "success": False,
                "output_path": None,
            }

        if target == "har":
            return None

        combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in profile_paths)
        if build_mode and re.search(r"(?i)\bbuildModeSet\b", combined):
            if not re.search(rf'(?i)"name"\s*:\s*"{re.escape(build_mode)}"', combined):
                return {
                    "error_code": "INVALID_BUILD_MODE",
                    "stdout": "",
                    "stderr": f'build mode "{build_mode}" is not declared in build-profile.json5',
                    "success": False,
                    "output_path": None,
                }

        product_signing_match = re.search(
            rf'(?is)"name"\s*:\s*"{re.escape(product)}".*?"signingConfig"\s*:\s*"([^"]+)"',
            combined,
        )
        if not product_signing_match:
            return None

        signing_name = product_signing_match.group(1)
        if not re.search(rf'(?is)"name"\s*:\s*"{re.escape(signing_name)}"', combined):
            return {
                "error_code": "SIGNING_CONFIG_MISSING",
                "stdout": "",
                "stderr": f'signing config "{signing_name}" referenced by product "{product}" was not found',
                "success": False,
                "output_path": None,
            }

        missing_files = self._find_missing_signing_files(profile_paths)
        if missing_files:
            return {
                "error_code": "SIGNING_FILE_NOT_FOUND",
                "stdout": "",
                "stderr": (
                    "signing files referenced by build-profile.json5 were not found: "
                    + ", ".join(missing_files)
                ),
                "success": False,
                "output_path": None,
            }

        logger.debug(
            f"validated build config for target={target}, build_mode={build_mode}, product={product}, module_name={module_name or ''}"
        )
        return None

    def _extract_output_path_from_logs(
        self,
        stdout: str,
        stderr: str,
        output_type: str,
        not_before: Optional[float] = None,
    ) -> Optional[Path]:
        extension = f".{output_type}"
        token_pattern = re.compile(rf"([A-Za-z]:[\\/][^\s'\"<>]+?{re.escape(extension)}|[^\s'\"<>]+?{re.escape(extension)})")

        for text in (stdout, stderr):
            for raw_match in token_pattern.findall(text or ""):
                candidate_text = raw_match.strip("\"'")
                candidate = Path(candidate_text)
                if candidate.is_absolute() and self._is_fresh_output(candidate, not_before):
                    return candidate

                relative_candidates = [
                    (self.project_path / candidate_text).resolve(),
                    (self.project_path / Path(candidate_text).name).resolve(),
                ]
                for relative_candidate in relative_candidates:
                    if self._is_fresh_output(relative_candidate, not_before):
                        return relative_candidate
        return None

    def _find_output_from_metadata(
        self,
        output_type: str,
        product: str,
        module_name: Optional[str],
        not_before: Optional[float] = None,
    ) -> Optional[Path]:
        if output_type != "hap":
            return None

        module_root = self.project_path / (module_name or "entry")
        metadata_path = module_root / "build" / product / "intermediates" / "hap_metadata" / product / "output_metadata.json"
        if not metadata_path.exists():
            return None

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(metadata, list):
            return None

        for item in metadata:
            if not isinstance(item, dict):
                continue
            hap_name = item.get("hapName")
            if not hap_name:
                continue
            candidate = module_root / "build" / product / "outputs" / product / hap_name
            if self._is_fresh_output(candidate, not_before):
                return candidate
        return None

    def _find_sign_fallback_script(self, build_mode: str) -> Optional[Path]:
        candidates = [
            self.project_path / "hapsigner" / f"2-{build_mode}-sign.bat",
            self.project_path / "hapsigner" / f"sign-{build_mode}.bat",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _run_sign_fallback(self, build_mode: str) -> Dict[str, Any]:
        script_path = self._find_sign_fallback_script(build_mode)
        if script_path is None:
            return {
                "success": False,
                "error_code": "SIGN_FALLBACK_SCRIPT_MISSING",
                "stdout": "",
                "stderr": f"sign fallback script not found for build_mode={build_mode}",
                "output_path": None,
            }

        expected_output = script_path.parent / "signApp.hap"
        if expected_output.exists():
            expected_output.unlink(missing_ok=True)

        existing_outputs = {
            path.resolve()
            for path in script_path.parent.glob("*.hap")
            if path.is_file()
        }

        runner_path = script_path.parent / f".mcp-sign-{build_mode}.bat"
        try:
            original_script = script_path.read_text(encoding="utf-8", errors="ignore")
            runner_lines = [line for line in original_script.splitlines() if line.strip().lower() != "pause"]
            runner_path.write_text("\n".join(runner_lines) + "\n", encoding="utf-8")

            result = subprocess.run(
                ["cmd.exe", "/c", str(runner_path)],
                cwd=str(script_path.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=Config.BUILD_TIMEOUT,
                env=self._build_command_env(),
                close_fds=True,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error_code": "SIGN_FALLBACK_TIMEOUT",
                "stdout": "",
                "stderr": f"sign fallback timed out after {Config.BUILD_TIMEOUT}s",
                "output_path": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "error_code": "SIGN_FALLBACK_ERROR",
                "stdout": "",
                "stderr": str(exc),
                "output_path": None,
            }
        finally:
            runner_path.unlink(missing_ok=True)

        signed_output = self._extract_output_path_from_logs(
            result.stdout,
            result.stderr,
            "hap",
        )
        if signed_output is None:
            signed_output = self._resolve_sign_fallback_output(script_path.parent, existing_outputs, expected_output)
        success = result.returncode == 0 and signed_output is not None
        return {
            "success": success,
            "error_code": None if success else "SIGN_FALLBACK_FAILED",
            "stdout": result.stdout.replace("Press any key to continue . . .", "").strip(),
            "stderr": result.stderr.replace("Press any key to continue . . .", "").strip(),
            "output_path": str(signed_output) if signed_output else None,
            "artifact_source": "sign_fallback" if success else None,
        }

    @staticmethod
    def _resolve_sign_fallback_output(
        output_dir: Path,
        existing_outputs: set[Path],
        expected_output: Path,
    ) -> Optional[Path]:
        if expected_output.exists():
            return expected_output

        candidates = [
            path.resolve()
            for path in output_dir.glob("*.hap")
            if path.is_file() and path.resolve() not in existing_outputs
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates[0]

    @staticmethod
    def _resolve_sign_status(output_path: Optional[Path]) -> str:
        if output_path is None:
            return "unknown"
        lowered_name = output_path.name.lower()
        if lowered_name.endswith((".hap", ".hsp")):
            if "unsigned" in lowered_name:
                return "unsigned"
            if "signed" in lowered_name:
                return "signed"
        return "unknown"

    def _score_output_path(
        self,
        path: Path,
        output_type: str,
        build_mode: str,
        product: str,
        module_name: Optional[str],
    ) -> tuple[int, float]:
        lowered_name = path.name.lower()
        lowered_path = str(path).lower()
        score = 0

        if output_type in lowered_name:
            score += 20
        if "signed" in lowered_name and "unsigned" not in lowered_name:
            score += 30
        if build_mode and build_mode.lower() in lowered_path:
            score += 40
        if product and product.lower() in lowered_path:
            score += 40
        if module_name and module_name.lower() in lowered_path:
            score += 40
        if "outputs" in lowered_path:
            score += 10
        if output_type == "hap" and "unsigned" in lowered_name:
            score += 5
        if path.parent.name.lower() == product.lower():
            score += 10

        return score, path.stat().st_mtime

    @staticmethod
    def _build_output_resolution_guidance(*, stale_logged_output: bool = False) -> str:
        guidance = [
            "Build completed, but the tool could not locate a fresh artifact for this run.",
        ]
        if stale_logged_output:
            guidance.append(
                "The path mentioned in hvigor output points to an existing artifact whose timestamp predates the current build."
            )
        else:
            guidance.append(
                "This usually means an incremental build reused cached outputs without updating timestamps, or the signed output path was not emitted in a way the tool could recognize."
            )
        guidance.append(
            "Try build_app with is_clean=true, or check whether the expected package already exists under the project's build outputs or hapsigner directory."
        )
        return " ".join(guidance)

    @staticmethod
    def _hap_contains_hnp(path: Path) -> bool:
        try:
            with zipfile.ZipFile(path) as archive:
                return any(name.startswith("hnp/") and name.endswith(".hnp") for name in archive.namelist())
        except (OSError, zipfile.BadZipFile):
            return False

    @staticmethod
    def _hap_contains_hsp(path: Path) -> bool:
        try:
            with zipfile.ZipFile(path) as archive:
                return any(name.startswith("shared_libs/") and name.endswith(".hsp") for name in archive.namelist())
        except (OSError, zipfile.BadZipFile):
            return False

    @staticmethod
    def _find_matching_token(text: str, start: int, open_token: str, close_token: str) -> Optional[int]:
        depth = 0
        quote: Optional[str] = None
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char == open_token:
                depth += 1
            elif char == close_token:
                depth -= 1
                if depth == 0:
                    return index
        return None

    @classmethod
    def _extract_array_objects(cls, content: str, key: str) -> List[str]:
        pattern = re.compile(rf'(?is)["\']?{re.escape(key)}["\']?\s*:\s*\[')
        match = pattern.search(content)
        if not match:
            return []

        array_start = content.find("[", match.start())
        array_end = cls._find_matching_token(content, array_start, "[", "]")
        if array_end is None:
            return []

        array_content = content[array_start + 1 : array_end]
        objects: List[str] = []
        search_from = 0
        while True:
            object_start = array_content.find("{", search_from)
            if object_start < 0:
                break
            object_end = cls._find_matching_token(array_content, object_start, "{", "}")
            if object_end is None:
                break
            objects.append(array_content[object_start : object_end + 1])
            search_from = object_end + 1
        return objects

    @staticmethod
    def _extract_scalar_value(content: str, key: str) -> Optional[str]:
        pattern = re.compile(
            rf'(?is)["\']?{re.escape(key)}["\']?\s*:\s*'
            r'(?:"([^"]*)"|\'([^\']*)\'|([^,\n\r}]+))'
        )
        match = pattern.search(content)
        if not match:
            return None
        value = next(group for group in match.groups() if group is not None)
        return value.strip().rstrip(",")

    @classmethod
    def _extract_object_value(cls, content: str, key: str) -> Optional[str]:
        pattern = re.compile(rf'(?is)["\']?{re.escape(key)}["\']?\s*:\s*\{{')
        match = pattern.search(content)
        if not match:
            return None
        object_start = content.find("{", match.start())
        object_end = cls._find_matching_token(content, object_start, "{", "}")
        if object_end is None:
            return None
        return content[object_start : object_end + 1]

    @classmethod
    def _extract_named_array_object(cls, content: str, array_key: str, name: str) -> Optional[str]:
        for item in cls._extract_array_objects(content, array_key):
            if cls._extract_scalar_value(item, "name") == name:
                return item
        return None

    @staticmethod
    def _resolve_profile_relative_path(raw_value: str, profile_path: Path, project_path: Path) -> Path:
        path_value = Path(raw_value).expanduser()
        if path_value.is_absolute():
            return path_value

        candidates = [
            (profile_path.parent / path_value).resolve(),
            (project_path / path_value).resolve(),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    @staticmethod
    def _extract_compatible_version(product_object: str) -> str:
        for key in ("compatibleSdkVersion", "targetSdkVersion"):
            value = HvigorWrapper._extract_scalar_value(product_object, key)
            if not value:
                continue
            parenthesized = re.search(r"\((\d+)\)", value)
            if parenthesized:
                return parenthesized.group(1)
            numeric = re.search(r"\b(\d+)\b", value)
            if numeric:
                return numeric.group(1)
        return "9"

    def _resolve_repack_signing_config(self, product: str, error_prefix: str) -> Dict[str, Any]:
        for profile_path in self._build_profile_paths():
            try:
                content = profile_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            product_object = self._extract_named_array_object(content, "products", product)
            if product_object is None:
                continue

            signing_name = self._extract_scalar_value(product_object, "signingConfig")
            if not signing_name:
                return {
                    "success": False,
                    "error_code": f"{error_prefix}_SIGNING_CONFIG_MISSING",
                    "stderr": f'product "{product}" does not declare signingConfig',
                }

            signing_object = self._extract_named_array_object(content, "signingConfigs", signing_name)
            if signing_object is None:
                return {
                    "success": False,
                    "error_code": f"{error_prefix}_SIGNING_CONFIG_MISSING",
                    "stderr": f'signing config "{signing_name}" referenced by product "{product}" was not found',
                }

            material = self._extract_object_value(signing_object, "material") or signing_object
            scalar_keys = ["keyAlias", "keyPassword", "storePassword", "certpath", "profile", "storeFile"]
            values = {key: self._extract_scalar_value(material, key) for key in scalar_keys}
            missing = [key for key, value in values.items() if value is None]
            if missing:
                return {
                    "success": False,
                    "error_code": f"{error_prefix}_SIGNING_CONFIG_INCOMPLETE",
                    "stderr": "signing material is missing required keys: " + ", ".join(missing),
                }

            path_keys = {
                "certpath": "app_cert_file",
                "profile": "profile_file",
                "storeFile": "keystore_file",
            }
            resolved_paths = {
                output_key: self._resolve_profile_relative_path(values[input_key], profile_path, self.project_path)
                for input_key, output_key in path_keys.items()
            }
            missing_paths = [str(path) for path in resolved_paths.values() if not path.exists()]
            if missing_paths:
                return {
                    "success": False,
                    "error_code": f"{error_prefix}_SIGNING_FILE_NOT_FOUND",
                    "stderr": "signing files were not found: " + ", ".join(missing_paths),
                }

            return {
                "success": True,
                "key_alias": values["keyAlias"],
                "key_password": values["keyPassword"],
                "keystore_password": values["storePassword"],
                "sign_alg": self._extract_scalar_value(material, "signAlg") or "SHA256withECDSA",
                "compatible_version": self._extract_compatible_version(product_object),
                **resolved_paths,
            }

        return {
            "success": False,
            "error_code": f"{error_prefix}_SIGNING_CONFIG_MISSING",
            "stderr": f'product "{product}" was not found in build-profile.json5',
        }

    def _resolve_module_root(self, module_name: Optional[str]) -> Path:
        module = module_name or "entry"
        candidates = [
            self.project_path / module,
            self.project_path / "harmony" / "app" / module,
            self.project_path / "app" / module,
        ]
        for profile_path in self._build_profile_paths():
            try:
                content = profile_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for module_object in self._extract_array_objects(content, "modules"):
                name = self._extract_scalar_value(module_object, "name")
                if name != module:
                    continue
                src_path = self._extract_scalar_value(module_object, "srcPath")
                if src_path:
                    candidates.insert(0, (profile_path.parent / src_path).resolve())

        for candidate in candidates:
            if (candidate / "src" / "main" / "module.json5").exists() or (candidate / "build").exists():
                return candidate.resolve()
        return candidates[0].resolve()

    @staticmethod
    def _contains_hnp_package(path: Path) -> bool:
        if not path.exists():
            return False
        ignored_parts = {".git", ".hvigor", "build", "node_modules", "oh_modules"}
        for hnp in path.rglob("*.hnp"):
            if ignored_parts & {part.lower() for part in hnp.parts}:
                continue
            return True
        return False

    @staticmethod
    def _hnp_root_for_package(package_path: Path) -> Path:
        abi_names = {"arm64-v8a", "armeabi-v7a", "x86_64", "x86"}
        if package_path.parent.name in abi_names:
            return package_path.parent.parent
        return package_path.parent

    def _find_hnp_source_root(self, module_root: Path) -> Optional[Path]:
        candidates = [
            module_root / "hnp",
            module_root / "src" / "main" / "hnp",
            self.project_path / "hnp",
        ]
        for candidate in candidates:
            if self._contains_hnp_package(candidate):
                return candidate.resolve()

        ignored_parts = {".git", ".hvigor", "build", "node_modules", "oh_modules"}
        search_roots = [module_root, self.project_path]
        for root in search_roots:
            if not root.exists():
                continue
            for package_path in root.rglob("*.hnp"):
                if ignored_parts & {part.lower() for part in package_path.parts}:
                    continue
                return self._hnp_root_for_package(package_path).resolve()
        return None

    def _discover_shared_modules(self) -> List[str]:
        modules: List[str] = []
        for profile_path in self._build_profile_paths():
            try:
                content = profile_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for module_object in self._extract_array_objects(content, "modules"):
                name = self._extract_scalar_value(module_object, "name")
                src_path = self._extract_scalar_value(module_object, "srcPath")
                if not name or not src_path:
                    continue
                module_json = profile_path.parent / src_path / "src" / "main" / "module.json5"
                if not module_json.exists():
                    continue
                try:
                    module_content = module_json.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if re.search(r'(?is)["\']?type["\']?\s*:\s*["\']shared["\']', module_content):
                    modules.append(name)

        if not modules:
            for module_json in self.project_path.glob("*/src/main/module.json5"):
                try:
                    module_content = module_json.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if re.search(r'(?is)["\']?type["\']?\s*:\s*["\']shared["\']', module_content):
                    modules.append(module_json.parents[2].name)

        return sorted(set(modules))

    @staticmethod
    def _path_inside(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    def _stage_hnp_source(self, source_root: Path, outputs_root: Path, module_root: Path) -> Path:
        staging_root = (outputs_root / "native").resolve()
        if not self._path_inside(staging_root, module_root):
            raise ValueError(f"refusing to stage HNP packages outside module root: {staging_root}")

        if staging_root.exists():
            shutil.rmtree(staging_root)
        staging_root.mkdir(parents=True, exist_ok=True)
        for child in source_root.iterdir():
            destination = staging_root / child.name
            if child.is_dir():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)
        return staging_root

    def _stage_hsp_outputs(self, hsp_paths: List[Path], outputs_root: Path, module_root: Path) -> Path:
        staging_root = (outputs_root / "shared_libs").resolve()
        if not self._path_inside(staging_root, module_root):
            raise ValueError(f"refusing to stage HSP packages outside module root: {staging_root}")

        if staging_root.exists():
            shutil.rmtree(staging_root)
        staging_root.mkdir(parents=True, exist_ok=True)
        for hsp_path in hsp_paths:
            shutil.copy2(hsp_path, staging_root / hsp_path.name)
        return staging_root

    def _merge_hsp_pack_info(
        self,
        base_pack_info: Path,
        hsp_paths: List[Path],
        outputs_root: Path,
        module_root: Path,
    ) -> Dict[str, Any]:
        merged_pack_info = (outputs_root / "hsp_pack_info" / "pack.info").resolve()
        if not self._path_inside(merged_pack_info, module_root):
            return {
                "success": False,
                "error_code": "HSP_PACK_INFO_ERROR",
                "stderr": f"refusing to write merged pack.info outside module root: {merged_pack_info}",
            }

        try:
            merged = json.loads(base_pack_info.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "success": False,
                "error_code": "HSP_PACK_INFO_ERROR",
                "stderr": f"failed to read base pack.info: {exc}",
            }

        summary = merged.setdefault("summary", {})
        merged_modules = summary.setdefault("modules", [])
        merged_packages = merged.setdefault("packages", [])
        module_names = {
            module.get("distro", {}).get("moduleName")
            for module in merged_modules
            if isinstance(module, dict)
        }
        package_names = {
            package.get("name")
            for package in merged_packages
            if isinstance(package, dict)
        }

        for hsp_path in hsp_paths:
            try:
                with zipfile.ZipFile(hsp_path) as archive:
                    hsp_pack = json.loads(archive.read("pack.info").decode("utf-8"))
            except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
                return {
                    "success": False,
                    "error_code": "HSP_PACK_INFO_ERROR",
                    "stderr": f"failed to read pack.info from HSP {hsp_path}: {exc}",
                }

            for module in hsp_pack.get("summary", {}).get("modules", []):
                module_name = module.get("distro", {}).get("moduleName") if isinstance(module, dict) else None
                if module_name and module_name not in module_names:
                    merged_modules.append(module)
                    module_names.add(module_name)
            for package in hsp_pack.get("packages", []):
                package_name = package.get("name") if isinstance(package, dict) else None
                if package_name and package_name not in package_names:
                    merged_packages.append(package)
                    package_names.add(package_name)

        try:
            merged_pack_info.parent.mkdir(parents=True, exist_ok=True)
            merged_pack_info.write_text(
                json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        except OSError as exc:
            return {
                "success": False,
                "error_code": "HSP_PACK_INFO_ERROR",
                "stderr": f"failed to write merged pack.info: {exc}",
            }

        return {"success": True, "pack_info": merged_pack_info}

    def _find_toolchain_jar(self, jar_name: str) -> Optional[Path]:
        candidates = [
            self.sdk_root / "default" / "openharmony" / "toolchains" / "lib" / jar_name,
            self.sdk_root / "openharmony" / "toolchains" / "lib" / jar_name,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        for candidate in self.sdk_root.rglob(jar_name):
            if candidate.is_file():
                return candidate
        return None

    def _java_command(self) -> str:
        java_name = "java.exe" if platform.system() == "Windows" else "java"
        if self.java_home:
            candidate = self.java_home / "bin" / java_name
            if candidate.exists():
                return str(candidate)
        resolved = shutil.which(java_name) or shutil.which("java")
        return resolved or java_name

    def _run_packaging_command(self, cmd: List[str], error_prefix: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=Config.BUILD_TIMEOUT,
                env=self._build_command_env(),
                close_fds=True,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error_code": f"{error_prefix}_TIMEOUT",
                "stdout": "",
                "stderr": f"{error_prefix} command timed out after {Config.BUILD_TIMEOUT}s",
            }
        except Exception as exc:
            return {
                "success": False,
                "error_code": f"{error_prefix}_ERROR",
                "stdout": "",
                "stderr": str(exc),
            }

        return {
            "success": result.returncode == 0,
            "error_code": None if result.returncode == 0 else f"{error_prefix}_FAILED",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    @staticmethod
    def _merge_outputs(*parts: Optional[str]) -> str:
        return "\n".join(part.strip() for part in parts if part and part.strip())

    @staticmethod
    def _looks_like_deveco_encrypted_password(value: str) -> bool:
        return len(value) >= 32 and re.fullmatch(r"[0-9A-Fa-f]+", value) is not None

    @staticmethod
    def _password_candidates(signing: Dict[str, Any]) -> List[tuple[str, str]]:
        candidates: List[tuple[str, str]] = []

        def add(key_password: Optional[str], store_password: Optional[str]) -> None:
            if key_password is None or store_password is None:
                return
            pair = (key_password, store_password)
            if pair not in candidates:
                candidates.append(pair)

        add(signing["key_password"], signing["keystore_password"])

        env_key_password = os.getenv("HAP_KEY_PASSWORD")
        env_store_password = os.getenv("HAP_STORE_PASSWORD")
        if env_key_password or env_store_password:
            add(
                env_key_password or signing["key_password"],
                env_store_password or signing["keystore_password"],
            )

        shared_password = os.getenv("HAP_SIGN_PASSWORD")
        if shared_password:
            add(shared_password, shared_password)

        if (
            HvigorWrapper._looks_like_deveco_encrypted_password(signing["key_password"])
            or HvigorWrapper._looks_like_deveco_encrypted_password(signing["keystore_password"])
        ):
            add("123456", "123456")

        return candidates

    def _build_hnp_sign_command(
        self,
        java: str,
        hap_sign_tool: Path,
        unsigned_hnp: Path,
        signed_hnp: Path,
        signing: Dict[str, Any],
        key_password: str,
        keystore_password: str,
    ) -> List[str]:
        return [
            java,
            "-jar",
            str(hap_sign_tool),
            "sign-app",
            "-mode",
            "localSign",
            "-keyAlias",
            signing["key_alias"],
            "-keyPwd",
            key_password,
            "-appCertFile",
            str(signing["app_cert_file"]),
            "-profileFile",
            str(signing["profile_file"]),
            "-inFile",
            str(unsigned_hnp),
            "-signAlg",
            signing["sign_alg"],
            "-keystoreFile",
            str(signing["keystore_file"]),
            "-keystorePwd",
            keystore_password,
            "-outFile",
            str(signed_hnp),
            "-compatibleVersion",
            signing["compatible_version"],
            "-signCode",
            "1",
        ]

    def _run_base_hap_build_for_repack(
        self,
        build_mode: str,
        product: str,
        module_name: Optional[str],
        is_clean: bool,
        purpose: str,
    ) -> Dict[str, Any]:
        if is_clean:
            clean_result = self.clean(product=product, module_name=module_name)
            if not clean_result["success"]:
                return {
                    "success": False,
                    "error_code": clean_result.get("error_code", "CLEAN_FAILED"),
                    "stdout": clean_result.get("stdout", ""),
                    "stderr": clean_result.get("stderr", "clean failed"),
                    "output_path": None,
                }

        logger.info(f"build base HAP for {purpose} packaging product={product}")
        args: List[str] = [
            "--no-daemon",
            "--mode",
            "module",
            "-p",
            f"product={product}",
            "-p",
            f"buildMode={build_mode}",
        ]
        if module_name:
            args.extend(["-p", f"module={module_name}"])
        args.extend(["assembleHap", "--analyze=normal", "--parallel", "--incremental"])
        result = self._execute_command(args)
        if not result["success"]:
            result["output_path"] = None
            logger.error(f"base HAP build for {purpose} failed: {result['stderr']}")
        return result

    def _repack_and_sign_hnp(
        self,
        module_root: Path,
        hnp_source_root: Path,
        product: str,
        signing: Dict[str, Any],
    ) -> Dict[str, Any]:
        app_packing_tool = self._find_toolchain_jar("app_packing_tool.jar")
        hap_sign_tool = self._find_toolchain_jar("hap-sign-tool.jar")
        if app_packing_tool is None or hap_sign_tool is None:
            missing = []
            if app_packing_tool is None:
                missing.append("app_packing_tool.jar")
            if hap_sign_tool is None:
                missing.append("hap-sign-tool.jar")
            return {
                "success": False,
                "error_code": "HNP_TOOLCHAIN_NOT_FOUND",
                "stdout": "",
                "stderr": "required SDK toolchain jars were not found: " + ", ".join(missing),
                "output_path": None,
            }

        build_root = module_root / "build" / product
        intermediates = build_root / "intermediates"
        outputs = build_root / "outputs" / product
        packaging_inputs = {
            "json": intermediates / "package" / product / "module.json",
            "resources": intermediates / "res" / product / "resources",
            "ets": intermediates / "loader_out" / product / "ets",
            "index": intermediates / "res" / product / "resources.index",
            "pack_info": outputs / "pack.info",
            "pkg_context": intermediates / "loader" / product / "pkgContextInfo.json",
        }
        missing_inputs = [str(path) for path in packaging_inputs.values() if not path.exists()]
        if missing_inputs:
            return {
                "success": False,
                "error_code": "HNP_PACKAGING_INPUT_MISSING",
                "stdout": "",
                "stderr": "HNP packaging inputs were not found: " + ", ".join(missing_inputs),
                "output_path": None,
            }

        outputs.mkdir(parents=True, exist_ok=True)
        hnp_staging_root = self._stage_hnp_source(hnp_source_root, outputs, module_root)
        module = module_root.name
        unsigned_hnp = outputs / f"{module}-{product}-unsigned-hnp.hap"
        signed_hnp = outputs / f"{module}-{product}-signed-hnp.hap"
        lib_path = intermediates / "libs" / product
        java = self._java_command()

        pack_cmd = [
            java,
            "-jar",
            str(app_packing_tool),
            "--mode",
            "hap",
            "--json-path",
            str(packaging_inputs["json"]),
            "--resources-path",
            str(packaging_inputs["resources"]),
            "--ets-path",
            str(packaging_inputs["ets"]),
            "--out-path",
            str(unsigned_hnp),
            "--hnp-path",
            str(hnp_staging_root),
            "--index-path",
            str(packaging_inputs["index"]),
            "--pack-info-path",
            str(packaging_inputs["pack_info"]),
            "--pkg-context-path",
            str(packaging_inputs["pkg_context"]),
            "--force",
            "true",
        ]
        if lib_path.exists():
            pack_cmd.extend(["--lib-path", str(lib_path)])

        logger.info(f"repacking HAP with HNP packages from {hnp_source_root}")
        pack_result = self._run_packaging_command(pack_cmd, "HNP_REPACK")
        if not pack_result["success"] or not unsigned_hnp.exists():
            return {
                **pack_result,
                "output_path": None,
                "error_code": pack_result.get("error_code") or "HNP_REPACK_FAILED",
            }

        logger.info(f"signing HAP with HNP packages: {signed_hnp}")
        sign_failures: List[Dict[str, Any]] = []
        successful_sign_result: Optional[Dict[str, Any]] = None
        for key_password, keystore_password in self._password_candidates(signing):
            signed_hnp.unlink(missing_ok=True)
            sign_cmd = self._build_hnp_sign_command(
                java,
                hap_sign_tool,
                unsigned_hnp,
                signed_hnp,
                signing,
                key_password,
                keystore_password,
            )
            sign_result = self._run_packaging_command(sign_cmd, "HNP_SIGN")
            if sign_result["success"] and signed_hnp.exists():
                successful_sign_result = sign_result
                break
            sign_failures.append(sign_result)

        if successful_sign_result is None:
            combined_stdout = self._merge_outputs(
                pack_result.get("stdout"),
                *(failure.get("stdout") for failure in sign_failures),
            )
            combined_stderr = self._merge_outputs(
                pack_result.get("stderr"),
                *(failure.get("stderr") for failure in sign_failures),
            )
            last_failure = sign_failures[-1] if sign_failures else {}
            return {
                "success": False,
                "error_code": last_failure.get("error_code") or "HNP_SIGN_FAILED",
                "stdout": combined_stdout,
                "stderr": combined_stderr,
                "output_path": None,
            }

        combined_stdout = self._merge_outputs(pack_result.get("stdout"), successful_sign_result.get("stdout"))
        combined_stderr = self._merge_outputs(pack_result.get("stderr"), successful_sign_result.get("stderr"))
        if not self._hap_contains_hnp(signed_hnp):
            return {
                "success": False,
                "error_code": "HNP_NOT_IN_HAP",
                "stdout": combined_stdout,
                "stderr": f"signed HAP does not contain hnp/*.hnp: {signed_hnp}",
                "output_path": None,
            }

        return {
            "success": True,
            "error_code": None,
            "stdout": combined_stdout,
            "stderr": combined_stderr,
            "output_path": str(signed_hnp),
            "artifact_source": "hnp_direct",
            "sign_status": "signed",
        }

    def _build_hnp(
        self,
        build_mode: str,
        product: str,
        module_name: Optional[str],
        is_clean: bool,
    ) -> Dict[str, Any]:
        base_result = self._run_base_hap_build_for_repack(
            build_mode,
            product,
            module_name,
            is_clean,
            "HNP",
        )
        if not base_result.get("success"):
            return base_result

        module_root = self._resolve_module_root(module_name)
        hnp_source_root = self._find_hnp_source_root(module_root)
        if hnp_source_root is None:
            return {
                "error_code": "HNP_PACKAGE_NOT_FOUND",
                "stdout": base_result.get("stdout", ""),
                "stderr": (
                    "target=hnp requires built HNP packages under a module hnp directory, "
                    f"for example {module_root / 'hnp'} containing ABI subdirectories with .hnp files"
                ),
                "success": False,
                "output_path": None,
            }

        signing = self._resolve_repack_signing_config(product, "HNP")
        if not signing.get("success"):
            return {
                "success": False,
                "error_code": signing["error_code"],
                "stdout": base_result.get("stdout", ""),
                "stderr": self._merge_outputs(base_result.get("stderr"), signing["stderr"]),
                "output_path": None,
            }

        result = self._repack_and_sign_hnp(module_root, hnp_source_root, product, signing)
        result["stdout"] = self._merge_outputs(base_result.get("stdout"), result.get("stdout"))
        result["stderr"] = self._merge_outputs(base_result.get("stderr"), result.get("stderr"))
        if result.get("success"):
            logger.info(f"HNP build succeeded: {result['output_path']}")
        else:
            logger.error(f"HNP build failed: {result.get('stderr', '')}")

        return result

    def _build_hsp_outputs(
        self,
        build_mode: str,
        product: str,
        hsp_module_names: Optional[List[str]],
    ) -> Dict[str, Any]:
        modules = self._resolve_hsp_module_names(hsp_module_names)
        if not modules:
            modules = self._discover_shared_modules()
        if not modules:
            return {
                "success": False,
                "error_code": "HSP_MODULE_NOT_FOUND",
                "stdout": "",
                "stderr": (
                    "include_hsp=true requires at least one shared module. Pass hsp_module_names "
                    "or add modules whose src/main/module.json5 declares "
                    'type="shared".'
                ),
                "output_paths": [],
            }

        outputs: List[Path] = []
        stdout_parts: List[str] = []
        stderr_parts: List[str] = []
        for module in modules:
            result = self.build(
                target="hsp",
                build_mode=build_mode,
                product=product,
                module_name=module,
                is_clean=False,
                include_hsp=False,
            )
            if not result.get("success") and result.get("error_code") in {
                "BUILD_OUTPUT_NOT_FOUND",
                "STALE_BUILD_ARTIFACT",
            }:
                logger.info(f"retry HSP module build with clean because output was not refreshed: {module}")
                retry_result = self.build(
                    target="hsp",
                    build_mode=build_mode,
                    product=product,
                    module_name=module,
                    is_clean=True,
                    include_hsp=False,
                )
                if retry_result.get("success"):
                    result = retry_result
                else:
                    retry_result["stdout"] = self._merge_outputs(
                        result.get("stdout"),
                        retry_result.get("stdout"),
                    )
                    retry_result["stderr"] = self._merge_outputs(
                        result.get("stderr"),
                        retry_result.get("stderr"),
                    )
                    result = retry_result
            stdout_parts.append(result.get("stdout", ""))
            stderr_parts.append(result.get("stderr", ""))
            if not result.get("success"):
                return {
                    "success": False,
                    "error_code": result.get("error_code", "HSP_BUILD_FAILED"),
                    "stdout": self._merge_outputs(*stdout_parts),
                    "stderr": self._merge_outputs(*stderr_parts),
                    "output_paths": [],
                }
            output_path = result.get("output_path")
            if not output_path:
                return {
                    "success": False,
                    "error_code": "HSP_OUTPUT_NOT_FOUND",
                    "stdout": self._merge_outputs(*stdout_parts),
                    "stderr": f"HSP build completed but no output path was returned for module {module}",
                    "output_paths": [],
                }
            outputs.append(Path(output_path))

        return {
            "success": True,
            "stdout": self._merge_outputs(*stdout_parts),
            "stderr": self._merge_outputs(*stderr_parts),
            "output_paths": outputs,
        }

    @staticmethod
    def _resolve_hsp_module_names(hsp_module_names: Optional[List[str]]) -> List[str]:
        modules: List[str] = []

        for raw_value in hsp_module_names or []:
            if not raw_value:
                continue
            module = raw_value.strip()
            if module and module not in modules:
                modules.append(module)
        return modules

    def _repack_and_sign_hap_with_hsp(
        self,
        module_root: Path,
        hsp_paths: List[Path],
        product: str,
        signing: Dict[str, Any],
    ) -> Dict[str, Any]:
        app_packing_tool = self._find_toolchain_jar("app_packing_tool.jar")
        hap_sign_tool = self._find_toolchain_jar("hap-sign-tool.jar")
        if app_packing_tool is None or hap_sign_tool is None:
            missing = []
            if app_packing_tool is None:
                missing.append("app_packing_tool.jar")
            if hap_sign_tool is None:
                missing.append("hap-sign-tool.jar")
            return {
                "success": False,
                "error_code": "HSP_TOOLCHAIN_NOT_FOUND",
                "stdout": "",
                "stderr": "required SDK toolchain jars were not found: " + ", ".join(missing),
                "output_path": None,
            }

        build_root = module_root / "build" / product
        intermediates = build_root / "intermediates"
        outputs = build_root / "outputs" / product
        packaging_inputs = {
            "json": intermediates / "package" / product / "module.json",
            "resources": intermediates / "res" / product / "resources",
            "ets": intermediates / "loader_out" / product / "ets",
            "index": intermediates / "res" / product / "resources.index",
            "pack_info": outputs / "pack.info",
            "pkg_context": intermediates / "loader" / product / "pkgContextInfo.json",
        }
        missing_inputs = [str(path) for path in packaging_inputs.values() if not path.exists()]
        if missing_inputs:
            return {
                "success": False,
                "error_code": "HSP_PACKAGING_INPUT_MISSING",
                "stdout": "",
                "stderr": "HSP packaging inputs were not found: " + ", ".join(missing_inputs),
                "output_path": None,
            }

        outputs.mkdir(parents=True, exist_ok=True)
        shared_libs_root = self._stage_hsp_outputs(hsp_paths, outputs, module_root)
        merged_pack_info = self._merge_hsp_pack_info(
            packaging_inputs["pack_info"],
            hsp_paths,
            outputs,
            module_root,
        )
        if not merged_pack_info.get("success"):
            return {
                "success": False,
                "error_code": merged_pack_info["error_code"],
                "stdout": "",
                "stderr": merged_pack_info["stderr"],
                "output_path": None,
            }
        module = module_root.name
        unsigned_hap = outputs / f"{module}-{product}-unsigned-hsp.hap"
        signed_hap = outputs / f"{module}-{product}-signed-hsp.hap"
        lib_path = intermediates / "libs" / product
        java = self._java_command()

        pack_cmd = [
            java,
            "-jar",
            str(app_packing_tool),
            "--mode",
            "hap",
            "--json-path",
            str(packaging_inputs["json"]),
            "--resources-path",
            str(packaging_inputs["resources"]),
            "--ets-path",
            str(packaging_inputs["ets"]),
            "--out-path",
            str(unsigned_hap),
            "--shared-libs-path",
            str(shared_libs_root),
            "--index-path",
            str(packaging_inputs["index"]),
            "--pack-info-path",
            str(merged_pack_info["pack_info"]),
            "--pkg-context-path",
            str(packaging_inputs["pkg_context"]),
            "--force",
            "true",
        ]
        if lib_path.exists():
            pack_cmd.extend(["--lib-path", str(lib_path)])

        logger.info(f"repacking HAP with HSP packages from {shared_libs_root}")
        pack_result = self._run_packaging_command(pack_cmd, "HSP_REPACK")
        if not pack_result["success"] or not unsigned_hap.exists():
            return {
                **pack_result,
                "output_path": None,
                "error_code": pack_result.get("error_code") or "HSP_REPACK_FAILED",
            }

        logger.info(f"signing HAP with HSP packages: {signed_hap}")
        sign_failures: List[Dict[str, Any]] = []
        successful_sign_result: Optional[Dict[str, Any]] = None
        for key_password, keystore_password in self._password_candidates(signing):
            signed_hap.unlink(missing_ok=True)
            sign_cmd = self._build_hnp_sign_command(
                java,
                hap_sign_tool,
                unsigned_hap,
                signed_hap,
                signing,
                key_password,
                keystore_password,
            )
            sign_result = self._run_packaging_command(sign_cmd, "HSP_SIGN")
            if sign_result["success"] and signed_hap.exists():
                successful_sign_result = sign_result
                break
            sign_failures.append(sign_result)

        if successful_sign_result is None:
            combined_stdout = self._merge_outputs(
                pack_result.get("stdout"),
                *(failure.get("stdout") for failure in sign_failures),
            )
            combined_stderr = self._merge_outputs(
                pack_result.get("stderr"),
                *(failure.get("stderr") for failure in sign_failures),
            )
            last_failure = sign_failures[-1] if sign_failures else {}
            return {
                "success": False,
                "error_code": last_failure.get("error_code") or "HSP_SIGN_FAILED",
                "stdout": combined_stdout,
                "stderr": combined_stderr,
                "output_path": None,
            }

        combined_stdout = self._merge_outputs(
            pack_result.get("stdout"),
            successful_sign_result.get("stdout"),
        )
        combined_stderr = self._merge_outputs(
            pack_result.get("stderr"),
            successful_sign_result.get("stderr"),
        )
        if not self._hap_contains_hsp(signed_hap):
            return {
                "success": False,
                "error_code": "HSP_NOT_IN_HAP",
                "stdout": combined_stdout,
                "stderr": f"signed HAP does not contain shared_libs/*.hsp: {signed_hap}",
                "output_path": None,
            }

        return {
            "success": True,
            "error_code": None,
            "stdout": combined_stdout,
            "stderr": combined_stderr,
            "output_path": str(signed_hap),
            "artifact_source": "hsp_direct",
            "sign_status": "signed",
        }

    def _build_hap_with_hsp(
        self,
        build_mode: str,
        product: str,
        module_name: Optional[str],
        hsp_module_names: Optional[List[str]],
        is_clean: bool,
    ) -> Dict[str, Any]:
        base_result = self._run_base_hap_build_for_repack(
            build_mode,
            product,
            module_name,
            is_clean,
            "HSP",
        )
        if not base_result.get("success"):
            return base_result

        hsp_result = self._build_hsp_outputs(
            build_mode,
            product,
            hsp_module_names,
        )
        if not hsp_result.get("success"):
            return {
                **hsp_result,
                "stdout": self._merge_outputs(base_result.get("stdout"), hsp_result.get("stdout")),
                "stderr": self._merge_outputs(base_result.get("stderr"), hsp_result.get("stderr")),
                "output_path": None,
            }

        module_root = self._resolve_module_root(module_name)
        signing = self._resolve_repack_signing_config(product, "HSP")
        if not signing.get("success"):
            return {
                "success": False,
                "error_code": signing["error_code"],
                "stdout": self._merge_outputs(base_result.get("stdout"), hsp_result.get("stdout")),
                "stderr": self._merge_outputs(
                    base_result.get("stderr"),
                    hsp_result.get("stderr"),
                    signing["stderr"],
                ),
                "output_path": None,
            }

        result = self._repack_and_sign_hap_with_hsp(
            module_root,
            hsp_result["output_paths"],
            product,
            signing,
        )
        result["hsp_output_paths"] = [str(path) for path in hsp_result["output_paths"]]
        result["stdout"] = self._merge_outputs(
            base_result.get("stdout"),
            hsp_result.get("stdout"),
            result.get("stdout"),
        )
        result["stderr"] = self._merge_outputs(
            base_result.get("stderr"),
            hsp_result.get("stderr"),
            result.get("stderr"),
        )
        if result.get("success"):
            logger.info(f"HSP-integrated HAP build succeeded: {result['output_path']}")
        else:
            logger.error(f"HSP-integrated HAP build failed: {result.get('stderr', '')}")
        return result

    def build(
        self,
        target: str = "hap",
        build_mode: str = "debug",
        product: str = "default",
        module_name: Optional[str] = None,
        is_clean: bool = False,
        include_hsp: bool = False,
        hsp_module_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if target not in {"hap", "har", "hsp", "app", "hnp"}:
            return {
                "error_code": "INVALID_BUILD_TARGET",
                "stdout": "",
                "stderr": 'target must be one of "hap", "har", "hsp", "app", or "hnp"',
                "success": False,
                "output_path": None,
            }
        if target in {"har", "hsp"} and not module_name:
            return {
                "error_code": "MISSING_MODULE_NAME",
                "stdout": "",
                "stderr": f'module_name is required when target="{target}"',
                "success": False,
                "output_path": None,
            }

        validation_error = self._validate_build_config(target, build_mode, product, module_name)
        if validation_error is not None:
            return validation_error

        if target == "hnp":
            return self._build_hnp(build_mode, product, module_name, is_clean)
        if target == "hap" and include_hsp:
            return self._build_hap_with_hsp(
                build_mode,
                product,
                module_name,
                hsp_module_names,
                is_clean,
            )

        build_started_at = time.time()
        if is_clean:
            clean_result = self.clean(
                product=product,
                module_name=module_name if target in {"hap", "har", "hsp"} else None,
            )
            if not clean_result["success"]:
                return {
                    "success": False,
                    "error_code": clean_result.get("error_code", "CLEAN_FAILED"),
                    "stdout": clean_result.get("stdout", ""),
                    "stderr": clean_result.get("stderr", "clean failed"),
                    "output_path": None,
                }

        logger.info(f"build {target.upper()} for product={product}")
        args: List[str] = ["--no-daemon"]
        if target in {"hap", "har", "hsp"}:
            args.extend(["--mode", "module"])
        args.extend(["-p", f"product={product}", "-p", f"buildMode={build_mode}"])
        if target in {"har", "hsp"} and module_name:
            args.extend(["-p", f"module={module_name}"])
        args.extend(
            [
                {"hap": "assembleHap", "har": "assembleHar", "hsp": "assembleHsp", "app": "assembleApp"}[target],
                "--analyze=normal",
                "--parallel",
                "--incremental",
            ]
        )
        result = self._execute_command(args)
        if result["success"]:
            logged_output = None
            artifact_source = ""
            sign_status = "unknown"
            output_path = self._find_output_from_metadata(target, product, module_name, not_before=build_started_at)
            if output_path is not None:
                artifact_source = "metadata"
                sign_status = self._resolve_sign_status(output_path)
            if output_path is None:
                logged_output = self._extract_output_path_from_logs(
                    result.get("stdout", ""),
                    result.get("stderr", ""),
                    target,
                )
                output_path = self._extract_output_path_from_logs(
                    result.get("stdout", ""),
                    result.get("stderr", ""),
                    target,
                    not_before=build_started_at,
                )
                if output_path is not None:
                    artifact_source = "logs"
                    sign_status = self._resolve_sign_status(output_path)
            if output_path is None:
                output_path = self._find_build_output(
                    target,
                    build_mode,
                    product,
                    module_name,
                    not_before=build_started_at,
                )
                if output_path is not None:
                    artifact_source = "scan"
                    sign_status = self._resolve_sign_status(output_path)
            if output_path is None and logged_output is not None and not self._is_fresh_output(logged_output, build_started_at):
                return {
                    "success": False,
                    "error_code": "STALE_BUILD_ARTIFACT",
                    "stdout": result.get("stdout", ""),
                    "stderr": self._build_output_resolution_guidance(stale_logged_output=True),
                    "output_path": None,
                }
            if output_path is None:
                return {
                    "success": False,
                    "error_code": "BUILD_OUTPUT_NOT_FOUND",
                    "stdout": result.get("stdout", ""),
                    "stderr": self._build_output_resolution_guidance(),
                    "output_path": None,
                }
            if (
                target == "hap"
                and output_path is not None
                and "unsigned" in output_path.name.lower()
            ):
                fallback_result = self._run_sign_fallback(build_mode)
                if fallback_result["success"]:
                    output_path = Path(fallback_result["output_path"])
                    result["stdout"] = f"{result.get('stdout', '')}\n{fallback_result.get('stdout', '')}".strip()
                    result["stderr"] = f"{result.get('stderr', '')}\n{fallback_result.get('stderr', '')}".strip()
                    artifact_source = fallback_result.get("artifact_source", "sign_fallback")
                    sign_status = "signed"
                elif fallback_result.get("error_code") != "SIGN_FALLBACK_SCRIPT_MISSING":
                    return {
                        "success": False,
                        "error_code": fallback_result["error_code"],
                        "stdout": f"{result.get('stdout', '')}\n{fallback_result.get('stdout', '')}".strip(),
                        "stderr": (
                            f"{result.get('stderr', '')}\n{fallback_result.get('stderr', '')}"
                        ).strip(),
                        "output_path": None,
                    }
            result["output_path"] = str(output_path) if output_path else None
            result["artifact_source"] = artifact_source or None
            result["sign_status"] = sign_status
            logger.info(f"{target.upper()} build succeeded: {result['output_path']}")
        else:
            result["output_path"] = None
            logger.error(f"{target.upper()} build failed: {result['stderr']}")
        return result

    def _find_build_output(
        self,
        output_type: str,
        build_mode: str = "debug",
        product: str = "default",
        module_name: Optional[str] = None,
        not_before: Optional[float] = None,
    ) -> Optional[Path]:
        """Return the newest build artifact for the requested output type."""
        output_dirs = [
            self.project_path / "build",
            self.project_path / "entry" / "build",
        ]
        if module_name:
            output_dirs.append(self.project_path / module_name / "build")

        matches: List[Path] = []
        extension = f".{output_type}"
        for output_dir in output_dirs:
            if not output_dir.exists():
                continue
            matches.extend(output_dir.rglob(f"*{extension}"))

        if not_before is not None:
            matches = [path for path in matches if self._is_fresh_output(path, not_before)]

        if not matches:
            return None

        if module_name:
            narrowed = [
                path
                for path in matches
                if module_name.lower() in path.name.lower()
                or module_name.lower() in str(path.parent).lower()
            ]
            if narrowed:
                matches = narrowed

        matches.sort(
            key=lambda path: self._score_output_path(path, output_type, build_mode, product, module_name),
            reverse=True,
        )
        return matches[0]
