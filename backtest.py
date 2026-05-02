import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta

from config import TARGET_PORTFOLIO, MONTHLY_DCA_BUDGET_USD, VOL_WINDOW, VOL_DCA_CAP
from src.indicators import calculate_rsi, calculate_macd, calculate_ema, calculate_volatility
from src.portfolio import calculate_rebalance_factors, get_action_signal
import numpy as np  

# 1. ตั้งค่าพารามิเตอร์ Backtest
START_DATE = "2021-01-01"  # ย้อนหลังกลับไปช่วงตลาดกระทิงและหมี
END_DATE = datetime.today().strftime('%Y-%m-%d')
BUDGET_PER_MONTH = MONTHLY_DCA_BUDGET_USD # $45

print(f"🚀 Starting Backtest Engine: {START_DATE} to {END_DATE}")

# 2. โหลดข้อมูลราคาย้อนหลังทั้งหมด (ครั้งเดียวเพื่อประหยัด API)
print("📥 Downloading historical data...")
hist_data = {}
for symbol in TARGET_PORTFOLIO.keys():
    # ใช้ GLD แทน GC=F สำหรับดึงราคาทองคำย้อนหลังเพื่อความเสถียร
    ticker = 'GLD' if symbol == 'GC=F' else symbol
    df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 🛡️ ระบบ Fallback: หา Adj Close ก่อน ถ้าหาไม่เจอให้กลับไปใช้ Close
    if 'Adj Close' in df.columns:
        hist_data[symbol] = df['Adj Close']
    else:
        hist_data[symbol] = df['Close']

print("✅ Data downloaded. Starting simulation...\n")

# 3. สร้างตัวแปรจำลองพอร์ตโฟลิโอ
portfolio_shares = {symbol: 0.0 for symbol in TARGET_PORTFOLIO.keys()}
portfolio_history = []
pure_dca_shares = {symbol: 0.0 for symbol in TARGET_PORTFOLIO.keys()} # พอร์ตโง่ๆ ไว้เทียบ

# สร้าง List ของวันที่ ที่จะทำการ DCA (เช่น ทุกวันที่ 1 ของเดือน)
dates = pd.date_range(start=START_DATE, end=END_DATE, freq='MS')

# ฟังก์ชันคำนวณ Portfolio Volatility แบบ Weighted
def get_portfolio_vol(current_indicators, target_portfolio):
    total_weight = sum(target_portfolio.values())
    weighted_vol = 0.0
    for symbol, pct in target_portfolio.items():
        if current_indicators[symbol] is not None and 'vol' in current_indicators[symbol]:
            weighted_vol += (pct / total_weight) * current_indicators[symbol]['vol']
    return weighted_vol

# ฟังก์ชันคำนวณ Adjusted DCA Budget
def get_adjusted_budget(port_vol):
    if port_vol > 0:
        multiplier = min(1 + (port_vol / 2), VOL_DCA_CAP)
        return MONTHLY_DCA_BUDGET_USD * multiplier
    return MONTHLY_DCA_BUDGET_USD

