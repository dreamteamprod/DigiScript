import threading
from contextlib import asynccontextmanager
from typing import Dict

import tornado.locks


class NamedLockRegistry:
    _locks: Dict[str, tornado.locks.Lock] = {}
    _registry_lock = threading.Lock()

    @classmethod
    def get_lock(cls, name: str) -> tornado.locks.Lock:
        if name in cls._locks:
            return cls._locks[name]

        with cls._registry_lock:
            if name not in cls._locks:
                cls._locks[name] = tornado.locks.Lock()
            return cls._locks[name]

    @classmethod
    @asynccontextmanager
    async def acquire(cls, name: str):
        lock = cls.get_lock(name)
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()


@asynccontextmanager
async def acquire_lock(name: str):
    async with NamedLockRegistry.acquire(name):
        yield
