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
        if lowered_name.endswith(".hap"):
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

    def build(
        self,
        target: str = "hap",
        build_mode: str = "debug",
        product: str = "default",
        module_name: Optional[str] = None,
        is_clean: bool = False,
    ) -> Dict[str, Any]:
        if target not in {"hap", "har", "app"}:
            return {
                "error_code": "INVALID_BUILD_TARGET",
                "stdout": "",
                "stderr": 'target must be one of "hap", "har", or "app"',
                "success": False,
                "output_path": None,
            }
        if target == "har" and not module_name:
            return {
                "error_code": "MISSING_MODULE_NAME",
                "stdout": "",
                "stderr": 'module_name is required when target="har"',
                "success": False,
                "output_path": None,
            }

        validation_error = self._validate_build_config(target, build_mode, product, module_name)
        if validation_error is not None:
            return validation_error

        build_started_at = time.time()
        if is_clean:
            clean_result = self.clean(product=product, module_name=module_name if target in {"hap", "har"} else None)
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
        if target in {"hap", "har"}:
            args.extend(["--mode", "module"])
        args.extend(["-p", f"product={product}", "-p", f"buildMode={build_mode}"])
        if target == "har" and module_name:
            args.extend(["-p", f"module={module_name}"])
        args.extend(
            [
                {"hap": "assembleHap", "har": "assembleHar", "app": "assembleApp"}[target],
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
                    "stderr": (
                        "build output path resolved to an existing artifact, but it was not generated by the current build"
                    ),
                    "output_path": None,
                }
            if output_path is None:
                return {
                    "success": False,
                    "error_code": "BUILD_OUTPUT_NOT_FOUND",
                    "stdout": result.get("stdout", ""),
                    "stderr": "build succeeded but no fresh output artifact could be resolved for the current run",
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
