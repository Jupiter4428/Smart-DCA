"""
📊 OUTPUT & REPORTING
=====================
Console and Excel report generation for the DCA Portfolio System.
"""

import pandas as pd
import os
import csv
from datetime import datetime
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

from config import (
    TARGET_PORTFOLIO,
    CURRENT_HOLDINGS_SHARES,
    MTS_GOLD_OZ,
    MONTHLY_DCA_BUDGET_USD,
    REMAINING_MONTHS,
    REBALANCE_TOLERANCE,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    AVERAGE_COST_USD,
)

from src.indicators import download_historical_data, calculate_rsi, calculate_macd, calculate_historical_growth
from src.utils import get_status_indicator
from src.portfolio import get_action_signal, calculate_rebalance_factors
import yfinance as yf

# ─────────────────────────────────────────────────────────────────
# 🔍 P/E Ratio Fetcher
# ─────────────────────────────────────────────────────────────────
PE_CACHE = {}
def get_cached_pe(symbol):
    """ดึงค่า P/E Ratio ปัจจุบันจาก Yahoo Finance"""
    if symbol in PE_CACHE:
        return PE_CACHE[symbol]
    if symbol in ['GC=F', 'GLD', 'RGTI', 'QBTS', 'BITO', 'IBIT']: 
        PE_CACHE[symbol] = "N/A"
        return "N/A"
    try:
        pe = yf.Ticker(symbol).info.get('trailingPE', "N/A")
        PE_CACHE[symbol] = round(pe, 2) if isinstance(pe, (float, int)) else "N/A"
    except:
        PE_CACHE[symbol] = "N/A"
    return PE_CACHE[symbol]

# ─────────────────────────────────────────────────────────────────
# In-Memory Indicator Cache
# ─────────────────────────────────────────────────────────────────
_indicator_cache: dict = {}
_cache_hits:   list[str] = []
_cache_misses: list[str] = []

def get_cached_indicators(symbol: str) -> dict | None:
    """Return cached technical indicators for a symbol."""
    if symbol not in _indicator_cache:
        from src.indicators import _is_cache_valid, _get_cache_path
        from config import DATA_PERIOD

        was_cached = _is_cache_valid(_get_cache_path(symbol, DATA_PERIOD))

        df = download_historical_data(symbol)
        if df is None or df.empty:
            _indicator_cache[symbol] = None
        else:
            close = df['Close'].squeeze()
            rsi_series = calculate_rsi(close)
            macd_series, signal_series = calculate_macd(close)

            latest_rsi = rsi_series.iloc[-1]
            if pd.isna(latest_rsi):
                _indicator_cache[symbol] = None
            else:
                _indicator_cache[symbol] = {
                    'rsi'   : float(latest_rsi),
                    'macd'  : float(macd_series.iloc[-1]),
                    'signal': float(signal_series.iloc[-1]),
                    'price' : float(close.iloc[-1]),
                    'df'    : df,
                }

        if was_cached:
            _cache_hits.append(symbol)
        else:
            _cache_misses.append(symbol)

    return _indicator_cache[symbol]

def print_cache_summary() -> None:
    if _cache_hits:
        print(f"📂 Cache hit : {', '.join(_cache_hits)}")
    if _cache_misses:
        print(f"🌐 Downloaded: {', '.join(_cache_misses)}")

def clear_indicator_cache() -> None:
    _indicator_cache.clear()
    _cache_hits.clear()
    _cache_misses.clear()

# ─────────────────────────────────────────────────────────────────
# Portfolio Value Calculation
# ─────────────────────────────────────────────────────────────────

def _display_name(symbol: str) -> str:
    return f"{symbol} (MTS-Gold)" if symbol == 'GC=F' else symbol

