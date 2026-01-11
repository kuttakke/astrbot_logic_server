"""Main entry point.

启动 RPC 服务器。
导入模块即触发 @api 自动注册。
"""

import asyncio
import importlib

from service.service import RPCServer
from utils.logger import setup_logger


def main() -> None:
    """主函数."""
    setup_logger()

    server = RPCServer()
    # 导入模块即可自动注册其中的 @api 方法和生命周期钩子
    importlib.import_module("modules.test1.test")

    asyncio.run(server.start())


if __name__ == "__main__":
    main()
