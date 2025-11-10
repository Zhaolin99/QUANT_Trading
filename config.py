"""Global/default configuration for the project."""
from typing import Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
	"train_ratio": 0.70,  # 70% train / 30% test
	"init_cash": 100_000.0,  # initial capital for backtest
	"freq": "H",  # 60m data ≈ hourly frequency for annualization
}