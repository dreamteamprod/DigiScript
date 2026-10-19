import threading
from contextlib import asynccontextmanager
from typing import Dict

import tornado.locks


class NamedLockRegistry:
    """Registry of named asyncio locks.

    Locks are created on demand and discarded again as soon as nobody holds or
    is waiting for them, so the registry cannot grow without bound when names
    are derived from user input.
    """

    _locks: Dict[str, tornado.locks.Lock] = {}
    _refs: Dict[str, int] = {}
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
        # Take a reference before awaiting so the lock is not pruned while
        # another task is queued on it.
        with cls._registry_lock:
            cls._refs[name] = cls._refs.get(name, 0) + 1
        lock = cls.get_lock(name)
        try:
            await lock.acquire()
            try:
                yield
            finally:
                lock.release()
        finally:
            with cls._registry_lock:
                remaining = cls._refs.get(name, 1) - 1
                if remaining <= 0:
                    cls._refs.pop(name, None)
                    cls._locks.pop(name, None)
                else:
                    cls._refs[name] = remaining


@asynccontextmanager
async def acquire_lock(name: str):
    async with NamedLockRegistry.acquire(name):
        yield
