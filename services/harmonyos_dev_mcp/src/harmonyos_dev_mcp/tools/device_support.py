import functools
import inspect
from typing import Optional

from loguru import logger

from common.tools.base import ToolBase
from common.tools.response import error_result


class DeviceToolSupport(ToolBase):
    @staticmethod
    def build_device_error(code: str, detail: str, **result_fields):
        return error_result(code, detail, result=result_fields, tool="with_device")

    @staticmethod
    def get_device_id(device_id: Optional[str] = None):
        if device_id:
            return True, device_id, None

        try:
            from ..container import get_hdc

            hdc = get_hdc()
            devices = hdc.list_devices()
            if not devices:
                return False, None, DeviceToolSupport.build_device_error("DEVICE_NOT_FOUND", "No device found")
            return True, devices[0], None
        except Exception as exc:
            logger.error(f"Failed to get device list: {exc}")
            return False, None, DeviceToolSupport.build_device_error("DEVICE_LIST_ERROR", str(exc))

    @staticmethod
    def with_device(**error_fields):
        def decorator(func):
            if inspect.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    device_id = kwargs.get("device_id")
                    ok, resolved_device, device_error = DeviceToolSupport.get_device_id(device_id)
                    if not ok:
                        device = device_error or DeviceToolSupport.build_device_error("DEVICE_NOT_FOUND", "No device found")
                        for key, value in error_fields.items():
                            device.setdefault("result", {})
                            device["result"].setdefault(key, value)
                        return device
                    kwargs["device_id"] = resolved_device
                    return await func(*args, **kwargs)

                return async_wrapper

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                device_id = kwargs.get("device_id")
                ok, resolved_device, device_error = DeviceToolSupport.get_device_id(device_id)
                if not ok:
                    device = device_error or DeviceToolSupport.build_device_error("DEVICE_NOT_FOUND", "No device found")
                    for key, value in error_fields.items():
                        device.setdefault("result", {})
                        device["result"].setdefault(key, value)
                    return device
                kwargs["device_id"] = resolved_device
                return func(*args, **kwargs)

            return wrapper

        return decorator
