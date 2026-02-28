"""
hdc 截图模块

提供设备截图功能。
"""
import os
from datetime import datetime
from typing import Dict, Any
from loguru import logger


class HdcScreenshot:
    """截图相关方法"""

    def take_screenshot(
        self,
        device_id: str,
        local_path: str,
        display_id: int = 0
    ) -> Dict[str, Any]:
        """
        对设备屏幕进行截图

        使用 snapshot_display 命令在设备上截图，然后拉取到本地。

        Args:
            device_id: 设备ID
            local_path: 本地保存路径（支持 .png 格式）
            display_id: 显示器ID，默认为主屏幕(0)

        Returns:
            包含截图结果的字典:
            - success: 是否成功
            - local_path: 本地文件路径
            - file_size: 文件大小（字节）
            - device_id: 设备ID
        """
        logger.info(f"对设备 {device_id} 进行截图")

        # 设备上的临时文件路径（HarmonyOS snapshot_display 只支持 .jpeg 后缀）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        remote_path = f"/data/local/tmp/screenshot_{timestamp}.jpeg"

        try:
            # 1. 在设备上执行截图命令
            # snapshot_display -f <output_file> [-i display_id]
            if display_id == 0:
                screenshot_cmd = f"snapshot_display -f {remote_path}"
            else:
                screenshot_cmd = f"snapshot_display -f {remote_path} -i {display_id}"

            result = self.execute_shell(device_id, screenshot_cmd, timeout=10)

            if not result['success']:
                logger.error(f"截图命令执行失败: {result.get('stderr', '')}")
                return {
                    'success': False,
                    'error': f"截图命令执行失败: {result.get('stderr', '')}",
                    'device_id': device_id
                }

            # 2. 检查截图文件是否生成
            check_result = self.execute_shell(device_id, f"ls -la {remote_path}")
            if not check_result['success'] or 'No such file' in check_result.get('stdout', ''):
                return {
                    'success': False,
                    'error': '截图文件未生成',
                    'device_id': device_id
                }

            # 3. 确保本地目录存在
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)

            # 4. 拉取截图到本地
            pull_success = self.pull_file(device_id, remote_path, local_path)

            if not pull_success:
                return {
                    'success': False,
                    'error': '拉取截图文件失败',
                    'device_id': device_id
                }

            # 5. 清理设备上的临时文件
            self.execute_shell(device_id, f"rm {remote_path}")

            # 6. 获取本地文件大小
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            logger.info(f"截图保存成功: {local_path} ({file_size} bytes)")

            return {
                'success': True,
                'local_path': local_path,
                'file_size': file_size,
                'device_id': device_id,
                'message': f'截图已保存到 {local_path}'
            }

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'device_id': device_id
            }

    def take_element_screenshot(
        self,
        device_id: str,
        local_path: str,
        bounds: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        对指定元素区域进行截图（先全屏截图再裁剪）

        Args:
            device_id: 设备ID
            local_path: 本地保存路径
            bounds: 元素边界 {'left': x1, 'top': y1, 'right': x2, 'bottom': y2}

        Returns:
            包含截图结果的字典
        """
        logger.info(f"对设备 {device_id} 的元素区域进行截图: {bounds}")

        # 先进行全屏截图（使用独立的临时文件名，避免与目标路径冲突）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base, ext = os.path.splitext(local_path)
        temp_path = f"{base}_full_{timestamp}{ext or '.png'}"

        full_result = self.take_screenshot(device_id, temp_path)

        if not full_result['success']:
            return full_result

        try:
            # 尝试使用 PIL 裁剪
            from PIL import Image

            left = bounds.get('left', 0)
            top = bounds.get('top', 0)
            right = bounds.get('right', 0)
            bottom = bounds.get('bottom', 0)

            # 打开全屏截图并裁剪
            with Image.open(temp_path) as img:
                # 确保边界在图片范围内
                width, height = img.size
                left = max(0, min(left, width))
                top = max(0, min(top, height))
                right = max(left, min(right, width))
                bottom = max(top, min(bottom, height))

                cropped = img.crop((left, top, right, bottom))
                cropped.save(local_path)

            # 删除临时全屏截图
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning(f"删除临时截图失败: {e}")

            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            logger.info(f"元素截图保存成功: {local_path}")

            return {
                'success': True,
                'local_path': local_path,
                'file_size': file_size,
                'device_id': device_id,
                'bounds': bounds,
                'message': f'元素截图已保存到 {local_path}'
            }

        except ImportError:
            # 如果没有 PIL，返回全屏截图
            logger.warning("PIL 未安装，无法裁剪元素截图，返回全屏截图")
            os.rename(temp_path, local_path)
            file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

            return {
                'success': True,
                'local_path': local_path,
                'file_size': file_size,
                'device_id': device_id,
                'warning': 'PIL 未安装，返回全屏截图',
                'message': f'截图已保存到 {local_path}（全屏）'
            }
        except Exception as e:
            logger.error(f"裁剪截图失败: {e}")
            # 裁剪失败时返回全屏截图
            if os.path.exists(temp_path):
                os.rename(temp_path, local_path)
                file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                return {
                    'success': True,
                    'local_path': local_path,
                    'file_size': file_size,
                    'device_id': device_id,
                    'warning': f'裁剪失败: {e}，返回全屏截图',
                    'message': f'截图已保存到 {local_path}（全屏）'
                }
            return {
                'success': False,
                'error': str(e),
                'device_id': device_id
            }
