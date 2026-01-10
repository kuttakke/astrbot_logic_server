import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, get_type_hints

import msgpack

from utils.singleton import SingletonMeta

from .structs import BaseParameters, BaseResponse, CallParameters, CallResponse


@dataclass
class ApiMeta:
    func: Callable
    param_model: type[BaseParameters]
    resp_model: type[BaseResponse]
    is_async: bool


class RPCServer(metaclass=SingletonMeta):
    def __init__(self, socket_path: Path = Path("/run/logic/logic.sock")):
        self.socket_path: Path = socket_path
        self.handlers: dict[str, ApiMeta] = {}  # 全局方法注册表
        self.instance_map: dict[str, Any] = {}  # 模块实例（可选）

    def register(self, method_name: str, meta: ApiMeta):
        if method_name in self.handlers:
            raise ValueError(f"Method {method_name} already registered")
        self.handlers[method_name] = meta

    def register_module(self, module_instance: Any):
        """从模块实例中自动注册所有 @api 标记的方法"""
        for name, obj in module_instance.__class__.__dict__.items():
            if hasattr(obj, "_rpc_meta"):  # 通过装饰器打标记
                meta = obj._rpc_meta
                full_method_name = (
                    f"{module_instance.__class__.__name__}.{name}"  # 推荐加模块前缀
                )
                self.register(full_method_name, meta)
                self.instance_map[full_method_name] = module_instance

    async def _read_msgpack(self, reader: asyncio.StreamReader) -> dict:
        size_data = await reader.readexactly(4)
        size = int.from_bytes(size_data, byteorder="big")
        data = await reader.readexactly(size)
        return msgpack.unpackb(data, raw=False)

    async def _write_msgpack(self, writer: asyncio.StreamWriter, message: dict):
        packed = msgpack.packb(message, use_bin_type=True)
        size = len(packed)  # type: ignore
        writer.write(size.to_bytes(4, byteorder="big"))
        writer.write(packed)  # type: ignore
        await writer.drain()

    async def _call_handler(self, method: str, params: BaseParameters) -> BaseResponse:
        if method not in self.handlers:
            raise ValueError(f"Unknown method: {method}")

        meta = self.handlers[method]
        instance = self.instance_map.get(method)  # 所属模块实例

        # 构建调用参数
        args = [params]
        if instance is not None:
            args.insert(0, instance)  # self

        if meta.is_async:
            result = await meta.func(*args)
        else:
            result = await asyncio.to_thread(meta.func, *args)

        if not isinstance(result, meta.resp_model):
            raise TypeError(f"Return type mismatch for {method}")

        return result

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            req = await self._read_msgpack(reader)
            call = CallParameters(**req)

            result = await self._call_handler(call.method, call.params)

            resp = CallResponse(
                ok=True,
                data=result,
                unified_msg_origin=call.unified_msg_origin,
                error_message="",
            )

        except Exception as e:
            resp = CallResponse(
                ok=False,
                unified_msg_origin=req.get("unified_msg_origin", ""),
                data=None,
                error_message=str(e),
            )

        await self._write_msgpack(writer, resp.model_dump())
        writer.close()
        await writer.wait_closed()

    async def start(self):
        self.socket_path.unlink(missing_ok=True)
        server = await asyncio.start_unix_server(  # type: ignore
            self.handle_client, path=self.socket_path
        )
        print(f"RPC Server listening on {self.socket_path}")
        async with server:
            await server.serve_forever()


# 装饰器实现（支持 self，支持 sync/async）
def api(func=None):
    def decorator(f):
        import inspect

        sig = inspect.signature(f)
        hints = get_type_hints(f)

        # 检查：self + params
        params = list(sig.parameters.items())
        if len(params) < 2:
            raise TypeError("Expected at least self + params")

        _, param_info = params[1]
        param_type = hints.get(param_info.name)
        if not issubclass(param_type, BaseParameters):  # type: ignore
            raise TypeError("Param must subclass BaseParameters")

        return_type = hints.get("return")
        if not issubclass(return_type, BaseResponse):  # type: ignore
            raise TypeError("Return must subclass BaseResponse")

        is_async = inspect.iscoroutinefunction(f)

        # 打上标记，供 register_module 自动发现
        f._rpc_meta = ApiMeta(f, param_type, return_type, is_async)

        return f

    return decorator if func is None else decorator(func)