def _get_current_holdings_usd() -> dict[str, float]:
    holdings_usd: dict[str, float] = {}
    for symbol in TARGET_PORTFOLIO:
        if symbol == 'GC=F':
            ind = get_cached_indicators('GC=F')
            holdings_usd['GC=F'] = (MTS_GOLD_OZ * ind['price']) if (ind and MTS_GOLD_OZ > 0) else 0.0
        else:
            shares = CURRENT_HOLDINGS_SHARES.get(symbol, 0.0)
            if shares > 0:
                ind = get_cached_indicators(symbol)
                holdings_usd[symbol] = shares * (ind['price'] if ind else 0.0)
            else:
                holdings_usd[symbol] = 0.0
    return holdings_usd

def _get_total_portfolio_usd(holdings_usd: dict[str, float]) -> float:
    return sum(holdings_usd.values())

# ─────────────────────────────────────────────────────────────────
# Report Generators
# ─────────────────────────────────────────────────────────────────

def generate_portfolio_summary(rate: float) -> pd.DataFrame:
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)
    total_thb    = total_usd * rate

    total_weighted_growth = 0.0
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        if ind and 'df' in ind:
            df = ind['df']
            if len(df) >= 2:
                start_price = df['Close'].iloc[0]
                end_price = df['Close'].iloc[-1]
                historical_growth = (end_price - start_price) / start_price
                total_weighted_growth += (historical_growth * (target_pct / 100))

    dynamic_annual_target = total_weighted_growth if total_weighted_growth != 0 else 0.12
    monthly_rate = dynamic_annual_target / 12

    fv_current = total_usd * ((1 + monthly_rate) ** REMAINING_MONTHS)
    fv_dca = MONTHLY_DCA_BUDGET_USD * (((1 + monthly_rate) ** REMAINING_MONTHS - 1) / monthly_rate)
    target_end_usd = fv_current + fv_dca
    target_end_thb = target_end_usd * rate

    denominator = (((1 + monthly_rate) ** REMAINING_MONTHS - 1) / monthly_rate)
    req_dca_usd = (target_end_usd - fv_current) / denominator

    gcf_ind = get_cached_indicators('GC=F')
    gcf_price_str = f"${gcf_ind['price']:,.2f}/oz" if gcf_ind else "N/A"
    gold_usd = holdings_usd.get('GC=F', 0.0)

    data = {
        'Metric': [
            'Timestamp',
            'Total Portfolio Value (USD / THB)',
            'Exchange Rate (THB/USD)',
            'Dynamic Annual Growth Target (Based on History)',
            'Monthly DCA Budget (USD / THB)',
            'Remaining Months',
            'Target End Year Value (USD / THB)',
            'Required Monthly DCA (USD / THB)',
            'Gold Holdings',
        ],
        'Value': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f"${total_usd:,.2f}  /  ฿{total_thb:,.2f}",
            f"{rate:.2f}",
            f"{dynamic_annual_target * 100:.2f}%",
            f"${MONTHLY_DCA_BUDGET_USD:,.2f}  /  ฿{MONTHLY_DCA_BUDGET_USD * rate:,.2f}",
            REMAINING_MONTHS,
            f"${target_end_usd:,.2f}  /  ฿{target_end_thb:,.2f}",
            f"${req_dca_usd:,.2f}  /  ฿{req_dca_usd * rate:,.2f}",
            f"{MTS_GOLD_OZ:.6f} oz  |  {gcf_price_str}  |  ${gold_usd:,.2f}",
        ]
    }
    return pd.DataFrame(data)

