"""
HarmonyOS编译辅助工具 - 文件读取、脚本写入、脚本执行

职责：
- 读取项目构建文件供远端AI分析
- 写入AI生成的编译脚本
- 执行编译脚本并返回结果

不包含：
- 任何分析逻辑（由远端AI完成）
- 任何脚本生成逻辑（由远端AI完成）
"""
import os
import shutil
import subprocess
import functools
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import time


class CompileEnvironment:
    """编译环境检测 - 获取HarmonyOS SDK和编译器信息"""
    
    def __init__(self):
        self.sdk_root = os.getenv('HARMONYOS_SDK_PATH') or os.getenv('OHOS_SDK_ROOT')
        self.deveco_path = os.getenv('DEVECO_STUDIO_PATH')
        self.hdc_path = os.getenv('HDC_PATH')
        
    def get_sdk_path(self) -> Optional[str]:
        """获取SDK路径"""
        if self.sdk_root:
            return self.sdk_root
        
        # 尝试自动检测
        possible_paths = [
            str(Path.home() / 'harmonyos' / 'sdk' / 'default'),
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def get_compiler_path(self, arch: str = 'aarch64') -> str:
        """获取编译器路径"""
        sdk_path = self.get_sdk_path()
        if not sdk_path:
            return f'{arch}-unknown-linux-ohos-clang'
        
        arch_map = {
            'aarch64': 'aarch64-unknown-linux-ohos-clang',
            'armv7': 'armv7-unknown-linux-ohos-clang',
            'x86_64': 'x86_64-unknown-linux-ohos-clang',
        }
        
        compiler_name = arch_map.get(arch, f'{arch}-unknown-linux-ohos-clang')
        compiler_path = Path(sdk_path) / 'openharmony' / 'native' / 'llvm' / 'bin' / compiler_name
        
        return str(compiler_path) if compiler_path.exists() else compiler_name
    
    def get_sysroot_path(self) -> str:
        """获取sysroot路径"""
        sdk_path = self.get_sdk_path()
        if not sdk_path:
            return ''
        
        sysroot = Path(sdk_path) / 'openharmony' / 'native' / 'sysroot'
        return str(sysroot) if sysroot.exists() else ''
    
    def get_cmake_path(self) -> str:
        """获取HarmonyOS工具链自带的cmake路径"""
        sdk_path = self.get_sdk_path()
        if not sdk_path:
            return ''

        cmake_path = Path(sdk_path) / 'openharmony' / 'native' / 'build-tools' / 'cmake' / 'bin' / 'cmake'
        return str(cmake_path) if cmake_path.exists() else ""

    def get_toolchain_tools(self) -> Dict[str, str]:
        """获取工具链内置构建工具路径"""
        tools: Dict[str, str] = {}
        cmake = self.get_cmake_path()
        if cmake:
            tools['cmake'] = cmake
        return tools

    def get_host_tools(self) -> Dict[str, str]:
        """获取主机侧构建工具路径（来自PATH）"""
        candidates = [
            'make', 'ninja', 'gn', 'perl', 'python3', 'pkg-config',
            'autoconf', 'automake', 'libtool', 'm4'
        ]
        tools: Dict[str, str] = {}
        for name in candidates:
            path = shutil.which(name)
            if path:
                tools[name] = path
        return tools

    def get_environment_info(self, target_arch: str = 'aarch64') -> Dict[str, Any]:
        """获取完整的环境信息"""
        return {
            'sdk_path': self.get_sdk_path(),
            'compiler': self.get_compiler_path(target_arch),
            'cxx_compiler': self.get_compiler_path(target_arch).replace('-clang', '-clang++'),
            'sysroot': self.get_sysroot_path(),
            'cmake': self.get_cmake_path(),
            'tools': {
                'toolchain': self.get_toolchain_tools(),
                'host': self.get_host_tools()
            },
            'target_arch': target_arch
        }


class BuildFileReader:
    """读取项目构建文件供远端AI分析"""
    
    # 需要读取的构建文件模式
    BUILD_FILE_PATTERNS = [
        'CMakeLists.txt',
        'configure',
        'configure.ac',
        'Makefile',
        'Makefile.in',
        'meson.build',
        'setup.py',
        'build.py',
        'build.gradle',
        'pom.xml',
        'Cargo.toml',
        'go.mod',
        'Configure',
        'BUILD.gn',   # GN build
    ]
    
    def read_project_files(self, project_dir: str, max_file_size: int = 100000) -> Dict[str, Any]:
        """
        读取项目的构建文件
        
        Args:
            project_dir: 项目目录
            max_file_size: 最大文件大小（字节），超过则截断
        
        Returns:
            {
                "files": {文件名: 内容},
                "structure": "目录结构",
                "special_dirs": [特殊目录列表]
            }
        """
        project_path = Path(project_dir)
        result = {
            'files': {},
            'structure': '',
            'special_dirs': []
        }
        
        if not project_path.exists():
            logger.warning(f"项目目录不存在: {project_dir}")
            return result
        
        # 读取构建文件
        for pattern in self.BUILD_FILE_PATTERNS:
            file_path = project_path / pattern
            if file_path.exists() and file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size:
                        content = f"[文件过大 {file_size} 字节，已截断前 {max_file_size} 字节]\n"
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content += f.read(max_file_size)
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    
                    result['files'][pattern] = content
                    logger.info(f"读取构建文件: {pattern} ({file_size} 字节)")
                except Exception as e:
                    logger.warning(f"读取文件失败 {pattern}: {e}")
        
        # 检测特殊目录（可能包含构建配置）
        special_dirs = ['cmake', 'Configurations', 'build', 'config', 'm4']
        for dir_name in special_dirs:
            dir_path = project_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                result['special_dirs'].append(dir_name)
        
        # 生成目录结构（仅前两层）
        try:
            structure_lines = [f"{project_path.name}/"]
            for item in sorted(project_path.iterdir()):
                if item.is_dir():
                    structure_lines.append(f"  {item.name}/")
                else:
                    structure_lines.append(f"  {item.name}")
            result['structure'] = '\n'.join(structure_lines[:50])  # 限制50行
        except Exception as e:
            logger.warning(f"生成目录结构失败: {e}")
        
        return result


class ScriptWriter:
    """写入AI生成的编译脚本"""
    
    def write_script(self, project_dir: str, script_content: str, 
                    script_name: str = 'compile_harmonyos.sh') -> Dict[str, Any]:
        """
        写入编译脚本文件并设置执行权限
        
        Args:
            project_dir: 项目目录
            script_content: 脚本内容（由AI生成）
            script_name: 脚本文件名
        
        Returns:
            {
                "success": bool,
                "script_path": str,
                "message": str
            }
        """
        try:
            project_path = Path(project_dir)
            if not project_path.exists():
                return {
                    'success': False,
                    'message': f"项目目录不存在: {project_dir}"
                }
            
            script_path = project_path / script_name
            
            # 写入脚本
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 设置执行权限
            os.chmod(script_path, 0o755)
            
            logger.info(f"编译脚本已写入: {script_path}")
            
            return {
                'success': True,
                'script_path': str(script_path),
                'message': f"脚本已写入: {script_path}"
            }
        except Exception as e:
            logger.error(f"写入脚本失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"写入脚本失败: {str(e)}"
            }


class ScriptExecutor:
    """执行编译脚本并捕获输出"""
    
    def execute(self, script_path: str, cwd: str = None, 
               timeout: int = 1800) -> Dict[str, Any]:
        """
        执行编译脚本
        
        Args:
            script_path: 脚本文件路径
            cwd: 工作目录（默认为脚本所在目录）
            timeout: 超时时间（秒）
        
        Returns:
            {
                "success": bool,
                "exit_code": int,
                "stdout": str,
                "stderr": str,
                "duration": float,
                "message": str
            }
        """
        script_file = Path(script_path)
        
        if not script_file.exists():
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f"脚本文件不存在: {script_path}",
                'duration': 0,
                'message': f"脚本文件不存在: {script_path}"
            }
        
        # 默认工作目录为脚本所在目录
        if cwd is None:
            cwd = str(script_file.parent)
        
        logger.info(f"开始执行编译脚本: {script_path}")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['bash', str(script_path)],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            logger.info(f"脚本执行完成，返回码: {result.returncode}，耗时: {duration:.2f}秒")
            
            return {
                'success': success,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'message': f"执行{'成功' if success else '失败'}，返回码: {result.returncode}"
            }
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"脚本执行超时: {timeout}秒")
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': f"执行超时（{timeout}秒）",
                'duration': duration,
                'message': f"执行超时（{timeout}秒）"
            }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"脚本执行异常: {e}", exc_info=True)
            return {
                'success': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': duration,
                'message': f"执行异常: {str(e)}"
            }



