## 目录 (TOC)

- 1. 简介
- 2. 架构总览（含 Mermaid）
- 3. 安装与环境
- 4. 关键概念
- 5. 模型接口与信号规范 <a name="signal-spec"></a>
- 6. 训练与离线评估
- 7. 回测（vectorbt）
- 8. 实盘/模拟执行（可选）
- 9. 配置与参数
- 10. 开发工作流（含代码风格、commit 规范、测试与CI）
- 11. 常见问题（FAQ）
- 12. 变更日志（Changelog）
- 附：文档校验清单

---

## 1. 简介

本文档面向工程师与量化研究员，目的是帮助快速理解并接入本仓库中的 Agent：

- 定位：轻量级、以监督学习为主的单标的量化信号生成与回测框架（频率：60min，数据源：yfinance，回测框架：vectorbt）。
- 目标读者：负责模型研发、回测验证、以及将信号接入回测/执行流水线的工程师与研究员。
- 范围：从数据下载 → 特征工程 → 训练/推理 → 信号生成 → 回测/执行 的端到端示例与规范。

我们优先保证「模型替换无痛」：只要新的模型遵守“模型接口与信号规范”（第 5 章，文档锚点：#signal-spec），即可无缝替换训练/推理逻辑。

---

## 2. 架构总览（含 Mermaid）

高层流程（单标的示意）：

```mermaid
flowchart LR
  A[数据下载
  (yfinance, 60min)] --> B[特征工程]
  B --> C[模型训练/推理]
  C --> D[信号生成
  (entries/exits)]
  D --> E[回测
  (vectorbt)]
  E --> F[报告/评估]
  D --> G[实盘/模拟执行]

  style A fill:#f9f,stroke:#333,stroke-width:1px
  style E fill:#bbf,stroke:#333,stroke-width:1px
```

扩展到多标的（高阶）：通过并行化数据下载与模型推理，或在模型层以表格(batch)方式处理多标的。第 7 章说明回测扩展要点。

---

## 3. 安装与环境

本项目在 macOS / Linux 下测试良好。Windows 用户请参照下面的备注。

基础步骤 (macOS/Linux):

```bash
# 在项目根目录执行
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

推荐的快速验证（MRE 的一部分）：

```bash
.venv/bin/python main.py --symbol 0700.HK --period 365d --interval 60m --proba_th 0.55
```

注意：yfinance 有速率限制（YFRateLimitError）。如遇到空数据或限流，请采用短周期/日线数据或本地缓存（参见第 8 章的本地模式）。

环境变量（示例）

| 变量 | 说明 | 示例 |
|---|---:|---|
| AGENT_ENV | 运行环境标识（dev/staging/prod） | dev |
| YF_API_KEY | （可选）yfinance 的第三方加速密钥（如有） | TODO |

（TODO：如需对接付费行情或交易所，补充 API Key 配置）

---

## 4. 关键概念

- 频率与可交易时间：默认使用 60min K 线（文件与代码中以 `H` 或 `60m` 表示）。
- 单标的 vs 多标的：默认流程以单标的为例（`--symbol`），多标的通过批量/并行化处理扩展。
- 轻量监督学习：当前实现为 LogisticRegression（见 `models/logistic_model.py`），输出为下一根 bar 向上概率 `proba_up`。
- 信号（entries / exits）：boolean 序列，针对每个可交易时间点是否开/平仓（详见第 5 章）。
- 回测：基于 vectorbt 的 `Portfolio.from_signals`，在 `backtest/vectorbt_engine.py` 中封装。
- 成本与滑点：当前实现中置为 0（占位），可通过配置打开真实成本开关（第 9 章）。

---

## 5. 模型接口与信号规范（文档锚点：#signal-spec）

核心目标：定义一套稳定、易替换的接口，确保不同模型能无缝接入回测/执行流水线。

接口要点（契约）：

- 输入（模型）：
  - 类型：pd.DataFrame（OHLCV，tz-aware index）
  - 必有列：`Close`, `Volume`（若特征使用其它列，请在模型实现中做兼容处理）
  - 索引：时间序列，必须为 pd.DatetimeIndex，建议时区为 `Asia/Hong_Kong`。
- 输出（模型）：
  - For 预测（推理）函数：返回 (test_index, proba_series)
  - `test_index`：pd.DatetimeIndex，与 `proba_series.index` 一致。
  - `proba_series`：pd.Series，数值范围 [0,1]，名字建议 `proba_up`。

信号规范（entries/exits）：

- entries：pd.Series[bool]，index 与 price series 对齐，True 表示在该 bar 开多仓。vectorbt 期望 entries 是对“可交易时刻”的布尔序列。
- exits：pd.Series[bool]，index 与 price series 对齐，True 表示在该 bar 平仓（可使用 shift 避免同一根 K 线开平仓冲突）。

示例：使用现有轻量模型链路

```python
from data.downloader import download_ohlcv
from models.logistic_model import train_predict
from signals.adapter import to_entries_exits
from backtest.vectorbt_engine import run_backtest

