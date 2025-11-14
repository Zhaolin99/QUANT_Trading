# Test folder overview

This `test/` folder contains unit tests and a short doc for the project's critical components.

Files

- `test_imports.py` — smoke test to ensure core modules import without syntax errors.
- `test_model_features.py` — tests `models.logistic_model.build_features` with synthetic OHLCV.
- `test_signals.py` — tests `signals.adapter.to_entries_exits` behavior on synthetic series.
- `test_downloader.py` — tests `data.downloader.download_ohlcv` using monkeypatched `yfinance.download` for success and empty-data handling.
- `test_downloader_rate_limit.py` — tests retry/backoff behavior by simulating transient failures and permanent failures.
- `test_downloader_rate_limit.py` — tests retry/backoff behavior by simulating transient failures and permanent failures.
- `test_downloader_live.py` — (optional) integration test that performs a live fetch from yfinance. This test is NOT mocked and may fail under rate limits; run it manually.

How to run

Use the project's virtualenv and run pytest from the repository root. Examples:

```bash
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest
PYTHONPATH=. .venv/bin/pytest -q test
```

Notes

- All downloader tests use `monkeypatch` to avoid calling the real yfinance API. This ensures CI can run tests offline and reliably.
- If you want to extend tests to integration tests that call yfinance, keep them separate and gated (e.g., via pytest markers) because of rate limits.

Recommended CI steps

1. Run `pytest -q test`.
2. Ensure tests that need network are skipped unless a special token/flag is set.
