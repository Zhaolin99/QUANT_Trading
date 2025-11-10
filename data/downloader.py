"""Data downloading and timezone handling utilities."""
from __future__ import annotations


from typing import Literal
import pandas as pd
import yfinance as yf
from zoneinfo import ZoneInfo


HK_TZ = ZoneInfo("Asia/Hong_Kong")




def download_ohlcv(
	symbol: str,
	period: str = "730d",
	interval: Literal["1d", "60m", "30m", "15m", "5m", "1m"] = "60m",
	auto_adjust: bool = True,
) -> pd.DataFrame:
	"""Download OHLCV for a single symbol using yfinance and convert to HK timezone.


	Parameters
	----------
	symbol : str
		Ticker (e.g., "0700.HK").
	period : str
		yfinance period window (e.g., "730d", "365d").
	interval : {"1d","60m","30m","15m","5m","1m"}
		Bar interval.
	auto_adjust : bool
		Adjust OHLC for splits/dividends.


	Returns
	-------
	pd.DataFrame
		Columns: Open, High, Low, Close, Volume (tz-aware in Asia/Hong_Kong).
	"""
	df = yf.download(
		symbol, period=period, interval=interval, auto_adjust=auto_adjust, progress=False
	)
	if df is None or df.empty:
		raise ValueError(
			f"Empty data from yfinance for {symbol} (period={period}, interval={interval}). "
			"Try shortening period or switching interval."
		)

	# Ensure timezone-awareness and convert to HK time
	if df.index.tz is None:
		# yfinance intraday often returns UTC-naive; assume UTC
		df = df.tz_localize("UTC")
		df = df.tz_convert(HK_TZ)

	# Keep standard columns only
	cols = ["Open", "High", "Low", "Close", "Volume"]
	df = df[cols].dropna()

	if df.empty:
		raise ValueError("DataFrame became empty after column selection / dropna.")

	return df