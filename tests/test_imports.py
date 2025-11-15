def test_imports():
    # Simple smoke test to ensure modules import without syntax errors.
    import importlib

    modules = [
        'config',
        'data.downloader',
        'models.logistic_model',
        'signals.adapter',
        'backtest.vectorbt_engine',
    ]

    for m in modules:
        importlib.import_module(m)

