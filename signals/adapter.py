import pandas as pd

def to_entries_exits(signal: pd.Series, th: float):
    entries = signal > th
    exits = (~entries).shift(1).fillna(False)
    return entries, exits

