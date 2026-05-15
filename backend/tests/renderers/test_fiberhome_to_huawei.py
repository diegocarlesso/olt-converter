from app.parsers.fiberhome.parser import FiberhomeParser
from app.renderers.huawei.fiberhome_to_huawei import render_fiberhome_to_huawei


def test_render_contains_service_port():
    text = open("backend/tests/fixtures/fiberhome/small.cfg", encoding="utf-8").read()
    config = FiberhomeParser().parse(text)
    rendered = render_fiberhome_to_huawei(config)
    assert "service-port 1 vlan 100" in rendered
