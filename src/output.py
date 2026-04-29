"""
📊 OUTPUT & REPORTING
=====================
Console and Excel report generation for the DCA Portfolio System.

Fixes applied:
  1. _indicator_cache → ดึง yfinance ครั้งเดียวต่อ symbol (ลดจาก 22 → 11 API calls)
  2. generate_dca_action_report → ใช้ calculate_rebalance_factors() จาก portfolio.py
     แทนการเขียน rebalance logic ซ้ำ inline
"""

import pandas as pd
import os
import numpy as np
from datetime import datetime
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# Imports from Root and Source
from config import (
    TARGET_PORTFOLIO, CURRENT_HOLDINGS, CURRENT_PORTFOLIO_VALUE_USD,
    ANNUAL_GROWTH_TARGET, MONTHLY_DCA_BUDGET_USD, REMAINING_MONTHS,
    REBALANCE_TOLERANCE
)
from src.indicators import download_historical_data, calculate_rsi, calculate_macd, get_latest_indicators
from src.utils import get_status_indicator, get_thb_usd_rate
from src.portfolio import get_action_signal, calculate_rebalance_factors


# ─────────────────────────────────────────────────────────────────
# ✅ FIX 1: Indicator Cache
# ─────────────────────────────────────────────────────────────────
_indicator_cache: dict = {}
_cache_hits: list[str] = []    # symbols ที่โหลดจาก disk cache
_cache_misses: list[str] = []  # symbols ที่ download ใหม่จาก yfinance


def get_cached_indicators(symbol: str) -> dict | None:
    """
    Return cached technical indicators for a symbol.
    Downloads from yfinance only on first call; subsequent calls return cached result.
    Tracks cache hits/misses for batch summary printing.
    """
    if symbol not in _indicator_cache:
        from src.indicators import _is_cache_valid, _get_cache_path
        from config import DATA_PERIOD

        # ตรวจว่า disk cache มีอยู่ก่อน download → ใช้ track hit/miss
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
                    'rsi': float(latest_rsi),
                    'macd': float(macd_series.iloc[-1]),
                    'signal': float(signal_series.iloc[-1]),
                    'price': float(close.iloc[-1]),
                    'df': df,
                }

        # บันทึก hit/miss
        if was_cached:
            _cache_hits.append(symbol)
        else:
            _cache_misses.append(symbol)

    return _indicator_cache[symbol]


def print_cache_summary() -> None:
    """แสดงสรุป cache status เป็นบรรทัดเดียว แทนการ print ทีละ symbol"""
    if _cache_hits:
        print(f"📂 Cache hit : {', '.join(_cache_hits)}")
    if _cache_misses:
        print(f"🌐 Downloaded: {', '.join(_cache_misses)}")


def clear_indicator_cache():
    """Clear the indicator cache and hit/miss tracking (useful for testing or forced refresh)."""
    _indicator_cache.clear()
    _cache_hits.clear()
    _cache_misses.clear()


# ─────────────────────────────────────────────────────────────────
# Report Generators
# ─────────────────────────────────────────────────────────────────

def generate_portfolio_summary(rate):
    """Generate high-level portfolio metrics (USD primary, THB secondary)."""
    total_usd = CURRENT_PORTFOLIO_VALUE_USD
    total_thb = total_usd * rate
    target_end_usd = total_usd * (1 + ANNUAL_GROWTH_TARGET)
    target_end_thb = target_end_usd * rate
    req_dca_usd = (target_end_usd - total_usd) / REMAINING_MONTHS
    req_dca_thb = req_dca_usd * rate
    budget_thb = MONTHLY_DCA_BUDGET_USD * rate

    data = {
        'Metric': [
            'Timestamp',
            'Total Portfolio Value (USD / THB)',
            'Exchange Rate (THB/USD)',
            'Annual Growth Target',
            'Monthly DCA Budget (USD / THB)',
            'Remaining Months (2026)',
            'Target End Year Value (USD / THB)',
            'Required Monthly DCA (USD / THB)',
        ],
        'Value': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f"${total_usd:,.2f}  /  ฿{total_thb:,.2f}",
            f"{rate:.2f}",
            f"{ANNUAL_GROWTH_TARGET * 100:.1f}%",
            f"${MONTHLY_DCA_BUDGET_USD:,.2f}  /  ฿{budget_thb:,.2f}",
            REMAINING_MONTHS,
            f"${target_end_usd:,.2f}  /  ฿{target_end_thb:,.2f}",
            f"${req_dca_usd:,.2f}  /  ฿{req_dca_thb:,.2f}",
        ]
    }
    return pd.DataFrame(data)


