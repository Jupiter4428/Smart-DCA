"""
📋 PORTFOLIO MANAGEMENT
======================
Portfolio rebalancing status, tracking, and calculations.
"""

from config import REBALANCE_TOLERANCE, RSI_OVERSOLD, RSI_OVERBOUGHT
from src.utils import get_status_indicator


def calculate_rebalance_factors(portfolio, current_holdings, total_value_usd, exchange_rate):
    """
    Calculate rebalancing factors to prioritize underweighted assets.
    
    Args:
        portfolio (dict): Target portfolio allocation
        current_holdings (dict): Current holdings in THB
        total_value_usd (float): Total portfolio value in USD
        exchange_rate (float): THB/USD exchange rate
        
    Returns:
        dict: Rebalancing factors for each symbol
    """
    rebalance_factors = {}
    
    for symbol in portfolio.keys():
        current_value_thb = current_holdings.get(symbol, 0)
        current_value_usd = current_value_thb / exchange_rate
        current_pct = (current_value_usd / total_value_usd * 100) if total_value_usd > 0 else 0
        target_pct = portfolio[symbol]
        
        diff_pct = current_pct - target_pct
        
        # Boost underweighted, reduce overweighted
        if diff_pct < 0:  # Underweight
            rebalance_factors[symbol] = 1 + abs(diff_pct) / 10
        elif diff_pct > 2:  # Overweight
            rebalance_factors[symbol] = max(0.3, 1 - abs(diff_pct) / 10)
        else:
            rebalance_factors[symbol] = 1.0
    
    # Normalize factors
    total_factor = sum(rebalance_factors.values())
    return {k: v / total_factor for k, v in rebalance_factors.items()}


def get_rebalance_status(symbol, current_holdings, portfolio, total_value, exchange_rate):
    """
    Get rebalancing status for a single symbol.
    
    Args:
        symbol (str): Stock symbol
        current_holdings (dict): Current holdings
        portfolio (dict): Target portfolio
        total_value (float): Total portfolio value in THB
        exchange_rate (float): THB/USD rate
        
    Returns:
        dict: Status information
    """
    current_value_thb = current_holdings.get(symbol, 0)
    current_value_usd = current_value_thb / exchange_rate
    total_value_usd = total_value / exchange_rate
    
    current_pct = (current_value_usd / total_value_usd * 100) if total_value_usd > 0 else 0
    target_pct = portfolio[symbol]
    diff_pct = current_pct - target_pct
    
    target_value_usd = total_value_usd * (target_pct / 100)
    target_value_thb = target_value_usd * exchange_rate
    need_to_add = target_value_thb - current_value_thb
    
    status, emoji = get_status_indicator(diff_pct, REBALANCE_TOLERANCE)
    
    return {
        'symbol': symbol,
        'current_thb': current_value_thb,
        'current_usd': current_value_usd,
        'current_pct': current_pct,
        'target_pct': target_pct,
        'diff_pct': diff_pct,
        'need_to_add': need_to_add,
        'status': status,
        'emoji': emoji
    }


def print_portfolio_status(target_portfolio, current_holdings, total_value, exchange_rate):
    """
    Display portfolio rebalance status with currency optimization.
    
    Args:
        target_portfolio (dict): Target allocation
        current_holdings (dict): Current holdings
        total_value (float): Total portfolio value
        exchange_rate (float): THB/USD rate
    """
    print(f"{'='*140}")
    print(f"📋 PORTFOLIO REBALANCE STATUS: ตรวจสอบความสมดุล (Currency: THB/USD Optimized)")
    print(f"{'='*140}")
    print(f"{'Symbol':<8} | {'Current (THB)':<15} | {'Current (USD)':<15} | {'Current %':<10} | {'Target %':<10} | {'Diff %':<10} | {'Status':<25} | {'Need (THB)':<15}")
    print("-" * 140)
    
    total_current = sum(current_holdings.values())
    
    for symbol in target_portfolio.keys():
        status_info = get_rebalance_status(
            symbol, current_holdings, target_portfolio, total_value, exchange_rate
        )
        
        print(f"{symbol:<8} | ฿{status_info['current_thb']:<14,.2f} | ${status_info['current_usd']:<14,.2f} | {status_info['current_pct']:>8.2f}% | {status_info['target_pct']:>8.2f}% | {status_info['diff_pct']:>8.2f}% | {status_info['status']:<25} | ฿{status_info['need_to_add']:>13,.2f}")
    
    print("-" * 140)
    total_value_usd = total_value / exchange_rate
    print(f"{'TOTAL':<8} | ฿{total_value:<14,.2f} | ${total_value_usd:<14,.2f} | {total_current/total_value*100:>8.2f}% | {'100.00':>8}% |")
    print(f"{'='*140}\n")
    
