"""
📋 PORTFOLIO CONFIGURATION & SETTINGS
=====================================
All portfolio targets, current holdings, and DCA strategy defined here.

🔴 [TRADE SIGNAL LOGIC & CONDITION SUMMARY] 🔴
-----------------------------------------------------------------------
ระบบใช้ Multi-Factor Decision ในการตัดสินใจ โดยแบ่งสีและสัญญาณดังนี้:

1. 🟢 BUY (Accumulate / Strong Buy)
   - เงื่อนไขหลัก: หุ้นมีสัดส่วนน้อยกว่าเป้าหมาย (Underweight)
   - สัญญาณประกอบ: 
     - RSI < 70: ยังไม่แพงเกินไป
     - MACD Bullish: โมเมนตัมเป็นขาขึ้น
     - EMA 26 Support: ราคาอยู่ที่แนวรับ หรือ พักฐานเพื่อไปต่อ
   - การแบ่งสีย่อย:
     - 🟢 Strong Buy: RSI < 30 (Oversold) + MACD Bull 
     - 🟢 Accumulate: RSI 30-70 + Underweight

2. 🟡 BUY (Caution Buy)
   - เงื่อนไข: สัดส่วนน้อยกว่าเป้า (Underweight) แต่ราคามีความเสี่ยง
   - สัญญาณประกอบ:
     - High P/E: ราคาสูงเมื่อเทียบกับกำไร
     - RSI > 70: เข้าเขต Overbought (ซื้อตามวินัยแต่ต้องระวัง)

3. 🔵 DCA (Maintain)
   - เงื่อนไข: ใช้สำหรับสินทรัพย์พิเศษ เช่น Gold (GC=F) 
   - สัญญาณประกอบ: เน้นรักษาวินัย (Disciplined Buy) ไม่ว่ากราฟจะเป็นอย่างไร เพื่อ Hedge พอร์ต

4. ⚪ HOLD (Wait / Rebalance)
   - เงื่อนไขหลัก: หุ้นมีสัดส่วนเกินเป้าหมาย (Overweight)
   - สัญญาณประกอบ: 
     - ระบบจะหยุดจ่ายเงิน DCA ให้ตัวนี้ แล้วโยกงบไปซื้อตัวที่ Underweight แทน
     - "Redirect DCA funds": เก็บกำไรไว้ในหุ้นเดิม แต่ไม่เติมเงินเพิ่ม

5. 🔴 SELL / TRIM (Take Profit)
   - เงื่อนไข: Overweight รุนแรง (> Rebalance Tolerance) 
   - สัญญาณประกอบ: 
     - RSI > 80: ร้อนแรงขั้นสุด
     - MACD Bearish: เริ่มกลับตัวเป็นขาลง

-----------------------------------------------------------------------
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════════
# PRIVATE DATA — โหลดจาก config_private.py (ไม่ถูก push ขึ้น git)
# ═══════════════════════════════════════════════════════════════════
try:
    from config_private import (
        TARGET_PORTFOLIO,
        CURRENT_HOLDINGS_SHARES,
        MTS_GOLD_OZ,
        AVERAGE_COST_USD,
    )
except ImportError:
    raise SystemExit(
        "\n❌ ไม่พบไฟล์ config_private.py\n"
        "   คัดลอก config_private.example.py → config_private.py\n"
        "   แล้วกรอกข้อมูลพอร์ตของคุณ\n"
    )

assert MTS_GOLD_OZ >= 0, "MTS_GOLD_OZ ต้องเป็นค่า >= 0"

# ═══════════════════════════════════════════════════════════════════
# DCA STRATEGY SETTINGS
# ═══════════════════════════════════════════════════════════════════
ANNUAL_GROWTH_TARGET   = 0.12    # เป้าหมาย 12% ต่อปี
MONTHLY_DCA_BUDGET_USD = 45.00   # งบ DCA ต่อเดือน (USD)

# Auto-calculate เดือนที่เหลือในปีปัจจุบัน
_today = date.today()
REMAINING_MONTHS = max(1, 12 - _today.month + 1)
# ═══════════════════════════════════════════════════════════════════
# TECHNICAL INDICATOR SETTINGS
# ═══════════════════════════════════════════════════════════════════
RSI_PERIOD     = 14
RSI_OVERSOLD   = 30
RSI_OVERBOUGHT = 70
MACD_FAST      = 12
MACD_SLOW      = 26
MACD_SIGNAL    = 9
DATA_PERIOD    = "1y"

# ═══════════════════════════════════════════════════════════════════
# REBALANCING SETTINGS
# ═══════════════════════════════════════════════════════════════════
REBALANCE_TOLERANCE  = 0.5
MIN_REBALANCE_FACTOR = 0.3
MAX_REBALANCE_FACTOR = 1.5

# ── Volatility-Adjusted DCA ──────────────────────────────────────
VOL_WINDOW  = 20    # rolling window (trading days)
VOL_DCA_CAP = 1.50  # hard cap: multiplier = 1 + vol/2, never exceed 1.5×

# ═══════════════════════════════════════════════════════════════════
# CURRENCY SETTINGS
# ═══════════════════════════════════════════════════════════════════
DEFAULT_EXCHANGE_RATE = 33.5
EXCHANGE_RATE_TIMEOUT = 5

# ═══════════════════════════════════════════════════════════════════
# DISPLAY SETTINGS
# ═══════════════════════════════════════════════════════════════════
SHOW_EMOJI     = True
DECIMAL_PLACES = 2