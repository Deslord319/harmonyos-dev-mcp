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
import subprocess
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
            '/home/aoqiduan/projects/harmonyOS-mcp/command-line-tools/sdk/default',
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
    
    def get_environment_info(self, target_arch: str = 'aarch64') -> Dict[str, Any]:
        """获取完整的环境信息"""
        return {
            'sdk_path': self.get_sdk_path(),
            'compiler': self.get_compiler_path(target_arch),
            'cxx_compiler': self.get_compiler_path(target_arch).replace('-clang', '-clang++'),
            'sysroot': self.get_sysroot_path(),
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
        'Configure',  # OpenSSL
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


# 全局实例
_environment = None
_file_reader = None
_script_writer = None
_script_executor = None


def get_compile_environment():
    global _environment
    if _environment is None:
        _environment = CompileEnvironment()
    return _environment


def get_build_file_reader():
    global _file_reader
    if _file_reader is None:
        _file_reader = BuildFileReader()
    return _file_reader


def get_script_writer():
    global _script_writer
    if _script_writer is None:
        _script_writer = ScriptWriter()
    return _script_writer


def get_script_executor():
    global _script_executor
    if _script_executor is None:
        _script_executor = ScriptExecutor()
    return _script_executor
