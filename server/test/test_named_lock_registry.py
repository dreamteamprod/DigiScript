import asyncio
import threading

import pytest
import tornado.locks

from registry.named_locks import NamedLockRegistry, acquire_lock


@pytest.fixture
def reset_registry():
    """Reset the NamedLockRegistry between tests"""
    NamedLockRegistry._locks = {}
    yield
    NamedLockRegistry._locks = {}


@pytest.mark.asyncio
async def test_get_lock_returns_same_lock_for_same_name(reset_registry):
    """Test that get_lock returns the same lock object for the same name"""
    lock1 = NamedLockRegistry.get_lock("resource1")
    lock2 = NamedLockRegistry.get_lock("resource1")

    assert lock1 is lock2
    assert isinstance(lock1, tornado.locks.Lock)


@pytest.mark.asyncio
async def test_get_lock_returns_different_locks_for_different_names(reset_registry):
    """Test that get_lock returns different lock objects for different names"""
    lock1 = NamedLockRegistry.get_lock("resource1")
    lock2 = NamedLockRegistry.get_lock("resource2")

    assert lock1 is not lock2
    assert isinstance(lock1, tornado.locks.Lock)
    assert isinstance(lock2, tornado.locks.Lock)


@pytest.mark.asyncio
async def test_acquire_lock_context_manager(reset_registry):
    """Test that the acquire_lock context manager acquires and releases the lock"""
    test_name = "test_resource"

    # Get the lock to manipulate it directly
    lock = NamedLockRegistry.get_lock(test_name)

    # Verify it's unlocked initially
    assert lock._block._value == 1

    # Use the context manager
    async with acquire_lock(test_name):
        # Lock should be acquired within the context
        assert lock._block._value == 0

    # Lock should be released after the context
    assert lock._block._value == 1


@pytest.mark.asyncio
async def test_lock_prevents_concurrent_access(reset_registry):
    """Test that the lock prevents concurrent access to a critical section"""
    test_name = "concurrent_resource"
    shared_counter = 0
    iterations = 100
    num_tasks = 10

    async def increment_counter():
        nonlocal shared_counter
        for _ in range(iterations):
            async with acquire_lock(test_name):
                # Store the current value
                current = shared_counter
                # Simulate some processing time that could lead to race conditions
                await asyncio.sleep(0.001)
                # Increment
                shared_counter = current + 1

    # Create and run multiple tasks that try to increment the counter
    tasks = [asyncio.create_task(increment_counter()) for _ in range(num_tasks)]
    await asyncio.gather(*tasks)

    # Without proper locking, we'd expect the counter to be less than iterations * num_tasks
    # due to race conditions, but with locking it should be exactly iterations * num_tasks
    assert shared_counter == iterations * num_tasks


@pytest.mark.asyncio
async def test_different_locks_dont_block_each_other(reset_registry):
    """Test that different named locks don't block each other"""
    resource1 = "resource1"
    resource2 = "resource2"

    # We'll use these events to control and verify the execution order
    resource1_acquired = asyncio.Event()
    resource2_accessed = asyncio.Event()

    async def task1():
        async with acquire_lock(resource1):
            # Signal that resource1 is locked
            resource1_acquired.set()
            # Wait for task2 to access resource2
            await resource2_accessed.wait()
            # If we get here, it means task2 was able to access resource2 while resource1 was locked

    async def task2():
        # Wait until task1 has acquired the lock on resource1
        await resource1_acquired.wait()
        # Try to acquire resource2 - this should not be blocked
        async with acquire_lock(resource2):
            # Signal that we've accessed resource2
            resource2_accessed.set()

    # Run both tasks concurrently and wait for them to complete
    await asyncio.gather(task1(), task2())

    # If we get here without deadlock, the test passed
    assert resource1_acquired.is_set() and resource2_accessed.is_set()


@pytest.mark.asyncio
async def test_thread_safety_of_get_lock(reset_registry):
    """Test that the get_lock method is thread-safe when creating new locks"""
    test_name = "thread_safety_test"
    NUM_THREADS = 20
    results = []

    def get_lock_from_thread():
        # Get the lock from a separate thread
        lock = NamedLockRegistry.get_lock(test_name)
        results.append(lock)

    # Create and start multiple threads
    threads = [
        threading.Thread(target=get_lock_from_thread) for _ in range(NUM_THREADS)
    ]
    for thread in threads:
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # All threads should have got the same lock object
    assert len(results) == NUM_THREADS
    for lock in results:
        assert lock is results[0]


@pytest.mark.asyncio
async def test_acquire_exceptions_release_lock(reset_registry):
    """Test that the lock is released even if an exception occurs in the context"""
    test_name = "exception_test"
    lock = NamedLockRegistry.get_lock(test_name)

    try:
        async with NamedLockRegistry.acquire(test_name):
            assert lock._block._value == 0
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Lock should be released even though an exception was raised
    assert lock._block._value == 1
