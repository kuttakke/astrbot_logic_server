"""RPC Server Service Module.

提供基于 Unix Socket 的 RPC 服务，支持自动注册和生命周期管理。
"""

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, get_type_hints

import msgpack
from loguru import logger

from utils.singleton import SingletonMeta

from .structs import BaseParameters, BaseResponse, CallParameters, CallResponse

_start = """/n
#################################
#       Astrbot Logic Server     #
#       RPC Server Started       #
#################################
"""


@dataclass
class ApiMeta:
    """API 方法元信息."""

    func: Callable
    param_model: type[BaseParameters]
    resp_model: type[BaseResponse]
    is_async: bool
    method_name: str = ""


class RPCServer(metaclass=SingletonMeta):
    """RPC 服务器单例."""

    def __init__(self, socket_path: Path = Path("/run/logic/logic.sock")):
        self.socket_path: Path = socket_path
        self.handlers: dict[str, ApiMeta] = {}
        self.start_hooks: list[Callable] = []
        self.shutdown_hooks: list[Callable] = []
        self._is_running: bool = False

    def _register_api(self, method_name: str, meta: ApiMeta) -> None:
        """注册 API 方法."""
        if method_name in self.handlers:
            raise ValueError(f"Method '{method_name}' already registered")
        logger.debug(f"Registering API method: {method_name}")
        self.handlers[method_name] = meta

    async def _execute_hooks(self, hooks: list[Callable]) -> None:
        """执行生命周期钩子."""
        for hook in hooks:
            if inspect.iscoroutinefunction(hook):
                await hook()
            else:
                await asyncio.to_thread(hook)

    async def _read_msgpack(self, reader: asyncio.StreamReader) -> dict[str, Any]:
        """从流中读取 msgpack 数据."""
        size_data = await reader.readexactly(4)
        size = int.from_bytes(size_data, byteorder="big")
        data = await reader.readexactly(size)
        return msgpack.unpackb(data, raw=False)  # type: ignore[return-value]

    async def _write_msgpack(
        self, writer: asyncio.StreamWriter, message: dict[str, Any]
    ) -> None:
        """将数据以 msgpack 格式写入流."""
        packed = msgpack.packb(message, use_bin_type=True)
        size = len(packed)  # type: ignore
        writer.write(size.to_bytes(4, byteorder="big"))
        writer.write(packed)  # type: ignore
        await writer.drain()

    async def _call_handler(self, method: str, params: BaseParameters) -> BaseResponse:
        """调用对应的处理函数."""
        if method not in self.handlers:
            raise ValueError(f"Unknown method: {method}")

        meta = self.handlers[method]

        if meta.is_async:
            result = await meta.func(params)
        else:
            result = await asyncio.to_thread(meta.func, params)

        if not isinstance(result, meta.resp_model):
            raise TypeError(f"Return type mismatch for {method}")

        return result

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """处理客户端连接."""
        try:
            req = await self._read_msgpack(reader)
            call = CallParameters(**req)
            logger.debug(f"[RPC] Received call: {call.method}")
            result = await self._call_handler(call.method, call.params)
            logger.debug(f"[RPC] call {call.method} completed successfully")
            resp = CallResponse(
                ok=True,
                data=result,
                unified_msg_origin=call.unified_msg_origin,
                error_message="",
            )

        except Exception as exc:
            logger.error(f"[RPC] call {req.get('method', '')} failed: {exc}")
            resp = CallResponse(
                ok=False,
                unified_msg_origin=req.get("unified_msg_origin", ""),
                data=None,
                error_message=str(exc),
            )

        await self._write_msgpack(writer, resp.model_dump())
        writer.close()
        await writer.wait_closed()

    async def start(self) -> None:
        """启动 RPC 服务器."""
        # 执行启动钩子
        await self._execute_hooks(self.start_hooks)

        self.socket_path.unlink(missing_ok=True)
        server = await asyncio.start_unix_server(  # type: ignore[arg-type]
            self.handle_client, path=self.socket_path
        )
        logger.info(_start)
        logger.info(f"RPC Server started at {self.socket_path}")
        self._is_running = True

        try:
            async with server:
                await server.serve_forever()
        finally:
            self._is_running = False

    async def shutdown(self) -> None:
        """关闭 RPC 服务器."""
        logger.info("Shutting down RPC Server...")
        await self._execute_hooks(self.shutdown_hooks)


# 全局 RPC 服务器实例
_rpc_server: RPCServer | None = None


def _get_server() -> RPCServer:
    """获取或创建全局 RPC 服务器实例."""
    global _rpc_server
    if _rpc_server is None:
        _rpc_server = RPCServer()
    return _rpc_server


def api(
    func: Callable | None = None,
    *,
    method_name: str | None = None,
) -> Callable:
    """API 方法装饰器.

    自动将方法注册到全局 RPC 服务器。
    方法签名: (params: Parameters) -> Response
    """

    def decorator(f: Callable) -> Callable:
        hints = get_type_hints(f)

        # 获取 params 参数
        param_type = hints.get("params")
        if not param_type or not issubclass(param_type, BaseParameters):
            raise TypeError("Parameter 'params' must be a subclass of BaseParameters")

        return_type = hints.get("return")
        if not return_type or not issubclass(return_type, BaseResponse):
            raise TypeError("Return type must be a subclass of BaseResponse")

        is_async = inspect.iscoroutinefunction(f)

        # 构建方法名
        if method_name is not None:
            full_method_name = method_name
        else:
            full_method_name = f.__name__

        # 创建元信息并注册
        meta = ApiMeta(
            func=f,
            param_model=param_type,
            resp_model=return_type,
            is_async=is_async,
            method_name=full_method_name,
        )
        server = _get_server()
        server._register_api(full_method_name, meta)

        return f

    if func is not None:
        return decorator(func)
    return decorator


def on_start(func: Callable) -> Callable:
    """启动钩子装饰器."""
    server = _get_server()
    server.start_hooks.append(func)
    return func


def on_shutdown(func: Callable) -> Callable:
    """关闭钩子装饰器."""
    server = _get_server()
    server.shutdown_hooks.append(func)
    return func
