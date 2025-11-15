import pandas as pd


def _make_sample_df():
    idx = pd.date_range('2025-01-01 09:00', periods=4, freq='60min')
    return pd.DataFrame(
        {
            'Open': [100, 101, 102, 103],
            'High': [101, 102, 103, 104],
            'Low': [99, 100, 101, 102],
            'Close': [100, 101, 102, 103],
            'Volume': [1000, 1100, 1200, 1300],
        },
        index=idx,
    )


def test_retry_succeeds_after_transient(monkeypatch):
    """Simulate yfinance raising on early calls then succeeding; downloader should retry and succeed."""
    from data.downloader import download_ohlcv

    # ensure local CSV is not used in this test
    monkeypatch.setattr('data.downloader.load_local_ohlcv', lambda s: None)

    calls = {'n': 0}

    def fake_download(symbol, period, interval, auto_adjust, progress):
        calls['n'] += 1
        if calls['n'] < 3:
            raise RuntimeError('Simulated rate limit')
        return _make_sample_df()

    monkeypatch.setattr('yfinance.download', fake_download)

    # should succeed when max_retries >= 3
    out = download_ohlcv('0700.HK', period='1d', interval='60m', max_retries=4, backoff_sec=0.01)
    assert list(out.columns) == ['Open', 'High', 'Low', 'Close', 'Volume']
    assert len(out) == 4


def test_retry_exhausts_and_raises(monkeypatch):
    """If yfinance keeps failing, downloader should raise after retries are exhausted."""
    from data.downloader import download_ohlcv

    # ensure local CSV is not used in this test
    monkeypatch.setattr('data.downloader.load_local_ohlcv', lambda s: None)

    def always_fail(*args, **kwargs):
        raise RuntimeError('Always fail')

    monkeypatch.setattr('yfinance.download', always_fail)

    raised = False
    try:
        download_ohlcv('0700.HK', period='1d', interval='60m', max_retries=2, backoff_sec=0.01)
    except Exception:
        raised = True

    assert raised
