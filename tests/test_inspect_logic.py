from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter

from display_inspect.photo_quality import all_photos_unusable, assess_photo
from display_inspect.postprocess import build_report
from display_inspect.schemas import PhotoQuality


def _jpeg(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_dark_photo_flagged():
    img = Image.new("RGB", (400, 300), (4, 4, 4))
    q = assess_photo(_jpeg(img), "dark.jpg")
    assert q.too_dark
    assert "过暗" in q.issues


def test_blurry_photo_flagged():
    img = Image.new("RGB", (400, 300), (180, 180, 180))
    draw = ImageDraw.Draw(img)
    draw.rectangle((20, 20, 80, 80), fill=(20, 20, 20))
    img = img.filter(ImageFilter.GaussianBlur(radius=18))
    q = assess_photo(_jpeg(img), "blur.jpg")
    assert q.blurry
    assert "模糊" in q.issues


def test_sharp_bright_photo_ok():
    img = Image.new("RGB", (400, 300), (210, 210, 210))
    draw = ImageDraw.Draw(img)
    for x in range(0, 400, 8):
        draw.line((x, 0, x, 300), fill=(10, 10, 10), width=2)
    q = assess_photo(_jpeg(img), "ok.jpg")
    assert not q.too_dark
    assert not q.blurry
    assert q.issues == []


def test_all_photos_unusable():
    bad = PhotoQuality(too_dark=True, issues=["过暗"])
    assert all_photos_unusable([bad])
    assert not all_photos_unusable([PhotoQuality(too_dark=False, blurry=False)])


def test_unusable_photo_forces_unclear_on_other_categories():
    qualities = [
        PhotoQuality(filename="a.jpg", too_dark=True, issues=["过暗"], notes="过暗"),
    ]
    raw = {
        "overall": {"compliant": "合规", "summary": "整店很好"},
        "findings": [
            {
                "category": "挂装",
                "compliant": "合规",
                "issue": "衣架整齐",
                "standard": "x",
                "region": "左侧",
                "severity": "低",
                "suggestion": "保持",
                "visible_in_photo": True,
            }
        ],
    }
    report = build_report(
        inspection_id="t1",
        created_at="2026-09-15 12:00:00",
        raw=raw,
        qualities=qualities,
        image_count=1,
    )
    assert report.overall == "无法判断"
    hang = next(f for f in report.findings if f.category == "挂装")
    assert hang.compliant == "无法判断"
    assert "无法判断" in hang.issue
    photo = next(f for f in report.findings if f.category == "照片有效性")
    assert photo.compliant == "不合规"


def test_fallen_goods_is_high_severity():
    raw = {
        "overall": {"compliant": "不合规", "summary": "有商品落地"},
        "findings": [
            {
                "category": "叠装",
                "compliant": "不合规",
                "issue": "中岛有商品落地",
                "standard": "",
                "region": "中岛下层",
                "severity": "低",
                "suggestion": "立即拣起",
                "visible_in_photo": True,
            }
        ],
    }
    report = build_report(
        inspection_id="t2",
        created_at="2026-09-15 12:00:00",
        raw=raw,
        qualities=[PhotoQuality(filename="ok.jpg")],
        image_count=1,
    )
    fold = next(f for f in report.findings if f.category == "叠装")
    assert fold.severity == "高"
    assert report.overall == "不合规"


def test_missing_categories_become_unclear():
    report = build_report(
        inspection_id="t3",
        created_at="2026-09-15 12:00:00",
        raw={"findings": []},
        qualities=[PhotoQuality(filename="ok.jpg")],
        image_count=1,
    )
    assert len(report.findings) == 7
    assert all(f.standard for f in report.findings)
    assert "无法判断" in report.summary


def test_price_tag_unreadable_wording():
    raw = {
        "findings": [
            {
                "category": "价签",
                "compliant": "不合规",
                "issue": "价签文字看不清",
                "standard": "",
                "region": "右侧层板",
                "severity": "中",
                "suggestion": "重拍",
                "visible_in_photo": True,
            }
        ]
    }
    report = build_report(
        inspection_id="t4",
        created_at="2026-09-15 12:00:00",
        raw=raw,
        qualities=[PhotoQuality(filename="ok.jpg")],
        image_count=1,
    )
    tag = next(f for f in report.findings if f.category == "价签")
    assert "内容无法判断" in tag.issue
    assert tag.standard == "每个陈列组有价签；价签直立、正向、无遮挡；看不清文字时仅能判断「内容无法判断」。"
