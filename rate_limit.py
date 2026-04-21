"""In-memory sliding-window rate limit. Fine for single-instance Railway deploy + MVP."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

_WINDOW_SECONDS = 3600
_MAX_PER_WINDOW = 5

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check_and_record(ip: str) -> bool:
    """Returns True if request is allowed, False if over limit."""
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    with _lock:
        bucket = _buckets[ip]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= _MAX_PER_WINDOW:
            return False
        bucket.append(now)
        return True
