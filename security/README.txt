# XOR security stage

main.py reads ../imageprocessing/output/ycbcr_bitstreams.json and writes
encrypted_ycbcr_bitstreams.json in this security folder.

Change XOR_KEY in main.py (0..255).

All six streams are encrypted byte-by-byte:
Y_part1_bits, Y_part2_bits, Y_part3_bits, Y_part4_bits, Cb_bits, Cr_bits.

decode.py is used as:
python decode.py path\to\encrypted_ycbcr_bitstreams.json

It writes decrypted_ycbcr_bitstreams.json beside the input.
