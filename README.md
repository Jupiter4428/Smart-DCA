# 📈 Smart-DCA — Dynamic Portfolio Analysis System

An automated **Dynamic DCA + Active Rebalancing** portfolio analysis system designed to outperform conventional Dollar-Cost Averaging through quantitative analysis combined with technical, fundamental, and volatility signals.

---

## Key Features

- **Volatility-Adjusted DCA Budget** — Automatically scales monthly DCA budget proportionally when portfolio volatility exceeds 25% annualised. Higher volatility = lower prices = more buying power (capped at 1.5×)

- **Multi-Factor Decision Logic** — Investment decisions evaluated across 5 core factors: Rebalance Weight, RSI, MACD, EMA 26 Support, and P/E Ratio

- **P&L Tracking** — Tracks unrealized profit/loss per symbol based on average cost basis (`AVERAGE_COST_USD` in `config.py`)

- **Goal Progress Dashboard** — Shows total invested (cost basis), progress % toward year-end target, and estimated months to goal at the current adjusted DCA rate

- **Backtesting Engine** — Simulates historical investment performance from 2021 onward, comparing Smart DCA vs Pure DCA including Alpha calculation

- **EMA 26 Support Analysis** — Detects price consolidation zones to identify safe accumulation opportunities

- **Special Hedge Asset Handling** — Separates gold (MTS-Gold via GC=F) as a dedicated hedge asset with disciplined DCA regardless of market signals

- **Disk Cache System** — Stores stock prices as CSV files; valid for the current calendar day to minimise yfinance API calls

---

## Project Structure

```
smart_dca/
├── run.py                  # Entry Point — runs the current portfolio analysis
├── backtest.py             # Backtesting Engine — simulates historical investment
├── config.py               # All settings: portfolio targets, holdings, cost basis, DCA budget
├── requirements.txt        # Dependencies (pandas, yfinance, matplotlib, openpyxl, etc.)
├── data/cache/             # Disk cache for stock prices (auto-generated)
├── reports/                # Output folder (auto-generated)
│   ├── Master_Portfolio_Report.xlsx  # 5-sheet report (Summary, Holdings, DCA_Action, Technical, PnL)
│   ├── portfolio_history.csv         # Daily portfolio value snapshots
│   ├── portfolio_performance.png     # 4-panel performance chart
│   └── backtest_result.png           # Backtesting comparison chart
└── src/
    ├── indicators.py       # RSI, MACD, EMA, Volatility, Historical Growth + Disk Cache
    ├── portfolio.py        # Decision Logic, Action Signals & Rebalance Factors
    ├── output.py           # Console & Excel report generator (all report functions)
    ├── utils.py            # Exchange rate & formatting helpers
    └── visualize.py        # Performance chart generator (portfolio_history.csv → PNG)
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
# Number of shares per symbol (update after each purchase)
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

# Average cost per share/oz — used for P&L calculation
AVERAGE_COST_USD = {
    'MSFT' : 0.0,
    'GOOGL': 0.0,
    'NVDA' : 0.0,
    'ASML' : 0.0,
    'TSM'  : 0.0,
    'GC=F' : 0.0,
    'JNJ'  : 0.0,
    'PG'   : 0.0,
    'CVX'  : 0.0,
    'RGTI' : 0.0,
    'QBTS' : 0.0,
}

# MTS-Gold — enter total troy oz held
# 1 troy oz = 31.1035 g  |  Example: 5g = 5/31.1035 ≈ 0.1608 oz
MTS_GOLD_OZ = 0.0

# Monthly DCA budget (will be scaled up automatically when volatility is high)
MONTHLY_DCA_BUDGET_USD = 45.00
```

---

## Usage

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

## Output

| File | Description |
|------|-------------|
| `Master_Portfolio_Report.xlsx` | Excel workbook: Summary, Holdings, DCA_Action, Technical, PnL |
| `portfolio_history.csv` | Daily snapshot: date, total_usd, total_thb, rate, monthly_dca_usd, gold_oz, total_invested_usd, \<SYMBOL\>... |
| `portfolio_performance.png` | 4-panel chart: Portfolio Value / Holdings Breakdown / DCA Budget / Exchange Rate |
| `backtest_result.png` | Smart DCA vs Pure DCA comparison chart |

### Excel Sheets

| Sheet | Contents |
|-------|----------|
| **Summary** | Portfolio value, vol-adjusted DCA budget, year-end target, goal progress %, est. months to goal |
| **Holdings** | Shares/oz held, latest price, current vs target allocation, avg cost, P&L (USD & %) |
| **DCA_Action** | BUY/SELL/HOLD recommendations with vol-adjusted budget allocation (color-coded) |
| **Technical** | RSI(14), MACD, EMA(26) signal, annualised volatility for every asset |
| **PnL** | Unrealized P&L per symbol (green = profit, red = loss) |

---

## Target Portfolio