# 1) Download
df = download_ohlcv('0700.HK', period='365d', interval='60m')

# 2) Train + Predict (returns test_index, proba_up)
test_index, proba_up = train_predict(df, train_ratio=0.7)

# 3) Align price
close = df['Close'].reindex(test_index)

# 4) Convert to entries/exits
entries, exits = to_entries_exits(proba_up, th=0.55)

# 5) Backtest (vectorbt)
pf, stats, win_rate = run_backtest(close, entries, exits)
```

替换模型注意事项：

- 新模型必须提供与 `train_predict` 相同形态的返回值 (test_index, proba_series)。
- 特征工程可封装为 `build_features(df)` → 返回含 `y` 列的训练表格，便于复用。

替代输出格式（权重/仓位型模型）：

- 若模型输出为连续权重（[-1,1] 或 [0,1]），请在信号适配层（signals/adapter.py）中实现转换函数，将权重映射为 entries/exits 或按份额下单的策略。

---

## 6. 训练与离线评估

训练流程（简要）：

1. 数据准备：`download_ohlcv(symbol, period, interval)`。
2. 特征工程：`models.logistic_model.build_features(df)`（返回含 y 的表格）。
3. 按时间顺序拆分训练/测试（train_ratio，默认 0.7）。
4. 训练模型并保存（可选）：使用 scikit-learn Pipeline，方便序列化 `joblib.dump(model, path)`。
5. 离线评估：对测试集 `X_test` 计算 AUC、准确率、混淆矩阵、收益相关指标（见 MRE）。

示例（训练/评估脚本 skeleton）：

```python
from models.logistic_model import build_features
from sklearn.metrics import roc_auc_score

data = build_features(df)
split = int(len(data) * 0.7)
train = data.iloc[:split]
test = data.iloc[split:]

# fit model (see models/logistic_model.py)
# evaluate
proba = model.predict_proba(test.drop(columns='y'))[:,1]
auc = roc_auc_score(test['y'], proba)
print('AUC:', auc)
```

离线评估要点：

- 使用时间序列的分割方法（不要随机打散）。
- 记录训练/测试时间区间，确保回测中的价格数据与预测序列严格对齐。
- 使用 rolling / expanding 验证（walk-forward）可获得更稳健的泛化估计（稍进阶，TODO）。

---

## 7. 回测（vectorbt）

回测实现位于 `backtest/vectorbt_engine.py`，核心调用 `vbt.Portfolio.from_signals(close, entries, exits, init_cash, ...)`。

关键点：

- entries/exits 的 index 必须与 price series 对齐。
- 当前实现中 fees、slippage 均为 0；生产化时请开启真实成本开关（第 9 章）。
- vectorbt 版本可能影响 `pf.trades.records` 的字段命名，`vectorbt_engine` 中已尝试做防御性处理（寻找 `pnl` 字段）。

扩展到多标的：

- 将 `close`、`entries`、`exits` 扩展为 DataFrame（columns 为 tickers）并调用 `vbt.Portfolio.from_signals` 的多列版本，或对每只标的并行调用单标的回测并聚合结果。
- 注意资金管理（单策略多标的时需要考虑头寸分配与资金共享逻辑）。

回测示例：见第 5 章示例（同代码链路）。

---

## 8. 实盘/模拟执行（可选）

本仓库当前不包含交易对接适配器，但信号到执行的接口建议如下：

- 输入：entries/exits（与回测同规范）或按时间戳/订单列表输出（更贴合实际交易）。
- 输出：下单命令（限价/市价/数量），需包含唯一 trade_id 与时戳。

执行层建议：

1. 安全检查：仓位限制、最大下单数量、风控熔断。
2. 模拟模式（Dry-run）：将下单命令写入日志或本地模拟账本，便于回测对比。
3. 生产接入：连接经纪/交易 API（TODO：增加 exchange adapters，如 Interactive Brokers / CCXT / 华泰等）。

占位：真实交易成本开关

| 配置名 | 说明 | 默认 |
|---|---:|---:|
| ENABLE_REAL_TRADING | 是否启用真实下单 | False |
| APPLY_TRADING_COSTS | 回测时是否计入真实手续费/滑点 | False |

（TODO：在 config 中添加上述开关并在回测/执行链路中使用）

---

## 9. 配置与参数

主要配置文件：`config.py`（示例內容位于仓库根）

默认关键项（来自 `config.py`）：

| key | 含义 | 默认值 |
|---|---|---:|
| train_ratio | 训练集时间比例 | 0.7 |
| init_cash | 回测初始资金 | 100000.0 |
| freq | 年化頻率標識（用于统计） | H |

命令行参数（`main.py`）：

| 参数 | 说明 | 示例 |
|---|---|---|
| --symbol | 单标的 Ticker | 0700.HK |
| --period | yfinance period | 365d |
| --interval | yfinance interval | 60m |
| --proba_th | 概率阈值用于生成 entries | 0.55 |
| --train_ratio | 训练集比例 | 0.7 |

路径约定（示例）

| 路径 | 说明 |
|---|---|
| `data/` | 数据相关工具（`downloader.py`） |
| `models/` | 模型、特征工程 |
| `signals/` | 信号适配器（模型 → entries/exits） |
| `backtest/` | 回测引擎（vectorbt 封装） |

---

## 10. 开发工作流（含代码风格、commit 规范、测试与CI）

代码风格

- 使用 black（代码格式化）和 isort（导入排序）。建议 pre-commit 钩子统一格式化。示例 `.pre-commit-config.yaml`：TODO。
- 类型提示（typing）鼓励使用，便于静态检查。

Commit 规范（建议）

- 类型化前缀：feat/refactor/fix/docs/test
- 示例：`feat(model): add logistic regression pipeline and train_predict`。

测试与 CI

- 单元测试框架：pytest。
- 最小 CI（GitHub Actions）建议步骤：
  1. checkout
  2. setup python
  3. pip install -r requirements-dev.txt（包含 pytest, flake8, black）
  4. run linters
  5. run tests (pytest)

示例测试覆盖（MRE 应至少包含）：

- `test_imports.py`：确保模块能被导入（不依赖网络）。
- `test_signals.py`：对 signals.adapter 的 entries/exits 行为编写单元测试（用合成 pd.Series）。

CI 示例（简要，GitHub Actions YAML 为 TODO）

---

## 11. 常见问题（FAQ）

Q: yfinance 返回空数据或限流怎么办？

A: 常见处理：

- 短期重试（exponential backoff）。
- 缩短 `--period` 或改用 `--interval 1d`。
- 使用本地缓存或付费行情源。

Q: 如何替换模型为更复杂的 TS 模型（如 Transformer/XGBoost）？

A: 保持 `train_predict` 的返回类型（test_index, proba_series），并在信号适配层实现从模型分数到 entries/exits 的映射。

Q: vectorbt 版本升级导致字段变化怎么办？

A: `backtest/vectorbt_engine.py` 已包含防御性字段检索逻辑；若发现字段名变化，请在该文件中添加对应的字段映射并记录在 Changelog。

---

## 12. 变更日志（Changelog）

- 2025-11-10 — v0.1.0
  - 初始文档创建（`docs/agent.md`）
  - 修复代码缩进问题，整理模型/回测/数据下载模块。

（后续条目按时间往下追加）

---

## 最小可运行示例（MRE）

目的：保证从数据下载到回测的端到端流程在本地能跑通（受限于 yfinance 速率）。

步骤：

1. 创建 venv 并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 运行主流程（单标的示例，Mac/Linux）：

```bash
.venv/bin/python main.py --symbol 0700.HK --period 365d --interval 60m --proba_th 0.55
```

3. 若遇到 yfinance 限流，改用：

```bash
.venv/bin/python main.py --symbol 0700.HK --period 90d --interval 60m --proba_th 0.55
```

或者使用日线：

```bash
.venv/bin/python main.py --symbol 0700.HK --period 365d --interval 1d --proba_th 0.55
```

替代（离线）示例：使用仓库内或自建 CSV（TODO：添加 sample_data/0700_sample.csv）

```python
import pandas as pd
from models.logistic_model import train_predict

