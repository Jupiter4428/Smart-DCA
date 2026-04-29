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
    
def get_action_signal(symbol, current_pct, target_pct, rsi_value, pe_value):
    """
    Generate Action Signals based on STRICT DCA Principles + Fundamentals (P/E).
    """
    diff = current_pct - target_pct
    is_underweight = diff < -0.5
    is_overweight = diff > 2.0

    is_oversold = rsi_value <= RSI_OVERSOLD if rsi_value is not None else False
    is_overbought = rsi_value >= RSI_OVERBOUGHT if rsi_value is not None else False

    # 🔍 1. วิเคราะห์ความถูก/แพงจากค่า P/E
    is_expensive = False
    is_cheap = False
    
    if pe_value not in [None, "N/A"]:
        try:
            pe = float(pe_value)
            tech_stocks = ['MSFT', 'GOOGL', 'NVDA', 'ASML', 'TSM']
            value_stocks = ['JNJ', 'PG', 'CVX']
            
            if symbol in tech_stocks:
                if pe > 60: is_expensive = True
                elif pe < 30: is_cheap = True
            elif symbol in value_stocks:
                if pe > 25: is_expensive = True
                elif pe < 15: is_cheap = True
        except:
            pass

    # 🎯 2. ตัดสินใจ Action
    if is_underweight:
        if is_expensive:
            return "BUY 🟡", "Accumulate (Underweight but High P/E)"
        elif is_cheap and is_oversold:
            return "STRONG BUY 🟢🟢", "Undervalued (Low P/E) + Oversold"
        elif is_cheap:
            return "BUY 🟢", "Accumulate (Underweight & Low P/E)"
        else:
            return "BUY 🟢", "Accumulate (Underweight)"
    
    elif is_overweight:
        if is_expensive and is_overbought:
            return "HOLD ⚪", "Overvalued + Overbought (Wait)"
        else:
            return "HOLD ⚪", "Overweight (Redirect DCA funds)"
    
    else: 
        if is_cheap:
            return "DCA 🟢", "Price is cheap (Regular DCA)"
        elif is_expensive:
            return "DCA 🟡", "Price is high but maintain DCA"
        else:
            return "DCA 🔵", "Maintain discipline (Regular DCA)"