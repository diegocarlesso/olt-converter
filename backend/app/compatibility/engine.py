from __future__ import annotations

from dataclasses import dataclass

from app.models.universal_core import OLTConfig

FEATURE_MATRIX = {
    "multicast_mode_advanced": {"fiberhome": True, "huawei": True, "zte": False, "datacom": False},
    "qos_scheduler_strict": {"fiberhome": True, "huawei": True, "zte": True, "datacom": False},
    "vlan_translation": {"fiberhome": True, "huawei": True, "zte": True, "datacom": True},
    "wan_service_pppoe": {"fiberhome": True, "huawei": True, "zte": False, "datacom": False},
    "gem_tcont_mapping": {"fiberhome": True, "huawei": True, "zte": True, "datacom": True},
}


@dataclass
class LossyConversion:
    feature: str
    source_vendor: str
    target_vendor: str
    severity: str
    explanation: str


def analyze_compatibility(config: OLTConfig, target_vendor: str) -> list[LossyConversion]:
    out: list[LossyConversion] = []
    src = config.vendor

    if config.multicast_profiles and not FEATURE_MATRIX["multicast_mode_advanced"].get(target_vendor, False):
        out.append(LossyConversion("multicast_gem_mapping", src, target_vendor, "LOSSY_CONVERSION", "Target vendor lacks equivalent GEM multicast abstraction"))
    if config.scheduler_profiles and not FEATURE_MATRIX["qos_scheduler_strict"].get(target_vendor, False):
        out.append(LossyConversion("qos_scheduler", src, target_vendor, "UNSUPPORTED", "Target vendor lacks scheduler semantics"))
    if config.pppoe_services and not FEATURE_MATRIX["wan_service_pppoe"].get(target_vendor, False):
        out.append(LossyConversion("pppoe_service", src, target_vendor, "UNSUPPORTED", "Target vendor lacks PPPoE WAN service"))
    for onu in config.onus:
        tconts = {t.tcont_id for t in onu.tconts}
        for gem in onu.gem_ports:
            if gem.tcont_id not in tconts:
                out.append(LossyConversion("gem_tcont_mapping", src, target_vendor, "LOSSY_CONVERSION", "GEM/TCONT equivalent missing or invalid"))
    return out
