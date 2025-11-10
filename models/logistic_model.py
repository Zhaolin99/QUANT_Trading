"""Lightweight ML model (Logistic Regression) for direction classification.


This module focuses on producing a probability of next-bar up move (proba_up).
Replace this file later with time-series Transformers / XGBoost / etc.
"""
from __future__ import annotations


from typing import Tuple
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create minimal feature set and labeled target.


    Notes
    -----
    - All features are shifted by 1 to avoid lookahead bias.
    - Target y = 1 if next bar return > 0 else 0.
    - Requires enough history for rolling windows.
    """
    c = df["Close"]


    # Minimal but robust features
    feat = pd.DataFrame(
        {
            "ret1": c.pct_change(),  # 1-bar return
            "ret2": c.pct_change(2),  # 2-bar return
            "ma_gap": (c.rolling(5).mean() / c.rolling(20).mean()) - 1.0,
            "ma_slope": c.rolling(5).mean().pct_change(),  # slope of short MA
            "vol20": c.pct_change().rolling(20).std(),  # realized volatility
            "volchg": df["Volume"].pct_change(),  # volume change
        },
        index=df.index,
    ).shift(1)  # shift to ensure only past info is used


    y = (c.pct_change().shift(-1) > 0).astype(int).rename("y")


    data = pd.concat([feat, y], axis=1).dropna()


    # sanity check: must have enough rows for training
    if len(data) < 200:
        raise ValueError(
            "Not enough rows after feature engineering; reduce windowing or extend period."
        )


    return data




def train_predict(df: pd.DataFrame, train_ratio: float = 0.7, seed: int = 42) -> Tuple[pd.DatetimeIndex, pd.Series]:
    """Train logistic regression on early segment and predict proba on later segment.

    Parameters
    ----------
    df : pd.DataFrame
    OHLCV dataframe (tz-aware, HK time) with columns including `Close` and `Volume`.
    train_ratio : float
    Split ratio in time order; early part for training.
    seed : int
    Random seed for reproducibility.


    Returns
    -------
    Tuple[pd.DatetimeIndex, pd.Series]
    (test_index, proba_up), where proba_up is aligned with test timestamps.
    """
    data = build_features(df)
    split = int(len(data) * train_ratio)


    train = data.iloc[:split]
    test = data.iloc[split:]


    X_train = train.drop(columns="y")
    y_train = train["y"]
    X_test = test.drop(columns="y")


    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, random_state=seed)),
        ]
    )
    model.fit(X_train, y_train)


    proba_up = pd.Series(model.predict_proba(X_test)[:, 1], index=X_test.index, name="proba_up")
    return X_test.index, proba_up
