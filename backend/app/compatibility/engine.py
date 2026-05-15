from __future__ import annotations

from dataclasses import dataclass

from app.models.universal_core import OLTConfig

FEATURE_MATRIX = {
    "wan_profile": {"fiberhome": True, "huawei": True, "zte": True, "datacom": False},
    "service_binding_gem": {"fiberhome": True, "huawei": True, "zte": True, "datacom": True},
}


@dataclass
class CompatibilityIssue:
    severity: str
    feature: str
    message: str


def analyze_compatibility(config: OLTConfig, target_vendor: str) -> list[CompatibilityIssue]:
    issues: list[CompatibilityIssue] = []
    if config.wan_profiles and not FEATURE_MATRIX["wan_profile"].get(target_vendor, False):
        issues.append(CompatibilityIssue("UNSUPPORTED", "wan_profile", f"{target_vendor} não suporta wan_profile"))
    for binding in config.service_bindings:
        if binding.gem_id is None:
            issues.append(CompatibilityIssue("LOSSY_CONVERSION", "service_binding_gem", "binding sem GEM explícito"))
    return issues
