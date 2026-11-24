from app.compatibility.engine import analyze_compatibility
from app.models.universal_core import OLTConfig, MulticastProfile


def test_lossy_multicast_detection():
    cfg = OLTConfig(vendor="fiberhome", multicast_profiles=[MulticastProfile(name="m1")])
    issues = analyze_compatibility(cfg, "zte")
    assert any(i.feature == "multicast_gem_mapping" for i in issues)
