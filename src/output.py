"""
📊 OUTPUT & REPORTING
=====================
Console and Excel report generation for the DCA Portfolio System.

การเปลี่ยนแปลงหลัก:
  1. รองรับ CURRENT_HOLDINGS_SHARES (จำนวนหุ้น) → มูลค่า = shares × latest_price
  2. รองรับ MTS-GOLD: มูลค่า = MTS_GOLD_OZ × GC=F_price_per_troy_oz
  3. แก้ bug Price (USD) ใน Holdings — ดึงจาก get_cached_indicators() โดยตรง
  4. เพิ่ม GC=F label เป็น 'GC=F (MTS-Gold)' ใน legend ทุก report
  5. เพิ่ม print_action_alerts() — สรุป STRONG BUY / SELL ท้าย console
"""

import pandas as pd
import os
import csv
import numpy as np
from datetime import datetime
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

from config import (
    TARGET_PORTFOLIO,
    CURRENT_HOLDINGS_SHARES,
    MTS_GOLD_OZ,
    ANNUAL_GROWTH_TARGET,
    MONTHLY_DCA_BUDGET_USD,
    REMAINING_MONTHS,
    REBALANCE_TOLERANCE,
    RSI_OVERSOLD,      # <-- เพิ่มบรรทัดนี้
    RSI_OVERBOUGHT,    # <-- เพิ่มบรรทัดนี้
)

from src.indicators import download_historical_data, calculate_rsi, calculate_macd
from src.utils import get_status_indicator
from src.portfolio import get_action_signal, calculate_rebalance_factors


# ─────────────────────────────────────────────────────────────────
# In-Memory Indicator Cache
# ─────────────────────────────────────────────────────────────────
_indicator_cache: dict = {}
_cache_hits:   list[str] = []
_cache_misses: list[str] = []


def get_cached_indicators(symbol: str) -> dict | None:
    """
    Return cached technical indicators for a symbol.
    Downloads from yfinance only on first call per session.
    GC=F ถูกใช้เป็น proxy ราคาสำหรับ MTS-GOLD
    """
    if symbol not in _indicator_cache:
        from src.indicators import _is_cache_valid, _get_cache_path
        from config import DATA_PERIOD

        was_cached = _is_cache_valid(_get_cache_path(symbol, DATA_PERIOD))

        df = download_historical_data(symbol)
        if df is None or df.empty:
            _indicator_cache[symbol] = None
        else:
            close = df['Close'].squeeze()
            rsi_series, signal_series = calculate_rsi(close), None
            rsi_series  = calculate_rsi(close)
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
    """แสดงสรุป cache status เป็นบรรทัดเดียว"""
    if _cache_hits:
        print(f"📂 Cache hit : {', '.join(_cache_hits)}")
    if _cache_misses:
        print(f"🌐 Downloaded: {', '.join(_cache_misses)}")


def clear_indicator_cache() -> None:
    """Clear in-memory indicator cache and hit/miss tracking."""
    _indicator_cache.clear()
    _cache_hits.clear()
    _cache_misses.clear()


# ─────────────────────────────────────────────────────────────────
# Portfolio Value Calculation (shares × price)
# ─────────────────────────────────────────────────────────────────

def _display_name(symbol: str) -> str:
    """Return display label for a symbol."""
    return f"{symbol} (MTS-Gold)" if symbol == 'GC=F' else symbol


