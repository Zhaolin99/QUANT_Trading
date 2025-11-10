# HK Quant 60m ML Backtest Starter

This repo is a minimal yet extensible starter for Hong Kong stock 60-minute ML backtesting:

- ✅ HK stocks (e.g. `0700.HK`)
- ✅ 60-minute data
- ✅ Machine-learning factor model (LogisticRegression)
- ✅ Model → Signal → Backtest clean separation
- ✅ vectorbt execution engine
- ✅ Can be extended to:
  - XGBoost / LightGBM
  - Transformers (Chronos / TimesFM)
  - LLM scoring (DeepSeek / Qwen)

---

## 🌱 Goal

Bootstrapped environment to:

1. Fetch HK data
2. Train simple model
3. Convert model output → trading signal
4. Backtest with vectorbt
5. Then iterate

---

## 🚀 Quick Start

```bash
git clone <your repo url>
cd hk-quant-60m-ml

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt


---
## RUN

```bash
python main.py --symbol 0700.HK --interval 60m --period 730d --proba_th 0.55

---
## 📌 Roadmap
  Stage	Target
✅ v0	Logistic Regression + 60m + vectorbt
🔜 v1	Multi-asset support
🔜 v2	Chronos / TimesFM / TFT
🔜 v3	Live trading interface (Paper Trading)
🔜 v4	Broker integration, HK fees simulation

## 📂 Folder Layout

Follow main.py → data/downloader.py → models/* → signals/adapter.py → backtest/vectorbt_engine.py

## 🧪 Test new models

Replace model file under models/, output pd.Series, call adapter.


