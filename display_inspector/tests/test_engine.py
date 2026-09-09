from display_inspector.engine import build_report
from display_inspector.photo_quality import assess_photo
from display_inspector.rules import iter_rules, load_rules
from display_inspector.schema import (
    AccessoriesObs,
    CleanlinessObs,
    FoldedObs,
    HangingObs,
    MannequinObs,
    Observations,
    PhotoQuality,
    PriceTagObs,
)
from display_inspector.vision import VisionNotConfigured, parse_tristate, resolve_backend, skip_local_vlm
from PIL import Image, ImageDraw, ImageFilter


def _quality_ok() -> PhotoQuality:
    return PhotoQuality(usable=True, note="ok", laplacian_var=200, brightness=120)


def test_parse_tristate():
    assert parse_tristate("YES.") is True
    assert parse_tristate("No") is False
    assert parse_tristate("UNSURE") is None
    assert parse_tristate("not sure") is None


def test_rules_unique():
    ids = [r["id"] for r in iter_rules()]
    assert len(ids) == len(set(ids))
    catalog = load_rules()
    assert catalog["photo_validity"]["id"] == "P01"


def test_blurry_photo_all_undetermined():
    img = Image.new("RGB", (640, 480), (8, 8, 8))
    img = img.filter(ImageFilter.GaussianBlur(18))
    quality = assess_photo(img)
    assert quality.usable is False
    report = build_report(
        quality=quality,
        observations=Observations(),
        model_used="test",
        images=["dark.jpg"],
    )
    assert report.overall_status == "无法判断"
    assert report.overall_compliant is None
    assert report.issues == []
    assert all(f.status == "无法判断" for f in report.findings)
    assert any(
        "模糊" in (f.undetermined_reason or "") or "过暗" in (f.undetermined_reason or "")
        for f in report.findings
    )


def test_empty_hangers_maps_to_h05():
    obs = Observations(
        hanging=HangingObs(
            present=True,
            hanger_direction_consistent=True,
            hanger_material_consistent=False,
            hanger_color_consistent=False,
            spacing_even=True,
            clothes_hang_vertically=True,
            grouped_by_category=False,
            color_sequence_continuous=False,
            no_large_empty_hangers=False,
            notes="挂装杆中段大面积空衣架，黑塑与金属衣架混用",
        ),
        folded=FoldedObs(present=False),
        mannequin=MannequinObs(present=False),
        accessories=AccessoriesObs(present=False),
        price_tag=PriceTagObs(present=False, present_for_each_group=False, text_legible=None),
        cleanliness=CleanlinessObs(
            no_clutter=True, aisles_and_safety_clear=True, fixtures_stable=True
        ),
    )
    report = build_report(quality=_quality_ok(), observations=obs, model_used="test", images=["h.jpg"])
    by_id = {f.rule_id: f for f in report.findings}
    assert report.overall_status == "不合规"
    assert by_id["H05"].status == "不合规"
    assert by_id["H05"].severity == "中"
    assert by_id["H01"].status == "不合规"
    assert by_id["H04"].status == "不合规"
    assert by_id["F01"].status == "不适用"
    assert by_id["T01"].status == "不合规"
    assert by_id["T03"].status == "无法判断"
    assert by_id["T03"].undetermined_reason == "内容无法判断"


def test_floor_contact_is_high():
    obs = Observations(
        hanging=HangingObs(present=False),
        folded=FoldedObs(
            present=True,
            fold_width_consistent=True,
            front_edges_aligned=True,
            stack_count_in_range=True,
            max_stack_count=8,
            stack_stable=True,
            not_touching_floor=False,
            not_overhanging_shelf=False,
            notes="下层商品触地并探出层板",
        ),
        mannequin=MannequinObs(present=False),
        accessories=AccessoriesObs(present=False),
        price_tag=PriceTagObs(present=False),
        cleanliness=CleanlinessObs(
            no_clutter=True, aisles_and_safety_clear=True, fixtures_stable=True
        ),
    )
    report = build_report(quality=_quality_ok(), observations=obs, model_used="test", images=["f.jpg"])
    by_id = {f.rule_id: f for f in report.findings}
    assert by_id["F04"].status == "不合规"
    assert by_id["F04"].severity == "高"
    assert by_id["F05"].status == "不合规"
    assert by_id["F02"].status == "不合规"


def test_sharp_image_is_usable():
    img = Image.new("RGB", (640, 480), (220, 220, 220))
    draw = ImageDraw.Draw(img)
    for i in range(0, 640, 8):
        draw.line((i, 0, i, 480), fill=(20, 20, 20))
    quality = assess_photo(img)
    assert quality.usable is True
    assert quality.blurry is False


def test_skip_local_vlm_on_render(monkeypatch):
    monkeypatch.setenv("SKIP_LOCAL_VLM", "1")
    monkeypatch.delenv("VISION_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert skip_local_vlm() is True
    try:
        resolve_backend()
        raise AssertionError("should require API key")
    except VisionNotConfigured:
        pass
