r"""
hvigor构建工具封装

说明:
- 使用 DevEco Studio 自带的 hvigorw.js 进行构建
- 需要配合 DevEco Studio 自带的 Node.js 使用
- 支持通过环境变量 DEVECO_STUDIO_PATH 配置 DevEco Studio 路径
"""
import subprocess
import os
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from harmonyos_dev_mcp.config import Config


class HvigorWrapper:
    """hvigor构建系统封装类"""

    def __init__(self, project_path: str, deveco_path: Optional[str] = None):
        """
        初始化hvigor包装器

        Args:
            project_path: HarmonyOS项目路径
            deveco_path: DevEco Studio安装路径（可选，优先使用环境变量或自动检测）
        """
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise ValueError(f"项目路径不存在: {project_path}")

        # 查找DevEco Studio路径（优先级：参数覆盖 > 已初始化配置 > 自动发现）
        self.deveco_path = self._find_deveco_studio(deveco_path)
        if not self.deveco_path:
            raise ValueError(
                "未找到可用的 DevEco Studio 安装路径。请确认本机已安装 DevEco Studio，或显式传入 deveco_path。"
            )

        self.node_exe = self._find_node_executable()
        self.hvigorw_js = self._find_hvigor_wrapper()
        self.sdk_root = self._find_sdk_root()
        self.java_home = self._find_java_home()
        self.hvigor_user_home = self._resolve_hvigor_user_home()

        # 验证工具存在
        if not self.node_exe.exists():
            raise ValueError(f"未找到 Node.js: {self.node_exe}")
        if not self.hvigorw_js.exists():
            raise ValueError(f"未找到 hvigorw.js: {self.hvigorw_js}")
        if not self.sdk_root.exists():
            raise ValueError(f"未找到 HarmonyOS SDK 根目录: {self.sdk_root}")
        if self.java_home and not self.java_home.exists():
            raise ValueError(f"未找到 Java Home: {self.java_home}")

        logger.info(f"初始化 HvigorWrapper")
        logger.info(f"  项目路径: {project_path}")
        logger.info(f"  DevEco 路径: {self.deveco_path}")
        logger.info(f"  Node.js: {self.node_exe}")
        logger.info(f"  hvigorw.js: {self.hvigorw_js}")
        logger.info(f"  SDK 根路径: {self.sdk_root}")
        if self.java_home:
            logger.info(f"  JAVA_HOME: {self.java_home}")
        logger.info(f"  HVIGOR_USER_HOME: {self.hvigor_user_home}")

    @staticmethod
    def _is_writable_dir(path: Path) -> bool:
        """Check whether a directory is writable by creating a probe file."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def _resolve_hvigor_user_home(self) -> Path:
        """
        Pick a writable HVIGOR_USER_HOME.

        Preferred location is project-local `.hvigor/mcp-user-home`.
        Fallback uses system temp directory when project path is not writable.
        """
        preferred = self.project_path / ".hvigor" / "mcp-user-home"
        if self._is_writable_dir(preferred):
            return preferred

        fallback = Path(tempfile.gettempdir()) / "harmonyos_mcp" / "hvigor_home"
        if self._is_writable_dir(fallback):
            logger.warning(
                f"项目目录不可写，HVIGOR_USER_HOME 回退到临时目录: {fallback}"
            )
            return fallback

        raise PermissionError(
            f"HVIGOR_USER_HOME 不可写，项目路径与临时目录均不可用: {preferred}, {fallback}"
        )

    def _find_deveco_studio(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """
        查找 DevEco Studio 安装路径

        优先级：参数 > Config > 自动发现
        """
        # 1. 使用传入的自定义路径
        if custom_path:
            path = Path(custom_path)
            if Config._is_valid_deveco_path(path):
                return path

        # 2. 使用 Config 中已检测的路径
        if Config.DEVECO_STUDIO_PATH:
            path = Path(Config.DEVECO_STUDIO_PATH)
            if Config._is_valid_deveco_path(path):
                return path

        # 3. 自动检测（使用 Config 的搜索逻辑）
        detected = Config._detect_deveco_studio_path()
        if detected:
            path = Path(detected)
            logger.info(f"自动检测到 DevEco Studio: {path}")
            return path

        for path in Config._get_deveco_search_paths():
            if Config._is_valid_deveco_path(path):
                logger.info(f"自动检测到 DevEco Studio: {path}")
                return path

        return None

    def _find_node_executable(self) -> Path:
        if Config.NODE_PATH and Path(Config.NODE_PATH).exists():
            return Path(Config.NODE_PATH)

        # Keep discovery platform-agnostic. Test fixtures and mixed host layouts
        # can provide macOS/Linux style `node` paths even on Windows runners.
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
            # Windows/Linux: JBR directly under DevEco
            self.deveco_path / "jbr",
            # Linux: JBR with Home subdirectory
            self.deveco_path / "jbr" / "Contents" / "Home",
            # macOS: JBR inside Contents
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

    def _ensure_local_properties(self):
        """确保local.properties配置正确（仅用于OpenHarmony项目）
        
        注意: HarmonyOS项目（runtimeOS=HarmonyOS）不读取local.properties，
        而是通过DEVECO_SDK_HOME环境变量定位SDK。该方法已由_execute_command中
        设置DEVECO_SDK_HOME替代，保留供可能需要的OpenHarmony项目使用。
        """
        local_props = self.project_path / "local.properties"
        # SDK路径应该指向default目录，hvigor会在子目录中查找SDK组件
        sdk_dir = self.deveco_path / "sdk" / "default"
        nodejs_dir = self.deveco_path / "tools" / "node"

        # 读取现有配置
        existing_config = {}
        if local_props.exists():
            with open(local_props, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key.strip()] = value.strip()

        # 更新配置
        needs_update = False
        if existing_config.get('sdk.dir') != str(sdk_dir).replace('\\', '\\\\'):
            needs_update = True
        if existing_config.get('nodejs.dir') != str(nodejs_dir).replace('\\', '\\\\'):
            needs_update = True

        if needs_update:
            logger.info(f"更新local.properties配置")
            with open(local_props, 'w', encoding='utf-8') as f:
                f.write("# This file is automatically generated by HarmonyOS MCP Server\n")
                f.write("# Do not modify this file manually\n\n")
                # 使用正斜杠路径，这是跨平台的标准格式
                sdk_path = str(sdk_dir).replace('\\', '/')
                nodejs_path = str(nodejs_dir).replace('\\', '/')
                f.write(f"sdk.dir={sdk_path}\n")
                f.write(f"nodejs.dir={nodejs_path}\n")
    
    def _execute_command(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """
        执行hvigor命令

        Args:
            args: 命令参数列表（不包含node和hvigorw.js）
            timeout: 超时时间(秒)

        Returns:
            包含returncode, stdout, stderr的字典
        """
        # Windows 下 hvigor daemon 会在构建完成后长时间阻塞进程退出，
        # 直接导致 MCP 调用超时，因此统一禁用 daemon。
        effective_args = list(args)
        if (
            platform.system() == "Windows"
            and "--no-daemon" not in effective_args
            and "--daemon" not in effective_args
        ):
            effective_args.append("--no-daemon")

        # 构建完整命令: node hvigorw.js [args]
        cmd = [str(self.node_exe), str(self.hvigorw_js)] + effective_args
        timeout = timeout or Config.BUILD_TIMEOUT

        logger.debug(f"执行构建命令: {' '.join(cmd)}")

        # 设置正确的 DEVECO_SDK_HOME 环境变量
        # hvigor 的 HarmonyOS SDK 解析流程:
        #   1. HarmonyOS 项目不读取 local.properties（property-get.js._readFile 返回空）
        #   2. 通过 DEVECO_SDK_HOME 环境变量定位 SDK 根目录
        #   3. SDK scanner 在该目录下搜索 <子目录>/sdk-pkg.json 来发现 SDK 版本
        #   4. 因此 DEVECO_SDK_HOME 应指向 sdk/ 目录（其下有 default/sdk-pkg.json）
        env = os.environ.copy()
        env['DEVECO_SDK_HOME'] = str(self.sdk_root)
        env['HVIGOR_USER_HOME'] = str(self.hvigor_user_home)
        if self.java_home:
            env['JAVA_HOME'] = str(self.java_home)
            env['PATH'] = f"{self.java_home / 'bin'}{os.pathsep}{env.get('PATH', '')}"

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
                close_fds=True
            )

            command_success = result.returncode == 0 and not self._has_build_failure_output(
                result.stdout, result.stderr
            )

            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': command_success
            }
        except subprocess.TimeoutExpired:
            # 超时了，记录错误
            logger.error(f"构建命令执行超时({timeout}秒)")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'构建超时({timeout}秒)',
                'success': False
            }
        except Exception as e:
            logger.error(f"构建命令执行失败: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }

    @staticmethod
    def _has_build_failure_output(stdout: str, stderr: str) -> bool:
        combined = f"{stdout}\n{stderr}".upper()
        return 'BUILD FAILED' in combined or 'COMPILE RESULT:FAIL' in combined

    def _kill_process_tree(self, pid: int):
        """
        终止进程及其所有子进程

        Args:
            pid: 进程ID
        """
        try:
            if platform.system() == 'Windows':
                # 在 Windows 上使用 taskkill 终止进程树
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True,
                    timeout=5
                )
            else:
                # 在 Unix 系统上使用 kill
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception as e:
            logger.error(f"终止进程树失败: {e}")
    
    def clean(self, product: str = "default") -> Dict[str, Any]:
        """
        清理构建产物

        Args:
            product: 产品名称（品类）

        Returns:
            构建结果
        """
        logger.info("清理构建产物")
        args = [
            '--no-daemon',
            '--sync',
            '-p', f'product={product}',
            '--analyze=normal',
            '--parallel',
            '--incremental'
        ]
        result = self._execute_command(args)

        if result['success']:
            logger.info("清理成功")
        else:
            logger.error(f"清理失败: {result['stderr']}")

        return result

    def build_har(self, module_name: str, product: str = "default") -> Dict[str, Any]:
        """
        构建HAR包

        Args:
            module_name: 模块名称
            product: 产品名称（品类）

        Returns:
            构建结果,包含HAR包路径
        """
        logger.info(f"构建HAR包 (模块: {module_name}, 产品: {product})")

        args = [
            '--no-daemon',
            '--mode', 'module',
            '-p', f'product={product}',
            '-p', f'module={module_name}',
            'assembleHar',
            '--analyze=normal',
            '--parallel',
            '--incremental'
        ]

        result = self._execute_command(args)

        if result['success']:
            # 查找生成的HAR包
            har_path = self._find_build_output('har', module_name)
            result['har_path'] = str(har_path) if har_path else None
            logger.info(f"HAR包构建成功: {result['har_path']}")
        else:
            logger.error(f"HAR包构建失败: {result['stderr']}")

        return result

    def build_hap(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        """
        构建HAP包

        Args:
            build_mode: 构建模式 (debug/release)
            product: 产品名称（品类）

        Returns:
            构建结果,包含HAP包路径
        """
        logger.info(f"构建HAP包 (模式: {build_mode}, 产品: {product})")

        args = [
            '--no-daemon',
            '--mode', 'module',
            '-p', f'product={product}',
            'assembleHap',
            '--analyze=normal',
            '--parallel',
            '--incremental'
        ]

        result = self._execute_command(args)

        if result['success']:
            # 查找生成的HAP包
            hap_path = self._find_build_output('hap', build_mode)
            result['hap_path'] = str(hap_path) if hap_path else None
            logger.info(f"HAP包构建成功: {result['hap_path']}")
        else:
            logger.error(f"HAP包构建失败: {result['stderr']}")
        
        return result

    def build_app(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        """
        构建APP包（最终上架包）

        Args:
            build_mode: 构建模式 (debug/release)
            product: 产品名称（品类）

        Returns:
            构建结果,包含APP包路径
        """
        logger.info(f"构建APP包 (模式: {build_mode}, 产品: {product})")

        args = [
            '--no-daemon',
            '-p', f'product={product}',
            'assembleApp',
            '--analyze=normal',
            '--parallel',
            '--incremental'
        ]

        result = self._execute_command(args)

        if result['success']:
            # 查找生成的APP包
            app_path = self._find_build_output('app', build_mode)
            result['app_path'] = str(app_path) if app_path else None
            logger.info(f"APP包构建成功: {result['app_path']}")
        else:
            logger.error(f"APP包构建失败: {result['stderr']}")

        return result

    def _find_build_output(self, output_type: str, search_key: str = "") -> Optional[Path]:
        """
        查找构建输出文件

        Args:
            output_type: 输出类型 (har/hap/app)
            search_key: 搜索关键字（模块名或构建模式）

        Returns:
            输出文件路径
        """
        # 常见的输出路径
        output_dirs = [
            self.project_path / 'build',
            self.project_path / 'entry' / 'build',
        ]

        # 如果是HAR，还要搜索模块目录
        if output_type == 'har' and search_key:
            output_dirs.append(self.project_path / search_key / 'build')

        for output_dir in output_dirs:
            if not output_dir.exists():
                continue

            # 查找对应类型的文件
            extension = f'.{output_type}'
            for file in output_dir.rglob(f'*{extension}'):
                return file

        return None

    def get_build_info(self) -> Dict[str, Any]:
        """
        获取构建信息

        Returns:
            构建信息字典
        """
        info = {
            'project_path': str(self.project_path),
            'deveco_path': str(self.deveco_path),
            'node_exe': str(self.node_exe),
            'hvigorw_js': str(self.hvigorw_js),
            'has_build_profile': (self.project_path / 'build-profile.json5').exists(),
            'has_local_properties': (self.project_path / 'local.properties').exists(),
        }

        return info
