"""
HarmonyOS 编译结果验证工具

验证编译输出的 .so 文件格式、架构、依赖等。
"""

import os
import subprocess
from typing import Dict, Any, List, Optional

from loguru import logger


class CompileLibraryManager:
    """编译库管理器 - 验证 .so 输出"""

    def __init__(self, tools_dir: str = None):
        """
        初始化编译库管理器

        Args:
            tools_dir: HarmonyOS CommandLine Tools 目录路径（未使用，保留兼容性）
        """
        self.tools_dir = tools_dir or os.path.join(os.getcwd(), "harmonyos_commandline_tools")
        logger.info(f"初始化 CompileLibraryManager，工具目录：{self.tools_dir}")

    def _find_so_files(self, directory: str) -> List[str]:
        """递归查找目录下的所有 .so 文件"""
        so_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".so") or ".so." in file:
                    so_files.append(os.path.join(root, file))
        return so_files

    def verify_so_output(
        self, project_dir: str, output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证编译输出的 .so 文件

        Args:
            project_dir: 项目目录
            output_dir: 输出目录（可选，默认为 project_dir/build_harmonyos）

        Returns:
            验证结果
        """
        logger.info(f"验证 .so 文件输出：{project_dir}")

        # 确定输出目录
        if output_dir is None:
            output_dir = os.path.join(project_dir, "build_harmonyos")

        if not os.path.exists(output_dir):
            return {
                "success": False,
                "message": f"输出目录不存在：{output_dir}",
                "verified": False,
                "so_files": [],
            }

        # 查找所有 .so 文件
        so_files = self._find_so_files(output_dir)

        if not so_files:
            return {
                "success": False,
                "message": f"未找到任何 .so 文件：{output_dir}",
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
                errors.append(
                    f"{os.path.basename(so_file)}: {file_info.get('error', 'Unknown error')}"
                )

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
                    result["error"] = "不是有效的 ELF 文件：" + format_info
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
                logger.warning("格式检查失败：" + str(e))

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
                logger.debug("依赖检查失败：" + str(e))

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
                            # 格式：address type symbol
                            symbols.append({"type": parts[1], "name": parts[2]})
                    # 只保留前 20 个符号作为示例
                    result["symbols"] = symbols[:20]
                    result["symbol_count"] = len(nm_cmd.stdout.split("\n"))
            except FileNotFoundError:
                logger.debug("nm 命令不可用，跳过符号表检查")
            except subprocess.TimeoutExpired:
                logger.warning("nm 命令执行超时")
            except Exception as e:
                logger.debug("符号表检查失败：" + str(e))

            return result

        except Exception as e:
            logger.error(".so 文件验证失败：" + str(e))
            result["valid"] = False
            result["error"] = str(e)
            return result
