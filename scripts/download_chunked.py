"""Small CLI to download large ranges in chunks and show a short preview.

Usage (from project root, using the repo virtualenv):

.venv/bin/python scripts/download_chunked.py --symbol 0700.HK --period 15y --interval 1d --chunk-years 1

"""
from __future__ import annotations

import argparse
from data.downloader import download_ohlcv_chunked


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--period", default=None)
    p.add_argument("--interval", default="1d")
    p.add_argument("--chunk-years", type=int, default=1)
    p.add_argument("--chunk-months", type=int, default=None,
                   help="If provided, chunk by months instead of years (eg 6 for 6-month chunks)")
    p.add_argument("--prefer-local", action="store_true", default=True,
                   help="If set (default), prefer loading local CSVs from data/ and skip downloads.")
    p.add_argument("--cache-dir", default="data/cache")
    p.add_argument("--max-retries", type=int, default=6)
    p.add_argument("--backoff-sec", type=float, default=2.0)

    args = p.parse_args()

    # If user prefers local and the symbol CSV exists, load it directly
    if args.prefer_local:
        try:
            from data.downloader import load_local_ohlcv

            local = load_local_ohlcv(args.symbol)
            if local is not None:
                print(f"Loaded local CSV for {args.symbol}, rows={len(local)}")
                print(local.head().to_string())
                return
        except Exception:
            # fall back to chunked download if local load fails
            pass

    df = download_ohlcv_chunked(
        args.symbol,
        start=args.start,
        end=args.end,
        period=args.period,
        interval=args.interval,
        chunk_years=args.chunk_years,
        chunk_months=args.chunk_months,
        cache_dir=args.cache_dir,
        max_retries=args.max_retries,
        backoff_sec=args.backoff_sec,
    )

    print(f"Combined rows: {len(df)}")
    print("HEAD:")
    print(df.head().to_string())
    print("\nTAIL:")
    print(df.tail().to_string())


if __name__ == "__main__":
    main()
