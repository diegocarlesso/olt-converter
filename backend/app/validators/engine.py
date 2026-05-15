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
    for vlan in config.vlans:
        if vlan.vlan_id < 1 or vlan.vlan_id > 4094:
            issues.append(ValidationIssue("ERROR", "VLAN_RANGE", f"VLAN inválida: {vlan.vlan_id}"))
    if not config.pons:
        issues.append(ValidationIssue("WARNING", "NO_PON", "Nenhuma PON encontrada"))
    if not config.service_bindings:
        issues.append(ValidationIssue("INFO", "NO_SERVICE_BINDING", "Nenhum service binding encontrado"))
    for onu in config.onus:
        if onu.serial_number is None:
            issues.append(ValidationIssue("UNSUPPORTED", "ONU_NO_SN", "ONU sem serial pode ser incompatível"))
    return issues
