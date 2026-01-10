import asyncio

from modules.test1.test import TestModule

from service.service import RPCServer

if __name__ == "__main__":
    server = RPCServer()
    server.register_module(TestModule())
    asyncio.run(server.start())
