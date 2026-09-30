"""
Main encoder.

Output structure:
    output/
        1_converted/
            Cb_downsampled.png
            Cr_downsampled.png
            Y_part1.png ... Y_part4.png
        2_upscaled_put_together/
            Y_full.png
            reconstructed_rgb.png
        3_comparison/
            original.png
            reconstructed.png
            absolute_difference.png
            comparison_side_by_side.png
            quality_metrics.txt
        ycbcr_bitstreams.json
"""

import argparse
import os
import time

from generate_sample_image import generate_test_image
from ycbcr_processor import YCbCrProcessor


def main():
    parser = argparse.ArgumentParser(
        description="1024x1024 RGB -> YCbCr -> 4-stream Y + Cb + Cr JSON encoder."
    )

    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="Input image. MUST be exactly 1024x1024.",
    )

    parser.add_argument(
        "-o",
        "--output_dir",
        default="output",
        help="Root output directory.",
    )

    parser.add_argument(
        "--generate_sample",
        action="store_true",
        help="Generate the sample image before processing.",
    )

    args = parser.parse_args()

    print("=" * 72)
    print("       1024x1024 RGB -> YCbCr STREAM ENCODER")
    print("=" * 72)

    os.makedirs(args.output_dir, exist_ok=True)

    if args.generate_sample or args.input is None:
        input_path = "sample_1024x1024.png"
        if args.generate_sample or not os.path.exists(input_path):
            print("[*] Generating 1024x1024 sample image...")
            generate_test_image(input_path)
    else:
        input_path = args.input

    print(f"[*] Input: {input_path}")
    t0 = time.time()

    print("[*] Converting RGB -> YCbCr...")
    print("[*] Downsampling Cb and Cr using 2x2 averaging...")
    results = YCbCrProcessor.process_image(input_path)

    # Keep the bitstream JSON directly inside output/, alongside the three
    # visual folders.
    json_path = os.path.join(args.output_dir, "ycbcr_bitstreams.json")

    print("[*] Creating Y/Cb/Cr bitstreams...")
    print("[*] Splitting Y into four consecutive 25% streams...")
    YCbCrProcessor.export_json(results, json_path)

    print("[*] Exporting organized visual files...")
    visual_paths = YCbCrProcessor.export_visuals(results, args.output_dir)

    print("[*] Creating comparison files...")
    comparison_paths = YCbCrProcessor.export_comparison(
        results["rgb_original"],
        results["rgb_reconstructed"],
        args.output_dir,
    )

    elapsed = time.time() - t0

    y_samples = YCbCrProcessor.Y_SAMPLES
    y_part_samples = YCbCrProcessor.Y_PART_SAMPLES
    chroma_samples = YCbCrProcessor.CHROMA_SAMPLES

    y_bits = y_samples * 8
    y_part_bits = y_part_samples * 8
    cb_bits = chroma_samples * 8
    cr_bits = chroma_samples * 8
    total_bits = y_bits + cb_bits + cr_bits

    print()
    print("=" * 72)
    print("                         SUMMARY")
    print("=" * 72)
    print("Input resolution          : 1024 x 1024")
    print("Y resolution              : 1024 x 1024")
    print("Cb resolution             : 512 x 512")
    print("Cr resolution             : 512 x 512")
    print()
    print("Y STREAM")
    print(f"  Total Y samples         : {y_samples:,}")
    print("  Bits/sample             : 8")
    print(f"  Total Y bits            : {y_bits:,}")
    print(f"  Part 1 samples          : {y_part_samples:,}")
    print(f"  Part 2 samples          : {y_part_samples:,}")
    print(f"  Part 3 samples          : {y_part_samples:,}")
    print(f"  Part 4 samples          : {y_part_samples:,}")
    print(f"  Bits in each Y part     : {y_part_bits:,}")
    print()
    print("CHROMA STREAMS")
    print(f"  Cb samples              : {chroma_samples:,}")
    print(f"  Cb bits                 : {cb_bits:,}")
    print(f"  Cr samples              : {chroma_samples:,}")
    print(f"  Cr bits                 : {cr_bits:,}")
    print()
    print("TOTAL")
    print(f"  Total bits              : {total_bits:,}")
    print(f"  Total bytes             : {total_bits // 8:,}")
    print(f"  Reference 4:2:0 MSE     : {results['mse']:.6f}")
    print(f"  Reference 4:2:0 PSNR    : {results['psnr_db']:.4f} dB")
    print(f"  Processing time         : {elapsed:.2f} sec")
    print()
    print("OUTPUT FOLDERS")
    print(f"  1_converted             : {os.path.join(args.output_dir, '1_converted')}")
    print(f"  2_upscaled_put_together : {os.path.join(args.output_dir, '2_upscaled_put_together')}")
    print(f"  3_comparison            : {os.path.join(args.output_dir, '3_comparison')}")
    print(f"  Bitstream JSON           : {json_path}")
    print()
    print("JSON")
    print(f"  {json_path}")
    print()
    print("COMPARISON")
    for name, path in comparison_paths.items():
        print(f"  {name:<24}: {path}")
    print("=" * 72)
    print(f"[OK] Output directory: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
