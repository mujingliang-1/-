from fastapi.testclient import TestClient

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
