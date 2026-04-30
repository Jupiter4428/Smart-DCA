# 📈 Smart-DCA — Portfolio Analysis System

ระบบวิเคราะห์และจัดการพอร์ตการลงทุนแบบ **Tactical DCA + Active Rebalancing** อัตโนมัติ ออกแบบมาเพื่อเพิ่มประสิทธิภาพการลงทุนเหนือกว่าการ DCA ทั่วไป โดยใช้การคำนวณเชิงปริมาณ (Quantitative Analysis) ร่วมกับสัญญาณทางเทคนิคและพื้นฐาน

---

## ✨ ฟีเจอร์เด่น (Key Features)

- **Multi-Factor Decision Logic:** ตัดสินใจซื้อขายโดยประเมินจาก 4 ปัจจัยหลัก: Rebalance Weight, RSI, MACD และ P/E Ratio (Fundamental)

- **Backtesting Engine:** 🚀 **ใหม่!** ระบบจำลองการลงทุนย้อนหลังตั้งแต่ปี 2021 เพื่อเปรียบเทียบผลตอบแทนระหว่าง "Smart DCA" กับ "Pure DCA" พร้อมคำนวณค่า Alpha

- **EMA 26 Support Analysis:** วิเคราะห์จุดพักฐานของราคาเพื่อหาจังหวะสะสมหุ้นที่ปลอดภัยในเชิงโมเมนตัม

- **Special Hedge Asset Handling:** ระบบแยกการจัดการทองคำ (MTS-Gold) ออกเป็นสินทรัพย์ป้องกันความเสี่ยง เพื่อรักษาวินัยการซื้อสะสมอย่างต่อเนื่องแม้ในสภาวะตลาดผันผวน

- **Disk Cache System:** ระบบบันทึกราคาหุ้นเป็น CSV เพื่อลดการเรียก API (yfinance) และเพิ่มความเร็วในการประมวลผล

---

## 🗂️ Project Structure

```
project_DCA/
├── run.py                  # Entry Point — รันระบบวิเคราะห์พอร์ตปัจจุบัน
├── backtest.py             # 🚀 Backtesting Engine — รันจำลองการลงทุนย้อนหลัง
├── config.py               # ตั้งค่าพอร์ต, เป้าหมาย 12%, และงบประมาณ DCA
├── requirements.txt        # Dependencies (pandas, yfinance, matplotlib, etc.)
├── data/cache/             # Disk cache ราคาหุ้น (auto-generated)
├── reports/                # โฟลเดอร์เก็บผลลัพธ์ (auto-generated)
│   ├── Master_Portfolio_Report.xlsx  # รายงานละเอียด 4 Sheets
│   ├── portfolio_history.csv         # ข้อมูล Snapshot มูลค่าพอร์ตรายวัน
│   ├── portfolio_performance.png     # กราฟ Performance ภาพรวมพอร์ต
│   └── backtest_result.png           # กราฟเปรียบเทียบผลการทดสอบย้อนหลัง
└── src/
    ├── indicators.py       # RSI, MACD, EMA, Historical Growth
    ├── portfolio.py        # 🧠 Brain: Decision Logic & Rebalance Factor
    ├── output.py           # Console & Excel report generator
    └── utils.py            # Exchange rate & formatting helpers
```

---

## ⚙️ Setup

**1. Clone repo**
```bash
git clone https://github.com/Jupiter4428/Smart-DCA.git
cd Smart-DCA
```

**2. สร้าง Virtual Environment**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

**3. ติดตั้ง Dependencies**
```bash
pip install -r requirements.txt
```

**4. แก้ไข `config.py`** ให้ตรงกับพอร์ตของคุณ
```python
# จำนวนหุ้นแต่ละตัว (ดูจาก Dime app)
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

# ทองคำ MTS-Gold — ใส่จำนวน troy oz ที่ถือ
# 1 troy oz = 31.1035 กรัม  |  ตัวอย่าง: 5 กรัม = 5/31.1035 ≈ 0.1608 oz
MTS_GOLD_OZ = 0.0

# งบ DCA ต่อเดือน
MONTHLY_DCA_BUDGET_USD = 45.00
```

