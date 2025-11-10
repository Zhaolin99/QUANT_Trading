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
