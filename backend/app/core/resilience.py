import asyncio
import time
import functools
import logging
from enum import Enum

logger = logging.getLogger("orion.resilience")

def with_retry(max_attempts: int = 3, backoff_seconds: float = 1.5, exceptions: tuple = (Exception,)):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    wait = backoff_seconds * (2 ** (attempt - 1))
                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt}/{max_attempts} "
                        f"failed ({type(e).__name__}), retrying in {wait:.1f}s..."
                    )
                    await asyncio.sleep(wait)
        return wrapper
    return decorator

async def with_timeout(coro, seconds: float = 8.0, fallback=None):
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        logger.error(f"[Timeout] Coroutine timed out after {seconds}s")
        if fallback is not None:
            return fallback
        raise

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation — requests pass through
    OPEN = "open"            # Service is failing — reject immediately
    HALF_OPEN = "half_open"  # Recovery test — allow one request through

class CircuitBreaker:

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def call(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                elapsed = time.time() - (self.last_failure_time or 0)
                if elapsed > self.recovery_timeout:
                    logger.info(
                        f"[CircuitBreaker] Recovery timeout elapsed — entering HALF_OPEN"
                    )
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_timeout - elapsed
                    logger.warning(
                        f"[CircuitBreaker] OPEN — rejecting call. "
                        f"Recovery in {remaining:.0f}s"
                    )
                    raise RuntimeError(
                        f"Circuit breaker OPEN — service unavailable "
                        f"(recovery in {remaining:.0f}s)"
                    )

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception:
                self._on_failure()
                raise

        return wrapper

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("[CircuitBreaker] Probe succeeded — circuit CLOSED")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"[CircuitBreaker] Failure threshold ({self.failure_threshold}) "
                f"reached — circuit OPEN for {self.recovery_timeout}s"
            )
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("[CircuitBreaker] Probe failed — circuit re-OPENED")

    def reset(self):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("[CircuitBreaker] Manually reset to CLOSED")

groq_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
