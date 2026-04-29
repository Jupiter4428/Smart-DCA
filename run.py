"""
🚀 ENTRY POINT
==============
Run this file to execute the full portfolio analysis pipeline.

Usage:
    python run.py                 # รันปกติ (ใช้ disk cache ถ้ามี)
    python run.py --clear-cache   # ลบ cache ทั้งหมดแล้ว download ใหม่
    python run.py --no-cache      # ข้าม cache ครั้งนี้ (ไม่ลบ ไม่บันทึก)
    python run.py --no-record     # ข้ามการบันทึก performance history
    python run.py --dry-run       # แสดงผลใน console เท่านั้น ไม่บันทึกไฟล์ใดเลย
"""

import sys
from src.utils import get_thb_usd_rate, validate_portfolio_weights
from src.output import (
    print_reports_to_console,
    save_all_to_excel,
    clear_indicator_cache,
    append_performance_history,
)
from src.indicators import clear_disk_cache
from src.visualize import visualize_performance_history
from config import TARGET_PORTFOLIO

if __name__ == "__main__":
    print("🚀 Starting Portfolio Analysis System...")

    # ── Parse CLI flags ──
    args               = sys.argv[1:]
    should_clear_cache = "--clear-cache" in args
    no_cache           = "--no-cache"    in args
    no_record          = "--no-record"   in args
    dry_run            = "--dry-run"     in args

    if dry_run:
        print("🧪 DRY RUN MODE — no files will be written")

    # ── Validate portfolio weights ──
    try:
        validate_portfolio_weights(TARGET_PORTFOLIO)
        print("✅ Portfolio weights validated (sum = 100%)")
    except ValueError as e:
        print(f"❌ Portfolio configuration error: {e}")
        raise SystemExit(1)

    # ── Handle cache flags ──
    if should_clear_cache and not dry_run:
        clear_disk_cache()
        clear_indicator_cache()
        print("🔄 Cache cleared — will download fresh data from yfinance")
    elif no_cache or dry_run:
        clear_indicator_cache()
        print("⚡ No-cache mode — using live data this run (disk cache unchanged)")
    else:
        clear_indicator_cache()
        print("📂 Disk cache enabled — will reuse today's data if available")

    # ── Fetch exchange rate ──
    rate = get_thb_usd_rate()
    print(f"💱 Exchange rate: 1 USD = ฿{rate:.2f}")

    # ── Generate & display reports (always) ──
    print_reports_to_console(rate)

    # ── Write files (skip in dry-run) ──
    if dry_run:
        print("\n⏭️  Skipped: Excel / history / chart (dry-run mode)")
    else:
        save_all_to_excel(rate)

        if no_record:
            print("⏭️  Skipping performance history recording (--no-record)")
        else:
            append_performance_history(rate)

        visualize_performance_history()

    print("\n✨ All tasks completed successfully!")