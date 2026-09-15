from display_inspect.vision_client import _extract_json


def test_extract_json_from_fence():
    data = _extract_json('```json\n{"overall": {"compliant": "无法判断"}}\n```')
    assert data["overall"]["compliant"] == "无法判断"


def test_extract_json_embedded():
    data = _extract_json('说明如下 {"a": 1, "b": [2]} 结束')
    assert data["a"] == 1


def test_extract_json_repairs_truncated_object():
    data = _extract_json('{"overall": {"compliant": "无法判断", "summary": "x"')
    assert data["overall"]["compliant"] == "无法判断"
