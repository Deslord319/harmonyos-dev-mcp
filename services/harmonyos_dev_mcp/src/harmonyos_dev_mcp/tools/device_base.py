import functools
import inspect
from loguru import logger
from common.tools.base import ToolBase as _CommonToolBase

class ToolBase(_CommonToolBase):
    @staticmethod
    def get_device_id(device_id=None):
        if device_id:
            return True, device_id
        try:
            from ..container import get_hdc
            hdc = get_hdc()
            devices = hdc.list_devices()
            if not devices:
                return False, {
                    "tool": "with_device",
                    "ok": False,
                    "result": {},
                    "error": {"code": "DEVICE_NOT_FOUND", "detail": "No device found"},
                    "meta": {},
                }
            return True, devices[0]
        except Exception as e:
            logger.error(f'Failed to get device list: {e}')
            return False, {
                "tool": "with_device",
                "ok": False,
                "result": {},
                "error": {"code": "DEVICE_LIST_ERROR", "detail": str(e)},
                "meta": {},
            }

    @staticmethod
    def with_device(**error_fields):
        def decorator(func):
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    device_id = kwargs.get('device_id')
                    ok, device = ToolBase.get_device_id(device_id)
                    if not ok:
                        for k, v in error_fields.items():
                            device.setdefault("result", {})
                            device["result"].setdefault(k, v)
                        return device
                    kwargs['device_id'] = device
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    device_id = kwargs.get('device_id')
                    ok, device = ToolBase.get_device_id(device_id)
                    if not ok:
                        for k, v in error_fields.items():
                            device.setdefault("result", {})
                            device["result"].setdefault(k, v)
                        return device
                    kwargs['device_id'] = device
                    return func(*args, **kwargs)
                return wrapper
        return decorator

