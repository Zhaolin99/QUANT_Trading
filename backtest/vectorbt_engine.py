import vectorbt as vbt

def run_backtest(close, entries, exits, cash=100_000, freq="H"):
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
    trades = pf.trades
    win_rate = (trades.pnl > 0).mean() if trades.count() > 0 else None
    return pf, stats, win_rate

