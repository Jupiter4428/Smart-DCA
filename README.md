# 📈 Smart-DCA — Portfolio Analysis System

An automated **Tactical DCA + Active Rebalancing** portfolio analysis system designed to outperform conventional Dollar-Cost Averaging through quantitative analysis combined with technical and fundamental signals.

---

## ✨ Key Features

- **Multi-Factor Decision Logic** — Investment decisions evaluated across 4 core factors: Rebalance Weight, RSI, MACD, and P/E Ratio (Fundamental)

- **Backtesting Engine** 🚀 — Simulates historical investment performance from 2021 onward, comparing returns between Smart DCA and Pure DCA strategies, including Alpha calculation

- **EMA 26 Support Analysis** — Detects price consolidation zones to identify safe accumulation opportunities based on momentum

- **Special Hedge Asset Handling** — Separates gold (MTS-Gold) as a dedicated hedge asset, maintaining consistent accumulation discipline even in volatile market conditions

- **Disk Cache System** — Stores stock prices as CSV files to minimize yfinance API calls and improve processing speed

---

## 🗂️ Project Structure

```
smart_dca/
├── run.py                  # Entry Point — runs the current portfolio analysis
├── backtest.py             # 🚀 Backtesting Engine — simulates historical investment
├── config.py               # Portfolio settings, 12% annual target, and DCA budget
├── requirements.txt        # Dependencies (pandas, yfinance, matplotlib, etc.)
├── data/cache/             # Disk cache for stock prices (auto-generated)
├── reports/                # Output folder (auto-generated)
│   ├── Master_Portfolio_Report.xlsx  # Detailed report — 4 sheets
│   ├── portfolio_history.csv         # Daily portfolio value snapshots
│   ├── portfolio_performance.png     # Portfolio performance chart
│   └── backtest_result.png           # Backtesting comparison chart
└── src/
    ├── indicators.py       # RSI, MACD, EMA, Historical Growth
    ├── portfolio.py        # 🧠 Brain: Decision Logic & Rebalance Factor
    ├── output.py           # Console & Excel report generator
    └── utils.py            # Exchange rate & formatting helpers
```

---

## ⚙️ Setup

**1. Clone the repository**
```bash
git clone https://github.com/Jupiter4428/Smart-DCA.git
cd Smart-DCA
```

**2. Create a virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure `config.py`** to match your portfolio
```python
# Number of shares per symbol
CURRENT_HOLDINGS_SHARES = {
    'MSFT' : 0.0,
    'GOOGL': 0.0,
    'NVDA' : 0.0,
    'ASML' : 0.0,
    'TSM'  : 0.0,
    'JNJ'  : 0.0,
    'PG'   : 0.0,
    'CVX'  : 0.0,
    'RGTI' : 0.0,
    'QBTS' : 0.0,
}

# MTS-Gold — enter total troy oz held
# 1 troy oz = 31.1035 g  |  Example: 5g = 5/31.1035 ≈ 0.1608 oz
MTS_GOLD_OZ = 0.0

# Monthly DCA budget
MONTHLY_DCA_BUDGET_USD = 45.00
```

---

## 🚀 Usage

### 1. Analyze current portfolio

```bash
# Standard run (uses disk cache if available)
python run.py

# Force re-download — clears all cache then fetches fresh data
python run.py --clear-cache

# Skip cache this run (does not delete or save cache)
python run.py --no-cache

# Skip recording performance history
python run.py --no-record

# Dry run — console output only, no files written
python run.py --dry-run
```

### 2. Run backtesting

```bash
python backtest.py
```

---

## 📊 Output

| File | Description |
|------|-------------|
| `Master_Portfolio_Report.xlsx` | Excel workbook: Summary, Holdings, DCA_Action, Technical |
| `portfolio_history.csv` | Daily snapshot: date, total_usd, total_thb, rate, monthly_dca_usd, gold_oz, \<SYMBOL\>... |
| `portfolio_performance.png` | 4-panel chart: Portfolio Value / Holdings Breakdown / DCA Budget / Exchange Rate |
| `backtest_result.png` | Smart DCA vs Pure DCA comparison chart |

### Excel Sheets

- **Summary** — Portfolio value overview, year-end target, required DCA amount, gold oz/grams
- **Holdings** — Shares/oz held, latest price, current vs target allocation with color-coded status
- **DCA_Action** — BUY/SELL/SKIP recommendations based on RSI + rebalance factor (color-coded)
- **Technical** — RSI(14), MACD, and Signal line for every asset

