"""Unit tests for retry-with-backoff utility."""

import pytest

from reddit_automation.utils.retry import retry_with_backoff


class TestRetryWithBackoff:
    def test_succeeds_on_first_attempt(self):
        call_count = [0]

        def success():
            call_count[0] += 1
            return "ok"

        result = retry_with_backoff(success, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count[0] == 1

    def test_retries_then_succeeds(self):
        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("transient")
            return "recovered"

        result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "recovered"
        assert call_count[0] == 3

    def test_raises_after_exhausting_retries(self):
        call_count = [0]

        def always_fails():
            call_count[0] += 1
            raise ConnectionError("down")

        with pytest.raises(ConnectionError, match="down"):
            retry_with_backoff(always_fails, max_retries=3, base_delay=0.01)
        assert call_count[0] == 3

    def test_does_not_retry_non_retryable_exception(self):
        call_count = [0]

        def bad_value():
            call_count[0] += 1
            raise ValueError("bad")

        with pytest.raises(ValueError, match="bad"):
            retry_with_backoff(bad_value, max_retries=3, base_delay=0.01)
        assert call_count[0] == 1

    def test_custom_retryable_exceptions(self):
        call_count = [0]

        def flaky_http():
            call_count[0] += 1
            if call_count[0] < 2:
                raise OSError("timeout")
            return "done"

        result = retry_with_backoff(
            flaky_http,
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(OSError,),
        )
        assert result == "done"

    def test_backoff_delay_increases(self):
        sleep_calls = []

        def failing():
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            retry_with_backoff(failing, max_retries=4, base_delay=0.1, sleep_fn=sleep_calls.append)
        # 3 sleep calls between 4 attempts
        assert len(sleep_calls) == 3
        # Delays: 0.1, 0.2, 0.4
        assert sleep_calls == [0.1, 0.2, 0.4]
