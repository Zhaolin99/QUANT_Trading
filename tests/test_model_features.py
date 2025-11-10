import pandas as pd


def make_simple_ohlcv(n=300):
    idx = pd.date_range('2024-01-01', periods=n, freq='H')
    # simple walk-forward close price
    close = (1 + pd.Series(range(n)).pct_change().fillna(0)).cumprod() * 100
    vol = pd.Series(1000, index=idx)
    df = pd.DataFrame({'Close': close.values, 'Volume': vol.values}, index=idx)
    return df


def test_build_features_basic():
    from models.logistic_model import build_features

    df = make_simple_ohlcv(300)
    data = build_features(df)
    # data should contain the target y and some features
    assert 'y' in data.columns
    assert len(data) > 0

