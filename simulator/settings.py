import numpy as np

# ============================================================
# SETTINGS
# ============================================================

STREAM_BITS = {
    "Y1": "1011010011010110010110100101101011010011010110101010110100110101100101101001011010110100110101101010",
    "Y2": "11001011010100110101101001010110100110101100101010",
    "Y3": "01011010110100101101011010010110101100110101011010",
    "Y4": "10101101001011010110100101101001011010110100110101",
    "Cb": "01101011001010110100110101101001011010100110101101",
    "Cr": "11010100101101011010010110100101101011001011010110",
}

SAMPLES_PER_BIT = 160

# Carrier cycles per bit-width. Keeping this fixed means both modulations
# show the SAME carrier frequency: 2 cycles per 4-bit 16-QAM symbol,
# 1 cycle per 2-bit QPSK symbol.
CYCLES_PER_BIT = 0.5

# Number of bits visible at one time
WINDOW_BITS = 12

# Both constellations are scaled to unit average power, so the two
# waveforms are directly comparable on the same amplitude axis.
QAM16_SCALE = 1 / np.sqrt(10)
QPSK_SCALE = 1 / np.sqrt(2)

# Gray-coded 16-QAM levels (2 bits -> one axis)
GRAY_LEVEL = {"00": -3, "01": -1, "11": 1, "10": 3}

MODULATIONS = {
    "16-QAM": {"bits": 4, "points": 16},
    "QPSK": {"bits": 2, "points": 4},
}

# Colors
BG = "#101418"
PANEL = "#141a1f"
GRID = "#263038"
SPINE = "#303a43"
TICK = "#8d98a1"
ACCENT = "#61a8ff"
GREEN = "#5ee7b7"
BTN = "#263b4d"
