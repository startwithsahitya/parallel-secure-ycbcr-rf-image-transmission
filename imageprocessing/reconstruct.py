"""
JSON decoder / image reconstruction.

Input:
    output/ycbcr_bitstreams.json

Outputs:
    output/2_upscaled_put_together/reconstructed_rgb.png
    output/3_comparison/*
"""

import argparse
import os

from PIL import Image

from ycbcr_processor import YCbCrProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Reconstruct a 1024x1024 RGB image from Y/Cb/Cr JSON streams."
    )

    parser.add_argument(
        "-j",
        "--json",
        default="output/ycbcr_bitstreams.json",
        help="JSON bitstream file.",
    )

    parser.add_argument(
        "-i",
        "--original",
        default="sample_1024x1024.png",
        help="Original 1024x1024 image for quality comparison.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="output/2_upscaled_put_together/reconstructed_rgb.png",
        help="Reconstructed image path.",
    )

    parser.add_argument(
        "--output_dir",
        default="output",
        help="Root output directory for comparison files.",
    )

    args = parser.parse_args()

    print("=" * 72)
    print("              JSON -> RGB IMAGE RECONSTRUCTION")
    print("=" * 72)
    print(f"[*] JSON       : {args.json}")

    decoded = YCbCrProcessor.reconstruct_from_json(args.json)
    reconstructed = decoded["rgb_reconstructed"]

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    Image.fromarray(reconstructed).save(args.output)
    print(f"[*] Reconstructed image saved: {args.output}")

    mse, psnr = YCbCrProcessor.compare_images(args.original, reconstructed)
    print()
    print("QUALITY COMPARISON")
    print("------------------")
    print(f"Original image      : {args.original}")
    print(f"Reconstructed image : {args.output}")
    print(f"MSE                 : {mse:.6f}")
    print(f"PSNR                : {psnr:.4f} dB")

    original_rgb, _ = YCbCrProcessor.load_1024_image(args.original)
    comparison_paths = YCbCrProcessor.export_comparison(
        original_rgb,
        reconstructed,
        args.output_dir,
    )

    assert reconstructed.shape == (1024, 1024, 3)

    print()
    print("COMPARISON FILES")
    for name, path in comparison_paths.items():
        print(f"  {name:<24}: {path}")

    print()
    print("[OK] Reconstruction completed.")
    print("[OK] Reconstructed resolution is exactly 1024x1024.")
    print("=" * 72)


if __name__ == "__main__":
    main()
