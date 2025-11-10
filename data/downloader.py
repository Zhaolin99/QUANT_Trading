import yfinance as yf
from zoneinfo import ZoneInfo

def download_ohlcv(symbol, period="730d", interval="60m"):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    return df.tz_convert(ZoneInfo("Asia/Hong_Kong"))[["Open","High","Low","Close","Volume"]].dropna()

