"""Adapters to transform model outputs into trading signals or weights."""
from __future__ import annotations


import pandas as pd


def to_entries_exits(signal: pd.Series, th: float) -> tuple[pd.Series, pd.Series]:
    """Map a probability-like signal to long entries/exits.


    Parameters
    ----------
    signal : pd.Series
    Probability or score aligned to tradable bars.
    th : float
    Threshold above which we enter long; below/equal triggers exit.


    Returns
    -------
    (entries, exits) : tuple[pd.Series, pd.Series]
    Boolean series aligned to price index for vectorbt.from_signals.
    """
    s = signal.dropna()
    entries = s > th
    # shift exits by 1 bar to avoid same-bar enter/exit conflicts
    exits = (~entries).shift(1).fillna(False)
    return entries, exits

