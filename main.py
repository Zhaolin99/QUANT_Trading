import argparse
from data.downloader import download_ohlcv
from models.logistic_model import train_predict
from signals.adapter import to_entries_exits
from backtest.vectorbt_engine import run_backtest
from config import DEFAULT_CONFIG

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="0700.HK")
    parser.add_argument("--period", default="730d")
    parser.add_argument("--interval", default="60m")
    parser.add_argument("--proba_th", type=float, default=0.55)
    args = parser.parse_args()

    df = download_ohlcv(args.symbol, args.period, args.interval)
    idx, proba = train_predict(df, DEFAULT_CONFIG["train_ratio"])
    close = df["Close"].reindex(idx)

    entries, exits = to_entries_exits(proba, args.proba_th)
    pf, stats, win_rate = run_backtest(close, entries, exits,
        DEFAULT_CONFIG["init_cash"],
        DEFAULT_CONFIG["freq"]
    )

    print(stats[["Total Return [%]","CAGR","Max Drawdown [%]"]])
    print("Win rate:", win_rate)

if __name__ == "__main__":
    main()

