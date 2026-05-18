"""轻量速率限制中间件（内存版）"""
import time
import threading
from typing import Optional

# token bucket: client_ip → (tokens, last_refill_timestamp)
_rate_limit_data: dict[str, tuple[float, float]] = {}
_rate_lock = threading.Lock()


class RateLimiter:
    """令牌桶速率限制器"""

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.rpm = max(1, int(requests_per_minute))
        self.burst = max(1, int(burst))
        self.refill_rate = self.rpm / 60.0

    def is_allowed(self, client_ip: str) -> tuple[bool, dict[str, str]]:
        """检查是否允许请求，返回 (是否允许, headers)"""
        now = time.time()
        with _rate_lock:
            tokens, last_refill = _rate_limit_data.get(client_ip, (float(self.burst), now))
            elapsed = max(0.0, now - last_refill)
            tokens = min(float(self.burst), tokens + elapsed * self.refill_rate)

            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0
            else:
                retry_after = max(1, int((1.0 - tokens) / self.refill_rate) + 1)

            _rate_limit_data[client_ip] = (tokens, now)
            remaining = int(tokens)
            reset_after = int((self.burst - tokens) / self.refill_rate) if tokens < self.burst else 0

        headers = {
            "X-RateLimit-Limit": str(self.rpm),
            "X-RateLimit-Burst": str(self.burst),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(now) + reset_after),
        }
        if not allowed:
            headers["Retry-After"] = str(retry_after)
        return allowed, headers

    def clear(self):
        """清空所有记录（测试用）"""
        with _rate_lock:
            _rate_limit_data.clear()


_limiter: Optional[RateLimiter] = None


def get_limiter() -> Optional[RateLimiter]:
    return _limiter


def init_limiter(requests_per_minute: int = 60, burst: int = 10):
    global _limiter
    _limiter = RateLimiter(requests_per_minute, burst)


def clear_limiter():
    global _limiter
    if _limiter:
        _limiter.clear()