def generate_holdings_report(rate: float) -> pd.DataFrame:
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    rows = []
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        val_usd = holdings_usd.get(symbol, 0.0)
        pct     = (val_usd / total_usd * 100) if total_usd > 0 else 0.0
        diff    = pct - target_pct
        status, _ = get_status_indicator(diff, REBALANCE_TOLERANCE)

        ind = get_cached_indicators(symbol)
        price_str = f"${ind['price']:,.2f}" if ind else "N/A"

        avg_cost = AVERAGE_COST_USD.get(symbol, 0.0)
        if symbol == 'GC=F' or symbol == 'GLD':
            units = MTS_GOLD_OZ
            units_str = f"{units:.6f} oz"
        else:
            units = CURRENT_HOLDINGS_SHARES.get(symbol, 0.0)
            units_str = f"{units:.7f} shares"
            
        total_cost_usd = units * avg_cost
        pnl_usd = val_usd - total_cost_usd
        pnl_pct = (pnl_usd / total_cost_usd) * 100 if total_cost_usd > 0 else 0.0
        pnl_str = f"${pnl_usd:,.2f} ({pnl_pct:+.2f}%)" if units > 0 else "N/A"

        rows.append({
            'Symbol'       : _display_name(symbol),
            'Units'        : units_str,
            'Avg Cost($)'  : f"${avg_cost:,.2f}" if avg_cost > 0 else "-",
            'Price (USD)'  : price_str,
            'P&L (USD)'    : pnl_str,
            'Current (USD)': round(val_usd, 2),
            'Curr %'       : f"{pct:.2f}%",
            'Tgt %'        : f"{target_pct:.2f}%",
            'Status'       : status,
        })
    return pd.DataFrame(rows)

def generate_dca_action_report(rate: float) -> pd.DataFrame:
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    rebalance_factors = calculate_rebalance_factors(
        portfolio        = TARGET_PORTFOLIO,
        current_holdings = holdings_usd,
        total_value_usd  = total_usd,
        exchange_rate    = 1.0,
    )

    symbol_actions = {}
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        rsi = ind['rsi'] if ind else None
        pe_val = get_cached_pe(symbol)
        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        action, reason = get_action_signal(symbol, curr_pct, target_pct, rsi, pe_val)
        symbol_actions[symbol] = {'action': action, 'reason': reason, 'rsi': rsi, 'ind': ind}

    eligible_symbols = [sym for sym, data in symbol_actions.items() if "HOLD" not in data['action'] and "SKIP" not in data['action']]
    eligible_factors_sum = sum(rebalance_factors[sym] for sym in eligible_symbols)
    
    allocations_usd = {}
    if eligible_factors_sum > 0:
        for sym in eligible_symbols:
            allocations_usd[sym] = MONTHLY_DCA_BUDGET_USD * (rebalance_factors[sym] / eligible_factors_sum)

    rows = []
    total_tactical_usd = 0.0

    for symbol, target_pct in TARGET_PORTFOLIO.items():
        data = symbol_actions[symbol]
        ind = data['ind']
        price_str = f"${ind['price']:,.2f}" if ind else "N/A"
        final_usd = allocations_usd.get(symbol, 0.0)
        total_tactical_usd += final_usd

        rows.append({
            'Symbol'       : _display_name(symbol),
            'Price (USD)'  : price_str,
            'RSI'          : data['rsi'],
            'DCA (USD)'    : final_usd,
            'DCA (THB)'    : final_usd * rate,
            'Action Signal': data['action'],
            'Reason'       : data['reason'],
        })

    remaining_usd = max(0.0, MONTHLY_DCA_BUDGET_USD - total_tactical_usd)
    df = pd.DataFrame(rows)
    df.loc[len(df)] = ['TOTAL', 'N/A', None, total_tactical_usd, total_tactical_usd * rate, 'REMAINING CASH:', f"${remaining_usd:.2f} / ฿{remaining_usd * rate:.2f}"]
    return df

