import threading
from contextlib import asynccontextmanager
from typing import Dict

import tornado.locks


#: Held while checking for existing users and creating one, shared by every
#: user-creation endpoint so first-run requests cannot race across them.
USER_CREATE_LOCK = "UserCreate"


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
        """Return the raw lock for *name*, creating it if needed.

        Internal to :meth:`acquire`. Using the returned lock directly bypasses
        the reference counting that keeps idle locks from accumulating, so
        callers must go through :meth:`acquire` instead.

        :param name: Lock name.
        :return: The lock registered under *name*.
        """
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
