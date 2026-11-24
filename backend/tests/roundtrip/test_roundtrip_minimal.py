from app.parsers.fiberhome.parser import FiberhomeParser
from app.renderers.huawei.fiberhome_to_huawei import render_fiberhome_to_huawei


def test_roundtrip_semantic_baseline():
    text = open("backend/tests/fixtures/fiberhome/small.cfg", encoding="utf-8").read()
    src = FiberhomeParser().parse(text).config
    rendered = render_fiberhome_to_huawei(src)
    assert "vlan 100" in rendered
    assert src.service_bindings[0].onu_id == 1
