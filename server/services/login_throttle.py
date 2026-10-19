"""In-memory brute-force protection for the login endpoint."""

import math
import time
from collections import OrderedDict
from typing import Callable, Hashable


class _Tracker:
    """Failure counters with exponential lockout for one kind of key.

    Once a key has accumulated ``free_attempts`` failures, every further failure
    locks it for ``base_lockout * 2 ** (failures - free_attempts)`` seconds,
    capped at ``max_lockout``. Entries are forgotten after ``decay`` seconds
    without a failure and the table never holds more than ``max_entries`` keys.
    """

    def __init__(
        self,
        free_attempts: int,
        base_lockout: float,
        max_lockout: float,
        decay: float,
        max_entries: int,
    ):
        self.free_attempts = free_attempts
        self.base_lockout = base_lockout
        self.max_lockout = max_lockout
        self.decay = decay
        self.max_entries = max_entries
        # key -> [failures, last_failure, locked_until]
        self.entries: "OrderedDict[Hashable, list]" = OrderedDict()

    def _expired(self, entry: list, now: float) -> bool:
        return now >= entry[2] and now - entry[1] >= self.decay

    def _prune(self, now: float) -> None:
        for key in [k for k, e in self.entries.items() if self._expired(e, now)]:
            del self.entries[key]

    def retry_after(self, key: Hashable, now: float) -> float:
        entry = self.entries.get(key)
        if entry is None:
            return 0.0
        if self._expired(entry, now):
            del self.entries[key]
            return 0.0
        return max(0.0, entry[2] - now)

    def record_failure(self, key: Hashable, now: float) -> None:
        entry = self.entries.get(key)
        if entry is not None and self._expired(entry, now):
            del self.entries[key]
            entry = None
        if entry is None:
            if len(self.entries) >= self.max_entries:
                self._prune(now)
            while len(self.entries) >= self.max_entries:
                self.entries.popitem(last=False)
            entry = [0, now, 0.0]
            self.entries[key] = entry
        entry[0] += 1
        entry[1] = now
        over = entry[0] - self.free_attempts
        if over >= 0:
            # Cap the exponent so the float never overflows on huge counts.
            entry[2] = now + min(
                self.base_lockout * (2 ** min(over, 30)), self.max_lockout
            )
        self.entries.move_to_end(key)

    def clear(self, key: Hashable) -> None:
        self.entries.pop(key, None)


class LoginThrottle:
    """Per-IP and per-username throttle for failed logins.

    Failed attempts are counted against both the client address and the
    submitted username (whether or not that username exists, so the response
    does not reveal which accounts are real). Once a key has used up its free
    attempts it is locked out with exponential backoff. A successful login
    clears the username counter only; the address counter is left to decay so
    that logging into an account of your own does not unlock guessing against
    others.

    A single instance lives on the application so state is per-server (and thus
    per-test), never module-level. The clock is injectable for tests.
    """

    USER_FREE_ATTEMPTS = 5
    IP_FREE_ATTEMPTS = 20
    BASE_LOCKOUT = 30.0
    MAX_LOCKOUT = 900.0
    DECAY = 900.0
    MAX_ENTRIES = 10_000
    MAX_USERNAME_LENGTH = 256

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._users = _Tracker(
            self.USER_FREE_ATTEMPTS,
            self.BASE_LOCKOUT,
            self.MAX_LOCKOUT,
            self.DECAY,
            self.MAX_ENTRIES,
        )
        self._ips = _Tracker(
            self.IP_FREE_ATTEMPTS,
            self.BASE_LOCKOUT,
            self.MAX_LOCKOUT,
            self.DECAY,
            self.MAX_ENTRIES,
        )

    def _user_key(self, username: str) -> str:
        return str(username)[: self.MAX_USERNAME_LENGTH]

    def retry_after(self, ip: str, username: str) -> int:
        """Seconds the caller must wait before another attempt (0 if allowed).

        :param ip: Client address.
        :param username: Submitted username.
        :return: Whole seconds to wait, rounded up.
        """
        now = self._clock()
        wait = max(
            self._ips.retry_after(ip, now),
            self._users.retry_after(self._user_key(username), now),
        )
        return math.ceil(wait)

    def record_failure(self, ip: str, username: str) -> None:
        """Count a failed login against the address and the username."""
        now = self._clock()
        self._ips.record_failure(ip, now)
        self._users.record_failure(self._user_key(username), now)

    def record_success(self, username: str) -> None:
        """Clear the username's failure counter after a successful login."""
        self._users.clear(self._user_key(username))

    def reset(self) -> None:
        """Forget all state."""
        self._users.entries.clear()
        self._ips.entries.clear()