| Symbol | Target % | Asset Type | Notes |
|--------|----------|------------|-------|
| MSFT   | 20%      | AI & Cloud | |
| GOOGL  | 15%      | AI & Search | |
| NVDA   | 12%      | AI Hardware | |
| ASML   | 12%      | Chip Equipment | |
| TSM    | 12%      | Chip Manufacturing | |
| GC=F   | 7%       | Gold Hedge | **MTS-Gold** (proxy via GC=F futures price/oz) |
| RGTI   | 7%       | Quantum (High-risk) | |
| QBTS   | 7%       | Quantum (High-risk) | |
| JNJ    | 3%       | Healthcare | |
| CVX    | 3%       | Energy | |
| PG     | 2%       | Consumer Staples | |

---

## Action Signal Logic

| Signal | Meaning | Condition |
|--------|---------|-----------|
| 🟢🟢 **STRONG BUY** | High-advantage entry | Underweight + (Oversold or Low P/E) + MACD Bullish / EMA Support |
| 🟢 **BUY** | Accumulate | Underweight + bullish momentum or near EMA 26 support |
| 🟡 **BUY (Caution)** | Accumulate carefully | Underweight but Overbought or expensive P/E |
| 🔵 **DCA** | Maintain discipline | On-target allocation or Hedge asset (Gold) |
| ⚪ **HOLD** | Pause contributions | Overweight — redirect DCA funds to underweight assets |
| 🔴 **SELL** | Take profit | Severely overweight (>5%) + RSI > 80 |

> The system prints **ACTION ALERTS** at the end of each run summarising all BUY signals.

---

## Volatility-Adjusted DCA

The monthly budget scales directly with portfolio volatility — if vol = x%, invest x/2% more:

```
multiplier = 1 + vol/2   [capped at 1.50×]

Examples:
  vol 10%  →  $45.00 × 1.05 = $47.25
  vol 20%  →  $45.00 × 1.10 = $49.50
  vol 40%  →  $45.00 × 1.20 = $54.00
  vol 100% →  $45.00 × 1.50 = $67.50  (cap)
```

The adjusted budget is displayed in the **Portfolio Summary** section and used in the **DCA Action Plan**.

---

## Cache System

- **Disk cache** — Stock prices saved as CSV in `data/cache/<SYMBOL>_1y.csv`; valid if the file's modified date matches today, preventing duplicate yfinance calls within the same day
- **In-memory cache** — Indicators (RSI, MACD, EMA, Vol, price, full DataFrame) computed once per session

---

## MTS-Gold

The system uses **GC=F** (Gold Futures) as a gold price proxy since MTS-Gold has no yfinance ticker.

- **Unit: troy oz** (1 troy oz = 31.1035 g)
- Update `MTS_GOLD_OZ` in `config.py` whenever you purchase additional gold

**Grams → oz conversion:**
```
oz = grams ÷ 31.1035
Example: 5g = 5 ÷ 31.1035 ≈ 0.160754 oz
```

---

## Key Settings (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CURRENT_HOLDINGS_SHARES` | dict | Shares held per symbol |
| `AVERAGE_COST_USD` | dict | Average cost per share/oz — drives P&L calculation |
| `MTS_GOLD_OZ` | `0.0021` | Troy oz of MTS-Gold held |
| `MONTHLY_DCA_BUDGET_USD` | `45.00` | Base monthly DCA budget (USD) |
| `ANNUAL_GROWTH_TARGET` | `0.12` | Year-end growth target (12%) |
| `RSI_PERIOD` | `14` | RSI lookback period |
| `RSI_OVERSOLD` | `30` | RSI buy zone threshold |
| `RSI_OVERBOUGHT` | `70` | RSI caution/sell zone threshold |
| `MACD_FAST/SLOW/SIGNAL` | `12/26/9` | MACD parameters |
| `DATA_PERIOD` | `1y` | Historical data period for indicators |
| `REBALANCE_TOLERANCE` | `0.5` | % tolerance before triggering rebalance status |
| `VOL_WINDOW` | `20` | Rolling window for volatility calculation (trading days) |
| `VOL_HIGH_THRESHOLD` | `0.25` | Annualised vol above this triggers DCA scale-up |
| `VOL_DCA_CAP` | `1.50` | Maximum DCA budget multiplier |

--- 

## Monthly Workflow

1. Purchase stocks/gold via your brokerage app based on DCA signals
2. Update `CURRENT_HOLDINGS_SHARES`, `MTS_GOLD_OZ`, and `AVERAGE_COST_USD` in `config.py`
3. Run `python run.py`
4. Review results in `reports/Master_Portfolio_Report.xlsx` (5 sheets including PnL)
5. Check console for **ACTION ALERTS** — any STRONG BUY or SELL signals?

---

## Dependencies

```
pandas, numpy, yfinance, openpyxl, matplotlib, requests, rich, unicodedata
```

---

## License

This project is licensed under the [MIT License](LICENSE).
