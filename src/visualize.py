"""
📈 PERFORMANCE VISUALIZER
==========================
Generate charts from portfolio_history.csv

Charts:
  1. Total Portfolio Value over time (line + fill)
  2. Holdings breakdown per symbol (stacked bar)
  3. Monthly DCA deployed (bar)
  4. Exchange Rate THB/USD over time (line)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from config import TARGET_PORTFOLIO

HISTORY_FILE = './reports/portfolio_history.csv'
CHART_FILE   = './reports/portfolio_performance.png'

# ─────────────────────────────────────────────────────────────────
# Theme
# ─────────────────────────────────────────────────────────────────
BG_DARK   = '#1e1e2e'
BG_PANEL  = '#0f172a'
GRID_COL  = '#334155'
TEXT_COL  = '#e2e8f0'
ACCENT    = '#7c3aed'
GREEN     = '#22c55e'
YELLOW    = '#facc15'

SYMBOL_COLORS = [
    '#818cf8', '#34d399', '#fb923c', '#f472b6',
    '#38bdf8', '#a78bfa', '#4ade80', '#fbbf24',
    '#f87171', '#2dd4bf', '#c084fc',
]


def _style_ax(ax):
    """Apply dark theme to a single axes."""
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    ax.yaxis.label.set_color(TEXT_COL)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.title.set_color(TEXT_COL)
    ax.grid(True, color=GRID_COL, linestyle='--', alpha=0.45, axis='y')
    for spine in ax.spines.values():
        spine.set_color(GRID_COL)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def visualize_performance_history() -> None:
    """
    Read portfolio_history.csv and generate a 4-panel performance chart.
    Saves to reports/portfolio_performance.png
    """
    # ── Guard: file exists ──
    if not os.path.exists(HISTORY_FILE):
        print("⚠️  No history data found — run the system at least once first.")
        return

    df = pd.read_csv(HISTORY_FILE, parse_dates=['date'])

    if len(df) < 1:
        print("⚠️  History file is empty.")
        return

    symbols     = list(TARGET_PORTFOLIO.keys())
    sym_cols    = [s for s in symbols if s in df.columns]
    date_labels = df['date'].dt.strftime('%b %y')
    single_point = len(df) == 1     # show marker only, no line

    # ── Figure layout ──
    fig = plt.figure(figsize=(18, 11))
    fig.patch.set_facecolor(BG_DARK)
    gs = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.30)

    # ══════════════════════════════════════════════════════════════
    # Chart 1 — Total Portfolio Value (USD)  [top, full width]
    # ══════════════════════════════════════════════════════════════
    ax1 = fig.add_subplot(gs[0, :])
    _style_ax(ax1)
    ax1.grid(True, color=GRID_COL, linestyle='--', alpha=0.45)   # both axes

    if single_point:
        ax1.scatter(df['date'], df['total_usd'], color=ACCENT, s=80, zorder=5)
    else:
        ax1.plot(df['date'], df['total_usd'],
                 color=ACCENT, linewidth=2.5, marker='o', markersize=6)
        ax1.fill_between(df['date'], df['total_usd'], alpha=0.15, color=ACCENT)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax1.set_title('📈 Total Portfolio Value (USD)', fontsize=13, pad=10)
    ax1.set_ylabel('USD ($)')

    # Annotate latest value
    last_usd = df['total_usd'].iloc[-1]
    ax1.annotate(
        f'  ${last_usd:,.2f}',
        xy=(df['date'].iloc[-1], last_usd),
        color=GREEN, fontsize=10, fontweight='bold', va='center'
    )

    # ══════════════════════════════════════════════════════════════
    # Chart 2 — Holdings Breakdown (stacked bar)  [bottom-left]
    # ══════════════════════════════════════════════════════════════
    ax2 = fig.add_subplot(gs[1, 0])
    _style_ax(ax2)

    bottom = [0.0] * len(df)
    for i, sym in enumerate(sym_cols):
        vals = df[sym].fillna(0).tolist()
        ax2.bar(date_labels, vals, bottom=bottom,
                label=sym, color=SYMBOL_COLORS[i % len(SYMBOL_COLORS)], alpha=0.88)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax2.set_title('🏦 Holdings Breakdown (USD)', fontsize=11, pad=10)
    ax2.set_ylabel('USD ($)')
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend(fontsize=7, ncol=2, facecolor='#1e293b',
               labelcolor=TEXT_COL, loc='upper left', framealpha=0.7)

    # ══════════════════════════════════════════════════════════════
    # Chart 3 — Monthly DCA Budget  [bottom-right top half]
    # ══════════════════════════════════════════════════════════════
    ax3 = fig.add_subplot(gs[1, 1])
    _style_ax(ax3)

    ax3.bar(date_labels, df['monthly_dca_usd'],
            color=GREEN, alpha=0.85, width=0.5)
    ax3.set_title('💰 Monthly DCA Budget (USD)', fontsize=11, pad=10)
    ax3.set_ylabel('USD ($)')
    ax3.tick_params(axis='x', rotation=45)

    # Annotate each bar
    for idx, (x, y) in enumerate(zip(date_labels, df['monthly_dca_usd'])):
        ax3.text(idx, y + 0.3, f'${y:.0f}',
                 ha='center', va='bottom', fontsize=8, color=GREEN)

    # ── Super title ──
    fig.suptitle(
        'Smart-DCA · Portfolio Performance Dashboard',
        color=TEXT_COL, fontsize=15, fontweight='bold', y=1.01
    )

    # ── Save ──
    os.makedirs('./reports', exist_ok=True)
    plt.savefig(CHART_FILE, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"📊 Performance chart saved → {CHART_FILE}")