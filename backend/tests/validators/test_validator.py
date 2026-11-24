from app.models.universal_core import OLTConfig, VLAN
from app.validators.engine import validate_config


def test_vlan_range_error():
    issues = validate_config(OLTConfig(vendor="fiberhome", vlans=[VLAN(vlan_id=5000)]))
    assert any(i.code == "VLAN_RANGE" and i.severity == "ERROR" for i in issues)
