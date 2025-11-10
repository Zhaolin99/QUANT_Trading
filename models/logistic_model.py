import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def build_features(df):
    c = df["Close"]
    feat = pd.DataFrame({
        "ret1": c.pct_change(),
        "ma_slope": c.rolling(5).mean().pct_change(),
        "vol20": c.pct_change().rolling(20).std()
    }).shift(1)
    y = (c.pct_change().shift(-1) > 0).astype(int)
    return pd.concat([feat, y.rename("y")], axis=1).dropna()

def train_predict(df, train_ratio=0.7, seed=42):
    data = build_features(df)
    split = int(len(data) * train_ratio)
    train, test = data.iloc[:split], data.iloc[split:]

    X_train, y_train = train.drop("y", axis=1), train["y"]
    X_test = test.drop("y", axis=1)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=500, random_state=seed))
    ])
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:,1]

    return test.index, pd.Series(proba, index=test.index, name="proba_up")

