"""
Unit and integration tests for the 1024x1024 YCbCr stream pipeline.
"""

import json
import os
import shutil
import unittest

import numpy as np
from PIL import Image

from generate_sample_image import generate_test_image
from ycbcr_processor import YCbCrProcessor


class TestYCbCrPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir = "test_output_sandbox"
        os.makedirs(cls.test_dir, exist_ok=True)

        cls.sample_path = os.path.join(
            cls.test_dir,
            "test_1024x1024.png",
        )

        generate_test_image(
            cls.sample_path,
            1024,
            1024,
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def test_input_dimensions_are_strict(self):
        results = YCbCrProcessor.process_image(self.sample_path)

        self.assertEqual(
            results["processed_shape"],
            (1024, 1024),
        )

    def test_bt601_pure_colors(self):
        white = np.full(
            (1024, 1024, 3),
            255,
            dtype=np.uint8,
        )

        y, cb, cr = YCbCrProcessor.rgb_to_ycbcr_full(white)

        self.assertEqual(int(y[0, 0]), 255)
        self.assertEqual(int(cb[0, 0]), 128)
        self.assertEqual(int(cr[0, 0]), 128)

        black = np.zeros(
            (1024, 1024, 3),
            dtype=np.uint8,
        )

        y, cb, cr = YCbCrProcessor.rgb_to_ycbcr_full(black)

        self.assertEqual(int(y[0, 0]), 0)
        self.assertEqual(int(cb[0, 0]), 128)
        self.assertEqual(int(cr[0, 0]), 128)

        red = np.zeros(
            (1024, 1024, 3),
            dtype=np.uint8,
        )
        red[:, :, 0] = 255

        y, cb, cr = YCbCrProcessor.rgb_to_ycbcr_full(red)

        self.assertEqual(int(y[0, 0]), 76)
        self.assertEqual(int(cb[0, 0]), 85)
        self.assertEqual(int(cr[0, 0]), 255)

    def test_2x2_average(self):
        matrix = np.array(
            [
                [10, 20, 100, 100],
                [30, 40, 100, 100],
                [0, 1, 250, 251],
                [2, 3, 252, 253],
            ],
            dtype=np.uint8,
        )

        down = YCbCrProcessor.downsample_2x2_average(matrix)

        expected = np.array(
            [
                [25, 100],
                [2, 252],
            ],
            dtype=np.uint8,
        )

        np.testing.assert_array_equal(down, expected)

    def test_dimensions(self):
        results = YCbCrProcessor.process_image(self.sample_path)

        self.assertEqual(
            results["y_full"].shape,
            (1024, 1024),
        )

        self.assertEqual(
            results["cb_downsampled"].shape,
            (512, 512),
        )

        self.assertEqual(
            results["cr_downsampled"].shape,
            (512, 512),
        )

    def test_y_split_is_four_equal_parts(self):
        results = YCbCrProcessor.process_image(self.sample_path)

        parts = YCbCrProcessor.split_y_into_four_parts(
            results["y_full"]
        )

        self.assertEqual(len(parts), 4)

        for part in parts:
            self.assertEqual(
                len(part),
                262144,
            )

        combined = np.concatenate(parts)

        np.testing.assert_array_equal(
            combined,
            results["y_full"].flatten(order="C"),
        )

    def test_bitstream_lengths(self):
        results = YCbCrProcessor.process_image(self.sample_path)

        stream_data = YCbCrProcessor.create_bitstream_data(results)

        self.assertEqual(
            len(stream_data["Y_part1_bits"]),
            262144 * 8,
        )
        self.assertEqual(
            len(stream_data["Y_part2_bits"]),
            262144 * 8,
        )
        self.assertEqual(
            len(stream_data["Y_part3_bits"]),
            262144 * 8,
        )
        self.assertEqual(
            len(stream_data["Y_part4_bits"]),
            262144 * 8,
        )

        self.assertEqual(
            len(stream_data["Cb_bits"]),
            262144 * 8,
        )

        self.assertEqual(
            len(stream_data["Cr_bits"]),
            262144 * 8,
        )

    def test_json_and_reconstruction(self):
        results = YCbCrProcessor.process_image(self.sample_path)

        json_path = os.path.join(
            self.test_dir,
            "streams.json",
        )

        YCbCrProcessor.export_json(
            results,
            json_path,
        )

        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(
            data["input"]["width"],
            1024,
        )
        self.assertEqual(
            data["input"]["height"],
            1024,
        )

        decoded = YCbCrProcessor.reconstruct_from_json(
            json_path
        )

        self.assertEqual(
            decoded["y"].shape,
            (1024, 1024),
        )

        self.assertEqual(
            decoded["cb_downsampled"].shape,
            (512, 512),
        )

        self.assertEqual(
            decoded["cr_downsampled"].shape,
            (512, 512),
        )

        self.assertEqual(
            decoded["rgb_reconstructed"].shape,
            (1024, 1024, 3),
        )

    def test_json_y_reconstruction_is_lossless(self):
        """
        Splitting Y into four streams and joining them again must reproduce
        the exact original Y matrix. No Y information is lost by splitting.
        """
        results = YCbCrProcessor.process_image(self.sample_path)

        json_path = os.path.join(
            self.test_dir,
            "streams_y_lossless.json",
        )

        YCbCrProcessor.export_json(
            results,
            json_path,
        )

        decoded = YCbCrProcessor.reconstruct_from_json(
            json_path
        )

        np.testing.assert_array_equal(
            decoded["y"],
            results["y_full"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
