from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from display_inspect.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_rules_cover_required_categories():
    r = client.get("/api/inspect/rules")
    assert r.status_code == 200
    data = r.json()
    cats = {item["category"] for item in data["rules"]}
    assert cats == {"照片有效性", "挂装", "叠装", "模特", "鞋包配件", "价签", "清洁与安全"}
    assert "高" in data["severity"]


def test_status_endpoint():
    r = client.get("/api/inspect/status")
    assert r.status_code == 200
    body = r.json()
    assert "llm_configured" in body
    assert "max_images" in body


def test_inspect_rejects_without_images():
    r = client.post("/api/inspect", data={"store_name": "测试店"})
    assert r.status_code in (400, 422)


def test_dark_photo_inspects_without_llm(tmp_path, monkeypatch):
    from display_inspect import store as inspect_store

    monkeypatch.setattr(inspect_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(inspect_store, "DB_PATH", tmp_path / "t.db")
    buf = BytesIO()
    Image.new("RGB", (200, 150), (3, 3, 3)).save(buf, format="JPEG")
    buf.seek(0)
    r = client.post(
        "/api/inspect",
        files={"files": ("dark.jpg", buf, "image/jpeg")},
        data={"store_name": "暗光门店"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["overall"] == "无法判断"
    hang = next(f for f in body["findings"] if f["category"] == "挂装")
    assert hang["compliant"] == "无法判断"
    assert "无法判断" in hang["issue"]
    photo = next(f for f in body["findings"] if f["category"] == "照片有效性")
    assert photo["compliant"] == "不合规"


def test_clear_photo_requires_api_key(monkeypatch):
    monkeypatch.setattr("display_inspect.agent.llm_configured", lambda: False)
    img = Image.new("RGB", (200, 150), (210, 210, 210))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for x in range(0, 200, 6):
        draw.line((x, 0, x, 150), fill=(10, 10, 10), width=2)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    r = client.post(
        "/api/inspect",
        files={"files": ("ok.jpg", buf, "image/jpeg")},
        data={"store_name": "测试店"},
    )
    assert r.status_code == 503
