"""Data downloading and timezone handling utilities."""
from __future__ import annotations


from typing import Literal
import time
import pandas as pd
import yfinance as yf
from zoneinfo import ZoneInfo
import os
from datetime import datetime
from typing import Optional


HK_TZ = ZoneInfo("Asia/Hong_Kong")


def load_local_ohlcv(symbol: str, data_dir: str = "data") -> Optional[pd.DataFrame]:
	"""Load a local CSV for `symbol` if present in `data_dir`.

	Expected CSV format (per repository convention):
	- columns: date, Close, High, Low, Open, Volume
	- date may be a column named 'date' (case-insensitive) or the first column as index
	- returns a DataFrame with columns [Open, High, Low, Close, Volume] and
	  a DatetimeIndex (tz-naive). If the file is not found, returns None.
	"""
	# Normalize symbol filename
	fname = os.path.join(data_dir, f"{symbol}.csv")
	if not os.path.exists(fname):
		return None

	# Try reading and normalizing columns
	try:
		df = pd.read_csv(fname)
	except Exception:
		return None

	# Detect date column
	date_col = None
	cols_lower = [c.lower() for c in df.columns]
	if "date" in cols_lower:
		date_col = df.columns[cols_lower.index("date")]
		df[date_col] = pd.to_datetime(df[date_col])
		df = df.set_index(date_col)
	else:
		# assume first column is date/index
		try:
			df = pd.read_csv(fname, index_col=0, parse_dates=True)
		except Exception:
			return None

	# Ensure columns exist and reorder to Open, High, Low, Close, Volume
	col_map = {c.lower(): c for c in df.columns}
	required = ["open", "high", "low", "close", "volume"]
	if not all(k in col_map for k in required):
		# try common alternative ordering (date, Close, High, Low, Open, Volume)
		# if still not matching, raise
		raise ValueError(f"Local CSV {fname} missing required OHLCV columns: {df.columns.tolist()}")

	df = df[[col_map["open"], col_map["high"], col_map["low"], col_map["close"], col_map["volume"]]]
	df.columns = ["Open", "High", "Low", "Close", "Volume"]

	# Leave index tz-naive per user instruction
	if not isinstance(df.index, pd.DatetimeIndex):
		df.index = pd.to_datetime(df.index)

	# drop rows with missing essential values
	df = df.dropna()

	if df.empty:
		raise ValueError(f"Local CSV {fname} is empty after processing.")

	return df




def download_ohlcv(
	symbol: str,
	period: str = "730d",
	interval: Literal["1d", "60m", "30m", "15m", "5m", "1m"] = "60m",
	auto_adjust: bool = True,
	max_retries: int = 3,
	backoff_sec: float = 1.0,
	force_remote: bool = False,
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

	# If a local CSV exists for the symbol, prefer loading it (user-provided data).
	local = load_local_ohlcv(symbol)
	if local is not None:
		return local

	# Wrap yfinance call with simple retry/backoff to handle transient rate limits

	# Prefer local CSV when present unless caller forces remote
	if not force_remote:
		local = load_local_ohlcv(symbol)
		if local is not None:
			# ensure columns are in expected order
			cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in local.columns]
			out = local[cols].dropna()
			if out.empty:
				raise ValueError(f"Local CSV for {symbol} found but contains no usable rows.")
			return out
	last_exc = None
	for attempt in range(1, max_retries + 1):
		try:
			df = yf.download(
				symbol, period=period, interval=interval, auto_adjust=auto_adjust, progress=False
			)
			if df is None or df.empty:
				raise ValueError(
					f"Empty data from yfinance for {symbol} (period={period}, interval={interval}). "
					"Try shortening period or switching interval."
				)
			# success
			last_exc = None
			break
		except Exception as exc:  # pragma: no cover - network related
			last_exc = exc
			if attempt < max_retries:
				sleep = backoff_sec * (2 ** (attempt - 1))
				# exponential backoff
				time.sleep(sleep)
				continue
			# no more retries, re-raise for the caller to handle
			raise

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


