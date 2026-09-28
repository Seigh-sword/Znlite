#!/usr/bin/env python3
"""Rebuild the original Znlite boot backdrop (Pillow + DejaVu Sans required).

This is decorative art only; console glyphs come from the signed fonts-dejavu-core
package. Keep the lower part quiet so both BIOS and UEFI menus remain readable.
"""
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
image = Image.new("RGB", (640, 480))
pixels = image.load()
for y in range(480):
    for x in range(640):
        glow = math.exp(-((x - 510) ** 2 / 44000 + (y - 35) ** 2 / 10000))
        pixels[x, y] = (int(8 + 4 * glow), int(15 + 26 * glow), int(24 + 34 * glow))
draw = ImageDraw.Draw(image)
font_dir = Path("/usr/share/fonts/truetype/dejavu")
title = ImageFont.truetype(str(font_dir / "DejaVuSansMono.ttf"), 34)
small = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), 12)
draw.text((40, 32), "Z N L I T E", font=title, fill=(105, 235, 232))
draw.text((43, 79), "A U R O R A   /   SMALL SYSTEM. BRIGHT IDEAS.", font=small, fill=(155, 184, 198))
draw.line((40, 114, 600, 114), fill=(38, 95, 110), width=1)
draw.text((43, 442), "VECTOR BY DEFAULT. RASTER WHEN YOU NEED IT.", font=small, fill=(94, 136, 155))
for kind in ("syslinux_common", "grub-pc"):
    image.save(ROOT / "live-build/config/bootloaders" / kind / "splash.png", optimize=True)
