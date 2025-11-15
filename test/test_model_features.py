import pandas as pd


def make_simple_ohlcv(n=300):
    idx = pd.date_range('2024-01-01', periods=n, freq='H')
    # deterministic increasing close price
    close = pd.Series([100 + i * 0.1 for i in range(n)], index=idx)
    vol = pd.Series(1000, index=idx)
    df = pd.DataFrame({'Close': close.values, 'Volume': vol.values}, index=idx)
    return df


def test_build_features_basic():
    from models.logistic_model import build_features

    # use a larger series so rolling windows produce enough rows
    df = make_simple_ohlcv(500)
    data = build_features(df)
    # data should contain the target y and some features
    assert 'y' in data.columns
    assert len(data) > 0