def _get_current_holdings_usd() -> dict[str, float]:
    """
    คำนวณมูลค่าปัจจุบันทุก symbol เป็น USD

    - หุ้นทั่วไป : shares × latest_price (USD)
    - GC=F (MTS-GOLD) : MTS_GOLD_OZ × GC=F_price_per_troy_oz

    Returns:
        dict {symbol: value_usd}
    """
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
    """Generate high-level portfolio metrics (USD primary, THB secondary)."""
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)
    total_thb    = total_usd * rate

    target_end_usd = total_usd * (1 + ANNUAL_GROWTH_TARGET)
    target_end_thb = target_end_usd * rate
    req_dca_usd    = (target_end_usd - total_usd) / REMAINING_MONTHS
    budget_thb     = MONTHLY_DCA_BUDGET_USD * rate

    # Gold display
    gcf_ind       = get_cached_indicators('GC=F')
    gcf_price_str = f"${gcf_ind['price']:,.2f}/oz" if gcf_ind else "N/A"
    gold_usd      = holdings_usd.get('GC=F', 0.0)

    data = {
        'Metric': [
            'Timestamp',
            'Total Portfolio Value (USD / THB)',
            'Exchange Rate (THB/USD)',
            'Annual Growth Target',
            'Monthly DCA Budget (USD / THB)',
            'Remaining Months',
            'Target End Year Value (USD / THB)',
            'Required Monthly DCA (USD / THB)',
            'Gold Holdings (MTS-Gold)',
        ],
        'Value': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f"${total_usd:,.2f}  /  ฿{total_thb:,.2f}",
            f"{rate:.2f}",
            f"{ANNUAL_GROWTH_TARGET * 100:.1f}%",
            f"${MONTHLY_DCA_BUDGET_USD:,.2f}  /  ฿{budget_thb:,.2f}",
            REMAINING_MONTHS,
            f"${target_end_usd:,.2f}  /  ฿{target_end_thb:,.2f}",
            f"${req_dca_usd:,.2f}  /  ฿{req_dca_usd * rate:,.2f}",
            f"{MTS_GOLD_OZ:.6f} oz  ({MTS_GOLD_OZ * 31.1035:.4f} g)  |  {gcf_price_str}  |  ${gold_usd:,.2f}",
        ]
    }
    return pd.DataFrame(data)


def generate_holdings_report(rate: float) -> pd.DataFrame:
    """Generate current allocation vs target report."""
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    rows = []
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        val_usd = holdings_usd.get(symbol, 0.0)
        val_thb = val_usd * rate
        pct     = (val_usd / total_usd * 100) if total_usd > 0 else 0.0
        diff    = pct - target_pct
        status, _ = get_status_indicator(diff, REBALANCE_TOLERANCE)

        # ── Price: ดึงจาก cache โดยตรง (แก้ bug เดิม) ──
        ind = get_cached_indicators(symbol)
        if ind:
            price_str = f"${ind['price']:,.2f}" + (" /oz" if symbol == 'GC=F' else "")
        else:
            price_str = "N/A"

        # ── Units display ──
        if symbol == 'GC=F':
            units_str = f"{MTS_GOLD_OZ:.6f} oz ({MTS_GOLD_OZ * 31.1035:.4f} g)"
        else:
            units_str = f"{CURRENT_HOLDINGS_SHARES.get(symbol, 0.0):.7f} shares"

        rows.append({
            'Symbol'       : _display_name(symbol),
            'Units'        : units_str,
            'Price (USD)'  : price_str,
            'Current (USD)': val_usd,
            'Current (THB)': val_thb,
            'Current %'    : f"{pct:.2f}%",
            'Target %'     : f"{target_pct:.2f}%",
            'Diff %'       : f"{diff:+.2f}%",
            'Status'       : status,
        })
    return pd.DataFrame(rows)


def generate_dca_action_report(rate: float) -> pd.DataFrame:
    """Generate tactical DCA recommendations."""
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    rebalance_factors = calculate_rebalance_factors(
        portfolio        = TARGET_PORTFOLIO,
        current_holdings = holdings_usd,
        total_value_usd  = total_usd,
        exchange_rate    = 1.0,
    )

    rows = []
    total_tactical_usd = 0.0

    for symbol, target_pct in TARGET_PORTFOLIO.items():
        adj_budget = MONTHLY_DCA_BUDGET_USD * rebalance_factors[symbol]

        ind = get_cached_indicators(symbol)
        rsi = ind['rsi'] if ind else None

        if rsi is not None and rsi >= RSI_OVERBOUGHT:
            mul = 0.20
        elif rsi is not None and rsi <= RSI_OVERSOLD:
            mul = 1.50
        elif rsi is not None:
            mul = float(np.clip((100 - rsi) / 50, 0.5, 1.5))
        else:
            mul = 1.0

        final_usd = adj_budget * mul
        total_tactical_usd += final_usd

        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        action, reason = get_action_signal(curr_pct, target_pct, rsi)

        rows.append({
            'Symbol'       : _display_name(symbol),
            'RSI'          : rsi,
            'DCA (USD)'    : final_usd,
            'DCA (THB)'    : final_usd * rate,
            'Action Signal': action,
            'Reason'       : reason,
        })

    remaining_usd = MONTHLY_DCA_BUDGET_USD - total_tactical_usd
    df = pd.DataFrame(rows)
    df.loc[len(df)] = [
        'TOTAL', None,
        total_tactical_usd, total_tactical_usd * rate,
        'REMAINING CASH:', f"${remaining_usd:.2f} / ฿{remaining_usd * rate:.2f}"
    ]
    return df


