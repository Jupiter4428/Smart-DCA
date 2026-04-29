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
from src.indicators import (
    download_historical_data, 
    calculate_rsi, 
    calculate_macd, 
    calculate_historical_growth,
    calculate_ema  # <-- เพิ่มคำนี้เข้าไป
)
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
    """สร้างรายงานการถือครองหุ้นปัจจุบัน โดยไม่แสดงต้นทุน"""
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

        if symbol == 'GC=F':
            units_str = f"{MTS_GOLD_OZ:.6f} oz"
        else:
            units = CURRENT_HOLDINGS_SHARES.get(symbol, 0.0)
            units_str = f"{units:.7f} shares"

        rows.append({
            'Symbol'       : _display_name(symbol),
            'Units'        : units_str,
            'Price (USD)'  : price_str,
            'Current (USD)': f"${val_usd:,.2f}",
            'Curr %'       : f"{pct:.2f}%",
            'Tgt %'        : f"{target_pct:.2f}%",
            'Status'       : status,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────
# 1. ฟังก์ชันสร้างข้อมูล DCA Action (แก้ไขชื่อคอลัมน์ให้สั้นและตรงกัน)
# ─────────────────────────────────────────────────────────────────
def generate_dca_action_report(rate: float) -> pd.DataFrame:
    holdings_usd = _get_current_holdings_usd()
    total_usd    = _get_total_portfolio_usd(holdings_usd)

    rebalance_factors = calculate_rebalance_factors(
        portfolio        = TARGET_PORTFOLIO,
        current_holdings = holdings_usd,
        total_value_usd  = total_usd,
        exchange_rate    = 1.0,
    )

    rows = []
    symbol_actions = {}
    for symbol, target_pct in TARGET_PORTFOLIO.items():
        ind = get_cached_indicators(symbol)
        rsi = ind['rsi'] if ind else None
        pe_val = get_cached_pe(symbol)
        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        action, reason = get_action_signal(symbol, curr_pct, target_pct, rsi, pe_val)
        symbol_actions[symbol] = {'action': action, 'reason': reason, 'rsi': rsi, 'price': ind['price'] if ind else 0.0}

    eligible_symbols = [s for s, d in symbol_actions.items() if "HOLD" not in d['action'] and "SKIP" not in d['action']]
    f_sum = sum(rebalance_factors[s] for s in eligible_symbols)
    
    total_dca_usd = 0.0
    for symbol in TARGET_PORTFOLIO:
        data = symbol_actions[symbol]
        final_usd = (MONTHLY_DCA_BUDGET_USD * (rebalance_factors[symbol] / f_sum)) if symbol in eligible_symbols and f_sum > 0 else 0.0
        total_dca_usd += final_usd
        
        # ใช้ชื่อคีย์ให้สั้นและตรงกับฟังก์ชัน print
        rows.append({
            'Symbol': _display_name(symbol), 
            'Price': f"${data['price']:,.2f}", 
            'RSI': data['rsi'],
            'DCA_USD': final_usd, 
            'DCA_THB': final_usd * rate, 
            'Action': data['action'], 
            'Reason': data['reason']
        })
    
    df = pd.DataFrame(rows)
    rem = max(0.0, MONTHLY_DCA_BUDGET_USD - total_dca_usd)
    df.loc[len(df)] = ['TOTAL', 'N/A', None, total_dca_usd, total_dca_usd * rate, 'REM CASH:', f"${rem:.2f}"]
    return df

# ─────────────────────────────────────────────────────────────────
# 2. ฟังก์ชันสร้างข้อมูล Technical (Ranging + แก้ไขชื่อคอลัมน์)
# ─────────────────────────────────────────────────────────────────
def generate_technical_report() -> pd.DataFrame:
    """สร้างรายงาน Technical Analysis: RSI Ranging + EMA 26 Support"""
    rows = []
    for symbol in TARGET_PORTFOLIO:
        ind = get_cached_indicators(symbol)
        if not ind: continue
        
        df = ind['df']
        close_price = ind['price']
        
        # --- EMA 26 Logic (ตามบทความ: เช็คจุดพักฐาน) ---
        ema_series = calculate_ema(df['Close'], 26)
        ema26 = ema_series.iloc[-1]
        diff_ema = ((close_price - ema26) / ema26) * 100
        
        if diff_ema > 5:
            ema_status = "Extended 🚀"    # ลอยห่างเส้น (จบยากแต่ระวังย่อ)
        elif diff_ema < -2:
            ema_status = "Below 📉"       # หลุดเส้น
        else:
            ema_status = "At Support 🛡️" # พักฐานใกล้เส้น (จุดสะสม)

        # --- RSI Ranging Logic ---
        rsi_val = ind['rsi']
        if rsi_val > 70:
            rsi_sig = "Overbought 🔴"
        elif rsi_val < 30:
            rsi_sig = "Oversold 🟢"
        else:
            rsi_sig = "Ranging ↔️"

        rows.append({
            'Symbol': _display_name(symbol), 
            'Price': f"${close_price:,.2f}", 
            'PE': get_cached_pe(symbol),
            'EMA26': f"${ema26:,.2f}",
            'EMA_S': ema_status,
            'RSI': round(rsi_val, 2), 
            'RSI_S': rsi_sig,
            'MSig': "Bull 🟢" if ind['macd'] > ind['signal'] else "Bear 🔴",
            'Growth': f"{calculate_historical_growth(df)*100:+.2f}%"
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
# 3. ฟังก์ชันหลักสำหรับพิมพ์ออกหน้า Console 
# ─────────────────────────────────────────────────────────────────
def print_reports_to_console(rate: float):
    """ฟังก์ชันพิมพ์รายงานแบบจัดช่องไฟใหม่ (FixedWidth) เพื่อให้ตารางตรงกันเป๊ะ"""
    
    # --- 1. Portfolio Summary ---
    print("\n" + "="*160 + "\n📋 PORTFOLIO SUMMARY\n" + "="*160)
    for _, r in generate_portfolio_summary(rate).iterrows(): 
        print(f"{r['Metric']:<50} {r['Value']}")
    
    # --- 2. Holdings Report ---
    print("\n" + "="*160 + "\n💼 HOLDINGS REPORT\n" + "="*160)
    h_df = generate_holdings_report(rate)
    # กำหนดความกว้างคอลัมน์ให้คงที่เพื่อป้องกันการเลี้ยว
    print(f"{'Symbol':<20} {'Units':<20} {'Price (USD)':<12} {'Current (USD)':<15} {'Curr %':>8} {'Tgt %':>8} {'Status'}")
    print("-" * 160)
    for _, r in h_df.iterrows():
        print(f"{r['Symbol']:<20} {r['Units']:<20} {r['Price (USD)']:<12} {r['Current (USD)']:<15} {r['Curr %']:>8} {r['Tgt %']:>8} {r['Status']}")

    # --- 3. DCA Action Plan ---
    print("\n" + "="*160 + "\n🎯 DCA ACTION PLAN\n" + "="*160)
    dca_df = generate_dca_action_report(rate)
    print(f"{'Symbol':<20} {'Price':<12} {'RSI':>8} {'DCA (USD)':>14} {'DCA (THB)':>14} {'Action':<18} {'Reason'}")
    print("-" * 160)
    for _, r in dca_df.iterrows():
        rsi = f"{r['RSI']:.2f}" if isinstance(r['RSI'], (float, int)) else ""
        usd = f"${r['DCA_USD']:,.2f}" if isinstance(r['DCA_USD'], (float, int)) else r['DCA_USD']
        thb = f"฿{r['DCA_THB']:,.2f}" if isinstance(r['DCA_THB'], (float, int)) else r['DCA_THB']
        print(f"{r['Symbol']:<20} {r['Price']:<12} {rsi:>8} {usd:>14} {thb:>14} {r['Action']:<18} {r['Reason']}")

    # --- 4. Technical Analysis (EMA 26 & RSI) ---
    print("\n" + "="*160 + "\n📊 TECHNICAL ANALYSIS (EMA 26 & RSI RANGING)\n" + "="*160)
    tech_df = generate_technical_report()
    # กำหนดความกว้างให้รองรับ Emoji และข้อความไม่ให้เบียดกัน
    print(f"{'Symbol':<20} {'Price':<12} {'PE':<8} {'EMA(26)':<12} {'EMA Signal':<18} {'RSI':>8} {'RSI Signal':<18} {'MSig':<10} {'Growth'}")
    print("-" * 160)
    for _, r in tech_df.iterrows():
        pe_str = str(r['PE'])
        print(f"{r['Symbol']:<20} {r['Price']:<12} {pe_str:<8} {r['EMA26']:<12} {r['EMA_S']:<18} {r['RSI']:>8.2f} {r['RSI_S']:<18} {r['MSig']:<10} {r['Growth']}")
    
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