import numpy as np

import state
from settings import (
    MODULATIONS,
    SAMPLES_PER_BIT,
    WINDOW_BITS,
    BG,
    PANEL,
    GRID,
    SPINE,
    TICK,
    ACCENT,
    GREEN,
    QPSK_SCALE,
    QAM16_SCALE,
)
from modulation import (
    bps,
    get_window_bits,
    get_symbols,
    reference_points,
    update_rf_line,
)


# ============================================================
# DRAWING  –  Matplotlib plotting and updating logic
# ============================================================


def style_axis(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TICK)
    for spine in ax.spines.values():
        spine.set_color(SPINE)
    ax.grid(True, color=GRID, alpha=0.5)


def draw_digital(ax_bits):
    ax_bits.clear()
    style_axis(ax_bits)

    bits = get_window_bits()
    count = len(bits)
    n = bps()

    # Symbol grouping: shaded bands + dashed boundaries + S1, S2... labels
    nsym = -(-count // n)
    for k in range(nsym):
        start = k * n
        end = min(start + n, count)
        if k % 2 == 0:
            ax_bits.axvspan(start, end, color=ACCENT, alpha=0.07, linewidth=0)
        if k > 0:
            ax_bits.axvline(
                start, color=ACCENT, linestyle="--", alpha=0.7, linewidth=1.2
            )
        ax_bits.text(
            (start + end) / 2, -0.2, f"S{k + 1}",
            color=ACCENT, fontsize=10, fontweight="bold",
            ha="center", va="center",
        )

    digital = np.repeat([int(b) for b in bits], SAMPLES_PER_BIT)
    local_t = np.arange(len(digital)) / SAMPLES_PER_BIT
    ax_bits.step(local_t, digital, where="post", color=GREEN, linewidth=3)

    for i, bit in enumerate(bits):
        ax_bits.text(
            i + 0.5, 1.08, bit,
            color="white", fontsize=14, fontweight="bold", ha="center",
        )

    ax_bits.set_ylim(-0.35, 1.3)
    ax_bits.set_xlim(0, WINDOW_BITS)
    ax_bits.set_ylabel("BIT", color="white")
    ax_bits.set_xlabel("Bit Position", color=TICK)
    ax_bits.set_title(
        f"Digital Data - {state.selected_stream}",
        color="white", loc="left", fontsize=12,
    )
    ax_bits.text(
        1.0, 1.02,
        f"Bits {state.window_start + 1}–{state.window_start + count} / {len(state.BITS)}",
        transform=ax_bits.transAxes, color="#9aa4ad", fontsize=9,
        ha="right", va="bottom",
    )


def draw_rf(ax_rf):
    n = bps()

    ax_rf.clear()
    style_axis(ax_rf)

    for i in range(WINDOW_BITS + 1):
        on_symbol = (i % n == 0)
        ax_rf.axvline(
            i,
            color=ACCENT if on_symbol else "#3a444c",
            linestyle="--",
            alpha=0.7 if on_symbol else 0.5,
            linewidth=1.2 if on_symbol else 0.8,
        )

    state.rf_line, = ax_rf.plot([], [], color=ACCENT, linewidth=2)
    update_rf_line()

    ax_rf.set_xlim(0, WINDOW_BITS)
    ax_rf.set_ylim(-1.55, 1.55)
    ax_rf.set_ylabel("RF", color="white")
    ax_rf.set_xlabel("Bit Position →", color=TICK)
    ax_rf.set_title(
        f"Simulated 868 MHz {state.modulation} RF Waveform",
        color="white", loc="left", fontsize=12,
    )


def draw_constellation(ax_const):
    ax_const.clear()
    style_axis(ax_const)

    # Full reference constellation with Gray labels
    refs = reference_points()
    ax_const.scatter(
        [p[1] for p in refs], [p[2] for p in refs],
        s=70 if state.modulation == "QPSK" else 55, color="#3a566f", zorder=2,
    )
    for label, x, y in refs:
        ax_const.text(
            x, y + 0.09, label,
            color=TICK, fontsize=9 if state.modulation == "QPSK" else 8, ha="center",
        )

    # QPSK: every point sits on the unit circle (constant amplitude)
    if state.modulation == "QPSK":
        theta = np.linspace(0, 2 * np.pi, 200)
        ax_const.plot(
            np.cos(theta), np.sin(theta),
            color="#3a566f", linestyle=":", linewidth=1, zorder=1,
        )

    # Symbols in the current window. Repeated symbols share one dot and
    # get a merged label such as "S1,S3" instead of overlapping text.
    groups = {}
    for idx, (x, y) in enumerate(get_symbols(), start=1):
        groups.setdefault((round(x, 4), round(y, 4)), []).append(idx)

    if groups:
        ax_const.scatter(
            [k[0] for k in groups], [k[1] for k in groups],
            s=110, color=ACCENT, edgecolors="white", linewidths=1, zorder=4,
        )
        for (x, y), ids in groups.items():
            ax_const.text(
                x, y - 0.19, ",".join(f"S{k}" for k in ids),
                color=ACCENT, fontsize=8, ha="center", fontweight="bold",
            )

    ax_const.axhline(0, color="#3a444c", linewidth=1)
    ax_const.axvline(0, color="#3a444c", linewidth=1)
    ax_const.set_xlim(-1.35, 1.35)
    ax_const.set_ylim(-1.35, 1.35)
    ax_const.set_xlabel("In-Phase (I)", color=TICK)
    ax_const.set_ylabel("Quadrature (Q)", color="white")
    ax_const.set_title(
        f"{state.modulation} Constellation • {bps()} bits/symbol • {state.selected_stream}",
        color="white", loc="left", fontsize=12,
    )


def update_info(info_label, stats_label):
    m = MODULATIONS[state.modulation]
    n = m["bits"]
    count = len(get_window_bits())
    pad = (-count) % n
    nsym = (count + pad) // n

    spacing = 2 * (QPSK_SCALE if state.modulation == "QPSK" else QAM16_SCALE)
    speed = n / 2

    info_label.config(
        text=f"6 Parallel Streams  •  300 kbps / stream  •  868 MHz  •  {state.modulation}"
    )
    stats_label.config(
        text=(
            f"{state.modulation}: {n} bits/symbol, {m['points']} points   |   "
            f"window {count} bits → {nsym} symbols"
            + (f" (+{pad} pad bits)" if pad else "")
            + f"   |   neighbour spacing {spacing:.2f} (smaller = more noise-sensitive)"
            f"   |   speed at same symbol rate: {speed:g}x QPSK"
        )
    )