---

## 🚀 Usage

### 1. วิเคราะห์พอร์ตปัจจุบัน

```bash
# รันปกติ (ใช้ disk cache ถ้ามี)
python run.py

# โหมดทดสอบ — แสดงผล console เท่านั้น ไม่บันทึกไฟล์ใด
python run.py --dry-run
```

### 2. ทดสอบย้อนหลัง (Backtesting)

```bash
# รันจำลองการลงทุนเพื่อดูประสิทธิภาพของ Logic
python backtest.py
```

---

## 📊 Output

| ไฟล์ | รายละเอียด |
|------|-----------|
| `Master_Portfolio_Report.xlsx` | Excel 4 sheets: Summary, Holdings, DCA_Action, Technical |
| `portfolio_history.csv` | Snapshot รายวัน: date, total_usd, total_thb, rate, monthly_dca_usd, gold_oz, \<SYMBOL\>... |
| `portfolio_performance.png` | Chart 4 panels: Portfolio Value / Holdings Breakdown / DCA Budget / Exchange Rate |
| `backtest_result.png` | กราฟเปรียบเทียบผลการทดสอบย้อนหลัง Smart DCA vs Pure DCA |

### Excel Sheets
- **Summary** — ภาพรวม portfolio value, เป้าหมายปลายปี, required DCA, gold oz/กรัม
- **Holdings** — จำนวน shares/oz, ราคาล่าสุด, current vs target allocation พร้อม status (color-coded)
- **DCA_Action** — คำแนะนำ BUY/SELL/SKIP ตาม RSI + rebalance factor (color-coded)
- **Technical** — RSI(14), MACD, Signal line ทุกหุ้น

---

## 🎯 Target Portfolio

| Symbol | Target % | Asset Type | หมายเหตุ |
|--------|----------|-----------|---------|
| MSFT   | 18%      | AI & Cloud | |
| GOOGL  | 14%      | AI & Search | |
| ASML   | 12%      | Chip Equipment | |
| TSM    | 12%      | Chip Manufacturing | |
| GLD    | 13%      | Gold Safe Haven | **MTS-Gold** (proxy GLD price/oz) |
| NVDA   | 6%       | AI GPU | |
| RGTI   | 6%       | Quantum (Growth) | |
| JNJ    | 5%       | Healthcare | |
| PG     | 5%       | Consumer Staples | |
| QBTS   | 5%       | Quantum (Growth) | |
| CVX    | 4%       | Energy | |

---

## 📈 ผลการทดสอบย้อนหลัง (Backtest Results)

จากการจำลองลงทุนตั้งแต่วันที่ 2021-01-01 ถึง ปัจจุบัน (งบ $45/เดือน):

- **เงินต้นทั้งหมด (Total Invested):** $2,880.00
- **Pure DCA Value:** $9,662.03 (ซื้อเท่ากันทุกตัวทุกเดือน)
- **Smart DCA Value:** $11,041.02 (ใช้ระบบวิเคราะห์นี้)
- 🏆 **Alpha:** ระบบสามารถสร้างผลตอบแทนชนะตลาดได้มากกว่าปกติ **+$1,378.99 (+14.2%)**

---

## 🥇 ทองคำ MTS-Gold

ระบบใช้ **GLD** (SPDR Gold Shares ETF) เป็น proxy ราคาทองคำสากล เพื่อความเสถียรของข้อมูลย้อนหลัง เนื่องจาก MTS-Gold ไม่มี ticker ใน yfinance

- **หน่วย: troy oz** (1 troy oz = 31.1035 กรัม)
- **อัปเดต:** แก้ไขค่า `MTS_GOLD_OZ` ใน `config.py` ตามจำนวนกรัมที่ถืออยู่จริง (กรัม ÷ 31.1035)

