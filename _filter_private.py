import re

data = blob.data.decode('utf-8', errors='replace')

# ทำงานเฉพาะ blob ที่มี config fields เหล่านี้
if 'CURRENT_HOLDINGS_SHARES' not in data and 'AVERAGE_COST_USD' not in data and 'MTS_GOLD_OZ' not in data:
    pass
else:
    # ── CURRENT_HOLDINGS_SHARES ─────────────────────────────────────
    data = re.sub(
        r"(CURRENT_HOLDINGS_SHARES\s*=\s*\{)[^}]*(})",
        (
            r"\1\n"
            r"    'MSFT' : 0.0,\n"
            r"    'GOOGL': 0.0,\n"
            r"    'NVDA' : 0.0,\n"
            r"    'ASML' : 0.0,\n"
            r"    'TSM'  : 0.0,\n"
            r"    'JNJ'  : 0.0,\n"
            r"    'PG'   : 0.0,\n"
            r"    'CVX'  : 0.0,\n"
            r"    'RGTI' : 0.0,\n"
            r"    'QBTS' : 0.0,\n"
            r"\2"
        ),
        data, flags=re.DOTALL
    )

    # ── MTS_GOLD_OZ ─────────────────────────────────────────────────
    data = re.sub(r'(MTS_GOLD_OZ\s*=\s*)[0-9.]+', r'\g<1>0.0', data)

    # ── AVERAGE_COST_USD ────────────────────────────────────────────
    data = re.sub(
        r"(AVERAGE_COST_USD\s*=\s*\{)[^}]*(})",
        (
            r"\1\n"
            r"    'MSFT' : 0.0,\n"
            r"    'GOOGL': 0.0,\n"
            r"    'NVDA' : 0.0,\n"
            r"    'ASML' : 0.0,\n"
            r"    'TSM'  : 0.0,\n"
            r"    'GC=F' : 0.0,\n"
            r"    'JNJ'  : 0.0,\n"
            r"    'PG'   : 0.0,\n"
            r"    'CVX'  : 0.0,\n"
            r"    'RGTI' : 0.0,\n"
            r"    'QBTS' : 0.0,\n"
            r"\2"
        ),
        data, flags=re.DOTALL
    )

    # ── TARGET_PORTFOLIO ────────────────────────────────────────────
    data = re.sub(
        r"(TARGET_PORTFOLIO\s*=\s*\{)[^}]*(})",
        (
            r"\1\n"
            r"    'MSFT' : 0.0,\n"
            r"    'GOOGL': 0.0,\n"
            r"    'NVDA' : 0.0,\n"
            r"    'ASML' : 0.0,\n"
            r"    'TSM'  : 0.0,\n"
            r"    'GC=F' : 0.0,\n"
            r"    'JNJ'  : 0.0,\n"
            r"    'PG'   : 0.0,\n"
            r"    'CVX'  : 0.0,\n"
            r"    'RGTI' : 0.0,\n"
            r"    'QBTS' : 0.0,\n"
            r"\2"
        ),
        data, flags=re.DOTALL
    )

    blob.data = data.encode('utf-8')
