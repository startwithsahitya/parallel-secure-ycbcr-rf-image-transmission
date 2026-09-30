"""
Generate a deterministic 1024x1024 RGB test image.

The image contains:
    - sky gradient
    - sun
    - mountains
    - snow
    - hills
    - meadow
    - barn
    - fence
    - eight color bars

This is intended to exercise both luminance and chroma behavior.
"""

from PIL import Image, ImageDraw


def generate_test_image(
    output_path: str = "sample_1024x1024.png",
    width: int = 1024,
    height: int = 1024,
) -> str:
    if width != 1024 or height != 1024:
        raise ValueError("The sample image must be exactly 1024x1024.")

    image = Image.new("RGB", (width, height), color=(135, 206, 235))
    draw = ImageDraw.Draw(image)

    # 1. Sky gradient
    for y in range(int(height * 0.65)):
        ratio = y / (height * 0.65)
        r = int(70 * (1 - ratio) + 180 * ratio)
        g = int(120 * (1 - ratio) + 215 * ratio)
        b = int(220 * (1 - ratio) + 245 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Sun and glow
    sun_center = (int(width * 0.75), int(height * 0.22))
    sun_radius = int(width * 0.08)

    for r in range(sun_radius * 2, sun_radius, -2):
        alpha_ratio = (sun_radius * 2 - r) / sun_radius
        glow_r = 255
        glow_g = int(240 * alpha_ratio + 180 * (1 - alpha_ratio))
        glow_b = int(100 * alpha_ratio + 220 * (1 - alpha_ratio))

        draw.ellipse(
            [
                sun_center[0] - r,
                sun_center[1] - r,
                sun_center[0] + r,
                sun_center[1] + r,
            ],
            outline=(glow_r, glow_g, glow_b),
        )

    draw.ellipse(
        [
            sun_center[0] - sun_radius,
            sun_center[1] - sun_radius,
            sun_center[0] + sun_radius,
            sun_center[1] + sun_radius,
        ],
        fill=(255, 245, 180),
        outline=(255, 220, 100),
    )

    # 3. Mountains
    mountain_points = [
        (0, int(height * 0.55)),
        (int(width * 0.15), int(height * 0.30)),
        (int(width * 0.32), int(height * 0.45)),
        (int(width * 0.50), int(height * 0.22)),
        (int(width * 0.68), int(height * 0.42)),
        (int(width * 0.85), int(height * 0.28)),
        (width, int(height * 0.50)),
        (width, int(height * 0.65)),
        (0, int(height * 0.65)),
    ]
    draw.polygon(mountain_points, fill=(90, 100, 125))

    snow_peaks = [
        [
            (int(width * 0.15), int(height * 0.30)),
            (int(width * 0.10), int(height * 0.38)),
            (int(width * 0.20), int(height * 0.38)),
        ],
        [
            (int(width * 0.50), int(height * 0.22)),
            (int(width * 0.42), int(height * 0.34)),
            (int(width * 0.58), int(height * 0.34)),
        ],
        [
            (int(width * 0.85), int(height * 0.28)),
            (int(width * 0.78), int(height * 0.38)),
            (int(width * 0.92), int(height * 0.38)),
        ],
    ]

    for peak in snow_peaks:
        draw.polygon(peak, fill=(240, 245, 255))

    # Midground hills
    hill_points = [
        (0, int(height * 0.60)),
        (int(width * 0.30), int(height * 0.52)),
        (int(width * 0.65), int(height * 0.58)),
        (width, int(height * 0.52)),
        (width, int(height * 0.75)),
        (0, int(height * 0.75)),
    ]
    draw.polygon(hill_points, fill=(60, 120, 50))

    # 4. Foreground meadow
    for y in range(int(height * 0.60), int(height * 0.90)):
        ratio = (y - height * 0.60) / (height * 0.30)
        r = int(90 * (1 - ratio) + 120 * ratio)
        g = int(140 * (1 - ratio) + 175 * ratio)
        b = int(45 * (1 - ratio) + 30 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 5. Barn
    barn_x1 = int(width * 0.18)
    barn_y1 = int(height * 0.60)
    barn_w = int(width * 0.32)
    barn_h = int(height * 0.20)
    barn_x2 = barn_x1 + barn_w
    barn_y2 = barn_y1 + barn_h

    roof_peak = (
        barn_x1 + barn_w // 2,
        barn_y1 - int(height * 0.08),
    )

    draw.polygon(
        [
            roof_peak,
            (barn_x1, barn_y1),
            (barn_x2, barn_y1),
        ],
        fill=(130, 45, 30),
        outline=(80, 25, 15),
    )

    draw.rectangle(
        [barn_x1, barn_y1, barn_x2, barn_y2],
        fill=(160, 75, 45),
        outline=(100, 40, 20),
        width=3,
    )

    door_w = int(barn_w * 0.3)
    door_h = int(barn_h * 0.65)
    door_x1 = barn_x1 + (barn_w - door_w) // 2
    door_y1 = barn_y2 - door_h

    draw.rectangle(
        [door_x1, door_y1, door_x1 + door_w, barn_y2],
        fill=(60, 30, 15),
        outline=(40, 20, 10),
        width=2,
    )

    draw.line(
        [(door_x1, door_y1), (door_x1 + door_w, barn_y2)],
        fill=(180, 100, 60),
        width=2,
    )
    draw.line(
        [(door_x1, barn_y2), (door_x1 + door_w, door_y1)],
        fill=(180, 100, 60),
        width=2,
    )

    # Fence
    fence_y = barn_y2 - int(height * 0.02)

    for fx in range(
        barn_x2,
        int(width * 0.85),
        int(width * 0.04),
    ):
        draw.line(
            [
                (fx, fence_y - int(height * 0.03)),
                (fx, fence_y + int(height * 0.03)),
            ],
            fill=(170, 135, 95),
            width=3,
        )

    draw.line(
        [
            (barn_x2, fence_y - int(height * 0.015)),
            (int(width * 0.85), fence_y - int(height * 0.015)),
        ],
        fill=(150, 115, 75),
        width=3,
    )

    draw.line(
        [
            (barn_x2, fence_y + int(height * 0.015)),
            (int(width * 0.85), fence_y + int(height * 0.015)),
        ],
        fill=(150, 115, 75),
        width=3,
    )

    # 6. Color bars
    strip_y1 = int(height * 0.90)

    colors = [
        (255, 255, 255),
        (255, 255, 0),
        (0, 255, 255),
        (0, 255, 0),
        (255, 0, 255),
        (255, 0, 0),
        (0, 0, 255),
        (0, 0, 0),
    ]

    bar_w = width // len(colors)

    for i, color in enumerate(colors):
        x1 = i * bar_w
        x2 = (i + 1) * bar_w if i < len(colors) - 1 else width
        draw.rectangle(
            [x1, strip_y1, x2, height],
            fill=color,
        )

    image.save(output_path)
    print(f"[+] Generated {width}x{height}: {output_path}")

    return output_path


if __name__ == "__main__":
    generate_test_image()
