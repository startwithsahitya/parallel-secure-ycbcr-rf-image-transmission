from settings import STREAM_BITS

# ============================================================
# STATE  –  shared mutable variables
# ============================================================
# Every module that needs to read or write these values imports this
# module and accesses the attributes directly (e.g. state.running).
# Because Python caches module objects, all importers share the SAME
# instance, which eliminates the need for globals scattered across
# files and prevents circular-import issues.

running = False
animation_job = None
phase_offset = 0.0

modulation = "16-QAM"
selected_stream = "Y1"
BITS = STREAM_BITS[selected_stream]
window_start = 0

rf_line = None
