"""轻量速率限制中间件（内存版）"""
import time
import threading
from collections import defaultdict
from typing import Optional

# sliding window: client_ip → [(timestamp, count), ...]
_rate_limit_data: dict[str, list[tuple[float, int]]] = defaultdict(list)
_rate_lock = threading.Lock()


class RateLimiter:
    """滑动窗口速率限制器"""

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.rpm = requests_per_minute
        self.burst = burst  # 允许的突发请求数
        self.window = 60.0  # 窗口大小（秒）

    def is_allowed(self, client_ip: str) -> tuple[bool, dict[str, str]]:
        """检查是否允许请求，返回 (是否允许, headers)"""
        now = time.time()
        with _rate_lock:
            # 清理过期记录
            cutoff = now - self.window
            if client_ip in _rate_limit_data:
                _rate_limit_data[client_ip] = [
                    (ts, cnt) for ts, cnt in _rate_limit_data[client_ip] if ts > cutoff
                ]

            # 统计当前窗口内请求数
            total = sum(cnt for _, cnt in _rate_limit_data[client_ip])

            if total >= self.rpm:
                remaining = 0
                reset_time = int(self.window)
                allowed = False
            else:
                remaining = self.rpm - total
                allowed = True

            # 记录本次请求
            if allowed:
                if client_ip not in _rate_limit_data:
                    _rate_limit_data[client_ip] = []
                _rate_limit_data[client_ip].append((now, 1))

        headers = {
            "X-RateLimit-Limit": str(self.rpm),
            "X-RateLimit-Remaining": str(max(0, remaining - 1)),
            "X-RateLimit-Reset": str(int(now) + self.window),
        }
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
