"""
📋 PORTFOLIO CONFIGURATION & SETTINGS
=====================================
All portfolio targets, current holdings, and DCA strategy defined here.
Modify this file to update your portfolio settings.
"""

from datetime import date

# ═══════════════════════════════════════════════════════════════════
# 🎯 TARGET PORTFOLIO ALLOCATION (%)
# ═══════════════════════════════════════════════════════════════════
# Total must equal 100%
TARGET_PORTFOLIO = {
    'MSFT': 18.0,   # แกนหลัก AI & Cloud
    'GOOGL': 14.0,  # แกนหลัก AI & Search
    'NVDA': 6.0,    # AI GPU chips (เสริม ecosystem)
    'ASML': 12.0,   # เครื่องจักรผลิตชิป (supply chain)
    'TSM': 12.0,    # ผลิตชิป (supply chain)
    'GLD': 13.0,    # ทองคำ (Safe Haven) hedging
    'JNJ': 5.0,     # Healthcare defensive
    'PG': 5.0,      # Consumer Staples (ต้านเศรษฐกิจชะลอ)
    'CVX': 4.0,     # Energy/Inflation hedge
    'RGTI': 6.0,    # Quantum growth bet
    'QBTS': 5.0     # Quantum growth bet
}

# ═══════════════════════════════════════════════════════════════════
# 💰 CURRENT_HOLDINGS (in USD)
# ═══════════════════════════════════════════════════════════════════
# อัปเดตทุกเดือนหลัง DCA แล้ว
CURRENT_HOLDINGS = {
    'MSFT': 27.73,
    'GOOGL': 0.0,
    'NVDA': 0.0,
    'ASML': 25.99,
    'TSM': 22.94,
    'GLD': 9.66,
    'JNJ': 0.0,
    'PG': 0.0,
    'CVX': 0.0,
    'RGTI': 18.80,
    'QBTS': 18.35
}

# คำนวณ portfolio value จาก holdings อัตโนมัติ (USD)
CURRENT_PORTFOLIO_VALUE_USD = sum(CURRENT_HOLDINGS.values())

# ═══════════════════════════════════════════════════════════════════
# 📊 DCA STRATEGY SETTINGS
# ═══════════════════════════════════════════════════════════════════
ANNUAL_GROWTH_TARGET   = 0.12    # เป้าหมาย 12% ต่อปี
MONTHLY_DCA_BUDGET_USD = 46.22   # งบ DCA ต่อเดือน (USD)

# ── Auto-calculate เดือนที่เหลือในปีปัจจุบัน ──────────────────────
# เช่น รันเดือน เม.ย. (4) → 12 - 4 + 1 = 9 เดือน
# ไม่ต้องแก้มือทุกเดือนอีกต่อไป
_today = date.today()
REMAINING_MONTHS = max(1, 12 - _today.month + 1)

# ═══════════════════════════════════════════════════════════════════
# 🔧 TECHNICAL INDICATOR SETTINGS
# ═══════════════════════════════════════════════════════════════════
RSI_PERIOD     = 14      # RSI lookback period (days)
RSI_OVERSOLD   = 30      # RSI oversold threshold
RSI_OVERBOUGHT = 70      # RSI overbought threshold
MACD_FAST      = 12      # MACD fast EMA period
MACD_SLOW      = 26      # MACD slow EMA period
MACD_SIGNAL    = 9       # MACD signal line EMA period
DATA_PERIOD    = "12mo"  # Historical data period for analysis

# ═══════════════════════════════════════════════════════════════════
# ⚙️ REBALANCING SETTINGS
# ═══════════════════════════════════════════════════════════════════
REBALANCE_TOLERANCE  = 0.5   # % tolerance before rebalancing needed
MIN_REBALANCE_FACTOR = 0.3   # Minimum allocation multiplier
MAX_REBALANCE_FACTOR = 1.5   # Maximum allocation multiplier

# ═══════════════════════════════════════════════════════════════════
# 💱 CURRENCY SETTINGS
# ═══════════════════════════════════════════════════════════════════
DEFAULT_EXCHANGE_RATE  = 33.5  # Default THB/USD if API fails
EXCHANGE_RATE_TIMEOUT  = 5     # Seconds to wait for API response

# ═══════════════════════════════════════════════════════════════════
# 📋 DISPLAY SETTINGS
# ═══════════════════════════════════════════════════════════════════
SHOW_EMOJI     = True   # Show emoji in output
DECIMAL_PLACES = 2      # Decimal places for currency display