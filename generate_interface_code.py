from pathlib import Path

from service.service import RPCServer
from utils.logger import setup_logger


def generate_interface_code():
    """生成代码"""
    setup_logger()

    server = RPCServer()
    server.load_modules(modules_dir=Path(Path.cwd(), "modules"))

    server.generate_interface_code()


if __name__ == "__main__":
    generate_interface_code()
