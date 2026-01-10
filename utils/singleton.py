from threading import Lock
from typing import Any


class SingletonMeta(type):
    """线程安全的单例元类（双重检查锁模式）"""

    _instances: dict[type, Any] = {}
    _lock: Lock = Lock()  # 类级别的锁

    def __call__(cls, *args, **kwargs) -> "SingletonMeta":
        # 第一次检查（不加锁，性能友好）
        if cls not in cls._instances:
            with cls._lock:  # 获取锁
                # 第二次检查（双检锁经典写法）
                if cls not in cls._instances:
                    # 在锁内创建实例
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]
