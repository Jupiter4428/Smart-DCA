"""
📊 TECHNICAL INDICATORS
=======================
Calculations for RSI, MACD, Signal line, and trend analysis.

Disk Cache:
    ราคาหุ้นที่ download จาก yfinance จะถูก save ลง data/cache/<SYMBOL>.csv
    และ load กลับมาใช้ถ้า cache ยังเป็นวันปัจจุบัน (market data ไม่เปลี่ยนในวันเดิม)
    → ลด API call และรันเร็วขึ้นมากในรอบที่ 2+
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date
from config import (
    RSI_PERIOD, DATA_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_OVERSOLD, RSI_OVERBOUGHT
)

# ─────────────────────────────────────────────────────────────────
# Disk Cache Settings
# ─────────────────────────────────────────────────────────────────
CACHE_DIR = "./data/cache"


def _get_cache_path(symbol: str, period: str) -> str:
    """Return full path for a symbol's cache file."""
    return os.path.join(CACHE_DIR, f"{symbol}_{period}.csv")


def _is_cache_valid(cache_path: str) -> bool:
    """
    Cache ถือว่า valid ถ้า:
    1. ไฟล์มีอยู่จริง
    2. วันที่ modified ตรงกับวันนี้ (ข้อมูลวันเดิมไม่มีทางเปลี่ยน)
    """
    if not os.path.exists(cache_path):
        return False
    modified_date = date.fromtimestamp(os.path.getmtime(cache_path))
    return modified_date == date.today()


def _load_cache(cache_path: str) -> pd.DataFrame | None:
    """Load DataFrame from CSV cache file."""
    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df if not df.empty else None
    except Exception as e:
        print(f"⚠️  Cache load failed ({cache_path}): {e}")
        return None


def _save_cache(df: pd.DataFrame, cache_path: str) -> None:
    """Save DataFrame to CSV cache file."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(cache_path)
    except Exception as e:
        print(f"⚠️  Cache save failed ({cache_path}): {e}")


def clear_disk_cache() -> None:
    """
    ลบ cache ทั้งหมดใน data/cache/
    เรียกใช้เมื่อต้องการ force download ข้อมูลใหม่ทั้งหมด
    """
    if not os.path.exists(CACHE_DIR):
        print("ℹ️  No cache directory found, nothing to clear.")
        return
    removed = 0
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".csv"):
            os.remove(os.path.join(CACHE_DIR, filename))
            removed += 1
    print(f"🗑️  Cleared {removed} cache file(s) from {CACHE_DIR}")


# ─────────────────────────────────────────────────────────────────
# Core Data Download (with Disk Cache)
# ─────────────────────────────────────────────────────────────────

def download_historical_data(symbol: str, period: str = DATA_PERIOD) -> pd.DataFrame | None:
    """
    Download historical price data for a symbol.
    ใช้ disk cache เมื่อข้อมูลของวันนี้มีอยู่แล้ว → ไม่ hit yfinance ซ้ำ

    Args:
        symbol (str): Stock ticker symbol
        period (str): Data period (e.g., '6mo', '1y')

    Returns:
        DataFrame: Historical OHLCV data, or None if failed
    """
    cache_path = _get_cache_path(symbol, period)

    # ── Load from disk cache if valid ──
    if _is_cache_valid(cache_path):
        df = _load_cache(cache_path)
        if df is not None:
            return df

    # ── Download from yfinance ──
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if df.empty:
            return None

        # Flatten multi-level columns ถ้ามี (yfinance บางเวอร์ชัน return multi-index)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        _save_cache(df, cache_path)
        return df

    except Exception as e:
        print(f"❌ Error downloading {symbol}: {str(e)[:60]}")

        # ── Fallback: ใช้ cache เก่าถ้ามี (แม้จะ stale) ──
        if os.path.exists(cache_path):
            print(f"⚠️  Using stale cache for {symbol} (offline fallback)")
            return _load_cache(cache_path)

        return None


# ─────────────────────────────────────────────────────────────────
# Technical Indicator Calculations (ไม่เปลี่ยน)
# ─────────────────────────────────────────────────────────────────

def calculate_rsi(close_price: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """
    Calculate RSI (Relative Strength Index) using Wilder's Smoothing.

    Args:
        close_price (Series): Series of closing prices
        period (int): RSI lookback period (default 14)

    Returns:
        Series: RSI values
    """
    delta = close_price.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    # Prevent division by zero
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    close_price: pd.Series,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate MACD and Signal line.

    Args:
        close_price (Series): Series of closing prices
        fast (int): Fast EMA period (default 12)
        slow (int): Slow EMA period (default 26)
        signal (int): Signal line EMA period (default 9)

    Returns:
        tuple: (MACD Series, Signal Line Series)
    """
    ema_fast = close_price.ewm(span=fast, adjust=False).mean()
    ema_slow = close_price.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()

    return macd, signal_line


def get_latest_indicators(symbol: str) -> dict | None:
    """
    Get latest technical indicators for a symbol.

    Args:
        symbol (str): Stock ticker symbol

    Returns:
        dict | None: {'rsi', 'macd', 'signal'} or None if failed
    """
    df = download_historical_data(symbol)
    if df is None or df.empty:
        return None

    close_price = df['Close'].squeeze()

    rsi_series = calculate_rsi(close_price)
    macd_series, signal_series = calculate_macd(close_price)

    latest_rsi = rsi_series.iloc[-1]
    latest_macd = macd_series.iloc[-1]
    latest_signal = signal_series.iloc[-1]

    if pd.isna(latest_rsi):
        return None

    return {
        'rsi': float(latest_rsi),
        'macd': float(latest_macd),
        'signal': float(latest_signal),
    }


def analyze_trend(rsi: float, macd: float, signal: float) -> str:
    """
    Analyze trend based on technical indicators.

    Args:
        rsi (float): RSI value (0-100)
        macd (float): MACD value
        signal (float): Signal line value

    Returns:
        str: Trend description with emoji
    """
    trend = "Bullish 🟢" if macd > signal else "Bearish 🔴"

    if rsi < RSI_OVERSOLD:
        trend += " (Oversold - ของถูก!)"
    elif rsi > RSI_OVERBOUGHT:
        trend += " (Overbought - ระวังดอย)"

    return trend

def calculate_historical_growth(df):
    """คำนวณอัตราการเติบโตจริงจากข้อมูลย้อนหลังใน Cache"""
    if df is None or len(df) < 2:
        return 0.0
    
    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    
    # คำนวณหา % การเปลี่ยนแปลงรวม (Total Return)
    total_return = (end_price - start_price) / start_price
    return float(total_return)

def calculate_ema(series, period=26):
    """คำนวณ Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def calculate_volatility(close_price: pd.Series, window: int = 20) -> float:
    """
    Calculate annualised volatility from daily log returns.

    Args:
        close_price (Series): Series of closing prices
        window (int): Rolling window in trading days (default 20)

    Returns:
        float: Annualised volatility (e.g. 0.25 = 25%), or 0.0 if insufficient data
    """
    if len(close_price) < window + 1:
        return 0.0
    log_returns = np.log(close_price / close_price.shift(1)).dropna()
    return float(log_returns.iloc[-window:].std() * np.sqrt(252))