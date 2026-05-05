from dataclasses import dataclass
from time import time


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[float, int]] = {}

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitDecision:
        now = time()
        start, count = self._windows.get(key, (now, 0))
        if now - start >= window_seconds:
            self._windows[key] = (now, 1)
            return RateLimitDecision(True)
        if count >= limit:
            retry_after = max(1, int(window_seconds - (now - start)))
            return RateLimitDecision(False, retry_after)
        self._windows[key] = (start, count + 1)
        return RateLimitDecision(True)