class CompileLibraryManager:
    """三方库编译管理器 - 处理库拉取、构建系统分析、编译等操作"""
    
    def __init__(self, tools_dir: str = None):
        """
        初始化编译库管理器
        
        Args:
            tools_dir: HarmonyOS CommandLine Tools 目录路径
        """
        self.tools_dir = tools_dir or os.path.join(os.getcwd(), "harmonyos_commandline_tools")
        logger.info(f"初始化 CompileLibraryManager，工具目录: {self.tools_dir}")

    # ========================================================================
    # 三方库鸿蒙化编译相关方法
    # ========================================================================

    def check_wsl_available(self) -> Dict[str, Any]:
        """
        检查当前系统是否可用 WSL 环境

        Returns:
            检查结果与提示信息
        """
        import platform
        
        system = platform.system()
        
        if system != "Windows":
            return {
                "status": "not_windows",
                "message": f"当前系统 {system}，无需使用 WSL",
                "can_compile": True,
            }

        # Windows 系统检查 WSL
        try:
            result = subprocess.run(
                ["wsl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {
                    "status": "available",
                    "message": "检测到 WSL，可在 WSL 中执行鸿蒙化编译",
                    "can_compile": True,
                    "wsl_version": result.stdout.strip(),
                }
        except Exception as e:
            logger.debug(f"WSL 检查失败: {e}")

        return {
            "status": "missing",
            "message": "Windows 系统检测不到 WSL，请先安装 WSL 环境后再进行鸿蒙化交叉编译",
            "can_compile": False,
            "action": "install_wsl",
            "guidance": "请参考 https://learn.microsoft.com/zh-cn/windows/wsl/install",
        }

    def check_harmonyos_compiler_tools(self, tools_dir: str = "./harmonyos_commandline_tools") -> Dict[str, Any]:
        """
        检查 HarmonyOS Command Line Tools 是否已安装

        Args:
            tools_dir: HarmonyOS CommandLine Tools 所在目录

        Returns:
            检查结果
        """
        abs_tools_dir = os.path.abspath(tools_dir)
        
        if not os.path.exists(abs_tools_dir):
            return {
                "status": "missing",
                "message": f"HarmonyOS CommandLine Tools 目录不存在: {abs_tools_dir}",
                "can_compile": False,
                "action": "download_and_extract",
                "guidance": "请从官方网站下载 HarmonyOS Command Line Tool 并解压到指定目录",
                "doc": "https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-commandline-get",
            }

        return {
            "status": "present",
            "message": f"检测到 HarmonyOS CommandLine Tools: {abs_tools_dir}",
            "can_compile": True,
            "tools_dir": abs_tools_dir,
        }

    def clone_library(self, repo_url: str, local_path: str, version: str = None) -> Dict[str, Any]:
        """
        拉取三方库代码仓库并切换到指定版本

        Args:
            repo_url: 仓库 URL (git/https)
            local_path: 本地存放路径
            version: 可选，指定版本（tag/branch/commit），如 "v1.0.0" 或 "main"
                    如果tag/branch不存在，自动fallback到全量clone

        Returns:
            拉取结果，包含success、本地路径、实际拉取的版本等信息
        """
        logger.info(f"开始拉取三方库: {repo_url} -> {local_path} (版本: {version or 'default'})")
        
        # 确保本地目录存在
        parent_dir = os.path.dirname(os.path.abspath(local_path))
        os.makedirs(parent_dir, exist_ok=True)
        
        # 检查是否已存在
        if os.path.exists(local_path):
            return {
                "success": False,
                "error": f"目录已存在: {local_path}，请先删除或使用其他路径",
            }

        try:
            # 如果指定了版本，先尝试用浅克隆
            if version:
                logger.info(f"尝试使用浅克隆指定版本: {version}")
                clone_cmd = ["git", "clone", "--depth", "1", "--branch", version, repo_url, local_path]
                
                try:
                    result = subprocess.run(
                        clone_cmd,
                        capture_output=True,
                        text=True,
                        timeout=60  # 浅克隆应该快速失败
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"成功拉取三方库 (版本: {version}): {local_path}")
                        return {
                            "success": True,
                            "repo_url": repo_url,
                            "local_path": os.path.abspath(local_path),
                            "version": version,
                            "shallow_clone": True,
                        }
                    else:
                        # 版本不存在或网络问题，尝试全量clone
                        error_msg = result.stderr.strip() or result.stdout.strip()
                        logger.warning(f"指定版本克隆失败: {error_msg}，尝试全量clone")
                except subprocess.TimeoutExpired:
                    logger.warning(f"指定版本克隆超时，尝试全量clone")
                except Exception as e:
                    logger.warning(f"指定版本克隆异常: {e}，尝试全量clone")
            
            # 全量clone（没有指定版本，或者指定版本克隆失败）
            logger.info(f"执行全量clone: {repo_url}")
            clone_cmd = ["git", "clone", repo_url, local_path]
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"成功拉取三方库: {local_path}")
                return {
                    "success": True,
                    "repo_url": repo_url,
                    "local_path": os.path.abspath(local_path),
                    "version": version or "default",
                    "shallow_clone": False,
                    "note": "使用全量clone" if version else "默认clone",
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"全量clone失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "git clone操作超时 (300秒)，请检查网络连接",
            }
        except Exception as e:
            logger.error(f"克隆异常: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def analyze_build_system(self, project_dir: str) -> Dict[str, Any]:
        """
        分析项目的构建系统类型

        Args:
            project_dir: 项目目录

        Returns:
            构建系统分析结果
        """
        logger.info(f"分析项目构建系统: {project_dir}")
        
        if not os.path.exists(project_dir):
            return {
                "success": False,
                "error": f"项目目录不存在: {project_dir}",
            }

        build_systems = {}
        
        # 检查各种构建系统文件
        build_system_markers = {
            "GN": ["BUILD.gn", "build.gn"],
            "CMake": ["CMakeLists.txt"],
            "Makefile": ["Makefile", "makefile", "GNUmakefile"],
            "Autotools": ["configure.ac", "Makefile.am", "configure"],
            "Meson": ["meson.build"],
            "Gradle": ["build.gradle", "build.gradle.kts"],
            "Cargo": ["Cargo.toml"],
        }

        for build_system, markers in build_system_markers.items():
            for marker in markers:
                if os.path.exists(os.path.join(project_dir, marker)):
                    build_systems[build_system] = marker
                    break

        if not build_systems:
            return {
                "success": True,
                "detected_systems": [],
                "message": "未检测到已知构建系统，可能需要手动配置",
            }

        return {
            "success": True,
            "detected_systems": list(build_systems.keys()),
            "markers": build_systems,
            "primary_system": list(build_systems.keys())[0],  # 优先级按字典顺序
        }

    def compile_library(
        self,
        project_dir: str,
        build_system: str,
        tools_dir: str = None,
        output_dir: str = None,
        extra_args: List[str] = None
    ) -> Dict[str, Any]:
        """
        使用鸿蒙工具链编译三方库

        Args:
            project_dir: 项目目录
            build_system: 构建系统类型 (cmake/makefile/autotools/gn等)
            tools_dir: HarmonyOS CommandLine Tools 目录路径
            output_dir: 输出目录（可选）
            extra_args: 额外的编译参数（可选）

        Returns:
            编译结果
        """
        logger.info(f"开始编译三方库: {project_dir}, 构建系统: {build_system}")
        
        if not os.path.exists(project_dir):
            return {
                "success": False,
                "error": f"项目目录不存在: {project_dir}",
            }

        # 如果未指定工具目录，尝试使用当前目录下的 harmonyos_commandline_tools
        if not tools_dir:
            tools_dir = os.path.join(os.getcwd(), "harmonyos_commandline_tools")
        
        tools_dir = os.path.abspath(tools_dir)
        
        if not os.path.exists(tools_dir):
            return {
                "success": False,
                "error": f"HarmonyOS CommandLine Tools 目录不存在: {tools_dir}",
                "guidance": "请先下载并配置 HarmonyOS CommandLine Tools",
            }

        # 设置输出目录
        if not output_dir:
            output_dir = os.path.join(project_dir, "build_harmonyos")
        
        os.makedirs(output_dir, exist_ok=True)

        # 根据构建系统选择编译命令
        build_system_lower = build_system.lower()
        
        try:
            if build_system_lower == "cmake":
                # CMake 构建
                result = self._compile_with_cmake(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower in ["makefile", "make"]:
                # Makefile 构建
                result = self._compile_with_make(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower in ["autotools", "configure"]:
                # Autotools 构建
                result = self._compile_with_autotools(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            elif build_system_lower == "gn":
                # GN 构建
                result = self._compile_with_gn(
                    project_dir, tools_dir, output_dir, extra_args or []
                )
            else:
                return {
                    "success": False,
                    "error": f"不支持的构建系统: {build_system}",
                    "supported_systems": ["cmake", "makefile", "autotools", "gn"],
                }
            
            return result
            
        except Exception as e:
            logger.error(f"编译过程出现异常: {str(e)}")
            return {
                "success": False,
                "error": f"编译异常: {str(e)}",
            }

    def _compile_with_cmake(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 CMake 编译"""
        logger.info("使用 CMake 编译")
        
        # 查找工具链文件
        toolchain_file = self._find_toolchain_file(tools_dir, "ohos.toolchain.cmake")
        
        if not toolchain_file:
            return {
                "success": False,
                "error": "未找到 HarmonyOS CMake 工具链文件 (ohos.toolchain.cmake)",
                "guidance": "请检查 HarmonyOS CommandLine Tools 是否完整安装",
            }

        # 配置命令
        cmake_cmd = [
            "cmake",
            "-S", project_dir,
            "-B", output_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            "-DCMAKE_BUILD_TYPE=Release",
            *extra_args
        ]
        
        logger.info(f"配置命令: {' '.join(cmake_cmd)}")
        
        # 执行配置
        config_result = subprocess.run(
            cmake_cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if config_result.returncode != 0:
            return {
                "success": False,
                "phase": "configure",
                "error": config_result.stderr.strip() or config_result.stdout.strip(),
            }

        # 执行编译
        build_cmd = ["cmake", "--build", output_dir, "--", "-j4"]
        logger.info(f"编译命令: {' '.join(build_cmd)}")
        
        build_result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if build_result.returncode != 0:
            return {
                "success": False,
                "phase": "build",
                "error": build_result.stderr.strip() or build_result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "cmake",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_make(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 Make 编译"""
        logger.info("使用 Make 编译")
        
        # 查找工具链环境变量设置脚本
        env_script = self._find_env_script(tools_dir)
        
        if not env_script:
            return {
                "success": False,
                "error": "未找到 HarmonyOS 工具链环境配置脚本",
                "guidance": "需要手动配置交叉编译环境变量",
            }

        # 在 WSL 中执行编译（Windows环境）
        make_cmd = [
            "wsl", "bash", "-c",
            f"cd {project_dir} && source {env_script} && make {' '.join(extra_args)}"
        ]
        
        logger.info(f"编译命令: {' '.join(make_cmd)}")
        
        result = subprocess.run(
            make_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "phase": "build",
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(project_dir)
        
        return {
            "success": True,
            "build_system": "make",
            "output_dir": project_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_autotools(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 Autotools (configure) 编译"""
        logger.info("使用 Autotools 编译")
        
        # 查找工具链环境变量
        env_script = self._find_env_script(tools_dir)
        
        if not env_script:
            return {
                "success": False,
                "error": "未找到 HarmonyOS 工具链环境配置脚本",
                "guidance": "需要手动配置交叉编译环境变量",
            }

        # 在 WSL 中执行 configure + make
        configure_cmd = [
            "wsl", "bash", "-c",
            f"cd {project_dir} && source {env_script} && ./configure --prefix={output_dir} {' '.join(extra_args)} && make && make install"
        ]
        
        logger.info(f"配置编译命令: {' '.join(configure_cmd)}")
        
        result = subprocess.run(
            configure_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "phase": "configure_build",
                "error": result.stderr.strip() or result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "autotools",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _compile_with_gn(
        self, 
        project_dir: str, 
        tools_dir: str, 
        output_dir: str, 
        extra_args: List[str]
    ) -> Dict[str, Any]:
        """使用 GN 编译"""
        logger.info("使用 GN 编译")
        
        # GN 需要工具链文件配置
        toolchain_gn = self._find_toolchain_file(tools_dir, "ohos_toolchain.gn")
        
        if not toolchain_gn:
            return {
                "success": False,
                "error": "未找到 HarmonyOS GN 工具链配置文件",
                "guidance": "请检查 HarmonyOS CommandLine Tools 是否包含 GN 工具链",
            }

        # 执行 gn gen
        gn_cmd = [
            "gn", "gen", output_dir,
            f"--args=toolchain_file=\"{toolchain_gn}\"",
            *extra_args
        ]
        
        logger.info(f"GN配置命令: {' '.join(gn_cmd)}")
        
        gn_result = subprocess.run(
            gn_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=project_dir
        )
        
        if gn_result.returncode != 0:
            return {
                "success": False,
                "phase": "gn_gen",
                "error": gn_result.stderr.strip() or gn_result.stdout.strip(),
            }

        # 执行 ninja 编译
        ninja_cmd = ["ninja", "-C", output_dir]
        logger.info(f"Ninja编译命令: {' '.join(ninja_cmd)}")
        
        ninja_result = subprocess.run(
            ninja_cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if ninja_result.returncode != 0:
            return {
                "success": False,
                "phase": "ninja_build",
                "error": ninja_result.stderr.strip() or ninja_result.stdout.strip(),
            }

        # 查找生成的 .so 文件
        so_files = self._find_so_files(output_dir)
        
        return {
            "success": True,
            "build_system": "gn",
            "output_dir": output_dir,
            "so_files": so_files,
            "so_count": len(so_files),
        }

    def _find_toolchain_file(self, tools_dir: str, filename: str) -> Optional[str]:
        """查找工具链文件"""
        for root, dirs, files in os.walk(tools_dir):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def _find_env_script(self, tools_dir: str) -> Optional[str]:
        """查找环境配置脚本"""
        # 通常是 env.sh 或类似文件
        possible_names = ["env.sh", "setup_env.sh", "harmonyos_env.sh"]
        for name in possible_names:
            script_path = os.path.join(tools_dir, name)
            if os.path.exists(script_path):
                return script_path
        return None

    def _find_so_files(self, directory: str) -> List[str]:
        """递归查找目录下的所有 .so 文件"""
        so_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.so') or '.so.' in file:
                    so_files.append(os.path.join(root, file))
        return so_files

    def verify_so_output(self, project_dir: str, output_dir: str = None) -> Dict[str, Any]:
        """
        验证编译输出的 .so 文件

        Args:
            project_dir: 项目目录
            output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

        Returns:
            验证结果
        """
        logger.info(f"验证 .so 文件输出: {project_dir}")

        # 确定输出目录
        if output_dir is None:
            output_dir = os.path.join(project_dir, "build_harmonyos")

        if not os.path.exists(output_dir):
            return {
                "success": False,
                "message": f"输出目录不存在: {output_dir}",
                "verified": False,
                "so_files": [],
            }

        # 查找所有 .so 文件
        so_files = self._find_so_files(output_dir)

        if not so_files:
            return {
                "success": False,
                "message": f"未找到任何 .so 文件: {output_dir}",
                "verified": False,
                "so_files": [],
            }

        logger.info(f"找到 {len(so_files)} 个 .so 文件")

        verified_files = []
        errors = []

        for so_file in so_files:
            file_info = self._verify_single_so(so_file)
            verified_files.append(file_info)

            if not file_info["valid"]:
                errors.append(f"{os.path.basename(so_file)}: {file_info.get('error', 'Unknown error')}")

        # 判断整体验证结果
        all_valid = all(f["valid"] for f in verified_files)

        return {
            "success": True,
            "verified": all_valid,
            "message": "验证完成" if all_valid else f"发现 {len(errors)} 个问题",
            "so_files": verified_files,
            "so_count": len(so_files),
            "valid_count": sum(1 for f in verified_files if f["valid"]),
            "errors": errors,
        }

    def _verify_single_so(self, so_file: str) -> Dict[str, Any]:
        """
        验证单个 .so 文件

        Args:
            so_file: .so 文件路径

        Returns:
            验证结果字典
        """
        result = {
            "path": so_file,
            "name": os.path.basename(so_file),
            "valid": True,
            "size": 0,
            "format": None,
            "arch": None,
            "dependencies": [],
            "symbols": [],
            "error": None,
        }

        try:
            # 1. 检查文件大小
            file_size = os.path.getsize(so_file)
            result["size"] = file_size

            if file_size == 0:
                result["valid"] = False
                result["error"] = "文件大小为 0"
                return result

            # 2. 检查文件格式（使用 file 命令）
            try:
                file_cmd = subprocess.run(
                    ["file", so_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                format_info = file_cmd.stdout.strip()
                result["format"] = format_info

                # 检查是否是有效的 ELF 文件
                if "ELF" not in format_info:
                    result["valid"] = False
                    result["error"] = "不是有效的 ELF 文件: " + format_info
                    return result

                # 提取架构信息
                if "ARM" in format_info:
                    result["arch"] = "ARM"
                elif "x86-64" in format_info or "x86_64" in format_info:
                    result["arch"] = "x86_64"
                elif "AArch64" in format_info:
                    result["arch"] = "AArch64"

            except FileNotFoundError:
                logger.warning("file 命令不可用，跳过格式检查")
            except subprocess.TimeoutExpired:
                logger.warning("file 命令执行超时")
            except Exception as e:
                logger.warning("格式检查失败: " + str(e))

            # 3. 检查依赖库（使用 ldd）
            try:
                ldd_cmd = subprocess.run(
                    ["ldd", so_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if ldd_cmd.returncode == 0:
                    deps = []
                    for line in ldd_cmd.stdout.split("\n"):
                        line = line.strip()
                        if not line or "not found" in line.lower():
                            continue
                        # 解析 "libxxx.so => /path/to/lib" 格式
                        if "=>" in line:
                            parts = line.split("=>")
                            if len(parts) >= 2:
                                dep_name = parts[0].strip()
                                deps.append(dep_name)
                        elif line.startswith("linux-gate") or line.startswith("ld-linux"):
                            deps.append(line.split()[0])
                    result["dependencies"] = deps
            except FileNotFoundError:
                logger.debug("ldd 命令不可用，跳过依赖检查")
            except subprocess.TimeoutExpired:
                logger.warning("ldd 命令执行超时")
            except Exception as e:
                logger.debug("依赖检查失败: " + str(e))

            # 4. 检查符号表（使用 nm）
            try:
                nm_cmd = subprocess.run(
                    ["nm", "-D", so_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if nm_cmd.returncode == 0:
                    symbols = []
                    for line in nm_cmd.stdout.split("\n"):
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            # 格式: address type symbol
                            symbols.append({"type": parts[1], "name": parts[2]})
                    # 只保留前 20 个符号作为示例
                    result["symbols"] = symbols[:20]
                    result["symbol_count"] = len(nm_cmd.stdout.split("\n"))
            except FileNotFoundError:
                logger.debug("nm 命令不可用，跳过符号表检查")
            except subprocess.TimeoutExpired:
                logger.warning("nm 命令执行超时")
            except Exception as e:
                logger.debug("符号表检查失败: " + str(e))

            return result

        except Exception as e:
            logger.error(".so 文件验证失败: " + str(e))
            result["valid"] = False
            result["error"] = str(e)
            return result


@functools.lru_cache(maxsize=1)
def get_compile_environment():
    return CompileEnvironment()


@functools.lru_cache(maxsize=1)
def get_build_file_reader():
    return BuildFileReader()


@functools.lru_cache(maxsize=1)
def get_script_writer():
    return ScriptWriter()


@functools.lru_cache(maxsize=1)
def get_script_executor():
    return ScriptExecutor()
