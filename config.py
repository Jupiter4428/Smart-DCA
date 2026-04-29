"""
📋 PORTFOLIO CONFIGURATION & SETTINGS
=====================================
All portfolio targets, current holdings, and DCA strategy defined here.
Modify this file to update your portfolio settings.

หมายเหตุ GLD → MTS-GOLD:
    MTS Gold ไม่มีใน yfinance → ระบบใช้ราคา GLD (USD/troy oz) × ปริมาณทองแทน
    ตั้งค่า MTS_GOLD_OZ = จำนวน troy oz ทองที่ถือ
    มูลค่า (USD) = MTS_GOLD_OZ × GLD_price_per_oz
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════════
# 🎯 TARGET PORTFOLIO ALLOCATION (%)
# ═══════════════════════════════════════════════════════════════════
TARGET_PORTFOLIO = {
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

# ═══════════════════════════════════════════════════════════════════
# 📦 CURRENT HOLDINGS — จำนวนหุ้น (shares)
# ═══════════════════════════════════════════════════════════════════
# ✏️  กรอกตัวเลขจาก Dime app ทุกครั้งที่ซื้อเพิ่ม
# ระบบดึงราคาล่าสุดจาก yfinance แล้วคำนวณมูลค่า USD อัตโนมัติ
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

# ── ทองคำ MTS-Gold ──────────────────────────────────────────────
# MTS-GOLD ซื้อขายเป็น troy oz, ราคาอ้างอิง GLD (troy oz) จาก yfinance
# มูลค่า (USD) = MTS_GOLD_OZ × GLD_price_per_troy_oz
MTS_GOLD_OZ = 0.0   # ✏️  ใส่จำนวน troy oz ทองที่ถือใน MTS-Gold
                     #     1 troy oz = 31.1035 กรัม
                     #     ตัวอย่าง: ทอง 5 กรัม = 5 / 31.1035 ≈ 0.1608 oz

# ── Validation ──────────────────────────────────────────────────
assert MTS_GOLD_OZ >= 0, "MTS_GOLD_OZ ต้องเป็นค่า >= 0"

# ═══════════════════════════════════════════════════════════════════
# 📊 DCA STRATEGY SETTINGS
# ═══════════════════════════════════════════════════════════════════
ANNUAL_GROWTH_TARGET   = 0.12    # เป้าหมาย 12% ต่อปี
MONTHLY_DCA_BUDGET_USD = 46.22   # งบ DCA ต่อเดือน (USD)

# Auto-calculate เดือนที่เหลือในปีปัจจุบัน
_today = date.today()
REMAINING_MONTHS = max(1, 12 - _today.month + 1)

# ═══════════════════════════════════════════════════════════════════
# 🔧 TECHNICAL INDICATOR SETTINGS
# ═══════════════════════════════════════════════════════════════════
RSI_PERIOD     = 14
RSI_OVERSOLD   = 30
RSI_OVERBOUGHT = 70
MACD_FAST      = 12
MACD_SLOW      = 26
MACD_SIGNAL    = 9
DATA_PERIOD    = "12mo"

# ═══════════════════════════════════════════════════════════════════
# ⚙️ REBALANCING SETTINGS
# ═══════════════════════════════════════════════════════════════════
REBALANCE_TOLERANCE  = 0.5
MIN_REBALANCE_FACTOR = 0.3
MAX_REBALANCE_FACTOR = 1.5

# ═══════════════════════════════════════════════════════════════════
# 💱 CURRENCY SETTINGS
# ═══════════════════════════════════════════════════════════════════
DEFAULT_EXCHANGE_RATE = 33.5
EXCHANGE_RATE_TIMEOUT = 5

# ═══════════════════════════════════════════════════════════════════
# 📋 DISPLAY SETTINGS
# ═══════════════════════════════════════════════════════════════════
SHOW_EMOJI     = True
DECIMAL_PLACES = 2