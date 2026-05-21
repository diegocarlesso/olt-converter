from app.parsers.fiberhome.parser import FiberhomeParser


def test_fiberhome_minimal_parse():
    text = open("backend/tests/fixtures/fiberhome/small.cfg", encoding="utf-8").read()
    result = FiberhomeParser().parse(text)
    config = result.config
    assert len(config.vlans) == 1
    assert len(config.pons) == 1
    assert len(config.onus) == 1
    assert len(config.service_bindings) == 1
