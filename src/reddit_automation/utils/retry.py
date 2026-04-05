"""Retry-with-backoff utility for transient error recovery."""

import time


DEFAULT_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    OSError,
    TimeoutError,
)


def retry_with_backoff(
    fn,
    max_retries: int = 3,
    base_delay: float = 2.0,
    retryable_exceptions: tuple = None,
    sleep_fn=None,
):
    """Execute fn() with exponential backoff on transient errors.
    
    On success, returns the result immediately.
    On failure, retries up to max_retries times with increasing delay.
    After exhausting retries, re-raises the last exception.
    Non-retryable exceptions are raised immediately without retry.
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    last_exc = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                if sleep_fn:
                    sleep_fn(delay)
                else:
                    time.sleep(delay)
            # On final attempt, fall through to raise
    
    raise last_exc
