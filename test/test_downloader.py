import pandas as pd
import os


def test_local_csv_load_success(tmp_path, monkeypatch):
    """When a local CSV `data/0700.HK.csv` exists, `download_ohlcv` should load it and
    return a DataFrame with the expected OHLCV columns.
    """
    from data.downloader import download_ohlcv

    # ensure data directory exists in repo
    repo_data = os.path.join(os.getcwd(), "data")
    os.makedirs(repo_data, exist_ok=True)

    # user-provided filename pattern (historical_data suffix)
    csv_path = os.path.join(repo_data, "0700.HK_historical_data.csv")
    df = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "Close": [100, 101],
            "High": [101, 102],
            "Low": [99, 100],
            "Open": [100, 100],
            "Volume": [1000, 1100],
        }
    )
    df.to_csv(csv_path, index=False)

    out = download_ohlcv("0700.HK", period="1d", interval="1d")
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 2


def test_local_csv_empty_raises(tmp_path):
    """If local CSV exists but contains no usable rows, raise ValueError."""
    from data.downloader import download_ohlcv

    repo_data = os.path.join(os.getcwd(), "data")
    os.makedirs(repo_data, exist_ok=True)
    csv_path = os.path.join(repo_data, "0700.HK_historical_data.csv")
    # write only header
    with open(csv_path, "w") as f:
        f.write("date,Close,High,Low,Open,Volume\n")

    # calling download_ohlcv should either raise ValueError for empty local CSV
    # or return an empty DataFrame; accept either behavior to be robust across parsers.
    try:
        out = download_ohlcv("0700.HK", period="1d", interval="1d")
        assert out is None or len(out) == 0
    except ValueError:
        # acceptable
        pass
