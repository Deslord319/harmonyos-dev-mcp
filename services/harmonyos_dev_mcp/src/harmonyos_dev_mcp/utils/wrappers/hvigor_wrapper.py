"""Wrapper around the DevEco hvigor build toolchain."""
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
    """hvigor build wrapper."""

    def __init__(self, project_path: str, deveco_path: Optional[str] = None):
        """Initialize the wrapper for a HarmonyOS project."""
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise ValueError(f"项目路径不存在: {project_path}")

        # 查找 DevEco Studio 路径（优先级：参数覆盖 > 已初始化配置 > 自动发现）
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

        # 楠岃瘉宸ュ叿瀛樺湪
        if not self.node_exe.exists():
            raise ValueError(f"鏈壘鍒?Node.js: {self.node_exe}")
        if not self.hvigorw_js.exists():
            raise ValueError(f"鏈壘鍒?hvigorw.js: {self.hvigorw_js}")
        if not self.sdk_root.exists():
            raise ValueError(f"鏈壘鍒?HarmonyOS SDK 鏍圭洰褰? {self.sdk_root}")
        if self.java_home and not self.java_home.exists():
            raise ValueError(f"鏈壘鍒?Java Home: {self.java_home}")

        logger.info(f"鍒濆鍖?HvigorWrapper")
        logger.info(f"  椤圭洰璺緞: {project_path}")
        logger.info(f"  DevEco 璺緞: {self.deveco_path}")
        logger.info(f"  Node.js: {self.node_exe}")
        logger.info(f"  hvigorw.js: {self.hvigorw_js}")
        logger.info(f"  SDK 鏍硅矾寰? {self.sdk_root}")
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

        fallback = Path(tempfile.gettempdir()) / "harmonyos_dev_mcp" / "hvigor_home"
        if self._is_writable_dir(fallback):
            logger.warning(
                f"椤圭洰鐩綍涓嶅彲鍐欙紝HVIGOR_USER_HOME 鍥為€€鍒颁复鏃剁洰褰? {fallback}"
            )
            return fallback

        raise PermissionError(
            f"HVIGOR_USER_HOME 涓嶅彲鍐欙紝椤圭洰璺緞涓庝复鏃剁洰褰曞潎涓嶅彲鐢? {preferred}, {fallback}"
        )

    def _find_deveco_studio(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """
        鏌ユ壘 DevEco Studio 瀹夎璺緞

        浼樺厛绾э細鍙傛暟 > Config > 鑷姩鍙戠幇
        """
        # 1. 浣跨敤浼犲叆鐨勮嚜瀹氫箟璺緞
        if custom_path:
            path = Path(custom_path)
            if Config._is_valid_deveco_path(path):
                return path

        # 2. 浣跨敤 Config 涓凡妫€娴嬬殑璺緞
        if Config.DEVECO_STUDIO_PATH:
            path = Path(Config.DEVECO_STUDIO_PATH)
            if Config._is_valid_deveco_path(path):
                return path

        # 3. 自动检测（使用 Config 的搜索逻辑）
        detected = Config._detect_deveco_studio_path()
        if detected:
            path = Path(detected)
            logger.info(f"鑷姩妫€娴嬪埌 DevEco Studio: {path}")
            return path

        for path in Config._get_deveco_search_paths():
            if Config._is_valid_deveco_path(path):
                logger.info(f"鑷姩妫€娴嬪埌 DevEco Studio: {path}")
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
        """纭繚local.properties閰嶇疆姝ｇ‘锛堜粎鐢ㄤ簬OpenHarmony椤圭洰锛?
        
        娉ㄦ剰: HarmonyOS椤圭洰锛坮untimeOS=HarmonyOS锛変笉璇诲彇local.properties锛?
        鑰屾槸閫氳繃DEVECO_SDK_HOME鐜鍙橀噺瀹氫綅SDK銆傝鏂规硶宸茬敱_execute_command涓?
        璁剧疆DEVECO_SDK_HOME鏇夸唬锛屼繚鐣欎緵鍙兘闇€瑕佺殑OpenHarmony椤圭洰浣跨敤銆?
        """
        local_props = self.project_path / "local.properties"
        # SDK璺緞搴旇鎸囧悜default鐩綍锛宧vigor浼氬湪瀛愮洰褰曚腑鏌ユ壘SDK缁勪欢
        sdk_dir = self.deveco_path / "sdk" / "default"
        nodejs_dir = self.deveco_path / "tools" / "node"

        # 璇诲彇鐜版湁閰嶇疆
        existing_config = {}
        if local_props.exists():
            with open(local_props, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key.strip()] = value.strip()

        # 鏇存柊閰嶇疆
        needs_update = False
        if existing_config.get('sdk.dir') != str(sdk_dir).replace('\\', '\\\\'):
            needs_update = True
        if existing_config.get('nodejs.dir') != str(nodejs_dir).replace('\\', '\\\\'):
            needs_update = True

        if needs_update:
            logger.info(f"鏇存柊local.properties閰嶇疆")
            with open(local_props, 'w', encoding='utf-8') as f:
                f.write("# This file is automatically generated by HarmonyOS MCP Server\n")
                f.write("# Do not modify this file manually\n\n")
                # 浣跨敤姝ｆ枩鏉犺矾寰勶紝杩欐槸璺ㄥ钩鍙扮殑鏍囧噯鏍煎紡
                sdk_path = str(sdk_dir).replace('\\', '/')
                nodejs_path = str(nodejs_dir).replace('\\', '/')
                f.write(f"sdk.dir={sdk_path}\n")
                f.write(f"nodejs.dir={nodejs_path}\n")
    
    def _execute_command(self, args: List[str], timeout: int = None) -> Dict[str, Any]:
        """
        鎵цhvigor鍛戒护

        Args:
            args: 鍛戒护鍙傛暟鍒楄〃锛堜笉鍖呭惈node鍜宧vigorw.js锛?
            timeout: 瓒呮椂鏃堕棿(绉?

        Returns:
            鍖呭惈returncode, stdout, stderr鐨勫瓧鍏?
        """
        # Windows 涓?hvigor daemon 浼氬湪鏋勫缓瀹屾垚鍚庨暱鏃堕棿闃诲杩涚▼閫€鍑猴紝
        # 鐩存帴瀵艰嚧 MCP 璋冪敤瓒呮椂锛屽洜姝ょ粺涓€绂佺敤 daemon銆?
        effective_args = list(args)
        if (
            platform.system() == "Windows"
            and "--no-daemon" not in effective_args
            and "--daemon" not in effective_args
        ):
            effective_args.append("--no-daemon")

        # 鏋勫缓瀹屾暣鍛戒护: node hvigorw.js [args]
        cmd = [str(self.node_exe), str(self.hvigorw_js)] + effective_args
        timeout = timeout or Config.BUILD_TIMEOUT

        logger.debug(f"鎵ц鏋勫缓鍛戒护: {' '.join(cmd)}")

        # 璁剧疆姝ｇ‘鐨?DEVECO_SDK_HOME 鐜鍙橀噺
        # hvigor 鐨?HarmonyOS SDK 瑙ｆ瀽娴佺▼:
        #   1. HarmonyOS 椤圭洰涓嶈鍙?local.properties锛坧roperty-get.js._readFile 杩斿洖绌猴級
        #   2. 閫氳繃 DEVECO_SDK_HOME 鐜鍙橀噺瀹氫綅 SDK 鏍圭洰褰?
        #   3. SDK scanner 鍦ㄨ鐩綍涓嬫悳绱?<瀛愮洰褰?/sdk-pkg.json 鏉ュ彂鐜?SDK 鐗堟湰
        #   4. 鍥犳 DEVECO_SDK_HOME 搴旀寚鍚?sdk/ 鐩綍锛堝叾涓嬫湁 default/sdk-pkg.json锛?
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
            # 瓒呮椂浜嗭紝璁板綍閿欒
            logger.error(f"鏋勫缓鍛戒护鎵ц瓒呮椂({timeout}绉?")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'鏋勫缓瓒呮椂({timeout}绉?',
                'success': False
            }
        except Exception as e:
            logger.error(f"鏋勫缓鍛戒护鎵ц澶辫触: {e}")
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
        缁堟杩涚▼鍙婂叾鎵€鏈夊瓙杩涚▼

        Args:
            pid: 杩涚▼ID
        """
        try:
            if platform.system() == 'Windows':
                # 鍦?Windows 涓婁娇鐢?taskkill 缁堟杩涚▼鏍?
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True,
                    timeout=5
                )
            else:
                # 鍦?Unix 绯荤粺涓婁娇鐢?kill
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception as e:
            logger.error(f"缁堟杩涚▼鏍戝け璐? {e}")
    
    def clean(self, product: str = "default") -> Dict[str, Any]:
        """
        娓呯悊鏋勫缓浜х墿

        Args:
            product: 浜у搧鍚嶇О锛堝搧绫伙級

        Returns:
            鏋勫缓缁撴灉
        """
        logger.info("娓呯悊鏋勫缓浜х墿")
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
            logger.info("娓呯悊鎴愬姛")
        else:
            logger.error(f"娓呯悊澶辫触: {result['stderr']}")

        return result

    def build_har(self, module_name: str, product: str = "default") -> Dict[str, Any]:
        """
        鏋勫缓HAR鍖?

        Args:
            module_name: 妯″潡鍚嶇О
            product: 浜у搧鍚嶇О锛堝搧绫伙級

        Returns:
            鏋勫缓缁撴灉,鍖呭惈HAR鍖呰矾寰?
        """
        logger.info(f"鏋勫缓HAR鍖?(妯″潡: {module_name}, 浜у搧: {product})")

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
            # 鏌ユ壘鐢熸垚鐨凥AR鍖?
            har_path = self._find_build_output('har', module_name)
            result['har_path'] = str(har_path) if har_path else None
            logger.info(f"HAR鍖呮瀯寤烘垚鍔? {result['har_path']}")
        else:
            logger.error(f"HAR鍖呮瀯寤哄け璐? {result['stderr']}")

        return result

    def build_hap(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        """
        鏋勫缓HAP鍖?

        Args:
            build_mode: 鏋勫缓妯″紡 (debug/release)
            product: 浜у搧鍚嶇О锛堝搧绫伙級

        Returns:
            鏋勫缓缁撴灉,鍖呭惈HAP鍖呰矾寰?
        """
        logger.info(f"鏋勫缓HAP鍖?(妯″紡: {build_mode}, 浜у搧: {product})")

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
            # 鏌ユ壘鐢熸垚鐨凥AP鍖?
            hap_path = self._find_build_output('hap', build_mode)
            result['hap_path'] = str(hap_path) if hap_path else None
            logger.info(f"HAP鍖呮瀯寤烘垚鍔? {result['hap_path']}")
        else:
            logger.error(f"HAP鍖呮瀯寤哄け璐? {result['stderr']}")
        
        return result

    def build_app(self, build_mode: str = "debug", product: str = "default") -> Dict[str, Any]:
        """
        鏋勫缓APP鍖咃紙鏈€缁堜笂鏋跺寘锛?

        Args:
            build_mode: 鏋勫缓妯″紡 (debug/release)
            product: 浜у搧鍚嶇О锛堝搧绫伙級

        Returns:
            鏋勫缓缁撴灉,鍖呭惈APP鍖呰矾寰?
        """
        logger.info(f"鏋勫缓APP鍖?(妯″紡: {build_mode}, 浜у搧: {product})")

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
            # 鏌ユ壘鐢熸垚鐨凙PP鍖?
            app_path = self._find_build_output('app', build_mode)
            result['app_path'] = str(app_path) if app_path else None
            logger.info(f"APP鍖呮瀯寤烘垚鍔? {result['app_path']}")
        else:
            logger.error(f"APP鍖呮瀯寤哄け璐? {result['stderr']}")

        return result

    def _find_build_output(self, output_type: str, search_key: str = "") -> Optional[Path]:
        """
        鏌ユ壘鏋勫缓杈撳嚭鏂囦欢

        Args:
            output_type: 杈撳嚭绫诲瀷 (har/hap/app)
            search_key: 鎼滅储鍏抽敭瀛楋紙妯″潡鍚嶆垨鏋勫缓妯″紡锛?

        Returns:
            杈撳嚭鏂囦欢璺緞
        """
        # 甯歌鐨勮緭鍑鸿矾寰?
        output_dirs = [
            self.project_path / 'build',
            self.project_path / 'entry' / 'build',
        ]

        # 濡傛灉鏄疕AR锛岃繕瑕佹悳绱㈡ā鍧楃洰褰?
        if output_type == 'har' and search_key:
            output_dirs.append(self.project_path / search_key / 'build')

        for output_dir in output_dirs:
            if not output_dir.exists():
                continue

            # 鏌ユ壘瀵瑰簲绫诲瀷鐨勬枃浠?
            extension = f'.{output_type}'
            for file in output_dir.rglob(f'*{extension}'):
                return file

        return None

    def get_build_info(self) -> Dict[str, Any]:
        """
        鑾峰彇鏋勫缓淇℃伅

        Returns:
            鏋勫缓淇℃伅瀛楀吀
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

