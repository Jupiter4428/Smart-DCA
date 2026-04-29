# 📈 Smart-DCA — Portfolio Analysis System

ระบบวิเคราะห์พอร์ตการลงทุนแบบ Dollar-Cost Averaging (DCA) อัตโนมัติ  
ดึงข้อมูลราคาหุ้นจาก yfinance, คำนวณ RSI/MACD, และสร้างรายงาน Excel พร้อม chart

---

## 🗂️ Project Structure

```
project_DCA/
├── run.py                  # Entry Point — รันระบบทั้งหมด
├── config.py               # ตั้งค่าพอร์ต, จำนวนหุ้น, ทอง MTS-Gold, และงบประมาณ
├── requirements.txt        # Dependencies
├── data/cache/             # Disk cache ราคาหุ้น (auto-generated)
├── reports/                # ผลลัพธ์ (auto-generated)
│   ├── Master_Portfolio_Report.xlsx
│   ├── portfolio_history.csv
│   └── portfolio_performance.png
└── src/
    ├── indicators.py       # RSI, MACD, disk cache manager
    ├── portfolio.py        # Rebalance logic, action signals
    ├── output.py           # Console & Excel report generator
    ├── visualize.py        # Performance chart (matplotlib)
    └── utils.py            # Exchange rate, formatting helpers
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
MONTHLY_DCA_BUDGET_USD = 46.22
```

---

## 🚀 Usage

```bash
# รันปกติ (ใช้ disk cache ถ้ามี)
python run.py

# ลบ cache แล้ว download ข้อมูลใหม่ทั้งหมด
python run.py --clear-cache

# ข้าม cache รอบนี้ (disk cache ไม่เปลี่ยน)
python run.py --no-cache

# ไม่บันทึก performance snapshot รอบนี้
python run.py --no-record

# โหมดทดสอบ — แสดงผล console เท่านั้น ไม่บันทึกไฟล์ใด
python run.py --dry-run
```

---

## 📊 Output

| ไฟล์ | รายละเอียด |
|------|-----------|
| `Master_Portfolio_Report.xlsx` | Excel 4 sheets: Summary, Holdings, DCA_Action, Technical |
| `portfolio_history.csv` | Snapshot รายวัน: date, total_usd, total_thb, rate, monthly_dca_usd, gold_oz, \<SYMBOL\>... |
| `portfolio_performance.png` | Chart 4 panels: Portfolio Value / Holdings Breakdown / DCA Budget / Exchange Rate |

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

## 🥇 ทองคำ MTS-Gold

ระบบใช้ **GLD** (SPDR Gold Shares ETF) เป็น proxy ราคาทอง เนื่องจาก MTS-Gold ไม่มี ticker ใน yfinance

**หน่วย: troy oz** (1 troy oz = 31.1035 กรัม)

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

| Signal | Condition |
|--------|-----------|
| 🟢🟢 STRONG BUY | Underweight + Oversold (RSI < 30) |
| 🟢 BUY | Underweight หรือ Price dip |
| ⚪ DCA | On target + Neutral RSI |
| 🟡 SKIP | Overbought หรือ Target reached |
| ⚪ HOLD | Overweight + Oversold |
| 🔴 SELL | Overweight + Overbought |

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
pandas, numpy, yfinance, openpyxl, matplotlib, requests, rich
```

---

## 🔄 Workflow รายเดือน

1. ซื้อหุ้น/ทองผ่าน Dime app ตามสัญญาณ DCA
2. อัปเดต `CURRENT_HOLDINGS_SHARES` และ `MTS_GOLD_OZ` ใน `config.py`
3. รัน `python run.py`
4. ดูผลใน `reports/Master_Portfolio_Report.xlsx`
5. ดู Alert ใน console — มี STRONG BUY หรือ SELL ไหม?