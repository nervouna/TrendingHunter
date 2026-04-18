import time
from unittest.mock import MagicMock, patch

import anthropic

from trending_hunter.llm.client import _retry_call


def test_retry_call_succeeds_first_try():
    fn = MagicMock(return_value="ok")
    result = _retry_call(fn, max_retries=3)
    assert result == "ok"
    fn.assert_called_once()


def test_retry_call_retries_on_connection_error():
    fn = MagicMock(side_effect=[anthropic.APIConnectionError(request=MagicMock()), "ok"])
    with patch("time.sleep"):
        result = _retry_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_call_retries_on_rate_limit():
    fn = MagicMock(side_effect=[anthropic.RateLimitError(message="rate limited", response=MagicMock(), body=None), "ok"])
    with patch("time.sleep"):
        result = _retry_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.call_count == 2


def test_retry_call_raises_on_status_error():
    fn = MagicMock(side_effect=anthropic.APIStatusError(message="400", response=MagicMock(), body=None))
    try:
        _retry_call(fn, max_retries=3)
        assert False, "Should have raised"
    except anthropic.APIStatusError:
        pass
    fn.assert_called_once()


def test_retry_call_exhausts_retries():
    fn = MagicMock(side_effect=anthropic.APIConnectionError(request=MagicMock()))
    with patch("time.sleep"):
        try:
            _retry_call(fn, max_retries=3)
            assert False, "Should have raised"
        except anthropic.APIConnectionError:
            pass
    assert fn.call_count == 3
