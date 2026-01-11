"""Test Module.

演示 RPC 模块的自动注册和生命周期钩子功能。
"""

from loguru import logger

from service.module import Module
from service.structs import BaseParameters, BaseResponse

# 创建模块实例
_test_module = Module(
    id="test_module",
    name="TestModule",
    description="A test module for demonstrating RPC functionality.",
)

m = _test_module  # 模块实例别名


class TestParameters(BaseParameters):
    """测试参数模型."""

    value: int


class TestResponse(BaseResponse):
    """测试响应模型."""

    result: int


# ==================== 生命周期钩子 ====================


@m.on_start
def init_resources() -> None:
    """启动时初始化资源."""
    logger.info("TestModule: 初始化资源中...")


@m.on_shutdown
def cleanup() -> None:
    """关闭时清理资源."""
    logger.info("TestModule: 清理资源中...")


# ==================== 简单 API ====================


@m.api(method_name="test_function")
async def test_function(params: TestParameters) -> TestResponse:
    """测试方法.

    Args:
        params: 测试参数

    Returns:
        测试响应
    """
    return TestResponse(result=params.value * 2)


@m.api(method_name="test_function2")
async def test_function2(params: TestParameters) -> TestResponse:
    """测试错误处理."""
    raise ValueError("This is a test error.")
