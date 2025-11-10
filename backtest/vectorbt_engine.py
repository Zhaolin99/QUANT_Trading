"""VectorBT backtesting helpers."""
from __future__ import annotations


from typing import Tuple, Optional
import numpy as np
import pandas as pd
import vectorbt as vbt

def run_backtest(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    cash: float = 100_000.0,
    freq: str = "H",
) -> Tuple[vbt.portfolio.base.Portfolio, pd.Series, Optional[float]]:
    """Run a simple long-only backtest using entries/exits.


    Parameters
    ----------
    close : pd.Series
    Price series (tz-aware) aligned to entries/exits index.
    entries : pd.Series
    Boolean series: True where we enter long.
    exits : pd.Series
    Boolean series: True where we exit (shifted already to avoid conflict).
    cash : float
    Initial cash.
    freq : str
    Bar frequency string to help annualization in stats.


    Returns
    -------
    (pf, stats, win_rate)
    pf : vectorbt Portfolio
    stats : pd.Series of summary metrics
    win_rate : float in [0,1] or None if no trades
    """
    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=cash,
        fees=0.0,
        slippage=0.0,
        freq=freq,
    )


    stats = pf.stats()


    # Defensive win-rate calculation across vectorbt versions
    win_rate = None
    try:
        recs = pf.trades.records
        if isinstance(recs, (pd.DataFrame,)) and not recs.empty:
            # columns are version-dependent; "pnl" is common
            pnl_col = next((c for c in recs.columns if c.lower() == "pnl"), None)
            if pnl_col is not None:
                win_rate = float((recs[pnl_col] > 0).mean())
    except Exception:
        pass


    return pf, stats, win_rate

