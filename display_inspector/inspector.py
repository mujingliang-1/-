from __future__ import annotations

from io import BytesIO

from PIL import Image

from display_inspector.engine import build_report, merge_reports
from display_inspector.photo_quality import assess_photo
from display_inspector.schema import Observations, Report
from display_inspector.vision import VisionBackend, VisionNotConfigured, resolve_backend


def _open_image(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image.load()
    return image.convert("RGB")


def inspect_image(
    data: bytes,
    filename: str,
    user_note: str = "",
    region_hint: str = "",
    backend: VisionBackend | None = None,
) -> Report:
    image = _open_image(data)
    quality = assess_photo(image)
    if not quality.usable:
        return build_report(
            quality=quality,
            observations=Observations(),
            model_used="photo-quality-gate",
            images=[filename],
        )
    backend = backend or resolve_backend()
    observations = backend.observe(image, user_note=user_note, region_hint=region_hint)
    return build_report(
        quality=quality,
        observations=observations,
        model_used=backend.name,
        images=[filename],
    )


def inspect_images(
    files: list[tuple[str, bytes]],
    user_note: str = "",
    region_hint: str = "",
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> Report:
    backend = None
    reports: list[Report] = []
    for filename, data in files:
        image = _open_image(data)
        quality = assess_photo(image)
        if not quality.usable:
            reports.append(
                build_report(
                    quality=quality,
                    observations=Observations(),
                    model_used="photo-quality-gate",
                    images=[filename],
                )
            )
            continue
        if backend is None:
            try:
                backend = resolve_backend(api_key=api_key, base_url=base_url, model=model)
            except VisionNotConfigured as exc:
                reports.append(
                    build_report(
                        quality=quality,
                        observations=Observations(vision_notes=str(exc)),
                        model_used="vision-not-configured",
                        images=[filename],
                    )
                )
                continue
        try:
            observations = backend.observe(image, user_note=user_note, region_hint=region_hint)
            model_used = backend.name
        except Exception as exc:  # noqa: BLE001
            observations = Observations(
                vision_notes=f"视觉观察失败，相关项无法判断：{exc}",
            )
            model_used = f"{backend.name} (observe-failed)"
        report = build_report(
            quality=quality,
            observations=observations,
            model_used=model_used,
            images=[filename],
        )
        if observations.vision_notes.startswith("视觉观察失败"):
            report.extra["observe_error"] = observations.vision_notes
        reports.append(report)
    if not reports:
        raise ValueError("未收到可解析的图片")
    return merge_reports(reports)