def generate_technical_report() -> pd.DataFrame:
    """Generate technical analysis summary with P/E Ratio."""
    rows = []
    for symbol in TARGET_PORTFOLIO:
        ind = get_cached_indicators(symbol)
        pe_val = get_cached_pe(symbol)
        if ind:
            growth_rate = calculate_historical_growth(ind['df'])
            rows.append({
                'Symbol'     : _display_name(symbol),
                'Price (USD)': f"${ind['price']:,.2f}",
                'P/E Ratio'  : pe_val,
                'RSI(14)'    : round(ind['rsi'], 2),
                'RSI Signal' : ("Overbought" if ind['rsi'] > RSI_OVERBOUGHT else "Oversold" if ind['rsi'] < RSI_OVERSOLD else "Neutral"),
                'MACD'       : round(ind['macd'], 4),
                'Signal'     : round(ind['signal'], 4),
                'MACD Signal': "Bullish 🟢" if ind['macd'] > ind['signal'] else "Bearish 🔴",
                'Growth'     : f"{growth_rate*100:+.2f}%"
            })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────
# ✅ Action Alert Summary
# ─────────────────────────────────────────────────────────────────
def print_action_alerts(rate: float = 0) -> None:
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    strong_buys = []
    sells       = []

    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        rsi = ind['rsi'] if ind else None
        pe_val = get_cached_pe(symbol)
        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        action, reason = get_action_signal(symbol, curr_pct, target_pct, rsi, pe_val)

        name = _display_name(symbol)
        rsi_str = f"RSI {rsi:.1f}" if rsi is not None else "RSI N/A"

        if "STRONG BUY" in action:
            strong_buys.append(f"  {name:<22} {rsi_str}  — {reason}")
        elif "SELL" in action:
            sells.append(f"  {name:<22} {rsi_str}  — {reason}")

    print("\n" + "=" * 140)
    print("🚨 ACTION ALERTS")
    print("=" * 140)

    if strong_buys:
        print("🟢🟢 STRONG BUY — Value Zone + Underweight:")
        for line in strong_buys:
            print(line)
    else:
        print("🟢  No STRONG BUY signals at this time.")

    if sells:
        print("\n🔴 SELL — Take Profit:")
        for line in sells:
            print(line)
    else:
        print("🔴  No SELL signals at this time.")

    print("=" * 140)

# ─────────────────────────────────────────────────────────────────
# Console & Excel Output
# ─────────────────────────────────────────────────────────────────

def print_reports_to_console(rate: float):
    print("\n" + "="*140)
    print("📋 PORTFOLIO SUMMARY")
    print("="*140)
    summary = generate_portfolio_summary(rate)
    for _, row in summary.iterrows():
        print(f"{row['Metric'].ljust(60)} {row['Value']}")
        
    print("\n" + "="*140)
    print("💼 HOLDINGS REPORT")
    print("="*140)
    holdings_df = generate_holdings_report(rate)
    print(holdings_df.to_string(index=False))
    
    print("\n" + "="*140)
    print("🎯 DCA ACTION PLAN")
    print("="*140)
    dca_df = generate_dca_action_report(rate)
    print(dca_df.to_string(index=False))
    
    print("\n" + "="*140)
    print("📊 TECHNICAL ANALYSIS (With Fundamentals)")
    print("-" * 140)
    tech_df = generate_technical_report()
    
    print(
        f"{'Symbol':<15} {'Price (USD)':<12} {'P/E Ratio':<10} {'RSI(14)':>8} "
        f"{'RSI Signal':<11} {'MACD':>10} {'Signal':>10} {'MACD Signal':<12} {'Growth':<10}"
    )
    print("-" * 140)
    
    for _, row in tech_df.iterrows():
        pe_str = str(row['P/E Ratio'])
        print(
            f"{row['Symbol']:<15} {row['Price (USD)']:<12} {pe_str:<10} {row['RSI(14)']:>8.2f} "
            f"{row['RSI Signal']:<11} {row['MACD']:>10.4f} {row['Signal']:>10.4f} {row['MACD Signal']:<12} {row['Growth']:<10}"
        )
        
    print_action_alerts(rate)

