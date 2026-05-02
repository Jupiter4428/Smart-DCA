import os
import math
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime

from config import TARGET_PORTFOLIO, MONTHLY_DCA_BUDGET_USD, VOL_WINDOW, VOL_DCA_CAP
from src.indicators import calculate_rsi, calculate_macd, calculate_ema, calculate_volatility
from src.portfolio import calculate_rebalance_factors, get_action_signal

# ═══════════════════════════════════════════════════════════════════
# 🔧 TEST CONFIGURATION — แก้ตรงนี้เพื่อเปลี่ยนหุ้นที่ต้องการทดสอบ
# ═══════════════════════════════════════════════════════════════════
TEST_SYMBOLS = list(TARGET_PORTFOLIO.keys())   # ← เปลี่ยนเป็น list ที่ต้องการ เช่น ['MSFT', 'NVDA']
START_DATE   = "2021-01-01"
END_DATE     = datetime.today().strftime('%Y-%m-%d')
COLS         = 3   # จำนวนคอลัมน์ในกราฟ grid

# ═══════════════════════════════════════════════════════════════════

print(f"Starting Per-Stock Backtest: {START_DATE} to {END_DATE}")
print(f"Symbols: {TEST_SYMBOLS}\n")

# ── Helper: Volatility-Adjusted Budget ─────────────────────────────
def _portfolio_vol(current_indicators):
    total_w = sum(TARGET_PORTFOLIO.values())
    wvol = 0.0
    for sym, pct in TARGET_PORTFOLIO.items():
        ind = current_indicators.get(sym)
        if ind and 'vol' in ind:
            wvol += (pct / total_w) * ind['vol']
    return wvol

def _adjusted_budget(port_vol):
    if port_vol > 0:
        return MONTHLY_DCA_BUDGET_USD * min(1 + port_vol / 2, VOL_DCA_CAP)
    return MONTHLY_DCA_BUDGET_USD


# 1. Download historical data
print("Downloading historical data...")
hist_data = {}
for symbol in TARGET_PORTFOLIO.keys():
    ticker = 'GLD' if symbol == 'GC=F' else symbol
    df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    hist_data[symbol] = df['Adj Close'] if 'Adj Close' in df.columns else df['Close']
print("Data downloaded. Running simulation...\n")


# 2. Simulation state
portfolio_shares  = {s: 0.0 for s in TARGET_PORTFOLIO}
pure_dca_shares   = {s: 0.0 for s in TARGET_PORTFOLIO}
smart_invested    = {s: 0.0 for s in TARGET_PORTFOLIO}   # cumulative $ invested per symbol (Smart)
pure_invested     = {s: 0.0 for s in TARGET_PORTFOLIO}   # cumulative $ invested per symbol (Pure)

# Per-symbol history: {symbol: [{'date', 'smart_val', 'pure_val', 'smart_inv', 'pure_inv'}, ...]}
sym_history = {s: [] for s in TARGET_PORTFOLIO}

dates = pd.date_range(start=START_DATE, end=END_DATE, freq='MS')


# 3. Time-travel loop
for current_date in dates:
    ds = current_date.strftime('%Y-%m-%d')
    current_prices     = {}
    current_indicators = {}

    for symbol, prices in hist_data.items():
        past = prices.loc[:ds].dropna()
        if len(past) >= 35:
            current_prices[symbol] = float(past.iloc[-1])
            rsi_s          = calculate_rsi(past)
            macd_s, sig_s  = calculate_macd(past)
            ema26_s        = calculate_ema(past, 26)
            current_indicators[symbol] = {
                'rsi'   : float(rsi_s.iloc[-1]),
                'macd'  : float(macd_s.iloc[-1]),
                'signal': float(sig_s.iloc[-1]),
                'ema26' : float(ema26_s.iloc[-1]),
                'vol'   : calculate_volatility(past, VOL_WINDOW),
            }
        else:
            current_prices[symbol]     = 0.0
            current_indicators[symbol] = None

    # Portfolio value and rebalance factors
    holdings_usd   = {s: portfolio_shares[s] * current_prices[s] for s in TARGET_PORTFOLIO}
    total_value    = sum(holdings_usd.values())
    rebal_factors  = calculate_rebalance_factors(
        portfolio=TARGET_PORTFOLIO,
        current_holdings=holdings_usd,
        total_value_usd=total_value,
        exchange_rate=1.0,
    )

    # Action signals
    symbol_actions = {}
    for symbol in TARGET_PORTFOLIO:
        ind = current_indicators[symbol]
        if ind is not None:
            curr_pct   = (holdings_usd[symbol] / total_value * 100) if total_value > 0 else 0.0
            action, _  = get_action_signal(
                symbol=symbol,
                current_pct=curr_pct,
                target_pct=TARGET_PORTFOLIO[symbol],
                rsi_value=ind['rsi'],
                pe_value=None,
                macd_val=ind['macd'],
                signal_val=ind['signal'],
                price=current_prices[symbol],
                ema26=ind['ema26'],
            )
            symbol_actions[symbol] = action
        else:
            symbol_actions[symbol] = "SKIP"

    eligible = [s for s, a in symbol_actions.items() if "HOLD" not in a and "SKIP" not in a]
    f_sum    = sum(rebal_factors[s] for s in eligible)

    port_vol      = _portfolio_vol(current_indicators)
    adj_budget    = _adjusted_budget(port_vol)

    # Buy / record
    for symbol in TARGET_PORTFOLIO:
        price = current_prices[symbol]
        if price <= 0:
            sym_history[symbol].append({
                'date'     : current_date,
                'smart_val': portfolio_shares[symbol] * 0,
                'pure_val' : pure_dca_shares[symbol]  * 0,
                'smart_inv': smart_invested[symbol],
                'pure_inv' : pure_invested[symbol],
            })
            continue

        # Smart DCA
        if symbol in eligible and f_sum > 0:
            alloc = adj_budget * (rebal_factors[symbol] / f_sum)
            portfolio_shares[symbol] += alloc / price
            smart_invested[symbol]   += alloc

        # Pure DCA
        pure_alloc = MONTHLY_DCA_BUDGET_USD * (TARGET_PORTFOLIO[symbol] / 100)
        pure_dca_shares[symbol] += pure_alloc / price
        pure_invested[symbol]   += pure_alloc

        sym_history[symbol].append({
            'date'     : current_date,
            'smart_val': portfolio_shares[symbol] * price,
            'pure_val' : pure_dca_shares[symbol]  * price,
            'smart_inv': smart_invested[symbol],
            'pure_inv' : pure_invested[symbol],
        })


