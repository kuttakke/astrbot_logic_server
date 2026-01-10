from service.service import api
from service.structs import BaseParameters, BaseResponse


# 具体的调用参数模型
class TestParameters(BaseParameters):
    value: int

    def to_dict(self) -> dict:
        return {"value": self.value}


# 具体的调用响应模型
class TestResponse(BaseResponse):
    result: int

    def to_dict(self) -> dict:
        return {"result": self.result}


class TestModule:
    # function名自动传入
    @api
    async def test_function(self, params: TestParameters) -> TestResponse:
        return TestResponse(result=params.value * 2)

    @api
    @classmethod
    async def test_classmethod(cls, params: TestParameters) -> TestResponse:
        return TestResponse(result=params.value + 10)
