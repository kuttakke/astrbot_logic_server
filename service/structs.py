"""RPC 数据结构定义模块.

提供 RPC 通信中使用的基础 Pydantic 模型。
"""

from pydantic import BaseModel, Field


class BaseParameters(BaseModel):
    """基础参数模型.

    所有 RPC 方法的参数模型都应该继承此类。

    Example:
        >>> class MyParams(BaseParameters):
        ...     name: str
        ...     value: int
    """


class CallParameters(BaseModel):
    """RPC 调用参数模型.

    Attributes:
        unified_msg_origin: 会话的唯一 ID 标识符，用于追踪请求/响应
        method: 要调用的方法名称，格式为 "模块名.方法名"
        params: 方法调用的参数，继承自 BaseParameters
    """
    unified_msg_origin: str = Field(..., description="会话的唯一 ID 标识符")
    method: str = Field(..., description="要调用的方法名称")
    params: BaseParameters = Field(..., description="方法调用的参数")


class BaseResponse(BaseModel):
    """基础响应模型.

    所有 RPC 方法的响应模型都应该继承此类。
    """


class CallResponse(BaseModel):
    """RPC 调用响应模型.

    Attributes:
        ok: 操作是否成功
        unified_msg_origin: 会话的唯一 ID 标识符，与请求对应
        data: 方法调用返回的数据，类型为 BaseResponse 或 None
        error_message: 错误信息，如果有的话
    """
    ok: bool = Field(..., description="操作是否成功")
    unified_msg_origin: str = Field(..., description="会话的唯一 ID 标识符")
    data: BaseResponse | None = Field(..., description="方法调用返回的数据")
    error_message: str = Field(..., description="错误信息，如果有的话")
