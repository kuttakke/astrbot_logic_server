"""Main entry point.

启动 RPC 服务器。
导入模块即触发 @api 自动注册。
"""

import asyncio
from pathlib import Path

from service.service import RPCServer
from utils.logger import setup_logger


def main() -> None:
    """主函数."""
    setup_logger()

    server = RPCServer()
    server.load_modules(modules_dir=Path(Path.cwd(), "modules"))

    asyncio.run(server.start())


if __name__ == "__main__":
    main()
