"""
📊 OUTPUT & REPORTING
=====================
Console and Excel report generation for the DCA Portfolio System.
"""
import unicodedata
import pandas as pd
import os
import csv
from datetime import datetime
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

# เพิ่ม ANNUAL_GROWTH_TARGET เข้าไปในลิสต์การ import จาก config
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
    ANNUAL_GROWTH_TARGET  # <--- เพิ่มตัวนี้
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

    # 🔥 แก้ไข: ใช้ ANNUAL_GROWTH_TARGET จาก config แบบนิ่งๆ ป้องกันเป้าหมายแกว่งตามระยะเวลา cache ย้อนหลัง
    annual_target = ANNUAL_GROWTH_TARGET
    monthly_rate = annual_target / 12

    fv_current = total_usd * ((1 + monthly_rate) ** REMAINING_MONTHS)
    fv_dca = MONTHLY_DCA_BUDGET_USD * (((1 + monthly_rate) ** REMAINING_MONTHS - 1) / monthly_rate)
    target_end_usd = fv_current + fv_dca
    target_end_thb = target_end_usd * rate

    denominator = (((1 + monthly_rate) ** REMAINING_MONTHS - 1) / monthly_rate)
    # กัน error กรณี denominator = 0
    req_dca_usd = (target_end_usd - fv_current) / denominator if denominator > 0 else 0

    gcf_ind = get_cached_indicators('GC=F')
    gcf_price_str = f"${gcf_ind['price']:,.2f}/oz" if gcf_ind else "N/A"
    gold_usd = holdings_usd.get('GC=F', 0.0)

    data = {
        'Metric': [
            'Timestamp',
            'Total Portfolio Value (USD / THB)',
            'Exchange Rate (THB/USD)',
            'Annual Growth Target (Config)',
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
            f"{annual_target * 100:.2f}%",
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
        
        # ดึงค่า Indicators ออกมาเตรียมส่งให้ get_action_signal
        rsi = ind['rsi'] if ind else None
        macd_val = ind['macd'] if ind else None
        signal_val = ind['signal'] if ind else None
        price = ind['price'] if ind else 0.0
        
        # คำนวณ EMA26 เพื่อส่งให้ระบบตัดสินใจ
        ema26 = None
        if ind and 'df' in ind:
            ema_series = calculate_ema(ind['df']['Close'], 26)
            ema26 = ema_series.iloc[-1]

        pe_val = get_cached_pe(symbol)
        curr_pct = (holdings_usd.get(symbol, 0.0) / total_usd * 100) if total_usd > 0 else 0.0
        
        # 🔥 แก้ไข: ส่ง parameter ครบถ้วนตาม signature ใหม่
        action, reason = get_action_signal(
            symbol, curr_pct, target_pct, rsi, pe_val,
            macd_val=macd_val, signal_val=signal_val,
            price=price, ema26=ema26
        )
        
        symbol_actions[symbol] = {'action': action, 'reason': reason, 'rsi': rsi, 'price': price}

    eligible_symbols = [s for s, d in symbol_actions.items() if "HOLD" not in d['action'] and "SKIP" not in d['action']]
    f_sum = sum(rebalance_factors[s] for s in eligible_symbols)
    
    total_dca_usd = 0.0
    for symbol in TARGET_PORTFOLIO:
        data = symbol_actions[symbol]
        final_usd = (MONTHLY_DCA_BUDGET_USD * (rebalance_factors[symbol] / f_sum)) if symbol in eligible_symbols and f_sum > 0 else 0.0
        total_dca_usd += final_usd
        
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

        # --- RSI Ranging Logic (Same format as EMA Signal) ---
        rsi_val = ind['rsi']
        if rsi_val > 70:
            rsi_sig = "Overbought 🔴"      # Price stretched up (Caution)
        elif rsi_val < 30:
            rsi_sig = "Oversold 🟢"        # Value zone (Accumulate)
        else:
            rsi_sig = "Neutral 🔵"         # Normal range (Hold/DCA)

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

def print_action_alerts(rate: float):
    """ฟังก์ชันพิมพ์สรุปสัญญาณ Action Alerts โดยดึงเหตุผลจริงจากข้อมูล"""
    print("\n" + "="*165 + "\n🚨 STRATEGIC ACTION ALERTS\n" + "="*165)
    
    try:
        # ดึงข้อมูลจาก Action Plan ที่คำนวณไว้แล้ว
        dca_df = generate_dca_action_report(rate)
        
        # กรองเอาเฉพาะตัวที่มีสัญญาณ "BUY" (รวมถึง STRONG BUY)
        # จะได้ไม่เอาตัวที่เป็นแค่ "DCA" ธรรมดาหรือ "HOLD" มาแสดงให้รก
        alerts = dca_df[dca_df['Action'].str.contains('BUY', na=False)]
        
        if not alerts.empty:
            for _, r in alerts.iterrows():
                action_text = str(r['Action'])
                reason_text = str(r['Reason'])
                # ให้ปรินต์ชื่อ Action จริงๆ ออกมาเลย แทนที่จะ Hardcode คำว่า STRONG BUY
                print(f"{action_text:<18} : {r['Symbol']:<6} | {reason_text}")
        else:
            print("⚪ No aggressive BUY signals. Keep following the standard DCA plan.")
            
    except Exception as e:
        print(f"⚪ Alert system paused: {str(e)}")
        
    print("="*165)
    print(f"✅ Report location: ./reports/Master_Portfolio_Report.xlsx")

# ═══════════════════════════════════════════════════════
# DISPLAY WIDTH UTILITIES
# ═══════════════════════════════════════════════════════

FORCE_WIDTH2 = {
    0x2B05, 0x2B06, 0x2B07,
    0x27A1, 0x2194, 0x2195,
    0x25AA, 0x25AB, 0x25B6, 0x25C0,
}

def display_width(text: str) -> int:
    w = 0
    for c in str(text):
        cp = ord(c)
        if 0xFE00 <= cp <= 0xFE0F or cp == 0x200D:
            continue
        if cp in FORCE_WIDTH2 or unicodedata.category(c) == "So" \
                or 0x1F000 <= cp <= 0x1FFFF:
            w += 2
        elif unicodedata.east_asian_width(c) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w

def _rpad(text: str, width: int) -> str:
    s = str(text)
    return s + " " * max(0, width - display_width(s))

def _lpad(text: str, width: int) -> str:
    s = str(text)
    return " " * max(0, width - display_width(s)) + s

def _row(values, widths, aligns, sep=" ") -> str:
    parts = []
    for v, w, a in zip([str(x) for x in values], widths, aligns):
        parts.append(_lpad(v, w) if a == ">" else _rpad(v, w))
    return sep.join(parts)

def debug_ema_widths(tech_df):
    print("\n[DEBUG] EMA Signal display widths:")
    for _, r in tech_df.iterrows():
        s  = str(r["EMA_S"])
        dw = display_width(s)
        print(f"  {repr(s):<30} display_width={dw}")


# ═══════════════════════════════════════════════════════
# MAIN REPORT FUNCTION
# ═══════════════════════════════════════════════════════
def print_reports_to_console(rate: float):
    SEP = "═" * 150   # ← define ไว้ใน function
    DIV = "─" * 150
    # ─────────────────────────────────────────
    # 1. PORTFOLIO SUMMARY
    # ─────────────────────────────────────────
    print(f"\n{SEP}\n📋 PORTFOLIO SUMMARY\n{SEP}")
    summary_df = generate_portfolio_summary(rate)
    for _, row in summary_df.iterrows():
        print(f"{row['Metric']:.<70} {row['Value']}")
        
    # ─────────────────────────────────────────
    # 2. HOLDINGS REPORT
    # ─────────────────────────────────────────
    print(f"\n{SEP}\n💼  HOLDINGS REPORT\n{SEP}")
    h_df = generate_holdings_report(rate)

    H_COLS   = ["Symbol",  "Units", "Price (USD)", "Value (USD)", "Curr %", "Tgt %", "Status"]
    H_WIDTHS = [ 18,        16,      14,            14,            8,         7,       12]
    H_ALIGN  = [ "<",       "<",     "<",           "<",           ">",       ">",     "<"]

    print(_row(H_COLS, H_WIDTHS, H_ALIGN))
    print(DIV)
    for _, r in h_df.iterrows():
        print(_row(
            [r["Symbol"], r["Units"], r["Price (USD)"],
             r["Current (USD)"], r["Curr %"], r["Tgt %"], r["Status"]],
            H_WIDTHS, H_ALIGN
        ))

    # ─────────────────────────────────────────
    # 3. DCA ACTION PLAN
    # ─────────────────────────────────────────
    print(f"\n{SEP}\n🎯  DCA ACTION PLAN\n{SEP}")
    dca_df = generate_dca_action_report(rate)

    D_COLS   = ["Symbol",  "Price", "RSI", "DCA (USD)", "DCA (THB)", "Action Signal", "Reason"]
    D_WIDTHS = [ 18,        14,      7,     14,           14,           18,              28]
    D_ALIGN  = [ "<",       "<",     ">",   ">",          ">",          "<",             "<"]

    print(_row(D_COLS, D_WIDTHS, D_ALIGN))
    print(DIV)
    for _, r in dca_df.iterrows():
        rsi_v = f"{r['RSI']:.2f}"       if isinstance(r["RSI"],     (float, int)) else ""
        usd_v = f"${r['DCA_USD']:,.2f}" if isinstance(r["DCA_USD"], (float, int)) else r["DCA_USD"]
        thb_v = f"฿{r['DCA_THB']:,.2f}" if isinstance(r["DCA_THB"], (float, int)) else r["DCA_THB"]
        print(_row(
            [r["Symbol"], r["Price"], rsi_v, usd_v, thb_v, r["Action"], r["Reason"]],
            D_WIDTHS, D_ALIGN
        ))

    # ─────────────────────────────────────────
    # 4. TECHNICAL ANALYSIS
    # ─────────────────────────────────────────
    print(f"\n{SEP}\n📊  TECHNICAL ANALYSIS  (EMA 26 & RSI)\n{SEP}")
    tech_df = generate_technical_report()

    T_COLS   = ["Symbol", "Price", "PE", "EMA(26)", "EMA Signal", "RSI", "Signal RSI", "MACD", "Growth"]
    T_WIDTHS = [20, 12, 8, 14, 20, 10, 26, 10, 10]
    T_ALIGN  = ["<", "<", "<", ">", "<", ">", "<", "<", ">"]

    print(_row(T_COLS, T_WIDTHS, T_ALIGN))
    print(DIV)
    for _, r in tech_df.iterrows():
        rsi_str = f"{r['RSI']:.2f}" if isinstance(r["RSI"], (float, int)) else str(r["RSI"])
        print(_row(
            [r["Symbol"], r["Price"], r["PE"], r["EMA26"],
             r["EMA_S"], rsi_str, r["RSI_S"], r["MSig"], r["Growth"]],
            T_WIDTHS, T_ALIGN
        ))

    # ─────────────────────────────────────────
    # 5. ACTION ALERTS
    # ─────────────────────────────────────────
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