def generate_technical_report() -> pd.DataFrame:
    """Generate technical analysis summary (RSI, MACD, Signal)."""
    rows = []
    for symbol in TARGET_PORTFOLIO:
        ind = get_cached_indicators(symbol)
        if ind:
            rows.append({
                'Symbol'     : _display_name(symbol),
                'Price (USD)': f"${ind['price']:,.2f}" + (" /oz" if symbol == 'GC=F' else ""),
                'RSI(14)'    : round(ind['rsi'], 2),
                'RSI Signal' : ("Overbought" if ind['rsi'] > RSI_OVERBOUGHT
                                else "Oversold" if ind['rsi'] < RSI_OVERSOLD
                                else "Neutral"),
                'MACD'       : round(ind['macd'], 4),
                'Signal'     : round(ind['signal'], 4),
                'MACD Signal': "Bullish 🟢" if ind['macd'] > ind['signal'] else "Bearish 🔴",
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# ✅ ฟีเจอร์ใหม่: Action Alert Summary
# ─────────────────────────────────────────────────────────────────

def print_action_alerts(rate: float) -> None:
    """
    แสดงสรุป STRONG BUY และ SELL ท้าย console
    เรียกหลัง generate_dca_action_report() เพื่อใช้ cache ที่มีอยู่แล้ว
    """
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    strong_buys = []
    sells       = []

    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        rsi = ind['rsi'] if ind else None
        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        action, reason = get_action_signal(curr_pct, target_pct, rsi)

        name = _display_name(symbol)
        rsi_str = f"RSI {rsi:.1f}" if rsi is not None else "RSI N/A"

        if "STRONG BUY" in action:
            strong_buys.append(f"  {name:<22} {rsi_str}  — {reason}")
        elif "SELL" in action:
            sells.append(f"  {name:<22} {rsi_str}  — {reason}")

    print("\n" + "=" * 100)
    print("🚨 ACTION ALERTS")
    print("=" * 100)

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

    print("=" * 100)


# ─────────────────────────────────────────────────────────────────
# Console & Excel Output
# ─────────────────────────────────────────────────────────────────

def print_reports_to_console(rate: float) -> None:
    """Formatted terminal output of all reports with consistent table styles."""
    
    # ─────────────────────────────────────────────────────────────────
    # 📋 1. PORTFOLIO SUMMARY (ปรับให้มี Header เหมือนตารางอื่น)
    # ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("📊 PORTFOLIO ANALYSIS REPORT")
    print("=" * 100)
    print("\n📋 PORTFOLIO SUMMARY")
    print("-" * 100)
    summary_df = generate_portfolio_summary(rate)
    for _, row in summary_df.iterrows():
        print(f"{row['Metric']:.<60} {row['Value']}")

    # ─────────────────────────────────────────────────────────────────
    # 💰 2. HOLDINGS REPORT (ต้นแบบ)
    # ─────────────────────────────────────────────────────────────────
    print("\n💰 HOLDINGS REPORT")
    print("-" * 125)
    holdings_df = generate_holdings_report(rate)
    print(
        f"{'Symbol':<22}  {'Units':<28}  {'Price(USD)':<14}  "
        f"{'Current(USD)':>12}  {'Current(THB)':>13}  "
        f"{'Curr%':>7}  {'Tgt%':>6}  {'Diff%':>7}  {'Status':<22}"
    )
    print("-" * 125)
    for _, row in holdings_df.iterrows():
        print(
            f"{row['Symbol']:<22}  {row['Units']:<28}  {row['Price (USD)']:<14}  "
            f"{row['Current (USD)']:>12,.2f}  {row['Current (THB)']:>13,.2f}  "
            f"{row['Current %']:>7}  {row['Target %']:>6}  {row['Diff %']:>7}  {row['Status']:<22}"
        )

    # ─────────────────────────────────────────────────────────────────
    # 📈 3. DCA RECOMMENDATIONS (ปรับปรุงใหม่)
    # ─────────────────────────────────────────────────────────────────
    print("\n📈 DCA RECOMMENDATIONS (Tactical Action)")
    print("-" * 115)
    print_cache_summary()
    print("-" * 115)
    dca_df = generate_dca_action_report(rate)
    
    print(
        f"{'Symbol':<22}  {'RSI':>8}  {'DCA (USD)':>12}  "
        f"{'DCA (THB)':>13}  {'Action Signal':<18}  {'Reason':<30}"
    )
    print("-" * 115)
    
    for _, row in dca_df.iterrows():
        # จัดการกรณีแถว TOTAL ที่ค่าบางอย่างเป็น None
        rsi_val = f"{row['RSI']:.2f}" if isinstance(row['RSI'], (int, float)) else ""
        dca_usd = f"${row['DCA (USD)']:,.2f}" if isinstance(row['DCA (USD)'], (int, float)) else row['DCA (USD)']
        dca_thb = f"฿{row['DCA (THB)']:,.2f}" if isinstance(row['DCA (THB)'], (int, float)) else row['DCA (THB)']
        
        print(
            f"{row['Symbol']:<22}  {rsi_val:>8}  {dca_usd:>12}  "
            f"{dca_thb:>13}  {row['Action Signal']:<18}  {row['Reason']:<30}"
        )

    # ─────────────────────────────────────────────────────────────────
    # 📊 4. TECHNICAL ANALYSIS (ปรับปรุงใหม่)
    # ─────────────────────────────────────────────────────────────────
    print("\n📊 TECHNICAL ANALYSIS")
    print("-" * 115)
    tech_df = generate_technical_report()
    
    print(
        f"{'Symbol':<22}  {'Price (USD)':<15}  {'RSI(14)':>8}  "
        f"{'RSI Signal':<12}  {'MACD':>10}  {'Signal':>10}  {'MACD Signal':<15}"
    )
    print("-" * 115)
    
    for _, row in tech_df.iterrows():
        print(
            f"{row['Symbol']:<22}  {row['Price (USD)']:<15}  {row['RSI(14)']:>8.2f}  "
            f"{row['RSI Signal']:<12}  {row['MACD']:>10.4f}  {row['Signal']:>10.4f}  {row['MACD Signal']:<15}"
        )

    # Alerts (ท้ายสุด)
    print_action_alerts(rate)


def save_all_to_excel(rate: float, output_dir: str = './reports') -> None:
    """Save multi-sheet Excel with color highlights."""
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

        # ── DCA_Action: RSI & Action coloring ──
        ws_dca = wb['DCA_Action']
        for row in range(2, ws_dca.max_row + 1):
            rsi_cell    = ws_dca.cell(row=row, column=2)
            action_cell = ws_dca.cell(row=row, column=5)

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

        # ── Holdings: Status coloring ──
        ws_h = wb['Holdings']
        status_col = next(
            (cell.column for cell in ws_h[1] if cell.value == 'Status'), None
        )
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


# ─────────────────────────────────────────────────────────────────
# Performance History
# ─────────────────────────────────────────────────────────────────

def append_performance_history(rate: float) -> None:
    """
    Append today's portfolio snapshot to reports/portfolio_history.csv

    columns: date, total_usd, total_thb, rate, monthly_dca_usd,
             gold_oz, <SYMBOL_USD>...
    บันทึกวันละครั้ง — ถ้าวันนี้บันทึกแล้วจะ skip อัตโนมัติ
    """
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

    # Skip ถ้าวันนี้บันทึกแล้ว
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