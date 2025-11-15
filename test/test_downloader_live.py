import os
import pytest


def test_download_live_real():
    """Integration-style test that fetches real data from yfinance.

    This test is opt-in: to run it set the environment variable
    `RUN_LIVE_TESTS=1` to avoid unintended CI/network failures.
    """
    if os.environ.get("RUN_LIVE_TESTS") != "1":
        pytest.skip("Skipping live yfinance test (set RUN_LIVE_TESTS=1 to enable)")

    from data.downloader import download_ohlcv

    # keep this relatively small to reduce rate-limit exposure
    df = download_ohlcv("0700.HK", period="30d", interval="60m", max_retries=5)
    assert not df.empty
    # print a few lines for developer inspection
    print(df.head().to_string())
