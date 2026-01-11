from typing import Callable, Optional

fun = []


class A:
    def decorator(self, f: Optional[Callable] = None, *, name: str | None = None):
        if f is None:
            return lambda f: self.decorator(f, name=name)

        def wrapper(f: Callable):
            fun.append((name, f))
            print(f"Registered function '{name}'")
            return f

        return wrapper(f)


a = A()


@a.decorator(name="example")
def my_function(x: int) -> int:
    print(f"Function called with argument: {x}")
    return x * 2


@a.decorator
def another_function(y: int) -> int:
    print(f"Another function called with argument: {y}")
    return y + 10


print(fun)  # 查看注册的函数列表
print("---")
result = my_function(5)
print(f"Result: {result}")
print(fun)  # 再次查看注册的函数列表

# class Module:
#     def __init__(self, api: str):
#         self.name = "module_id"
#         self.api = api


# class Interface(Enum):
#     api1 = Module(api="api_1")
#     api2 = Module(api="api_2")
#     ... # etc.

# b_instance = B.interface
# print(b_instance.a)  # 输出: example

# class ModuleName:
#     name = "module_id"

#     @classmethod
#     async def api1(cls, params: CallParameters1) -> Response1:
#         ...
#     ... # etc.


class B: ...


class C(B):
    v: int
    ...


def func(t: type[B]): ...


func(C)
