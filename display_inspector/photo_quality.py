from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from display_inspector.schema import PhotoQuality

# Tuned on bundled samples: sharp store photos sit well above 80;
# Gaussian-blurred / darkened shots drop below 40.
BLUR_THRESHOLD = 55.0
DARK_THRESHOLD = 38.0
BRIGHT_THRESHOLD = 235.0
MIN_SIDE = 160


def _to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def assess_photo(image: Image.Image) -> PhotoQuality:
    width, height = image.size
    too_small = min(width, height) < MIN_SIDE

    bgr = _to_bgr(image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    blurry = laplacian_var < BLUR_THRESHOLD
    too_dark = brightness < DARK_THRESHOLD
    overexposed = brightness > BRIGHT_THRESHOLD and contrast < 18

    issues: list[str] = []
    if too_small:
        issues.append("分辨率过低")
    if blurry:
        issues.append("照片模糊")
    if too_dark:
        issues.append("照片过暗")
    if overexposed:
        issues.append("照片过曝、细节不足")

    usable = not (too_small or blurry or too_dark or overexposed)
    if usable:
        note = "画面亮度与清晰度满足检查条件，可继续按规则核验可见陈列。"
    else:
        note = "照片有效性不足：" + "、".join(issues) + "。相关检查项输出「无法判断」，不推测整店情况。"

    return PhotoQuality(
        usable=usable,
        blurry=blurry,
        too_dark=too_dark,
        overexposed=overexposed,
        too_small=too_small,
        laplacian_var=round(laplacian_var, 2),
        brightness=round(brightness, 2),
        issues=issues,
        note=note,
    )
