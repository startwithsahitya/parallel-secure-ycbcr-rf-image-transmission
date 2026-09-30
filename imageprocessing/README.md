# 1024x1024 RGB -> YCbCr Stream Pipeline

## Exact pipeline

```text
1024x1024 RGB
     |
     v
RGB -> YCbCr BT.601
     |
     +---------------- Y: 1024x1024 uint8
     |                       |
     |                       v
     |              flatten row-major
     |                       |
     |                       v
     |                 split into 4
     |                 equal sections
     |                       |
     |            +----------+----------+----------+
     |            |          |          |          |
     |           Y1         Y2         Y3         Y4
     |            |          |          |          |
     |            +----------+----------+----------+
     |
     +---------------- Cb: 1024x1024
     |                       |
     |                    2x2 avg
     |                       |
     |                    512x512
     |
     +---------------- Cr: 1024x1024
                             |
                          2x2 avg
                             |
                          512x512
```

Every Y/Cb/Cr sample remains 8 bits.

The four Y streams are NOT 4-bit values. They are four consecutive pieces of
the complete 8-bit Y array.

## Sizes

For 1024x1024:

- Y = 1,048,576 samples x 8 bits
- Y1 = 262,144 samples x 8 bits
- Y2 = 262,144 samples x 8 bits
- Y3 = 262,144 samples x 8 bits
- Y4 = 262,144 samples x 8 bits
- Cb = 512x512 = 262,144 samples x 8 bits
- Cr = 512x512 = 262,144 samples x 8 bits

## Install

```bash
pip install -r requirements.txt
```

## Generate sample + encode

```bash
python main.py --generate_sample
```

or:

```bash
python main.py --input your_1024x1024_image.png
```

The input MUST be exactly 1024x1024.

## Reconstruct from JSON

```bash
python reconstruct.py
```

Or:

```bash
python reconstruct.py \
    --json output/ycbcr_bitstreams.json \
    --original sample_1024x1024.png \
    --output output/reconstructed_from_json.png
```

## Run tests

```bash
python -m unittest test_ycbcr.py -v
```

## Output

The encoder creates:

```text
output/
    ycbcr_bitstreams.json
    Y_full.png
    Y_part1.png
    Y_part2.png
    Y_part3.png
    Y_part4.png
    Cb_downsampled.png
    Cr_downsampled.png
    reconstructed_rgb.png
```

The JSON contains:

```text
Y_part1_bits
Y_part2_bits
Y_part3_bits
Y_part4_bits
Cb_bits
Cr_bits
```

The decoder concatenates Y1+Y2+Y3+Y4 to recover the complete Y channel,
upsamples Cb/Cr, converts back to RGB, and reports MSE and PSNR.


## Organized output folders

After running `python main.py --input images/your_image.jpg`, the output is organized as:

```text
output/
├── 1_converted/
│   ├── Cb_downsampled.png
│   ├── Cr_downsampled.png
│   ├── Y_part1.png
│   ├── Y_part2.png
│   ├── Y_part3.png
│   └── Y_part4.png
├── 2_upscaled_put_together/
│   ├── Y_full.png
│   └── reconstructed_rgb.png
├── 3_comparison/
│   ├── original.png
│   ├── reconstructed.png
│   ├── absolute_difference.png
│   ├── comparison_side_by_side.png
│   └── quality_metrics.txt
└── ycbcr_bitstreams.json
```

`1_converted` contains the Y chunks and downsampled Cb/Cr. `2_upscaled_put_together` contains the full Y channel and the reconstructed RGB image. `3_comparison` contains the original/reconstructed comparison, an amplified absolute-difference image, and MSE/PSNR. `ycbcr_bitstreams.json` sits directly inside `output/`, alongside the three folders, and contains the six JSON bitstreams.
