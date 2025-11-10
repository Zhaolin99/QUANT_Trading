"""Project entry point: download data → train model → generate signals → backtest."""
from __future__ import annotations


import argparse
from typing import List


from data.downloader import download_ohlcv
from models.logistic_model import train_predict
from signals.adapter import to_entries_exits
from backtest.vectorbt_engine import run_backtest
from config import DEFAULT_CONFIG

# ---------------- CLI ---------------- #


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for a single-symbol backtest run."""
    parser = argparse.ArgumentParser(description="HK 60m ML backtest")
    parser.add_argument("--symbol", default="0700.HK", help="Ticker, e.g., 0700.HK")
    parser.add_argument("--period", default="730d", help="yfinance period, e.g., 730d/365d")
    parser.add_argument("--interval", default="60m", help="Bar interval, e.g., 60m or 1d")
    parser.add_argument("--proba_th", type=float, default=0.55, help="Probability threshold for long entries")
    parser.add_argument("--train_ratio", type=float, default=DEFAULT_CONFIG["train_ratio"], help="Train split ratio")
    return parser.parse_args()




def safe_print_stats(stats) -> None:
    """Print a few key stats without assuming exact keys (version-proof)."""
    candidates = [
        "CAGR",
        "Annual Return [%]",
        "Total Return [%]",
        "Max Drawdown [%]",
    ]
    print("\n===== Quick Stats =====")
    for key in candidates:
        if key in stats.index:
            print(f"{key}: {stats.loc[key]}")


# -------------- Main -------------- #
def main() -> None:
    args = parse_args()

    # 1) Data
    df = download_ohlcv(args.symbol, args.period, args.interval)

    # 2) Train + Predict (model outputs proba for the test range)
    test_index, proba_up = train_predict(df, train_ratio=args.train_ratio)

    # 3) Align Close price with model output timeline
    close = df["Close"].reindex(test_index)

    # 4) Convert model output to entries/exits
    entries, exits = to_entries_exits(proba_up, args.proba_th)

    # 5) Backtest
    pf, stats, win_rate = run_backtest(
        close,
        entries,
        exits,
        cash=DEFAULT_CONFIG["init_cash"],
        freq=DEFAULT_CONFIG["freq"],
    )

    # 6) Report
    safe_print_stats(stats)
    if win_rate is not None:
        print(f"Win Rate: {win_rate:.2%}")


if __name__ == "__main__":
    main()
