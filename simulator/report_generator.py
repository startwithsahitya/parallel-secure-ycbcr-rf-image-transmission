"""
RF transmission report + bit-error simulator.

Run from the simulator project:
    python report_generator.py

Or call from main.py:
    from report_generator import generate_report
    generate_report()

Input:
    ../imageprocessing/output/ycbcr_bitstreams.json

Outputs:
    rf_transmission_report.txt
    rf_transmission_report.json
    rf_transmission_error_bitstreams.json

The default BER is 1e-3 (0.1%). This is a SIMULATION ASSUMPTION,
not a universal "normal RF error". Change BER in generate_report()
to test other channel conditions.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from datetime import datetime, timezone


STREAM_MAP = {
    "Y1": "Y_part1_bits",
    "Y2": "Y_part2_bits",
    "Y3": "Y_part3_bits",
    "Y4": "Y_part4_bits",
    "Cb": "Cb_bits",
    "Cr": "Cr_bits",
}

FREQUENCIES_MHZ = {
    "Y1": (865.0, 865.3),
    "Y2": (865.4, 865.7),
    "Y3": (865.8, 866.1),
    "Y4": (866.2, 866.5),
    "Cb": (866.6, 866.9),
    "Cr": (867.0, 867.3),
}

CHANNEL_BANDWIDTH_HZ = 300_000
ROLL_OFF = 0.35

# Project modulation:
# 16-QAM = 4 bits/symbol
BITS_PER_SYMBOL = 4

# Reproducible error simulation.
DEFAULT_BER = 1e-3
DEFAULT_RANDOM_SEED = 20261001


def locate_input_json() -> Path:
    here = Path(__file__).resolve().parent

    candidates = [
        here.parent / "imageprocessing" / "output" / "ycbcr_bitstreams.json",
        here / "imageprocessing" / "output" / "ycbcr_bitstreams.json",
    ]

    for p in candidates:
        if p.exists():
            return p

    raise FileNotFoundError(
        "Could not find imageprocessing/output/ycbcr_bitstreams.json.\n"
        "Expected it one project directory above this script."
    )


def load_bitstreams(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    streams = data["streams"]

    result = {}
    for short_name, json_name in STREAM_MAP.items():
        bits = streams[json_name]
        if not isinstance(bits, str) or set(bits) - {"0", "1"}:
            raise ValueError(f"{json_name} is not a valid 0/1 bitstream.")
        result[short_name] = bits

    return data, result


def add_errors(bits: str, ber: float, rng: random.Random):
    """Flip each bit independently with probability BER."""
    if not (0.0 <= ber <= 1.0):
        raise ValueError("BER must be between 0 and 1.")

    chars = list(bits)
    error_positions = []

    for i, bit in enumerate(chars):
        if rng.random() < ber:
            chars[i] = "1" if bit == "0" else "0"
            error_positions.append(i)

    return "".join(chars), error_positions


def rate_calculation():
    # With raised-cosine filtering:
    # occupied bandwidth ~= symbol_rate * (1 + roll_off)
    symbol_rate = CHANNEL_BANDWIDTH_HZ / (1.0 + ROLL_OFF)
    raw_bit_rate = symbol_rate * BITS_PER_SYMBOL
    return symbol_rate, raw_bit_rate


def make_report(
    input_path: Path,
    original,
    corrupted,
    errors,
    ber: float,
):
    total_bits = sum(len(v) for v in original.values())
    total_errors = sum(len(v) for v in errors.values())

    symbol_rate, raw_bit_rate = rate_calculation()
    aggregate_rate = raw_bit_rate * len(original)

    tx_time_sec = total_bits / aggregate_rate

    per_stream = {}
    for name in STREAM_MAP:
        n = len(original[name])
        e = len(errors[name])
        per_stream[name] = {
            "bits": n,
            "bytes_equivalent": n // 8,
            "frequency_start_mhz": FREQUENCIES_MHZ[name][0],
            "frequency_end_mhz": FREQUENCIES_MHZ[name][1],
            "channel_bandwidth_khz": CHANNEL_BANDWIDTH_HZ / 1000,
            "modulation": "16-QAM",
            "bits_per_symbol": BITS_PER_SYMBOL,
            "estimated_symbol_rate_ksps": symbol_rate / 1000,
            "estimated_raw_bit_rate_kbps": raw_bit_rate / 1000,
            "simulated_bit_errors": e,
            "simulated_ber": e / n if n else 0.0,
        }

    report = {
        "report": {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "purpose": "16-QAM six-stream RF transmission calculation and BER simulation",
        },
        "input": {
            "source_json": str(input_path),
            "input_image_assumption": "1024x1024 RGB source represented by the supplied YCbCr bitstreams",
            "stream_count": len(original),
            "total_bits": total_bits,
            "total_bytes_equivalent": total_bits // 8,
            "total_mib_equivalent": total_bits / 8 / (1024 * 1024),
        },
        "bitstream_division": {
            name: {
                "json_field": STREAM_MAP[name],
                "bits": len(original[name]),
                "bytes_equivalent": len(original[name]) // 8,
                "percentage_of_total": 100 * len(original[name]) / total_bits,
            }
            for name in STREAM_MAP
        },
        "modulation": {
            "name": "16-QAM",
            "bits_per_symbol": BITS_PER_SYMBOL,
            "formula": "raw_bit_rate = symbol_rate × bits_per_symbol",
        },
        "channel_model": {
            "channel_bandwidth_hz": CHANNEL_BANDWIDTH_HZ,
            "channel_bandwidth_khz": CHANNEL_BANDWIDTH_HZ / 1000,
            "roll_off": ROLL_OFF,
            "symbol_rate_formula": "symbol_rate = bandwidth / (1 + roll_off)",
            "estimated_symbol_rate_baud": symbol_rate,
            "estimated_symbol_rate_ksps": symbol_rate / 1000,
            "raw_bit_rate_formula": "bit_rate = symbol_rate × 4",
            "estimated_raw_bit_rate_bps_per_stream": raw_bit_rate,
            "estimated_raw_bit_rate_kbps_per_stream": raw_bit_rate / 1000,
            "estimated_six_stream_aggregate_bps": aggregate_rate,
            "estimated_six_stream_aggregate_mbps": aggregate_rate / 1e6,
            "ideal_transmission_time_seconds": tx_time_sec,
        },
        "frequency_plan": {
            name: {
                "start_mhz": FREQUENCIES_MHZ[name][0],
                "end_mhz": FREQUENCIES_MHZ[name][1],
                "center_mhz": (FREQUENCIES_MHZ[name][0] + FREQUENCIES_MHZ[name][1]) / 2,
            }
            for name in STREAM_MAP
        },
        "error_simulation": {
            "model": "independent random bit flips",
            "configured_ber": ber,
            "note": "BER is a configurable simulation assumption; there is no single universal normal RF BER.",
            "random_seed": DEFAULT_RANDOM_SEED,
            "total_simulated_errors": total_errors,
            "measured_ber": total_errors / total_bits if total_bits else 0.0,
            "error_formula": "BER = number_of_wrong_bits / total_transmitted_bits",
        },
        "per_stream": per_stream,
    }

    return report


def write_text_report(report: dict, output_path: Path):
    inp = report["input"]
    mod = report["modulation"]
    ch = report["channel_model"]
    err = report["error_simulation"]

    lines = [
        "============================================================",
        "       16-QAM SIX-PARALLEL-STREAM RF TRANSMISSION REPORT",
        "============================================================",
        "",
        "1. INPUT BITSTREAM",
        "------------------------------------------------------------",
        f"Source JSON: {report['input']['source_json']}",
        f"Number of streams: {inp['stream_count']}",
        f"Total bits: {inp['total_bits']:,} bits",
        f"Total byte-equivalent: {inp['total_bytes_equivalent']:,} bytes",
        f"Total size: {inp['total_mib_equivalent']:.3f} MiB",
        "",
        "The supplied YCbCr JSON contains six equal streams.",
        "Y is divided into four 25% parts; Cb and Cr are each one stream.",
        "",
        "2. STREAM DIVISION",
        "------------------------------------------------------------",
    ]

    for name, d in report["bitstream_division"].items():
        lines += [
            f"{name}:",
            f"  JSON field: {d['json_field']}",
            f"  Bits: {d['bits']:,}",
            f"  Bytes equivalent: {d['bytes_equivalent']:,}",
            f"  Portion of total: {d['percentage_of_total']:.2f}%",
        ]

    lines += [
        "",
        "3. 16-QAM",
        "------------------------------------------------------------",
        "16-QAM carries 4 bits per symbol.",
        "Therefore:",
        "  raw bit rate = symbol rate × 4",
        "",
        "4. CHANNEL / SYMBOL-RATE ASSUMPTION",
        "------------------------------------------------------------",
        f"Channel bandwidth: {ch['channel_bandwidth_khz']:.0f} kHz per stream",
        f"Raised-cosine roll-off: {ch['roll_off']}",
        "Assumed relationship:",
        "  symbol rate = bandwidth / (1 + roll-off)",
        f"  symbol rate = 300,000 / (1 + {ch['roll_off']})",
        f"  symbol rate ≈ {ch['estimated_symbol_rate_baud']:,.1f} baud",
        "",
        "5. DATA RATE",
        "------------------------------------------------------------",
        "For 16-QAM:",
        "  bit rate = symbol rate × 4",
        f"  bit rate ≈ {ch['estimated_raw_bit_rate_bps_per_stream']:,.1f} bps",
        f"  ≈ {ch['estimated_raw_bit_rate_kbps_per_stream']:.2f} kbps per stream",
        "",
        f"Six-stream aggregate ≈ {ch['estimated_six_stream_aggregate_mbps']:.3f} Mbps raw.",
        "",
        "6. TRANSMISSION TIME",
        "------------------------------------------------------------",
        f"Total data = {inp['total_bits']:,} bits",
        f"Six-stream aggregate raw rate = {ch['estimated_six_stream_aggregate_mbps']:.3f} Mbps",
        "Ideal time = total bits / aggregate bit rate",
        f"Ideal transmission time ≈ {ch['ideal_transmission_time_seconds']:.3f} seconds",
        "",
        "This is an ideal PHY-rate estimate. Real payload throughput will",
        "be lower because of framing, synchronization, pilots, FEC,",
        "interleaving, implementation losses, and retransmissions.",
        "",
        "7. BIT-ERROR SIMULATION",
        "------------------------------------------------------------",
        f"Configured BER: {err['configured_ber']}",
        f"Configured BER percentage: {err['configured_ber'] * 100:.3f}%",
        "Model: each transmitted bit independently has the configured",
        "probability of being flipped.",
        "",
        "Important: there is no universal 'normal RF error rate'.",
        "BER depends on SNR, RF channel, interference, implementation,",
        "coding, synchronization, and receiver design.",
        "The configured BER is therefore an explicit simulation assumption.",
        "",
        f"Total simulated bit errors: {err['total_simulated_errors']:,}",
        f"Measured BER after simulation: {err['measured_ber']:.8f}",
        f"Measured BER percentage: {err['measured_ber'] * 100:.5f}%",
        "",
        "8. OUTPUT FILES",
        "------------------------------------------------------------",
        "rf_transmission_report.txt",
        "rf_transmission_report.json",
        "rf_transmission_error_bitstreams.json",
        "",
        "The error-bitstream JSON contains the same six stream names as",
        "the source JSON, but with simulated bit flips applied.",
        "============================================================",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_report(
    ber: float = DEFAULT_BER,
    random_seed: int = DEFAULT_RANDOM_SEED,
    output_dir: Path | None = None,
):
    input_path = locate_input_json()
    source_data, original = load_bitstreams(input_path)

    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(random_seed)
    corrupted = {}
    errors = {}

    for name, bits in original.items():
        corrupted[name], errors[name] = add_errors(bits, ber, rng)

    report = make_report(input_path, original, corrupted, errors, ber)

    report_json = output_dir / "rf_transmission_report.json"
    report_txt = output_dir / "rf_transmission_report.txt"
    error_json = output_dir / "rf_transmission_error_bitstreams.json"

    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_text_report(report, report_txt)

    error_streams = {
        STREAM_MAP[name]: corrupted[name]
        for name in STREAM_MAP
    }

    error_output = {
        "format": "YCbCr_6_streams_16QAM_BER_simulation",
        "source_file": str(input_path),
        "modulation": "16-QAM",
        "bits_per_symbol": 4,
        "configured_ber": ber,
        "random_seed": random_seed,
        "error_model": "independent random bit flips",
        "streams": error_streams,
    }

    error_json.write_text(json.dumps(error_output, indent=2), encoding="utf-8")

    print(f"Report written: {report_txt}")
    print(f"JSON report written: {report_json}")
    print(f"Error bitstreams written: {error_json}")
    print(f"Configured BER: {ber} ({ber * 100:.3f}%)")
    print(f"Total simulated errors: {sum(len(x) for x in errors.values()):,}")

    return report


if __name__ == "__main__":
    generate_report()
