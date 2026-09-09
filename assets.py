"""Prepare the app/exe assets from the hand-made logos.

  Rey detailed.png  ->  logo.png   (shown in the app header + README)
  Rey Flat.png      ->  icon.ico   (the app / .exe icon)

Run before packaging:  py -3 assets.py
Only needs Pillow.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DETAILED = os.path.join(HERE, "Rey detailed.png")
FLAT = os.path.join(HERE, "Rey Flat.png")

SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48),
         (64, 64), (128, 128), (256, 256)]


def main():
    # header / README logo (detailed)
    img = Image.open(DETAILED)
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGBA")
    img.save(os.path.join(HERE, "logo.png"))
    print("logo.png      <- Rey detailed.png")

    # app icon (flat) -> multi-size .ico
    icon = Image.open(FLAT).convert("RGBA")
    icon.save(os.path.join(HERE, "icon.ico"), format="ICO", sizes=SIZES)
    print("icon.ico      <- Rey Flat.png (%d sizes)" % len(SIZES))


if __name__ == "__main__":
    main()
