"""Test Module.

演示 RPC 模块的自动注册和生命周期钩子功能。
"""

from loguru import logger

from service.service import api, on_shutdown, on_start
from service.structs import BaseParameters, BaseResponse


class TestParameters(BaseParameters):
    """测试参数模型."""

    value: int


class TestResponse(BaseResponse):
    """测试响应模型."""

    result: int


# 全局状态（演示生命周期钩子）
_initialized: bool = False


@on_start
def init_resources() -> None:
    """启动时初始化资源."""
    global _initialized
    logger.info("TestModule: 初始化资源中...")
    _initialized = True


@on_shutdown
def cleanup() -> None:
    """关闭时清理资源."""
    global _initialized
    logger.info("TestModule: 清理资源中...")
    _initialized = False


@api(method_name="test_function")
async def test_function(params: TestParameters) -> TestResponse:
    """测试方法.

    Args:
        params: 测试参数

    Returns:
        测试响应
    """
    return TestResponse(result=params.value * 2)


@api(method_name="test_function2")
async def test_function2(params: TestParameters) -> TestResponse:
    """另一个测试方法.

    Args:
        params: 测试参数

    Returns:
        测试响应
    """
    # test error
    raise ValueError("This is a test error.")
    # return TestResponse(result=params.value + 10)
