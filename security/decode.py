import json
import sys
from pathlib import Path

# Used only if the encrypted JSON does not contain security.xor_key.
XOR_KEY = 90

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
    if len(sys.argv) != 2:
        print("Usage: python decode.py path\\to\\encrypted_ycbcr_bitstreams.json")
        raise SystemExit(1)

    input_json = Path(sys.argv[1]).resolve()
    if not input_json.exists():
        raise FileNotFoundError(f"Input JSON not found:\n{input_json}")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    key = data.get("security", {}).get("xor_key", XOR_KEY)
    if not isinstance(key, int) or not 0 <= key <= 255:
        raise ValueError("XOR key must be an integer from 0 to 255.")

    result = dict(data)
    result["streams"] = dict(data["streams"])

    for name in STREAM_NAMES:
        if name not in data["streams"]:
            raise KeyError(f"Missing stream: {name}")
        result["streams"][name] = xor_bitstream(
            data["streams"][name], key
        )

    result["security"] = {
        "method": "byte-wise XOR",
        "xor_key": key,
        "status": "decrypted"
    }

    output_json = input_json.parent / "decrypted_ycbcr_bitstreams.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("XOR decryption completed.")
    print(f"Key   : {key}")
    print(f"Input : {input_json}")
    print(f"Output: {output_json}")


if __name__ == "__main__":
    main()
