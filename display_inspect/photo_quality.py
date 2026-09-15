"""本地照片质量预检：过暗/过曝/模糊。遮挡与局部未入镜仍由视觉模型判定。"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFilter, ImageOps, ImageStat

from display_inspect.schemas import PhotoQuality

DARK_THRESHOLD = 38
BRIGHT_THRESHOLD = 245
BLUR_EDGE_THRESHOLD = 8.5


def load_rgb(image_bytes: bytes) -> Image.Image:
    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    return img


def encode_jpeg(img: Image.Image, max_side: int = 1600, quality: int = 85) -> bytes:
    out = img
    w, h = out.size
    longest = max(w, h)
    if longest > max_side:
        scale = max_side / float(longest)
        out = out.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    if out.mode != "RGB":
        out = out.convert("RGB")
    buf = BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def assess_photo(image_bytes: bytes, filename: str = "") -> PhotoQuality:
    img = load_rgb(image_bytes)
    gray = img.convert("L")
    # 缩小后再测，避免超大图过慢
    probe = gray.copy()
    probe.thumbnail((640, 640))
    brightness = float(ImageStat.Stat(probe).mean[0])
    edges = probe.filter(ImageFilter.FIND_EDGES)
    edge_strength = float(ImageStat.Stat(edges).mean[0])

    too_dark = brightness < DARK_THRESHOLD
    too_bright = brightness > BRIGHT_THRESHOLD
    blurry = edge_strength < BLUR_EDGE_THRESHOLD

    issues: list[str] = []
    if too_dark:
        issues.append("过暗")
    if too_bright:
        issues.append("过曝")
    if blurry:
        issues.append("模糊")

    notes = "；".join(issues) if issues else "本地预检未发现全局过暗/模糊"
    return PhotoQuality(
        filename=filename,
        width=img.width,
        height=img.height,
        mean_brightness=round(brightness, 2),
        edge_strength=round(edge_strength, 2),
        too_dark=too_dark,
        too_bright=too_bright,
        blurry=blurry,
        issues=issues,
        notes=notes,
    )


def all_photos_unusable(qualities: list[PhotoQuality]) -> bool:
    if not qualities:
        return True
    return all(q.too_dark or q.blurry for q in qualities)