df = pd.read_csv('sample_data/0700_sample.csv', index_col=0, parse_dates=True)
test_idx, proba = train_predict(df)
```

---

## 文档校验清单

在合并到主分支前请完成下列检查：

1. Markdown lint：`mdl` 或 `markdownlint` 检查无错误。
2. 链接检查：`markdown-link-check docs/agent.md`（或相似工具）。
3. 代码示例可运行：在干净 venv 中执行 MRE 步骤，至少 `download -> train_predict -> to_entries_exits -> run_backtest` 流程能执行（允许 yfinance retry/降频）。
4. 单元测试：`pytest` 无失败（至少包含 import tests 和 signals tests）。
5. CI 配置：确保 GitHub Actions（或其他 CI）包含上述 lint/test 步骤。

快速执行示例（Linux/macOS）：

```bash
# 1) markdown lint
# 安装 (一次): npm install -g markdownlint-cli
markdownlint docs/agent.md

# 2) 链接检查
# 安装 (一次): npm i -g markdown-link-check
markdown-link-check docs/agent.md

# 3) 运行 MRE（见上文）
```

Windows 用户：将上述命令的前缀替换为 PowerShell 路径（例如 `.\.venv\Scripts\Activate.ps1`），以及使用 `python`/`.venv\Scripts\python.exe`。

---

如果你希望我把 `docs/agent.md` 放入仓库并提交 PR，我可以继续：

- (A) 将本文件保存为 `docs/agent.md`（已完成）
- (B) 添加 `sample_data/` 的最小 CSV 并在 MRE 中使用（可选）
- (C) 在 `config.py` 中添加真实交易开关并在 `backtest/vectorbt_engine.py` 中使用（小改动）

TODOs

- 在 `docs/agent.md` 中标注了若干 TODO（如 sample_data、CI YAML、pre-commit），如需我继续实现这些项请指示。
