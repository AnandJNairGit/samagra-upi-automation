"""Thread-safe in-memory sliding window rate limiter for security-sensitive auth endpoints."""

import time
import threading
from typing import Dict, List, Tuple


class InMemoryRateLimiter:
    """Process-local in-memory sliding window rate limiter.

    Note: This provides baseline protection for single-instance deployments.
    For multi-process or distributed setups, this can be swapped with Redis.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: Dict[str, List[float]] = {}

    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """Check if request under key is allowed.

        Returns:
            Tuple[bool, int]: (allowed, retry_after_seconds)
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Clean up old timestamps
            timestamps = self._hits.get(key, [])
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= max_requests:
                # Calculate remaining time until oldest request in window expires
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now) + 1)
                self._hits[key] = valid_timestamps
                return False, retry_after

            valid_timestamps.append(now)
            self._hits[key] = valid_timestamps
            return True, 0

    def reset(self) -> None:
        """Reset all rate limiter state (primarily for tests)."""
        with self._lock:
            self._hits.clear()


# Global rate limiter instance
auth_rate_limiter = InMemoryRateLimiter()