def get_action_signal(symbol, current_pct, target_pct, rsi_value, pe_value, macd_val=None, signal_val=None, price=None, ema26=None):
    """
    Generate Action Signals with Full Risk Management, Robust None-handling, and Signal Priority.
    Designed for Smart-DCA Portfolio (Wutthisak Boonkan).
    """
    
    # 🔴 0. EXIT Position: ถูกนำออกจาก TARGET_PORTFOLIO แต่ยังถือครอง → ต้องขาย
    if target_pct == 0 and current_pct > 0:
        return "SELL 🔴", "Exit Position (Removed from portfolio — please sell)"

    # 🔵 1. จัดการสินทรัพย์พิเศษ (Hedge Asset)
    # ทองคำทำหน้าที่เป็นประกันความเสี่ยง จึงเน้นวินัยการซื้อ (Disciplined DCA) ไม่ใช้กฎการขายอัตโนมัติ
    if symbol in ['GC=F', 'GLD']:
        return "DCA 🔵", "Hedge asset (Disciplined Buy)"

    # 🛠️ 2. การดักจับค่า None และการคำนวณพื้นฐาน (Defensive Logic)
    # ป้องกัน Error กรณีข้อมูลจาก API มาไม่ครบ
    diff = (current_pct - target_pct) if (current_pct is not None and target_pct is not None) else 0
    is_underweight = diff < -0.5
    is_overweight = diff > 2.0 # สัดส่วนเกินเป้าหมายเกิน 2% เริ่มเข้าข่าย Overweight

    # ตรวจสอบ Technical Indicators (Default เป็น False หากไม่มีข้อมูล)
    is_oversold = (rsi_value <= RSI_OVERSOLD) if rsi_value is not None else False
    is_overbought = (rsi_value >= RSI_OVERBOUGHT) if rsi_value is not None else False
    macd_bullish = (macd_val > signal_val) if (macd_val is not None and signal_val is not None) else False
    
    # 📏 3. Risk Metric: Volatility & Support Check (EMA 26)
    at_ema_support = False
    price_extreme_drop = False # สัญญาณอันตราย: ราคาหลุดแนวรับสำคัญรุนแรง
    
    if all(v is not None for v in [price, ema26]) and ema26 > 0:
        diff_ema = ((price - ema26) / ema26) * 100
        # ช่วงพักฐานที่เหมาะสม (-2% ถึง 5% จากเส้น EMA26)
        at_ema_support = -2 <= diff_ema <= 5
        # Risk Management: หากราคาต่ำกว่า EMA26 เกิน 10% ถือว่าผิดปกติ (Panic/Trend Change)
        if diff_ema < -10:
            price_extreme_drop = True

    # 🔍 4. วิเคราะห์ความถูก/แพง (Fundamental Risk)
    is_expensive = False
    is_cheap = False
    if pe_value not in [None, "N/A", ""]:
        try:
            pe = float(pe_value)
            tech_stocks = ['MSFT', 'GOOGL', 'NVDA', 'ASML', 'TSM']
            value_stocks = ['JNJ', 'PG', 'CVX']
            
            if symbol in tech_stocks:
                is_expensive = pe > 60
                is_cheap = pe < 30
            elif symbol in value_stocks:
                is_expensive = pe > 25
                is_cheap = pe < 15
        except (ValueError, TypeError):
            pass

    # 🎯 5. การตัดสินใจตามลำดับความสำคัญ (Decision Hierarchy)

    # --- [A] RISK FIRST: CAPITAL PROTECTION ---
    # หากราคาร่วงรุนแรงผิดปกติ ให้หยุดซื้อเพื่อรอดูสถานการณ์ (Preserve Cash)
    if price_extreme_drop and not macd_bullish:
        return "HOLD 🟡", "Extreme Downtrend (Stop DCA & Preserve Cash)"

    # --- [B] CASE: UNDERWEIGHT (พอร์ตยังขาดหุ้นตัวนี้) ---
    if is_underweight:
        # Anti-FOMO: แม้สัดส่วนจะขาด แต่ถ้าราคาวิ่งแรงจน Overbought ให้รอย่อตัวก่อน
        if is_expensive or is_overbought:
            return "BUY 🟡", "Underweight but Overbought/Expensive (Wait for Dip)"
        
        # 🟢🟢 STRONG BUY: จุดเข้าซื้อที่ความเสี่ยงต่ำและมีพลังส่งสูง
        # เงื่อนไข: (ต้องมีโมเมนตัม) และ (ต้องถูกหรือ Oversold) และ (ต้องไม่ Overbought)[cite: 1]
        if (macd_bullish or at_ema_support) and (is_cheap or is_oversold) and not is_overbought:
            return "STRONG BUY 🟢🟢", "Undervalued/Oversold + Bullish Momentum"
        
        # 🟢 BUY ปกติ: สะสมเมื่อสัดส่วนขาดและมีสัญญาณบวกบางส่วน
        if macd_bullish or at_ema_support:
            return "BUY 🟢", "Accumulate (Underweight + Bullish/Support)"
        if is_cheap or is_oversold:
            return "BUY 🟢", "Accumulate (Undervalued or Oversold)"
            
        return "BUY 🟡", "Accumulate (Underweight, Neutral Trend)"
    
    # --- [C] CASE: OVERWEIGHT (พอร์ตบวมเกินเป้า) ---
    elif is_overweight:
        # Profit Harvesting: ขายทำกำไรเมื่อบวมมาก (>5%) และราคาร้อนแรงสุดขีด[cite: 1]
        if is_overbought and diff > 5.0:
            return "SELL 🔴", "Extreme Overweight + Overbought (Take Profit)"
        
        # Risk Reduction: หยุดเติมเงินในหุ้นที่แพงหรือ Overbought[cite: 1]
        if (is_expensive or is_overbought) and not macd_bullish:
            return "HOLD ⚪", "Risk Reduction: Overvalued (Wait for Rebalance)"
            
        return "HOLD ⚪", "Overweight (Redirect DCA funds to Underweight assets)"
    
    # --- [D] CASE: ON TARGET (สัดส่วนพอร์ตสมดุล) ---
    else:
        # รักษาพอร์ตตามวินัย (Maintenance DCA)
        if is_cheap and macd_bullish and not is_overbought:
            return "DCA 🟢", "Price is cheap + Bullish (Regular DCA)"
        elif is_expensive or is_overbought:
            return "DCA 🟡", "Price is high but maintain DCA"
            
        return "DCA 🔵", "Maintain discipline (Regular DCA)"