#!/usr/bin/env python3
"""Small utility to download OHLCV via yfinance and produce a simple HTML price chart.

Usage:
  python scripts/plot_price.py --symbol 0700.HK --period 90d --interval 60m --out charts/0700.html --open

This script uses the project's `data.downloader.download_ohlcv` so it benefits from
the retry/backoff wrapper.
"""
from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

import plotly.express as px

from data.downloader import download_ohlcv


def main() -> None:
    parser = argparse.ArgumentParser(description="Download OHLCV and plot Close price")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--period", default="90d")
    parser.add_argument("--interval", default="60m")
    parser.add_argument("--out", default="charts/price_chart.html")
    parser.add_argument("--open", action="store_true", help="Open the generated HTML in the browser")
    parser.add_argument("--max-retries", type=int, default=5)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {args.symbol} {args.interval} for {args.period} ...")
    df = download_ohlcv(args.symbol, period=args.period, interval=args.interval, max_retries=args.max_retries)

    if df.empty:
        raise SystemExit("No data returned")

    # prepare for plotting
    df_reset = df.reset_index()
    time_col = df_reset.columns[0]

    fig = px.line(df_reset, x=time_col, y="Close", title=f"{args.symbol} Close ({args.interval})")
    fig.update_layout(xaxis_title="Datetime", yaxis_title="Close")
    fig.write_html(out_path)

    print(f"Wrote chart to {out_path}")
    if args.open:
        webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
