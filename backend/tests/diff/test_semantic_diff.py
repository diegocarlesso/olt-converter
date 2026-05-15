from app.diff.semantic import semantic_diff
from app.models.universal_core import OLTConfig, VLAN


def test_semantic_diff_vlan_added_removed():
    a = OLTConfig(vendor="a", vlans=[VLAN(vlan_id=10)])
    b = OLTConfig(vendor="b", vlans=[VLAN(vlan_id=20)])
    d = semantic_diff(a, b)
    assert "vlan:20" in d.added
    assert "vlan:10" in d.removed
