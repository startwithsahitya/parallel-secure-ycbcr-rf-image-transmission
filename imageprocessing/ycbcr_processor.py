"""
YCbCr Image Processing Engine
=============================

Fixed 1024x1024 RGB -> YCbCr -> 4:2:0 pipeline.

Data format:
    Y  : 1024x1024, uint8, row-major
         split into four consecutive 25% streams.
         Each stream contains 262,144 samples, 8 bits/sample.

    Cb : 1024x1024 -> 512x512 using 2x2 averaging, uint8.
    Cr : 1024x1024 -> 512x512 using 2x2 averaging, uint8.

The JSON encoder stores bitstrings:
    Y_part1_bits
    Y_part2_bits
    Y_part3_bits
    Y_part4_bits
    Cb_bits
    Cr_bits

The decoder reconstructs Y by concatenating the four Y parts, reshapes
it to 1024x1024, upsamples Cb/Cr to 1024x1024, converts YCbCr -> RGB,
and calculates MSE and PSNR against the original image.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image


class YCbCrProcessor:
    WIDTH = 1024
    HEIGHT = 1024
    Y_SAMPLES = WIDTH * HEIGHT
    Y_PART_SAMPLES = Y_SAMPLES // 4
    CHROMA_WIDTH = WIDTH // 2
    CHROMA_HEIGHT = HEIGHT // 2
    CHROMA_SAMPLES = CHROMA_WIDTH * CHROMA_HEIGHT

    @staticmethod
    def load_1024_image(image_path: str) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Load an image and require exactly 1024x1024 pixels."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(image_path).convert("RGB")

        if img.size != (YCbCrProcessor.WIDTH, YCbCrProcessor.HEIGHT):
            raise ValueError(
                f"Input image must be exactly 1024x1024. "
                f"Received {img.size[0]}x{img.size[1]}."
            )

        return np.array(img, dtype=np.uint8), img.size

    @staticmethod
    def rgb_to_ycbcr_full(
        rgb_array: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert RGB to full-resolution BT.601 Y, Cb, Cr."""
        if rgb_array.shape != (1024, 1024, 3):
            raise ValueError(
                f"RGB array must have shape (1024,1024,3), got {rgb_array.shape}"
            )

        r = rgb_array[:, :, 0].astype(np.float64)
        g = rgb_array[:, :, 1].astype(np.float64)
        b = rgb_array[:, :, 2].astype(np.float64)

        y_float = 0.299 * r + 0.587 * g + 0.114 * b
        cb_float = -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0
        cr_float = 0.5 * r - 0.418688 * g - 0.081312 * b + 128.0

        y = np.clip(np.round(y_float), 0, 255).astype(np.uint8)
        cb = np.clip(np.round(cb_float), 0, 255).astype(np.uint8)
        cr = np.clip(np.round(cr_float), 0, 255).astype(np.uint8)

        return y, cb, cr

    @staticmethod
    def downsample_2x2_average(channel: np.ndarray) -> np.ndarray:
        """2x2 average downsampling, preserving uint8 values."""
        h, w = channel.shape

        if h % 2 != 0 or w % 2 != 0:
            raise ValueError("Channel dimensions must be even.")

        reshaped = channel.astype(np.float64).reshape(h // 2, 2, w // 2, 2)
        averaged = reshaped.mean(axis=(1, 3))

        return np.clip(np.round(averaged), 0, 255).astype(np.uint8)

    @staticmethod
    def upsample_2x2(
        channel_down: np.ndarray,
        target_shape: Tuple[int, int],
    ) -> np.ndarray:
        """Nearest-neighbor 2x2 replication."""
        target_h, target_w = target_shape

        upsampled = np.repeat(
            np.repeat(channel_down, 2, axis=0),
            2,
            axis=1,
        )

        return upsampled[:target_h, :target_w]

    @staticmethod
    def ycbcr_to_rgb(
        y_channel: np.ndarray,
        cb_channel: np.ndarray,
        cr_channel: np.ndarray,
    ) -> np.ndarray:
        """Inverse BT.601 conversion."""
        y = y_channel.astype(np.float64)
        cb = cb_channel.astype(np.float64)
        cr = cr_channel.astype(np.float64)

        cb_diff = cb - 128.0
        cr_diff = cr - 128.0

        r = y + 1.402 * cr_diff
        g = y - 0.344136 * cb_diff - 0.714136 * cr_diff
        b = y + 1.772 * cb_diff

        rgb = np.stack([r, g, b], axis=-1)

        return np.clip(np.round(rgb), 0, 255).astype(np.uint8)

    @staticmethod
    def calculate_metrics(
        original_rgb: np.ndarray,
        reconstructed_rgb: np.ndarray,
    ) -> Tuple[float, float]:
        """Calculate MSE and PSNR."""
        original = original_rgb.astype(np.float64)
        reconstructed = reconstructed_rgb.astype(np.float64)

        mse = float(np.mean((original - reconstructed) ** 2))

        if mse == 0:
            psnr = 99.99
        else:
            psnr = 10.0 * math.log10((255.0 ** 2) / mse)

        return mse, psnr

    @classmethod
    def process_image(cls, image_path: str) -> Dict[str, Any]:
        """Run RGB -> YCbCr -> 4:2:0 -> reconstruction quality pipeline."""
        rgb_original, original_size = cls.load_1024_image(image_path)

        y_full, cb_full, cr_full = cls.rgb_to_ycbcr_full(rgb_original)

        cb_downsampled = cls.downsample_2x2_average(cb_full)
        cr_downsampled = cls.downsample_2x2_average(cr_full)

        cb_reconstructed = cls.upsample_2x2(
            cb_downsampled,
            (cls.HEIGHT, cls.WIDTH),
        )
        cr_reconstructed = cls.upsample_2x2(
            cr_downsampled,
            (cls.HEIGHT, cls.WIDTH),
        )

        rgb_reconstructed = cls.ycbcr_to_rgb(
            y_full,
            cb_reconstructed,
            cr_reconstructed,
        )

        mse, psnr = cls.calculate_metrics(
            rgb_original,
            rgb_reconstructed,
        )

        return {
            "rgb_original": rgb_original,
            "original_size": original_size,
            "processed_shape": (cls.HEIGHT, cls.WIDTH),
            "y_full": y_full,
            "cb_full": cb_full,
            "cr_full": cr_full,
            "cb_downsampled": cb_downsampled,
            "cr_downsampled": cr_downsampled,
            "rgb_reconstructed": rgb_reconstructed,
            "mse": mse,
            "psnr_db": psnr,
        }

    # ------------------------------------------------------------------
    # Y ARRAY SPLITTING
    # ------------------------------------------------------------------

    @classmethod
    def split_y_into_four_parts(cls, y_full: np.ndarray):
        """
        Flatten Y row-major and split into four equal 25% sections.

        IMPORTANT:
            We do NOT split the 8 bits inside each Y value.
            Every sample remains an 8-bit value.
        """
        if y_full.shape != (cls.HEIGHT, cls.WIDTH):
            raise ValueError(f"Y must be 1024x1024, got {y_full.shape}")

        flat = y_full.flatten(order="C")

        return tuple(
            flat[i * cls.Y_PART_SAMPLES:(i + 1) * cls.Y_PART_SAMPLES].copy()
            for i in range(4)
        )

    @staticmethod
    def values_to_bitstream(values: np.ndarray) -> str:
        """Convert uint8 values to one continuous 8-bit binary stream."""
        return "".join(format(int(v), "08b") for v in values)

    @staticmethod
    def bitstream_to_values(bitstream: str, expected_samples: int) -> np.ndarray:
        """Convert a continuous 8-bit binary stream back to uint8 values."""
        expected_bits = expected_samples * 8

        if len(bitstream) != expected_bits:
            raise ValueError(
                f"Expected {expected_bits} bits for {expected_samples} samples, "
                f"received {len(bitstream)}."
            )

        if any(c not in "01" for c in bitstream):
            raise ValueError("Bitstream contains characters other than 0 and 1.")

        values = np.fromiter(
            (int(bitstream[i:i + 8], 2) for i in range(0, len(bitstream), 8)),
            dtype=np.uint8,
            count=expected_samples,
        )

        return values

    @classmethod
    def create_bitstream_data(cls, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the exact four-part Y + Cb + Cr bitstream representation.
        """
        y_parts = cls.split_y_into_four_parts(results["y_full"])

        cb_flat = results["cb_downsampled"].flatten(order="C")
        cr_flat = results["cr_downsampled"].flatten(order="C")

        data = {
            "Y_part1_bits": cls.values_to_bitstream(y_parts[0]),
            "Y_part2_bits": cls.values_to_bitstream(y_parts[1]),
            "Y_part3_bits": cls.values_to_bitstream(y_parts[2]),
            "Y_part4_bits": cls.values_to_bitstream(y_parts[3]),
            "Cb_bits": cls.values_to_bitstream(cb_flat),
            "Cr_bits": cls.values_to_bitstream(cr_flat),
        }

        return data

    @classmethod
    def export_json(
        cls,
        results: Dict[str, Any],
        output_path: str,
    ) -> str:
        """Write all encoded streams and metadata into one JSON file."""
        stream_data = cls.create_bitstream_data(results)

        metadata = {
            "format": "YCbCr_4:2:0_Y4x25percent_CbCr8bit",
            "input": {
                "width": cls.WIDTH,
                "height": cls.HEIGHT,
                "channels": "RGB",
            },
            "conversion": {
                "color_space": "YCbCr",
                "standard": "ITU-R BT.601",
            },
            "Y": {
                "width": cls.WIDTH,
                "height": cls.HEIGHT,
                "samples": cls.Y_SAMPLES,
                "bits_per_sample": 8,
                "total_bits": cls.Y_SAMPLES * 8,
                "split": "four consecutive 25% parts",
                "samples_per_part": cls.Y_PART_SAMPLES,
                "bits_per_part": cls.Y_PART_SAMPLES * 8,
            },
            "Cb": {
                "source_width": cls.WIDTH,
                "source_height": cls.HEIGHT,
                "downsample_method": "2x2 average",
                "width": cls.CHROMA_WIDTH,
                "height": cls.CHROMA_HEIGHT,
                "samples": cls.CHROMA_SAMPLES,
                "bits_per_sample": 8,
                "total_bits": cls.CHROMA_SAMPLES * 8,
            },
            "Cr": {
                "source_width": cls.WIDTH,
                "source_height": cls.HEIGHT,
                "downsample_method": "2x2 average",
                "width": cls.CHROMA_WIDTH,
                "height": cls.CHROMA_HEIGHT,
                "samples": cls.CHROMA_SAMPLES,
                "bits_per_sample": 8,
                "total_bits": cls.CHROMA_SAMPLES * 8,
            },
            "stream_lengths": {
                "Y_part1_bits": len(stream_data["Y_part1_bits"]),
                "Y_part2_bits": len(stream_data["Y_part2_bits"]),
                "Y_part3_bits": len(stream_data["Y_part3_bits"]),
                "Y_part4_bits": len(stream_data["Y_part4_bits"]),
                "Cb_bits": len(stream_data["Cb_bits"]),
                "Cr_bits": len(stream_data["Cr_bits"]),
            },
            "quality_of_4_2_0_reference": {
                "mse": round(results["mse"], 6),
                "psnr_db": round(results["psnr_db"], 4),
            },
            "streams": stream_data,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return output_path

    # ------------------------------------------------------------------
    # RECONSTRUCTION FROM JSON
    # ------------------------------------------------------------------

    @classmethod
    def reconstruct_from_json(
        cls,
        json_path: str,
    ) -> Dict[str, Any]:
        """
        Decode the JSON streams and reconstruct a 1024x1024 RGB image.

        Y:
            concatenate four 25% streams.

        Cb/Cr:
            decode 512x512 streams, then replicate each sample into a 2x2 block.
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data["input"]["width"] != 1024 or data["input"]["height"] != 1024:
            raise ValueError("JSON does not describe a 1024x1024 image.")

        streams = data["streams"]

        y1 = cls.bitstream_to_values(
            streams["Y_part1_bits"], cls.Y_PART_SAMPLES
        )
        y2 = cls.bitstream_to_values(
            streams["Y_part2_bits"], cls.Y_PART_SAMPLES
        )
        y3 = cls.bitstream_to_values(
            streams["Y_part3_bits"], cls.Y_PART_SAMPLES
        )
        y4 = cls.bitstream_to_values(
            streams["Y_part4_bits"], cls.Y_PART_SAMPLES
        )

        y_flat = np.concatenate([y1, y2, y3, y4])
        y = y_flat.reshape((cls.HEIGHT, cls.WIDTH), order="C")

        cb_flat = cls.bitstream_to_values(
            streams["Cb_bits"], cls.CHROMA_SAMPLES
        )
        cr_flat = cls.bitstream_to_values(
            streams["Cr_bits"], cls.CHROMA_SAMPLES
        )

        cb_down = cb_flat.reshape(
            (cls.CHROMA_HEIGHT, cls.CHROMA_WIDTH),
            order="C",
        )
        cr_down = cr_flat.reshape(
            (cls.CHROMA_HEIGHT, cls.CHROMA_WIDTH),
            order="C",
        )

        cb_full = cls.upsample_2x2(cb_down, (cls.HEIGHT, cls.WIDTH))
        cr_full = cls.upsample_2x2(cr_down, (cls.HEIGHT, cls.WIDTH))

        rgb_reconstructed = cls.ycbcr_to_rgb(y, cb_full, cr_full)

        return {
            "y": y,
            "cb_downsampled": cb_down,
            "cr_downsampled": cr_down,
            "cb_full": cb_full,
            "cr_full": cr_full,
            "rgb_reconstructed": rgb_reconstructed,
        }

    @staticmethod
    def compare_images(
        original_path: str,
        reconstructed_rgb: np.ndarray,
    ) -> Tuple[float, float]:
        """Compare reconstructed RGB array against the original PNG."""
        original = np.array(
            Image.open(original_path).convert("RGB"),
            dtype=np.uint8,
        )

        if original.shape != reconstructed_rgb.shape:
            raise ValueError(
                f"Image shapes differ: {original.shape} vs "
                f"{reconstructed_rgb.shape}"
            )

        return YCbCrProcessor.calculate_metrics(
            original,
            reconstructed_rgb,
        )

    # ------------------------------------------------------------------
    # ORGANIZED OUTPUTS / VISUALS
    # ------------------------------------------------------------------

    @staticmethod
    def export_visuals(
        results: Dict[str, Any],
        output_root: str,
    ) -> Dict[str, str]:
        """
        Export outputs into an organized folder structure:

            output_root/
                1_converted/
                    Cb_downsampled.png
                    Cr_downsampled.png
                    Y_part1.png ... Y_part4.png
                2_upscaled_put_together/
                    Y_full.png
                    reconstructed_rgb.png

        The bitstream JSON is intentionally kept directly under output_root
        by main.py, alongside these three folders.

        Y_part1..Y_part4 are shown as 256x1024 images. This preserves the
        row-major spatial meaning of the four consecutive Y sample chunks:
        part 1 = rows 0..255, part 2 = rows 256..511, etc.
        """
        converted_dir = os.path.join(output_root, "1_converted")
        upscaled_dir = os.path.join(output_root, "2_upscaled_put_together")
        os.makedirs(converted_dir, exist_ok=True)
        os.makedirs(upscaled_dir, exist_ok=True)

        paths: Dict[str, str] = {}

        # Converted/downsampled outputs.
        cb_path = os.path.join(converted_dir, "Cb_downsampled.png")
        cr_path = os.path.join(converted_dir, "Cr_downsampled.png")
        Image.fromarray(results["cb_downsampled"]).save(cb_path)
        Image.fromarray(results["cr_downsampled"]).save(cr_path)
        paths["Cb_downsampled"] = cb_path
        paths["Cr_downsampled"] = cr_path

        # Y is split into four consecutive sample chunks. Since the source
        # is 1024 pixels wide, each quarter contains 256 complete rows.
        y_parts = YCbCrProcessor.split_y_into_four_parts(results["y_full"])
        for i, part in enumerate(y_parts, start=1):
            image = part.reshape((256, 1024), order="C")
            path = os.path.join(converted_dir, f"Y_part{i}.png")
            Image.fromarray(image).save(path)
            paths[f"Y_part{i}"] = path

        # Full Y and reconstructed RGB.
        y_full_path = os.path.join(upscaled_dir, "Y_full.png")
        reconstructed_path = os.path.join(upscaled_dir, "reconstructed_rgb.png")
        Image.fromarray(results["y_full"]).save(y_full_path)
        Image.fromarray(results["rgb_reconstructed"]).save(reconstructed_path)
        paths["Y_full"] = y_full_path
        paths["reconstructed_rgb"] = reconstructed_path

        return paths

    @staticmethod
    def export_comparison(
        original_rgb: np.ndarray,
        reconstructed_rgb: np.ndarray,
        output_root: str,
    ) -> Dict[str, str]:
        """
        Create visual comparison files in output/3_comparison/.

        Files:
            original.png
            reconstructed.png
            absolute_difference.png
            comparison_side_by_side.png
            quality_metrics.txt
        """
        comparison_dir = os.path.join(output_root, "3_comparison")
        os.makedirs(comparison_dir, exist_ok=True)

        original = np.asarray(original_rgb, dtype=np.uint8)
        reconstructed = np.asarray(reconstructed_rgb, dtype=np.uint8)

        mse, psnr = YCbCrProcessor.calculate_metrics(original, reconstructed)

        original_path = os.path.join(comparison_dir, "original.png")
        reconstructed_path = os.path.join(comparison_dir, "reconstructed.png")
        difference_path = os.path.join(comparison_dir, "absolute_difference.png")
        side_by_side_path = os.path.join(comparison_dir, "comparison_side_by_side.png")
        metrics_path = os.path.join(comparison_dir, "quality_metrics.txt")

        Image.fromarray(original).save(original_path)
        Image.fromarray(reconstructed).save(reconstructed_path)

        # Absolute per-channel difference, scaled so small differences are visible.
        diff = np.abs(original.astype(np.int16) - reconstructed.astype(np.int16))
        diff_gray = np.max(diff, axis=2).astype(np.uint8)
        diff_max = int(diff_gray.max())
        if diff_max > 0:
            diff_display = np.clip(
                diff_gray.astype(np.float32) * (255.0 / diff_max), 0, 255
            ).astype(np.uint8)
        else:
            diff_display = diff_gray
        Image.fromarray(diff_display).save(difference_path)

        # Side-by-side comparison: original | reconstructed.
        h, w = original.shape[:2]
        canvas = Image.new("RGB", (w * 2, h), "white")
        canvas.paste(Image.fromarray(original), (0, 0))
        canvas.paste(Image.fromarray(reconstructed), (w, 0))
        canvas.save(side_by_side_path)

        metrics_text = (
            "YCbCr 4:2:0 Reconstruction Quality\n"
            "=================================\n\n"
            f"Original resolution      : {w} x {h}\n"
            f"Reconstructed resolution : {reconstructed.shape[1]} x {reconstructed.shape[0]}\n"
            f"MSE                     : {mse:.6f}\n"
            f"PSNR                    : {psnr:.4f} dB\n\n"
            "MSE: mean squared pixel error between original and reconstructed RGB.\n"
            "PSNR: peak signal-to-noise ratio calculated from MSE.\n"
        )
        with open(metrics_path, "w", encoding="utf-8") as f:
            f.write(metrics_text)

        return {
            "original": original_path,
            "reconstructed": reconstructed_path,
            "absolute_difference": difference_path,
            "comparison_side_by_side": side_by_side_path,
            "quality_metrics": metrics_path,
        }