def load_local_ohlcv(symbol: str, data_dir: str = "data") -> Optional[pd.DataFrame]:
	"""Load a local CSV for `symbol` if present.

	The function looks for filenames in this order:
	  1. {data_dir}/{symbol}.csv
	  2. {data_dir}/{symbol}_historical_data.csv

	Expected CSV format (as provided by the user):
	  - columns: date, Close, High, Low, Open, Volume
	  - daily bars, date column is parsed as index
	  - tz is ignored (tz-naive)

	Returns a DataFrame with columns ordered as [Open, High, Low, Close, Volume]
	and a DatetimeIndex, or None if no local file is found.
	"""
	candidates = [
		os.path.join(data_dir, f"{symbol}.csv"),
		os.path.join(data_dir, f"{symbol}_historical_data.csv"),
	]

	for path in candidates:
		if os.path.exists(path):
			# Some CSVs may contain multi-line headers (e.g. 'Price,Close,...' then 'Ticker,...' then 'Date')
			# We'll scan for the first data line that looks like a date (YYYY-)
			import io
			import re

			with open(path, "r", encoding="utf-8", errors="ignore") as fh:
				lines = fh.readlines()

			# find first line that starts with a date-like token
			data_start = None
			date_re = re.compile(r"^\d{4}-\d{2}-\d{2}")
			for i, line in enumerate(lines):
				if date_re.match(line.strip()):
					data_start = i
					break

			if data_start is None:
				# fallback: try pandas normal read and hope for the best
				df = pd.read_csv(path)
			else:
				data_text = "".join(lines[data_start:])
				df = pd.read_csv(io.StringIO(data_text), header=None)
				# assign expected columns: date, Close, High, Low, Open, Volume
				expected = ["date", "Close", "High", "Low", "Open", "Volume"]
				if df.shape[1] >= 6:
					df = df.iloc[:, :6]
					df.columns = expected
				else:
					# if malformed, try a normal read and continue
					df = pd.read_csv(path)

			# assume first column is date if named 'date' or not
			if "date" in df.columns:
				df = df.set_index("date")
			else:
				df = df.set_index(df.columns[0])

			# normalize column names
			df = df.rename(columns={
				"close": "Close",
				"open": "Open",
				"high": "High",
				"low": "Low",
				"volume": "Volume",
			})

			# keep required columns and order
			cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
			df = df[cols].copy()

			# ensure datetimeindex
			if not isinstance(df.index, pd.DatetimeIndex):
				df.index = pd.to_datetime(df.index)

			# return tz-naive daily bars (user requested to ignore tz)
			return df

	return None