def generate_holdings_report(rate):
    """Generate current allocation vs target report (USD primary, THB secondary)."""
    rows = []
    for s, t in TARGET_PORTFOLIO.items():
        val_usd = CURRENT_HOLDINGS.get(s, 0)
        val_thb = val_usd * rate
        pct = (val_usd / CURRENT_PORTFOLIO_VALUE_USD * 100) if CURRENT_PORTFOLIO_VALUE_USD > 0 else 0
        diff = pct - t
        status, _ = get_status_indicator(diff, REBALANCE_TOLERANCE)
        rows.append({
            'Symbol': s,
            'Current (USD)': val_usd,
            'Current (THB)': val_thb,
            'Current %': f"{pct:.2f}%",
            'Target %': f"{t:.2f}%",
            'Diff %': f"{diff:+.2f}%",
            'Status': status
        })
    return pd.DataFrame(rows)


def generate_dca_action_report(rate):
    """
    Generate tactical DCA recommendations (USD primary, THB secondary).
    """
    rebalance_factors = calculate_rebalance_factors(
        portfolio=TARGET_PORTFOLIO,
        current_holdings=CURRENT_HOLDINGS,
        total_value_usd=CURRENT_PORTFOLIO_VALUE_USD,
        exchange_rate=1.0  # holdings already in USD → no conversion needed
    )

    rows = []
    total_tactical_usd = 0

    for s, w in TARGET_PORTFOLIO.items():
        adj_budget = MONTHLY_DCA_BUDGET_USD * rebalance_factors[s]

        ind = get_cached_indicators(s)
        rsi = ind['rsi'] if ind else None

        if rsi is not None and rsi >= 70:
            mul = 0.20
        elif rsi is not None and rsi <= 30:
            mul = 1.50
        elif rsi is not None:
            mul = float(np.clip((100 - rsi) / 50, 0.5, 1.5))
        else:
            mul = 1.0

        final_usd = adj_budget * mul
        total_tactical_usd += final_usd

        curr_pct = (CURRENT_HOLDINGS.get(s, 0) / CURRENT_PORTFOLIO_VALUE_USD * 100) if CURRENT_PORTFOLIO_VALUE_USD > 0 else 0
        action, reason = get_action_signal(curr_pct, w, rsi)

        rows.append({
            'Symbol': s,
            'RSI': rsi,
            'DCA (USD)': final_usd,
            'DCA (THB)': final_usd * rate,
            'Action Signal': action,
            'Reason': reason
        })

    remaining_usd = MONTHLY_DCA_BUDGET_USD - total_tactical_usd
    df = pd.DataFrame(rows)
    df.loc[len(df)] = ['TOTAL', None, total_tactical_usd, total_tactical_usd * rate,
                       'REMAINING CASH:', f"${remaining_usd:.2f} / ฿{remaining_usd * rate:.2f}"]
    return df


