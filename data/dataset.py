import yfinance as yf
import pandas as pd
from config import TARGET_PORTFOLIO
def main():

    # =========================================================================
    # 💡 เงื่อนไขการเลือก PERIOD และ INTERVAL (Yahoo Finance Constraints)
    # -------------------------------------------------------------------------
    # Interval | Max Period ย้อนหลังที่ดึงได้  | การใช้งาน
    # ---------|--------------------------|------------------------------------
    #  1m      |  7d (7 วัน)               | เน้นจังหวะ Scalping
    #  2m, 5m  |  60d (60 วัน)             | กราฟระยะสั้นมาก
    #  15m, 30m|  60d (60 วัน)             | แนะนำสำหรับ DCA/SMC (ละเอียดพอดี)
    #  60m, 1h |  730d (2 ปี)              | มาตรฐานเทคนิคัลรายปี
    #  1d      |  MAX (ไม่จำกัด)            | ดูภาพรวมประวัติศาสตร์ทอง
    # =========================================================================

    # --- ตั้งค่าการดึงข้อมูล (อ้างอิงเงื่อนไขเดิม) ---
    MY_PERIOD = "60d" 
    MY_INTERVAL = "15m"

    try:
        df_portfolio = fetch_portfolio_data(TARGET_PORTFOLIO, MY_PERIOD, MY_INTERVAL)
        
        # บันทึกไฟล์ CSV
        output_file = f"portfolio_history_{MY_PERIOD}_{MY_INTERVAL}.csv"
        df_portfolio.to_csv(output_file)
        
        print("\n" + "="*40)
        print(f"✅ SUCCESS: {output_file}")
        print(f"📊 Total Data Points: {len(df_portfolio)}")
        print("="*40)
        
        # แสดงราคาล่าสุดของทุกตัวในพอร์ต
        print("\n--- Latest Prices (Bangkok Time) ---")
        print(df_portfolio.tail(1).T) # Transpose เพื่อให้ดูง่ายขึ้น

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
def fetch_portfolio_data(portfolio_dict, period, interval):
    """
    ฟังก์ชันดึงข้อมูลหุ้นและสินทรัพย์ตามรายชื่อใน Portfolio
    """
    tickers = list(portfolio_dict.keys())
    print(f"--- Downloading Portfolio: {tickers} ---")
    print(f"--- Period: {period}, Interval: {interval} ---")
    
    # 1. ดึงข้อมูลทุกตัวในครั้งเดียว
    data = yf.download(tickers, period=period, interval=interval, auto_adjust=True)
    
    # 2. จัดการโครงสร้างข้อมูล (เอาเฉพาะราคาปิด 'Close')
    # เนื่องจากดึงหลายตัว yfinance จะส่งกลับมาเป็น MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        close_prices = data['Close']
    else:
        close_prices = data[['Close']]
        close_prices.columns = tickers # กรณีมีตัวเดียว

    # 3. ตัดค่าว่าง (เช่น วันที่บางตัวหยุดแต่บางตัวไม่หยุด)
    close_prices = close_prices.dropna(how='all')

    # 4. จัดการ Timezone (US Stocks ส่วนใหญ่จะเป็น UTC)
    # หมายเหตุ: หุ้นเม็กซิโกหรือยุโรปอาจมีเวลาต่างกัน แต่ yfinance จะ normalize ให้
    if close_prices.index.tz is None:
        close_prices.index = close_prices.index.tz_localize('UTC')
    
    # คุณสามารถเลือกได้ว่าจะดูเวลา US หรือเวลาไทย (ในที่นี้ขอปรับเป็นเวลาไทยให้เหมือนเดิม)
    close_prices.index = close_prices.index.tz_convert('Asia/Bangkok')

    return close_prices

if __name__ == "__main__":
    main()
    
    
    
