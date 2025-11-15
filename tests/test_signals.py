import pandas as pd


def test_to_entries_exits_basic():
    from signals.adapter import to_entries_exits

    # construct a simple probability series
    idx = pd.date_range('2025-01-01', periods=5, freq='H')
    s = pd.Series([0.2, 0.6, 0.7, 0.4, 0.8], index=idx)

    entries, exits = to_entries_exits(s, th=0.55)

    # entries should be True where value > 0.55
    assert entries.sum() == 3
    # exits is (~entries).shift(1).fillna(False)
    assert exits.iloc[0] is False
    assert exits.iloc[1] == (not entries.iloc[1])

