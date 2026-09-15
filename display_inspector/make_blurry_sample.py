#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

root = Path(__file__).resolve().parent / "samples"
src = Image.open(root / "sample_hanging_messy.png").convert("RGB")
dark = ImageEnhance.Brightness(src).enhance(0.18)
blur = dark.filter(ImageFilter.GaussianBlur(radius=14))
out = root / "sample_blurry_dark.png"
blur.save(out)
print("wrote", out, blur.size)