def generate_technical_report():
    """
    Generate technical analysis summary.
    ✅ FIX 1 applied: ใช้ get_cached_indicators() แทน download_historical_data() ซ้ำ
    """
    rows = []
    for s in TARGET_PORTFOLIO.keys():
        # ✅ ดึงจาก cache — ถ้า generate_dca_action_report() รันก่อน จะไม่มี download เพิ่ม
        ind = get_cached_indicators(s)
        if ind is not None:
            rows.append({
                'Symbol': s,
                'Price (USD)': f"${ind['price']:.2f}",
                'RSI(14)': ind['rsi'],
                'RSI Signal': "Overbought" if ind['rsi'] > 70 else "Oversold" if ind['rsi'] < 30 else "Neutral",
                'MACD': ind['macd'],
                'Signal': ind['signal'],
                'MACD Signal': "Bullish" if ind['macd'] > ind['signal'] else "Bearish"
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# Console & Excel Output
# ─────────────────────────────────────────────────────────────────

def print_reports_to_console(rate):
    """Formatted Terminal Output."""
    print("\n" + "=" * 100)
    print("📊 PORTFOLIO ANALYSIS REPORT (English Edition)")
    print("=" * 100)

    print("\n📋 PORTFOLIO SUMMARY")
    print("-" * 100)
    summary_df = generate_portfolio_summary(rate)
    for _, row in summary_df.iterrows():
        print(f"{row['Metric']:.<60} {row['Value']}")

    print("\n💰 HOLDINGS REPORT")
    print("-" * 105)
    print(
        f"{'Symbol':>8}  {'Current (USD)':>13}  {'Current (THB)':>13}  "
        f"{'Current %':>9}  {'Target %':>8}  {'Diff %':>7}  {'Status':<12}"
    )
    print("-" * 105)
    for _, row in generate_holdings_report(rate).iterrows():
        print(
            f"{row['Symbol']:>8}  {row['Current (USD)']:>13,.2f}  {row['Current (THB)']:>13,.2f}  "
            f"{row['Current %']:>9}  {row['Target %']:>8}  {row['Diff %']:>7}  {row['Status']:<12}"
        )

    print("\n📈 DCA RECOMMENDATIONS (Tactical Action)")
    print("-" * 115)
    dca_df = generate_dca_action_report(rate)
    print_cache_summary()  # แสดงสรุป cache เป็นบรรทัดเดียว
    dca_print = dca_df.copy()
    dca_print['DCA (USD)'] = dca_print['DCA (USD)'].apply(
        lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else x
    )
    dca_print['DCA (THB)'] = dca_print['DCA (THB)'].apply(
        lambda x: f"฿{x:,.2f}" if isinstance(x, (int, float)) else x
    )
    print(dca_print.to_string(index=False))

    print("\n📊 TECHNICAL ANALYSIS")
    print("-" * 115)
    print(generate_technical_report().to_string(index=False))
    print("\n" + "=" * 100)


def save_all_to_excel(rate, output_dir='./reports'):
    """Save multi-sheet Excel with highlights."""
    os.makedirs(output_dir, exist_ok=True)
    excel_file = f'{output_dir}/Master_Portfolio_Report.xlsx'

    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        generate_portfolio_summary(rate).to_excel(writer, sheet_name='Summary', index=False)
        generate_holdings_report(rate).to_excel(writer, sheet_name='Holdings', index=False)
        generate_dca_action_report(rate).to_excel(writer, sheet_name='DCA_Action', index=False)
        generate_technical_report().to_excel(writer, sheet_name='Technical', index=False)

        # Style Definitions
        wb = writer.book
        green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
        red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
        yellow_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
        bold_font = Font(bold=True)

        # Style DCA_Action Sheet
        ws = wb['DCA_Action']
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 25

        for row in range(2, ws.max_row + 1):
            # RSI Highlighting
            rsi_cell = ws.cell(row=row, column=2)
            if isinstance(rsi_cell.value, (int, float)):
                if rsi_cell.value >= 70:
                    rsi_cell.fill = red_fill
                elif rsi_cell.value <= 30:
                    rsi_cell.fill = green_fill

            # Action Signal Highlighting
            action_cell = ws.cell(row=row, column=4)
            val = str(action_cell.value)
            if "BUY" in val:
                action_cell.fill = green_fill
                action_cell.font = bold_font
            elif "SKIP" in val:
                action_cell.fill = yellow_fill
            elif "SELL" in val:
                action_cell.fill = red_fill
                action_cell.font = bold_font

    print(f"✅ English Master Dashboard saved: {excel_file}")