def save_all_to_excel(rate: float, output_dir: str = './reports') -> None:
    os.makedirs(output_dir, exist_ok=True)
    excel_file = f'{output_dir}/Master_Portfolio_Report.xlsx'

    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        generate_portfolio_summary(rate).to_excel(writer, sheet_name='Summary',    index=False)
        generate_holdings_report(rate).to_excel(  writer, sheet_name='Holdings',   index=False)
        generate_dca_action_report(rate).to_excel( writer, sheet_name='DCA_Action', index=False)
        generate_technical_report().to_excel(      writer, sheet_name='Technical',  index=False)

        wb          = writer.book
        green_fill  = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
        red_fill    = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
        yellow_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
        bold_font   = Font(bold=True)

        def _auto_width(ws, min_w=12, max_w=40):
            for col in ws.columns:
                length = max(
                    (len(str(cell.value)) for cell in col if cell.value), default=min_w
                )
                ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(length + 2, min_w), max_w)

        for sheet_name in ['Summary', 'Holdings', 'DCA_Action', 'Technical']:
            _auto_width(wb[sheet_name])

        ws_dca = wb['DCA_Action']
        for row in range(2, ws_dca.max_row + 1):
            rsi_cell    = ws_dca.cell(row=row, column=3)
            action_cell = ws_dca.cell(row=row, column=6)
            if isinstance(rsi_cell.value, (int, float)):
                if rsi_cell.value >= RSI_OVERBOUGHT:
                    rsi_cell.fill = red_fill
                elif rsi_cell.value <= RSI_OVERSOLD:
                    rsi_cell.fill = green_fill
            val = str(action_cell.value)
            if "BUY" in val:
                action_cell.fill = green_fill
                action_cell.font = bold_font
            elif "SKIP" in val:
                action_cell.fill = yellow_fill
            elif "SELL" in val:
                action_cell.fill = red_fill
                action_cell.font = bold_font

        ws_h = wb['Holdings']
        status_col = next((cell.column for cell in ws_h[1] if cell.value == 'Status'), None)
        if status_col:
            for row in range(2, ws_h.max_row + 1):
                cell = ws_h.cell(row=row, column=status_col)
                val  = str(cell.value)
                if 'UNDERWEIGHT' in val:
                    cell.fill = red_fill
                elif 'OVERWEIGHT' in val:
                    cell.fill = yellow_fill
                elif 'On Target' in val:
                    cell.fill = green_fill

    print(f"✅ Master Portfolio Report saved: {excel_file}")

def append_performance_history(rate: float) -> None:
    history_file = './reports/portfolio_history.csv'
    os.makedirs('./reports', exist_ok=True)
    today        = datetime.now().strftime('%Y-%m-%d')
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    row: dict = {
        'date'           : today,
        'total_usd'      : round(total_usd, 4),
        'total_thb'      : round(total_usd * rate, 2),
        'rate'           : round(rate, 4),
        'monthly_dca_usd': MONTHLY_DCA_BUDGET_USD,
        'gold_oz'        : MTS_GOLD_OZ,
    }
    for sym, val in holdings_usd.items():
        row[sym] = round(val, 4)

    fieldnames = list(row.keys())
    if os.path.exists(history_file):
        try:
            df_existing = pd.read_csv(history_file, usecols=['date'])
            if today in df_existing['date'].values:
                print(f"ℹ️  History already recorded for {today} — skipping.")
                return
        except Exception:
            pass

    file_exists = os.path.exists(history_file)
    with open(history_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    grams = MTS_GOLD_OZ * 31.1035
    print(
        f"✅ Snapshot recorded → {today} | "
        f"Total: ${total_usd:,.2f} / ฿{total_usd * rate:,.2f} | "
        f"Gold: {MTS_GOLD_OZ:.6f} oz ({grams:.4f} g)"
    )

def get_dynamic_growth_target():
    total_weighted_growth = 0.0
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        if ind and 'df' in ind:
            growth = calculate_historical_growth(ind['df'])
            total_weighted_growth += (growth * (target_pct / 100))
    return total_weighted_growth