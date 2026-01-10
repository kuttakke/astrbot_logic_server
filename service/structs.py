from pydantic import BaseModel, Field


class BaseParameters(BaseModel):
    """基础参数模型"""


class CallParameters(BaseModel):
    """基础参数模型"""

    unified_msg_origin: str = Field(..., description="会话的唯一 ID 标识符")
    method: str = Field(..., description="要调用的方法名称")
    params: BaseParameters = Field(..., description="方法调用的参数")


class BaseResponse(BaseModel):
    """基础响应模型"""


class CallResponse(BaseResponse):
    """调用响应模型"""

    ok: bool = Field(..., description="操作是否成功")
    unified_msg_origin: str = Field(..., description="会话的唯一 ID 标识符")
    data: BaseResponse | None = Field(..., description="方法调用返回的数据")
    error_message: str = Field(..., description="错误信息，如果有的话")