def download_ohlcv_chunked(
	symbol: str,
	start: Optional[str] = None,
	end: Optional[str] = None,
	period: Optional[str] = None,
	interval: Literal["1d", "60m", "30m", "15m", "5m", "1m"] = "1d",
	chunk_years: int = 1,
	chunk_months: Optional[int] = None,
	cache_dir: str = "data/cache",
	max_retries: int = 6,
	backoff_sec: float = 2.0,
) -> pd.DataFrame:
	"""Download OHLCV in time chunks and optionally cache each chunk.

	This splits the requested time range into pieces (by years) and downloads
	each piece separately. This helps avoid rate-limits for very long periods
	(for example 10-15 years of daily bars).

	Parameters
	----------
	symbol, interval: same as `download_ohlcv`.
	start, end: ISO date strings (YYYY-MM-DD). If omitted and `period` is
		provided, `period` will be used to compute start relative to now.
	period: yfinance-style period (e.g., "15y"). Used only when start is None.
	chunk_years: number of years per chunk (default 1).
	cache_dir: directory to save per-chunk cache files (.parquet preferred,
		falls back to .csv if parquet support missing).
	max_retries, backoff_sec: retry/backoff for each chunk.

	Returns
	-------
	pd.DataFrame
		Combined DataFrame with Open/High/Low/Close/Volume indexed by tz-aware
		DatetimeIndex in Asia/Hong_Kong.
	"""
	os.makedirs(cache_dir, exist_ok=True)

	# Resolve start/end from period if necessary
	now = pd.Timestamp.now(tz=HK_TZ)
	if start is None:
		if period is None:
			raise ValueError("Either start/end or period must be provided.")
		# simple handler for '<N>y' periods
		if isinstance(period, str) and period.endswith("y"):
			years = int(period[:-1])
			start_ts = (now - pd.DateOffset(years=years)).normalize()
		else:
			# fallback: ask yfinance to interpret period by using download_ohlcv
			# with the whole period in one shot
			return download_ohlcv(symbol, period=period, interval=interval, max_retries=max_retries, backoff_sec=backoff_sec)
	else:
		start_ts = pd.to_datetime(start).tz_localize(HK_TZ) if pd.to_datetime(start).tzinfo is None else pd.to_datetime(start)

	if end is None:
		end_ts = now
	else:
		end_ts = pd.to_datetime(end).tz_localize(HK_TZ) if pd.to_datetime(end).tzinfo is None else pd.to_datetime(end)

	# build chunk boundaries
	chunks = []
	cur_start = start_ts
	while cur_start < end_ts:
		if chunk_months is not None and chunk_months > 0:
			cur_end = cur_start + pd.DateOffset(months=chunk_months) - pd.Timedelta(days=1)
		else:
			cur_end = cur_start + pd.DateOffset(years=chunk_years) - pd.Timedelta(days=1)
		if cur_end > end_ts:
			cur_end = end_ts
		chunks.append((cur_start, cur_end))
		cur_start = cur_end + pd.Timedelta(days=1)

	frames = []
	for s_ts, e_ts in chunks:
		s_str = s_ts.strftime("%Y-%m-%d")
		e_str = e_ts.strftime("%Y-%m-%d")
		cache_file_parquet = os.path.join(cache_dir, f"{symbol.replace('/','_')}_{s_str}_{e_str}.parquet")
		cache_file_csv = os.path.join(cache_dir, f"{symbol.replace('/','_')}_{s_str}_{e_str}.csv")

		# try cache
		if os.path.exists(cache_file_parquet):
			try:
				df_chunk = pd.read_parquet(cache_file_parquet)
				frames.append(df_chunk)
				continue
			except Exception:
				pass
		if os.path.exists(cache_file_csv):
			try:
				df_chunk = pd.read_csv(cache_file_csv, index_col=0, parse_dates=True)
				# ensure tz
				if df_chunk.index.tz is None:
					df_chunk = df_chunk.tz_localize(HK_TZ)
				frames.append(df_chunk)
				continue
			except Exception:
				pass

		# no cache: download single chunk with retries
		last_exc = None
		for attempt in range(1, max_retries + 1):
			try:
				df_chunk = yf.download(symbol, start=s_str, end=(pd.to_datetime(e_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), interval=interval, auto_adjust=True, progress=False)
				if df_chunk is None or df_chunk.empty:
					raise ValueError(f"Empty data from yfinance for {symbol} (start={s_str}, end={e_str}, interval={interval}).")
				last_exc = None
				break
			except Exception as exc:  # pragma: no cover - network related
				last_exc = exc
				if attempt < max_retries:
					sleep = backoff_sec * (2 ** (attempt - 1))
					time.sleep(sleep)
					continue
				raise

		# tz handling
		if df_chunk.index.tz is None:
			df_chunk = df_chunk.tz_localize("UTC").tz_convert(HK_TZ)

		df_chunk = df_chunk[["Open", "High", "Low", "Close", "Volume"]].dropna()

		# cache chunk: prefer parquet, fall back to csv
		try:
			df_chunk.to_parquet(cache_file_parquet)
		except Exception:
			try:
				df_chunk.to_csv(cache_file_csv)
			except Exception:
				# ignore caching errors
				pass

		frames.append(df_chunk)

	if not frames:
		raise ValueError("No data frames were downloaded; try shorter chunks or increase retries.")

	# concat, sort, dedupe by index
	df_all = pd.concat(frames).sort_index()
	df_all = df_all[~df_all.index.duplicated(keep="first")]

	if df_all.index.tz is None:
		df_all = df_all.tz_localize(HK_TZ)

	return df_all