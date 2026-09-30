import numpy as np

import state
from settings import (
    MODULATIONS,
    SAMPLES_PER_BIT,
    CYCLES_PER_BIT,
    WINDOW_BITS,
    QAM16_SCALE,
    QPSK_SCALE,
    GRAY_LEVEL,
)

# ============================================================
# MODULATION MATH  (one source of truth for encoder AND labels)
# ============================================================


def bps():
    """Bits per symbol for the current modulation."""
    return MODULATIONS[state.modulation]["bits"]


def bits_to_symbol(bits):
    """Map one symbol's worth of bits to a normalized (I, Q) pair."""
    if state.modulation == "QPSK":
        # Each bit independently picks the sign of one axis (Gray coded):
        # 00 -> (+,+)  01 -> (+,-)  11 -> (-,-)  10 -> (-,+)
        i = -1 if bits[0] == "1" else 1
        q = -1 if bits[1] == "1" else 1
        return i * QPSK_SCALE, q * QPSK_SCALE

    return (
        GRAY_LEVEL[bits[:2]] * QAM16_SCALE,
        GRAY_LEVEL[bits[2:]] * QAM16_SCALE,
    )


def reference_points():
    """Every constellation point with its bit label, built FROM the encoder
    so the background labels can never disagree with the plotted symbols."""
    n = bps()
    points = []
    for value in range(2 ** n):
        label = format(value, f"0{n}b")
        x, y = bits_to_symbol(label)
        points.append((label, x, y))
    return points


def get_window_bits():
    return state.BITS[state.window_start:min(state.window_start + WINDOW_BITS, len(state.BITS))]


def padded_bits():
    bits = get_window_bits()
    return bits + "0" * ((-len(bits)) % bps())


def get_symbols():
    p = padded_bits()
    n = bps()
    return [bits_to_symbol(p[i:i + n]) for i in range(0, len(p), n)]


def generate_rf(offset):
    symbols = get_symbols()
    if not symbols:
        return np.zeros(1)

    n = bps()
    sps = n * SAMPLES_PER_BIT
    u = np.arange(sps) / sps
    carrier = 2 * np.pi * (CYCLES_PER_BIT * n) * u + offset
    c, s = np.cos(carrier), np.sin(carrier)

    # Passband: s(t) = I*cos(wt) - Q*sin(wt)
    return np.concatenate([i_val * c - q_val * s for i_val, q_val in symbols])


def update_rf_line():
    rf = generate_rf(state.phase_offset)
    # Time axis uses the PADDED bit count: that is the duration the samples
    # really represent, so symbol boundaries land on true bit positions.
    t = np.linspace(0, len(padded_bits()), len(rf), endpoint=False)
    state.rf_line.set_data(t, rf)
