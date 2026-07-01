from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "app_icon.ico"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

images = []
for size in (16, 24, 32, 48, 64, 128, 256):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(1, size // 16)
    draw.rounded_rectangle(
        (margin, margin, size - margin - 1, size - margin - 1),
        radius=max(2, size // 5),
        fill="#2a2b30",
        outline="#6f7df6",
        width=max(1, size // 18),
    )
    shield = [
        (size * 0.50, size * 0.18),
        (size * 0.76, size * 0.29),
        (size * 0.71, size * 0.65),
        (size * 0.50, size * 0.82),
        (size * 0.29, size * 0.65),
        (size * 0.24, size * 0.29),
    ]
    draw.polygon(shield, fill="#6f7df6")
    stroke = max(1, size // 16)
    draw.line(
        [(size * 0.36, size * 0.50), (size * 0.46, size * 0.61), (size * 0.67, size * 0.39)],
        fill="#ffffff",
        width=stroke,
        joint="curve",
    )
    images.append(image)

images[-1].save(OUTPUT, format="ICO", append_images=images[:-1], sizes=[(i.width, i.height) for i in images])
print(OUTPUT)
