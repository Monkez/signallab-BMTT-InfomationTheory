"""Create the Windows icon used by PyInstaller from the SignalLab mark."""

from pathlib import Path

from PIL import Image, ImageDraw


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (31, 41, 55, 255))
    draw = ImageDraw.Draw(image)
    radius = max(2, size // 5)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=(31, 41, 55, 255))
    points = [
        (size * 0.15, size * 0.53),
        (size * 0.31, size * 0.53),
        (size * 0.39, size * 0.28),
        (size * 0.55, size * 0.75),
        (size * 0.65, size * 0.42),
        (size * 0.74, size * 0.58),
        (size * 0.87, size * 0.58),
    ]
    width = max(2, size // 12)
    draw.line(points, fill=(219, 234, 254, 255), width=width, joint="curve")
    dot = max(2, size // 14)
    for x, y in (points[2], points[4]):
        draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=(96, 165, 250, 255))
    return image


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "assets" / "app.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    draw_icon(256).save(output, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Created {output}")


if __name__ == "__main__":
    main()
