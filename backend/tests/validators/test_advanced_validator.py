from app.models.universal_core import OLTConfig, ONU, TCONT, GEMPort
from app.validators.engine import validate_config


def test_invalid_dba_and_missing_tcont_detected():
    onu = ONU(pon_ref="pon-1/1", onu_id=1, tconts=[TCONT(tcont_id=1, dba_profile="missing")], gem_ports=[GEMPort(gem_id=10, tcont_id=99)])
    issues = validate_config(OLTConfig(vendor="fiberhome", onus=[onu]))
    codes = {i.code for i in issues}
    assert "INVALID_DBA_REFERENCE" in codes
    assert "MISSING_TCONT_BINDING" in codes