# 4. Build per-symbol DataFrames
sym_dfs = {}
for symbol in TARGET_PORTFOLIO:
    if sym_history[symbol]:
        sym_dfs[symbol] = pd.DataFrame(sym_history[symbol]).set_index('date')


# 5. Console summary
print(f"\nPER-STOCK BACKTEST RESULTS  ({START_DATE} to {END_DATE})")
print("=" * 72)
print(f"{'Symbol':<8} {'Invested':>12} {'Smart Val':>12} {'Smart ROI':>10} {'Pure Val':>12} {'Pure ROI':>10} {'Alpha':>8}")
print("-" * 72)

for symbol in TEST_SYMBOLS:
    df = sym_dfs.get(symbol)
    if df is None or df.empty:
        print(f"{symbol:<8}  {'no data':>12}")
        continue
    # Use smart_invested as reference baseline for Smart ROI
    inv_smart  = df['smart_inv'].iloc[-1]
    inv_pure   = df['pure_inv'].iloc[-1]
    smart_val  = df['smart_val'].iloc[-1]
    pure_val   = df['pure_val'].iloc[-1]
    smart_roi  = ((smart_val - inv_smart) / inv_smart  * 100) if inv_smart  > 0 else 0.0
    pure_roi   = ((pure_val  - inv_pure)  / inv_pure   * 100) if inv_pure   > 0 else 0.0
    alpha      = smart_roi - pure_roi
    print(f"{symbol:<8} ${inv_smart:>10,.2f} ${smart_val:>10,.2f} {smart_roi:>+9.1f}% ${pure_val:>10,.2f} {pure_roi:>+9.1f}% {alpha:>+7.1f}%")

print("=" * 72)


# 6. Per-stock grid chart
n_plot = len(TEST_SYMBOLS)
n_cols = min(COLS, n_plot)
n_rows = math.ceil(n_plot / n_cols)

fig_w = n_cols * 5
fig_h = n_rows * 3.8
fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_w, fig_h))
fig.suptitle(
    f'Per-Stock Backtest: Smart DCA vs Pure DCA  ({START_DATE} → {END_DATE})',
    fontsize=13, fontweight='bold', y=1.01
)

# Flatten axes to 1-D list for easy indexing
if n_plot == 1:
    axes = [axes]
elif n_rows == 1:
    axes = list(axes)
else:
    axes = [ax for row in axes for ax in row]

for idx, symbol in enumerate(TEST_SYMBOLS):
    ax  = axes[idx]
    df  = sym_dfs.get(symbol)

    if df is None or df.empty:
        ax.set_title(f'{symbol}  (no data)', fontsize=10)
        ax.axis('off')
        continue

    inv_smart  = df['smart_inv'].iloc[-1]
    inv_pure   = df['pure_inv'].iloc[-1]
    smart_val  = df['smart_val'].iloc[-1]
    pure_val   = df['pure_val'].iloc[-1]
    smart_roi  = ((smart_val - inv_smart) / inv_smart  * 100) if inv_smart  > 0 else 0.0
    pure_roi   = ((pure_val  - inv_pure)  / inv_pure   * 100) if inv_pure   > 0 else 0.0

    ax.plot(df.index, df['smart_val'], color='#7c3aed', linewidth=1.8,
            label=f'Smart DCA  {smart_roi:+.1f}%')
    ax.plot(df.index, df['pure_val'],  color='#6b7280', linewidth=1.2,
            linestyle='--', label=f'Pure DCA   {pure_roi:+.1f}%')
    ax.fill_between(df.index, df['smart_inv'], alpha=0.08, color='#7c3aed',
                    label=f'Invested ${inv_smart:,.0f}')

    # Colour title by who wins
    title_color = '#16a34a' if smart_roi >= pure_roi else '#dc2626'
    ax.set_title(f'{symbol}', fontsize=11, fontweight='bold', color=title_color)
    ax.set_ylabel('Value (USD)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc='upper left')
    ax.grid(True, alpha=0.25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'${v:,.0f}'))

    # Rotate x-tick dates
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(30)
        lbl.set_ha('right')

# Hide unused subplot slots
for idx in range(n_plot, len(axes)):
    axes[idx].set_visible(False)

plt.tight_layout()
os.makedirs('./reports', exist_ok=True)
out_path = './reports/backtest_per_stock.png'
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"\nChart saved to {out_path}")
