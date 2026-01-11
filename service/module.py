import inspect
from typing import Any, Callable, Optional, TypeVar, get_type_hints

from service.structs import ApiMeta, BaseParameters, BaseResponse

T = TypeVar("T")


class Module:
    """
    模块相关
    """

    def __init__(self, id: str, name: str, description: str) -> None:
        self.id = id  # 模块唯一标识符
        self.name = name  # 模块名称
        self.description = description
        self.path = inspect.getfile(self.__class__)
        self.apis: dict[str, ApiMeta] = {}
        self.start_hooks: list[Callable] = []
        self.shutdown_hooks: list[Callable] = []
        self.context: dict[type, Any] = {}

    def api(self, f: Optional[Callable] = None, *, method_name: str | None = None):
        """注册 API 方法到模块."""

        if f is None:
            return lambda f: self.api(f, method_name=method_name)

        # 注册模块到服务器
        from service.service import get_server

        server = get_server()
        server._register_module(self)

        def decorator(f: Callable):
            hints = get_type_hints(f)
            param_type = hints.get("params") or hints.get("p")
            if not param_type or not issubclass(param_type, BaseParameters):
                raise TypeError(
                    "Parameter 'params' must be a subclass of BaseParameters"
                )

            return_type = hints.get("return")
            if not return_type or not issubclass(return_type, BaseResponse):
                raise TypeError("Return type must be a subclass of BaseResponse")

            is_async = inspect.iscoroutinefunction(f)

            # 构建方法名
            if method_name is not None:
                full_method_name = method_name
            else:
                full_method_name = f.__name__

            # 创建元信息并注册
            api_meta = ApiMeta(
                func=f,
                param_model=param_type,
                resp_model=return_type,
                is_async=is_async,
                method_name=full_method_name,
            )

            self.apis[full_method_name] = api_meta
            return f

        return decorator(f)

    def on_start(self, func: Callable) -> Callable:
        """注册启动钩子."""
        self.start_hooks.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        """注册关闭钩子."""
        self.shutdown_hooks.append(func)
        return func

    def set_context(self, key: type[T], value: T) -> None:
        """设置模块上下文."""
        self.context[key] = value

    def get_context(self, key: type[T]) -> T | None:
        return self.context.get(key)