---

## 🎯 Target Portfolio

| Symbol | Target % | Asset Type | Notes |
|--------|----------|------------|-------|
| MSFT   | 18%      | AI & Cloud | |
| GOOGL  | 14%      | AI & Search | |
| ASML   | 12%      | Chip Equipment | |
| TSM    | 12%      | Chip Manufacturing | |
| GLD    | 13%      | Gold Safe Haven | **MTS-Gold** (proxy via GLD price/oz) |
| NVDA   | 6%       | AI GPU | |
| RGTI   | 6%       | Quantum (Growth) | |
| JNJ    | 5%       | Healthcare | |
| PG     | 5%       | Consumer Staples | |
| QBTS   | 5%       | Quantum (Growth) | |
| CVX    | 4%       | Energy | |

---

## 📈 Backtest Results

Simulated from **2021-01-01** to present with a $45/month budget:

| Metric | Value |
|--------|-------|
| Total Invested | $2,880.00 |
| Pure DCA Value | $9,662.03 |
| Smart DCA Value | $11,041.02 |
| 🏆 Alpha | **+$1,378.99 (+14.2%)** |

---

## 🥇 MTS-Gold

The system uses **GLD** (SPDR Gold Shares ETF) as a gold price proxy for historical data stability, since MTS-Gold has no yfinance ticker.

- **Unit: troy oz** (1 troy oz = 31.1035 g)
- Update `MTS_GOLD_OZ` in `config.py` whenever you purchase additional gold

**Grams → oz conversion:**
```
oz = grams ÷ 31.1035
Example: 5g = 5 ÷ 31.1035 ≈ 0.160754 oz
```

```python
MTS_GOLD_OZ = 0.0   # Example: 5 grams of gold
```

---

## 🔧 Key Settings (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CURRENT_HOLDINGS_SHARES` | dict | Shares held per symbol |
| `MTS_GOLD_OZ` | `0.0` | Troy oz of MTS-Gold held |
| `MONTHLY_DCA_BUDGET_USD` | `46.22` | Monthly DCA budget (USD) |
| `RSI_PERIOD` | `14` | RSI lookback period |
| `RSI_OVERSOLD` | `30` | RSI buy zone threshold |
| `RSI_OVERBOUGHT` | `70` | RSI sell zone threshold |
| `MACD_FAST/SLOW/SIGNAL` | `12/26/9` | MACD parameters |
| `DATA_PERIOD` | `12mo` | Historical data period |
| `REBALANCE_TOLERANCE` | `0.5%` | Tolerance before triggering rebalance |
| `ANNUAL_GROWTH_TARGET` | `12%` | Year-end growth target |

---

## 📋 Action Signal Logic

| Signal | Meaning | Condition |
|--------|---------|-----------|
| 🟢🟢 **STRONG BUY** | High-advantage entry point | Underweight + (Oversold or Low P/E) + MACD Bullish / EMA Support |
| 🟢 **BUY** | Accumulate more | Underweight + Uptrend or near EMA 26 support |
| 🔵 **DCA** | Maintain discipline | On-target allocation or Hedge asset (Gold) |
| 🟣 **HOLD** | Pause contributions | Overweight or price running too hot (Overbought / Expensive) |
| 🔴 **SELL** | Take profit | Severely overweight (>5%) + RSI > 80 (Extreme Overbought) |

> The system automatically prints **ACTION ALERTS** summarizing STRONG BUY and SELL signals at the end of each console run.

---

## 💾 Cache System

- **Disk cache** — Stock prices saved as CSV in `data/cache/`; valid if the file's modified date is today, preventing duplicate yfinance calls within the same day
- **In-memory cache** — Indicators computed once per session, reducing API calls from 22 → 11

---

## 📦 Dependencies

```
pandas, numpy, yfinance, openpyxl, matplotlib, requests, rich, unicodedata
```

---

## 🔄 Monthly Workflow

1. Purchase stocks/gold via your brokerage app based on DCA signals
2. Update `CURRENT_HOLDINGS_SHARES` and `MTS_GOLD_OZ` in `config.py`
3. Run `python run.py`
4. Review results in `reports/Master_Portfolio_Report.xlsx`
5. Check console for **ACTION ALERTS** — any STRONG BUY or SELL signals?

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).