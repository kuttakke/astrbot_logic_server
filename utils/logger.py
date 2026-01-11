import logging
import sys
from pathlib import Path

from loguru import logger


class InterceptHandler(logging.Handler):
    """将标准日志记录重定向到 Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # 获取 Loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用栈深度
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # type: ignore[union-attr]
            frame = frame.f_back  # type: ignore[union-attr]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def rewrite_logging_logger(logger_name: str) -> None:
    """重写指定名称的标准日志记录器以使用 Loguru.

    Args:
        logger_name: 要重写的日志记录器名称
    """
    logging_logger = logging.getLogger(logger_name)
    for handler in logging_logger.handlers:
        logging_logger.removeHandler(handler)
    logging_logger.addHandler(InterceptHandler())
    logging_logger.setLevel(logging.DEBUG)


def setup_logger():
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG",
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=False,
    )
    # file logging
    logger.add(
        Path(Path.cwd(), "logs", "app.log"),
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format=log_format,
        encoding="utf-8",
        level="DEBUG",
        colorize=False,
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    # error file logging
    logger.add(
        Path(Path.cwd(), "logs", "error", "error.log"),
        rotation="00:00",
        retention="60 days",
        compression="zip",
        format=log_format,
        encoding="utf-8",
        level="ERROR",
        colorize=False,
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