# 4. ลูปข้ามเวลาทีละเดือน (Time-Travel Loop)
for current_date in dates:
    current_date_str = current_date.strftime('%Y-%m-%d')
    
    current_prices = {}
    current_indicators = {} # เก็บค่า Indicator ชั่วคราว
    
    # 4.1 เตรียมข้อมูลราคาและคำนวณ Indicator ณ วันนั้นๆ
    for symbol, prices in hist_data.items():
        past_prices = prices.loc[:current_date_str].dropna()
        
        # ต้องมีข้อมูลอย่างน้อย 35 วันถึงจะคำนวณ EMA26 และ MACD ได้แม่นยำ
        if len(past_prices) >= 35:
            current_prices[symbol] = float(past_prices.iloc[-1])
            
            # คำนวณ Indicators จากข้อมูลอดีตล้วนๆ
            rsi_val = calculate_rsi(past_prices).iloc[-1]
            macd_series, signal_series = calculate_macd(past_prices)
            macd_val = macd_series.iloc[-1]
            signal_val = signal_series.iloc[-1]
            ema26_val = calculate_ema(past_prices, 26).iloc[-1]
            
            current_indicators[symbol] = {
                'rsi': float(rsi_val),
                'macd': float(macd_val),
                'signal': float(signal_val),
                'ema26': float(ema26_val),
                'vol': calculate_volatility(past_prices, VOL_WINDOW)
            }
        else:
            current_prices[symbol] = 0.0
            current_indicators[symbol] = None

    # คำนวณมูลค่าพอร์ตรวม ณ วันนี้
    current_holdings_usd = {sym: portfolio_shares[sym] * current_prices[sym] for sym in TARGET_PORTFOLIO}
    total_value_usd = sum(current_holdings_usd.values())

    # 4.2 คำนวณ Rebalance Factors เบื้องต้น
    rebalance_factors = calculate_rebalance_factors(
        portfolio=TARGET_PORTFOLIO,
        current_holdings=current_holdings_usd,
        total_value_usd=total_value_usd,
        exchange_rate=1.0 
    )

    # 4.3 ตัดสินใจ Action (เอา Indicator มาคัดกรอง)
    symbol_actions = {}
    for symbol in TARGET_PORTFOLIO.keys():
        if current_indicators[symbol] is not None:
            curr_pct = (current_holdings_usd[symbol] / total_value_usd * 100) if total_value_usd > 0 else 0.0
            target_pct = TARGET_PORTFOLIO[symbol]
            ind = current_indicators[symbol]
            
            # ส่งเข้าสมองกลหลัก (P/E หาข้อมูลย้อนหลังยาก ให้ส่งเป็น None ไปก่อน)
            action, _ = get_action_signal(
                symbol=symbol, 
                current_pct=curr_pct, 
                target_pct=target_pct, 
                rsi_value=ind['rsi'], 
                pe_value=None, 
                macd_val=ind['macd'], 
                signal_val=ind['signal'], 
                price=current_prices[symbol], 
                ema26=ind['ema26']
            )
            symbol_actions[symbol] = action
        else:
            symbol_actions[symbol] = "SKIP"

    # กรองเฉพาะตัวที่ Action มีคำว่า "BUY" หรือ "DCA" (ตัด HOLD/SKIP ทิ้ง)
    eligible_symbols = [s for s, act in symbol_actions.items() if "HOLD" not in act and "SKIP" not in act]
    
    # 4.4 จัดสรรเงินลงทุน
    f_sum = sum(rebalance_factors[s] for s in eligible_symbols)

    # คำนวณ Portfolio Volatility และ Adjusted Budget
    port_vol = get_portfolio_vol(current_indicators, TARGET_PORTFOLIO)
    adjusted_budget = get_adjusted_budget(port_vol)

    for symbol in TARGET_PORTFOLIO.keys():
        if current_prices[symbol] > 0:
            # ซื้อแบบ Smart DCA (ซื้อเฉพาะตัวที่ผ่านเกณฑ์ Indicator ด้วยงบ Volatility-Adjusted)
            if symbol in eligible_symbols and f_sum > 0:
                allocate_usd = adjusted_budget * (rebalance_factors[symbol] / f_sum)
                portfolio_shares[symbol] += allocate_usd / current_prices[symbol]

            # ซื้อแบบ Pure DCA (ซื้อทุกเดือน หารเท่าเป้าหมายเสมอ ด้วยงบเดิม)
            pure_allocate = MONTHLY_DCA_BUDGET_USD * (TARGET_PORTFOLIO[symbol] / 100)
            pure_dca_shares[symbol] += pure_allocate / current_prices[symbol]

    # บันทึกประวัติ
    new_total_usd = sum(portfolio_shares[sym] * current_prices[sym] for sym in TARGET_PORTFOLIO)
    pure_total_usd = sum(pure_dca_shares[sym] * current_prices[sym] for sym in TARGET_PORTFOLIO)

    portfolio_history.append({
        'Date': current_date,
        'Smart_DCA_Value': new_total_usd,
        'Pure_DCA_Value': pure_total_usd,
        'Total_Invested': MONTHLY_DCA_BUDGET_USD * len(portfolio_history),
        'Smart_Adjusted_Budget': adjusted_budget,
        'Portfolio_Vol': port_vol
    })

# 5. สรุปผลและวาดกราฟ
results_df = pd.DataFrame(portfolio_history).set_index('Date')

# ดึงค่าตัวเลขวันสุดท้ายออกมา
total_invested = results_df['Total_Invested'].iloc[-1]
pure_dca_val = results_df['Pure_DCA_Value'].iloc[-1]
smart_dca_val = results_df['Smart_DCA_Value'].iloc[-1]
avg_adjusted_budget = results_df['Smart_Adjusted_Budget'].mean()
avg_port_vol = results_df['Portfolio_Vol'].mean()

# คำนวณ % กำไร (ROI)
pure_roi = ((pure_dca_val - total_invested) / total_invested) * 100
smart_roi = ((smart_dca_val - total_invested) / total_invested) * 100

# คำนวณส่วนต่างที่ Smart DCA ชนะ Pure DCA
alpha_usd = smart_dca_val - pure_dca_val
alpha_pct = (alpha_usd / pure_dca_val) * 100

print(f"\n📊 BACKTEST RESULTS ({START_DATE} to {END_DATE})")
print("=" * 60)
print(f"💰 Total Invested (Pure DCA): ${total_invested:,.2f}")
print(f"📉 Pure DCA Value : ${pure_dca_val:,.2f}  (กำไร {pure_roi:+.2f}%)")
print(f"📈 Smart DCA Value: ${smart_dca_val:,.2f}  (กำไร {smart_roi:+.2f}%)")
print("-" * 60)
print(f"   Avg Portfolio Vol : {avg_port_vol*100:.2f}%")
print(f"   Avg Adjusted Budget: ${avg_adjusted_budget:,.2f} / mo (vs ${MONTHLY_DCA_BUDGET_USD:,.2f} base)")
print("-" * 60)
print(f"🏆 Smart DCA เอาชนะตลาดได้ (Alpha): +${alpha_usd:,.2f} (+{alpha_pct:.2f}%)")
print("=" * 60 + "\n")

# วาดกราฟเปรียบเทียบ
plt.figure(figsize=(12, 6))
plt.plot(results_df.index, results_df['Smart_DCA_Value'], label=f'Smart DCA (+{smart_roi:.1f}%)', color='purple', linewidth=2)
plt.plot(results_df.index, results_df['Pure_DCA_Value'], label=f'Pure DCA (+{pure_roi:.1f}%)', color='gray', linestyle='--')
plt.plot(results_df.index, results_df['Total_Invested'], label='Total Capital Invested', color='red', linestyle=':')

plt.title('Backtest: Smart DCA vs Pure DCA Portfolio Value')
plt.ylabel('Portfolio Value (USD)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('./reports/backtest_result.png')
print("✅ Chart saved to ./reports/backtest_result.png")