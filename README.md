# 📈 Smart-DCA — Portfolio Analysis System

ระบบวิเคราะห์พอร์ตการลงทุนแบบ Dollar-Cost Averaging (DCA) อัตโนมัติ  
ดึงข้อมูลราคาหุ้นจาก yfinance, คำนวณ RSI/MACD, และสร้างรายงาน Excel พร้อม chart

---

## 🗂️ Project Structure

```
project_DCA/
├── run.py                  # Entry Point — รันระบบทั้งหมด
├── config.py               # ตั้งค่าพอร์ต, หุ้นเป้าหมาย, และงบประมาณ
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
CURRENT_HOLDINGS = {
    'MSFT': 27.73,   # ใส่มูลค่าจริง (USD)
    'GOOGL': 0.0,
    # ...
}
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
```

---

## 📊 Output

| ไฟล์ | รายละเอียด |
|------|-----------|
| `Master_Portfolio_Report.xlsx` | Excel 4 sheets: Summary, Holdings, DCA_Action, Technical |
| `portfolio_history.csv` | Snapshot รายวัน — บันทึกทุกครั้งที่รัน |
| `portfolio_performance.png` | Chart: Portfolio Value / Holdings Breakdown / DCA Budget |

### Excel Sheets
- **Summary** — ภาพรวม portfolio value, เป้าหมายปลายปี, required DCA
- **Holdings** — current vs target allocation พร้อม status
- **DCA_Action** — คำแนะนำ BUY/SELL/SKIP ตาม RSI + rebalance factor
- **Technical** — RSI(14), MACD, Signal line ทุกหุ้น

---

## 🎯 Target Portfolio

| Symbol | Target % | Asset Type |
|--------|----------|-----------|
| MSFT   | 18%      | AI & Cloud |
| GOOGL  | 14%      | AI & Search |
| ASML   | 12%      | Chip Equipment |
| TSM    | 12%      | Chip Manufacturing |
| GLD    | 13%      | Gold (Safe Haven) |
| NVDA   | 6%       | AI GPU |
| RGTI   | 6%       | Quantum (Growth) |
| JNJ    | 5%       | Healthcare |
| PG     | 5%       | Consumer Staples |
| QBTS   | 5%       | Quantum (Growth) |
| CVX    | 4%       | Energy |

---

## 🔧 Key Settings (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RSI_PERIOD` | 14 | RSI lookback period |
| `RSI_OVERSOLD` | 30 | RSI buy zone threshold |
| `RSI_OVERBOUGHT` | 70 | RSI sell zone threshold |
| `MACD_FAST/SLOW/SIGNAL` | 12/26/9 | MACD parameters |
| `DATA_PERIOD` | `12mo` | Historical data period |
| `REBALANCE_TOLERANCE` | 0.5% | Tolerance before rebalancing |
| `ANNUAL_GROWTH_TARGET` | 12% | Year-end growth target |

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

*อัปเดต `CURRENT_HOLDINGS` ใน `config.py` ทุกเดือนหลัง DCA แล้วรัน `python run.py`*