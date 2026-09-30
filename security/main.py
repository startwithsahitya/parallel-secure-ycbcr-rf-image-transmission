import json
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

# Change this number to choose the XOR key. Valid: 0..255.
XOR_KEY = 90

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "imageprocessing" / "output" / "ycbcr_bitstreams.json"
OUTPUT_JSON = Path(__file__).resolve().parent / "encrypted_ycbcr_bitstreams.json"

STREAM_NAMES = (
    "Y_part1_bits", "Y_part2_bits", "Y_part3_bits",
    "Y_part4_bits", "Cb_bits", "Cr_bits"
)


def xor_bitstream(bits, key):
    if not isinstance(bits, str):
        raise TypeError("Bitstream must be a string.")
    if any(b not in "01" for b in bits):
        raise ValueError("Bitstream contains characters other than 0 and 1.")
    if len(bits) % 8:
        raise ValueError("Bitstream length must be a multiple of 8.")

    out = []
    for i in range(0, len(bits), 8):
        value = int(bits[i:i+8], 2)
        out.append(f"{value ^ key:08b}")
    return "".join(out)


def main():
    if not 0 <= XOR_KEY <= 255:
        raise ValueError("XOR_KEY must be between 0 and 255.")
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Input JSON not found:\n{INPUT_JSON}")

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "streams" not in data:
        raise KeyError("Input JSON does not contain 'streams'.")

    result = dict(data)
    result["streams"] = dict(data["streams"])
    result["security"] = {
        "method": "byte-wise XOR",
        "xor_key": XOR_KEY,
        "status": "encrypted"
    }

    for name in STREAM_NAMES:
        if name not in data["streams"]:
            raise KeyError(f"Missing stream: {name}")
        result["streams"][name] = xor_bitstream(
            data["streams"][name], XOR_KEY
        )

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("XOR encryption completed.")
    print(f"Key   : {XOR_KEY}")
    print(f"Input : {INPUT_JSON}")
    print(f"Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
