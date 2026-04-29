"""
🔧 UTILITY FUNCTIONS
====================
Helper functions for data fetching, formatting, and common operations.
"""

import yfinance as yf
import requests
from config import DEFAULT_EXCHANGE_RATE, EXCHANGE_RATE_TIMEOUT


def get_thb_usd_rate():
    """
    Fetch real-time THB/USD exchange rate.

    Returns:
        float: Exchange rate (1 USD = X THB)

    Tries multiple sources:
    1. yfinance (USDTHB=X)
    2. exchangerate-api.com free API
    3. Default fallback value
    """
    # ─────────────────────────────────────────────────────────────
    # ✅ FIX: ระบุ exception ให้ชัดเจน แทน bare except:
    #    เดิม: except: ← จับทุกอย่างรวม KeyboardInterrupt, SystemExit
    # ─────────────────────────────────────────────────────────────
    try:
        # Method 1: yfinance
        # ✅ FIX: .values.flatten() รองรับทั้ง 1D และ 2D array จาก yfinance
        usd_thb = yf.download('USDTHB=X', period='1d', progress=False)['Close'].values.flatten()[-1]
        return float(usd_thb)
    except Exception as e:
        print(f"⚠️  yfinance exchange rate failed: {e}")
        try:
            # Method 2: Free API
            response = requests.get(
                'https://api.exchangerate-api.com/v4/latest/USD',
                timeout=EXCHANGE_RATE_TIMEOUT
            )
            response.raise_for_status()  # ✅ FIX: ตรวจ HTTP error ด้วย
            rate = response.json()['rates']['THB']
            return float(rate)
        except Exception as e:
            print(f"⚠️  exchangerate-api failed: {e}")
            print(f"⚠️  Warning: Could not fetch exchange rate, using default {DEFAULT_EXCHANGE_RATE}")
            return DEFAULT_EXCHANGE_RATE


def validate_portfolio_weights(portfolio):
    """
    Validate that portfolio weights sum to 100%.

    Args:
        portfolio (dict): Portfolio with symbols as keys and weights (%) as values

    Raises:
        ValueError: If weights don't sum to 100%
    """
    total_weight = sum(portfolio.values())
    if abs(total_weight - 100) > 0.01:
        raise ValueError(f"Portfolio weights must sum to 100%, but got {total_weight}%")


def format_currency(value, currency_symbol="฿"):
    """
    Format currency value with thousands separator.

    Args:
        value (float): Amount to format
        currency_symbol (str): Currency symbol

    Returns:
        str: Formatted currency string
    """
    return f"{currency_symbol}{value:,.2f}"


def format_percentage(value):
    """
    Format percentage value.

    Args:
        value (float): Percentage value

    Returns:
        str: Formatted percentage string
    """
    return f"{value:>8.2f}%"


def get_status_indicator(diff_pct, tolerance=0.5):
    """
    Get status indicator based on percentage difference.

    Args:
        diff_pct (float): Current % - Target %
        tolerance (float): Tolerance before triggering status

    Returns:
        tuple: (status_str, emoji_str)
    """
    if abs(diff_pct) < tolerance:
        return "✅ On Target", "✅"
    elif diff_pct > 0:
        return "⚠️  OVERWEIGHT", "⚠️"
    else:
        return "🔴 UNDERWEIGHT", "🔴"


def print_section(title, width=95):
    """
    Print a formatted section header.

    Args:
        title (str): Section title
        width (int): Width of the section
    """
    print(f"\n{'='*width}")
    print(f"📈 {title}")
    print(f"{'='*width}")


def print_subsection(title, width=130):
    """
    Print a formatted subsection header.

    Args:
        title (str): Subsection title
        width (int): Width of the subsection
    """
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")