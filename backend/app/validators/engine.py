from __future__ import annotations

from dataclasses import dataclass

from app.models.universal_core import OLTConfig


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str


def validate_config(config: OLTConfig) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    dba_names = {d.name for d in config.dba_profiles}
    for vlan in config.vlans:
        if vlan.vlan_id < 1 or vlan.vlan_id > 4094:
            issues.append(ValidationIssue("ERROR", "VLAN_RANGE", f"VLAN inválida: {vlan.vlan_id}"))
    seen_mapping: set[tuple[int, int, str]] = set()

    for onu in config.onus:
        tcont_ids = {t.tcont_id for t in onu.tconts}
        for t in onu.tconts:
            if t.dba_profile not in dba_names:
                issues.append(ValidationIssue("ERROR", "INVALID_DBA_REFERENCE", f"TCONT {t.tcont_id} referencia DBA inexistente {t.dba_profile}"))
        for gem in onu.gem_ports:
            if gem.tcont_id not in tcont_ids:
                issues.append(ValidationIssue("ERROR", "MISSING_TCONT_BINDING", f"GEM {gem.gem_id} sem TCONT válido"))
        if onu.tconts and not onu.gem_ports:
            issues.append(ValidationIssue("WARNING", "ORPHAN_TCONT", "ONU possui TCONT sem GEM"))

    uplinks = {u.name for u in config.uplinks}
    for b in config.service_bindings:
        key = (b.customer_vlan, b.service_vlan, b.uplink)
        if key in seen_mapping:
            issues.append(ValidationIssue("WARNING", "DUPLICATED_VLAN_MAPPING", f"Mapping duplicado cvlan/svlan/uplink {key}"))
        seen_mapping.add(key)
        if b.uplink not in uplinks:
            issues.append(ValidationIssue("UNSUPPORTED", "UNKNOWN_UPLINK", f"Uplink {b.uplink} não existe"))

    return issues
