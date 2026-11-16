"""Generate the WeSnap camera icon as a multi-size .ico."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "wesnap" / "wesnap.ico"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def build() -> Image.Image:
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 8, 248, 248), radius=52, fill=(43, 43, 43, 255))
    draw.rounded_rectangle((92, 58, 164, 94), radius=10,
                           outline=(255, 255, 255, 255), width=10)
    draw.rounded_rectangle((46, 84, 210, 198), radius=22,
                           outline=(255, 255, 255, 255), width=12)
    draw.ellipse((86, 106, 170, 190), outline=(0, 160, 255, 255), width=14)
    draw.ellipse((176, 100, 196, 120), fill=(255, 255, 255, 255))
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    build().save(OUT, format="ICO", sizes=SIZES)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