```
มูลค่าทอง (USD) = MTS_GOLD_OZ × GLD_price_per_troy_oz
```

**แปลงกรัม → oz:**
```
oz = กรัม ÷ 31.1035
ตัวอย่าง: 5 กรัม = 5 ÷ 31.1035 ≈ 0.160754 oz
```

**วิธีอัปเดต:** แก้ `MTS_GOLD_OZ` ใน `config.py` ทุกครั้งที่ซื้อทองเพิ่ม

```python
MTS_GOLD_OZ = 0.0   # ตัวอย่าง: ทอง 5 กรัม
```

---

## 🔧 Key Settings (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CURRENT_HOLDINGS_SHARES` | dict | จำนวนหุ้นแต่ละ symbol (ดูจาก Dime app) |
| `MTS_GOLD_OZ` | `0.0` | จำนวน troy oz ทอง MTS-Gold ที่ถือ |
| `MONTHLY_DCA_BUDGET_USD` | `46.22` | งบ DCA ต่อเดือน (USD) |
| `RSI_PERIOD` | `14` | RSI lookback period |
| `RSI_OVERSOLD` | `30` | RSI buy zone threshold |
| `RSI_OVERBOUGHT` | `70` | RSI sell zone threshold |
| `MACD_FAST/SLOW/SIGNAL` | `12/26/9` | MACD parameters |
| `DATA_PERIOD` | `12mo` | Historical data period |
| `REBALANCE_TOLERANCE` | `0.5%` | Tolerance before rebalancing |
| `ANNUAL_GROWTH_TARGET` | `12%` | Year-end growth target |

---

## 📋 Action Signal Logic

ระบบประเมินสถานะหุ้นแต่ละตัวผ่านเงื่อนไขที่ซับซ้อนเพื่อให้ได้จังหวะการลงทุนที่ดีที่สุด:

| Signal | ความหมาย | Condition (Technical + Fundamental) |
|--------|----------|--------------------------------------|
| 🟢🟢 **STRONG BUY** | จุดซื้อที่ได้เปรียบสูง | Underweight + (Oversold หรือ P/E ต่ำ) + MACD Bullish/EMA Support |
| 🟢 **BUY** | สะสมเพิ่ม | Underweight + แนวโน้มขาขึ้น หรือ อยู่ใกล้แนวรับ EMA 26 |
| 🔵 **DCA** | รักษาวินัย | สัดส่วนตามเป้า (On Target) หรือเป็นสินทรัพย์ Hedge (Gold) |
| 🟣 **HOLD** | หยุดเติมเงิน | Overweight (สัดส่วนเกิน) หรือ ราคาวิ่งแรงเกินไป (Overbought/Expensive) |
| 🔴 **SELL** | ขายทำกำไร | Overweight รุนแรง (> 5%) + RSI > 80 (Extreme Overbought) |

> ระบบจะแสดง **ACTION ALERTS** สรุป STRONG BUY และ SELL ท้าย console โดยอัตโนมัติ

---

## 💾 Cache System

- **Disk cache** — ราคาหุ้นบันทึกเป็น CSV ใน `data/cache/`  
  valid ถ้า modified date = วันนี้ → ไม่ hit yfinance ซ้ำในวันเดิม
- **In-memory cache** — indicators คำนวณครั้งเดียวต่อ session  
  ลด API call จาก 22 → 11 ครั้ง

---

## 📦 Dependencies

```
pandas, numpy, yfinance, openpyxl, matplotlib, requests, rich, unicodedata
```

---

## 🔄 Workflow รายเดือน

1. ซื้อหุ้น/ทองผ่าน Dime app ตามสัญญาณ DCA
2. อัปเดต `CURRENT_HOLDINGS_SHARES` และ `MTS_GOLD_OZ` ใน `config.py`
3. รัน `python run.py`
4. ดูผลใน `reports/Master_Portfolio_Report.xlsx`
5. ดู Alert ใน console — มี STRONG BUY หรือ SELL ไหม?