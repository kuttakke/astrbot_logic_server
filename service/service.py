"""RPC Server Service Module.

提供基于 Unix Socket 的 RPC 服务，支持自动注册和生命周期管理。
"""

import asyncio
import inspect
from pathlib import Path
from typing import Any, Callable

import msgpack
from loguru import logger

from service.module import Module
from utils.singleton import SingletonMeta

from .structs import BaseParameters, BaseResponse, CallParameters, CallResponse

_start = """
#################################
#       Astrbot Logic Server    #
#       RPC Server Started      #
#################################
"""


class RPCServer(metaclass=SingletonMeta):
    """RPC 服务器单例."""

    def __init__(self, socket_path: Path = Path("/run/logic/logic.sock")):
        self.socket_path: Path = socket_path
        self._is_running: bool = False
        self.modules: dict[str, "Module"] = {}

    def _register_module(self, module: "Module") -> None:
        """注册模块."""
        if module.name in self.modules:
            return
        logger.debug(f"Registering module: {module.name}")
        self.modules[module.name] = module

    async def _execute_hooks(self, hooks: list[Callable]) -> None:
        """执行生命周期钩子."""
        for hook in hooks:
            if inspect.iscoroutinefunction(hook):
                try:
                    await hook()
                except Exception as e:
                    logger.error(f"Error executing hook {hook.__name__}: {e}")
            else:
                try:
                    await asyncio.to_thread(hook)
                except Exception as e:
                    logger.error(f"Error executing hook {hook.__name__}: {e}")

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

    async def _call_handler(
        self, module_id: str, method: str, params: BaseParameters
    ) -> BaseResponse:
        """调用对应的处理函数."""

        module = self.modules.get(module_id)
        if not module:
            raise ValueError(f"Unknown module: {module_id}")

        meta = module.apis.get(method)
        if not meta:
            raise ValueError(f"Unknown method: {method}")

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
            result = await self._call_handler(call.module_id, call.method, call.params)
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

    def load_modules(self, modules_dir: Path) -> None:
        """加载指定目录下的所有模块."""
        for module_path in modules_dir.iterdir():
            if module_path.is_dir() and (module_path / "__init__.py").exists():
                module_name = module_path.name
                logger.info(f"Loading module: {module_name}")
                __import__(f"modules.{module_name}")

    async def start(self) -> None:
        """启动 RPC 服务器."""

        logger.info(_start)

        # 执行启动钩子
        for module in self.modules.values():
            await self._execute_hooks(module.start_hooks)

        self.socket_path.unlink(missing_ok=True)
        server = await asyncio.start_unix_server(  # type: ignore[arg-type]
            self.handle_client, path=self.socket_path
        )

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
        # 执行关闭钩子
        for module in self.modules.values():
            await self._execute_hooks(module.shutdown_hooks)

    def generate_interface_code(self):
        """生成接口代码供调用者使用."""
        dir_ = Path(Path.cwd(), "generated")
        dir_.mkdir(exist_ok=True)

        typed = set()

        for module in self.modules.values():
            path = dir_ / f"{module.name.lower()}.py"
            lines = [
                "from .rpc_client import BaseParameters, BaseResponse, get_rpc_client",
                "from astrbot.api.event import AstrMessageEvent",
                "",
                f"# ------------------- {module.name} -------------------",
            ]
            for api_name, api_meta in module.apis.items():
                param_model_name = api_meta.param_model.__name__
                resp_model_name = api_meta.resp_model.__name__
                if api_meta.param_model not in typed:
                    lines.append(f"class {param_model_name}(BaseParameters):")
                    lines.extend(
                        f"    {field_name}: {field_info.annotation.__name__}"  # type: ignore
                        for field_name, field_info in api_meta.param_model.model_fields.items()
                    )
                    lines.append("")
                    typed.add(api_meta.param_model)
                if api_meta.resp_model not in typed:
                    lines.append(f"class {resp_model_name}(BaseResponse):")
                    lines.extend(
                        f"    {field_name}: {field_info.annotation.__name__}"  # type: ignore
                        for field_name, field_info in api_meta.resp_model.model_fields.items()
                    )
                    lines.append("")
                    typed.add(api_meta.resp_model)

            lines.extend(
                (
                    f"class {module.name.capitalize()}:",
                    f'    module_id = "{module.id}"',
                    "",
                )
            )
            for api_name, api_meta in module.apis.items():
                param_model_name = api_meta.param_model.__name__
                resp_model_name = api_meta.resp_model.__name__

                lines.extend(
                    (
                        "    @classmethod",
                        f"    async def {api_name}(",
                        "        cls,",
                        f"        params: {param_model_name},",
                        "        *,",
                        "        event: AstrMessageEvent",
                        f"    ) -> {resp_model_name}:",
                        "        client = get_rpc_client()",
                        "        return await client.call(",
                        "            module_id=cls.module_id,",
                        f'            method="{api_name}",',
                        "            params=params,",
                        "            unified_msg_origin=event.unified_msg_origin,",
                        f"            resp_model={resp_model_name},",
                        "        )",
                        "",
                    )
                )
            code = "\n".join(lines)
            path.write_text(code, encoding="utf-8")
            lines.append("")

            code = "\n".join(lines)
            path.write_text(code, encoding="utf-8")


# 全局 RPC 服务器实例
_rpc_server: RPCServer | None = None


def get_server() -> RPCServer:
    """获取或创建全局 RPC 服务器实例."""
    global _rpc_server
    if _rpc_server is None:
        _rpc_server = RPCServer()
    return _rpc_server
