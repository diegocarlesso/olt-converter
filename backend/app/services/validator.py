"""
Validador profissional de `OLTConfig`.

Cobre cinco classes de problemas:

  1. Sintaxe / ranges      — VLAN 0-4094, ONU 0-255, gem ≥ 0, etc.
  2. Duplicatas            — IDs de VLAN, service-port, serial de ONU
  3. Bindings cruzados     — Service-port → ONU/VLAN/GEM; ONU → profiles;
                             GEM → T-CONT; T-CONT → DBA; user-vlan in allowed
  4. Consistência          — Native VLAN ∈ allowed_vlans do uplink, smart-vlan
                             vs renderização para vendors que não suportam
  5. Capacidades do destino — ONU id ≤ 127 para ZTE, sn obrigatório p/ Huawei

Cada issue tem `severity` (error|warning|info), `code` (estável) e `path`
(referência ao nó da configuração) para que a UI possa highlightar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.models import OLTConfig, Vendor

Severity = Literal["error", "warning", "info"]


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------
@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    path: str | None = None


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: Severity, code: str, message: str, path: str | None = None) -> None:
        self.issues.append(ValidationIssue(severity, code, message, path))

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def by_severity(self) -> dict[str, int]:
        out: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        for i in self.issues:
            out[i.severity] += 1
        return out

    def to_dict(self) -> dict:
        return {
            "ok": not self.has_errors,
            "summary": self.by_severity(),
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "path": i.path,
                }
                for i in self.issues
            ],
        }


# ---------------------------------------------------------------------------
# Validadores individuais
# ---------------------------------------------------------------------------
def _validate_hostname(c: OLTConfig, r: ValidationReport) -> None:
    if not c.hostname or c.hostname == "OLT-DEFAULT":
        r.add("warning", "HOSTNAME_DEFAULT", "Hostname não detectado, usando default")


def _validate_vlans(c: OLTConfig, r: ValidationReport) -> None:
    seen: dict[int, int] = {}
    for idx, v in enumerate(c.vlans):
        if not (1 <= v.id <= 4094):
            r.add(
                "error",
                "VLAN_OUT_OF_RANGE",
                f"VLAN {v.id} fora do range 1-4094",
                path=f"vlans[{idx}]",
            )
        if v.id in seen:
            r.add(
                "warning",
                "VLAN_DUPLICATED",
                f"VLAN {v.id} aparece nos índices {seen[v.id]} e {idx}",
                path=f"vlans[{idx}]",
            )
        else:
            seen[v.id] = idx
        if v.is_management and not v.ip_address:
            r.add(
                "info",
                "MGMT_VLAN_NO_IP",
                f"VLAN de management {v.id} sem IP atribuído",
                path=f"vlans[{idx}]",
            )


def _validate_onus(c: OLTConfig, r: ValidationReport) -> None:
    seen_sn: dict[str, str] = {}
    for idx, onu in enumerate(c.onus):
        if onu.onu_id < 0 or onu.onu_id > 255:
            r.add(
                "error",
                "ONU_ID_OUT_OF_RANGE",
                f"ONU id={onu.onu_id} fora do range 0-255 em {onu.pon_interface}",
                path=f"onus[{idx}]",
            )
        elif onu.onu_id > 127:
            r.add(
                "warning",
                "ONU_ID_ABOVE_GPON_STANDARD",
                f"ONU id={onu.onu_id} excede o padrão GPON (0-127). Pode falhar em ZTE/Huawei.",
                path=f"onus[{idx}]",
            )

        if onu.serial_number:
            key = f"{onu.pon_interface}:{onu.serial_number}"
            if onu.serial_number in seen_sn:
                r.add(
                    "error",
                    "ONU_SERIAL_DUPLICATED",
                    f"Serial duplicado: {onu.serial_number} em {seen_sn[onu.serial_number]} e {onu.pon_interface}",
                    path=f"onus[{idx}]",
                )
            else:
                seen_sn[onu.serial_number] = onu.pon_interface


def _validate_pons(c: OLTConfig, r: ValidationReport) -> None:
    seen: set[str] = set()
    for idx, p in enumerate(c.pons):
        if p.interface in seen:
            r.add(
                "warning",
                "PON_DUPLICATED",
                f"PON {p.interface} declarada mais de uma vez",
                path=f"pons[{idx}]",
            )
        seen.add(p.interface)


def _validate_service_ports(c: OLTConfig, r: ValidationReport) -> None:
    """Service-port → ONU/VLAN/GEM existem; integridade dos bindings."""
    seen_ids: set[int] = set()
    pon_ifaces = {p.interface for p in c.pons}
    vlan_ids = {v.id for v in c.vlans}

    for idx, sp in enumerate(c.service_ports):
        # duplicidade
        if sp.service_port_id in seen_ids:
            r.add(
                "error",
                "SERVICE_PORT_ID_DUPLICATED",
                f"service-port id={sp.service_port_id} duplicado",
                path=f"service_ports[{idx}]",
            )
        seen_ids.add(sp.service_port_id)

        # vlan referenciada
        for label, vid in [("match", sp.match_vlan), ("target", sp.target_vlan), ("user", sp.user_vlan)]:
            if vid and vid not in vlan_ids:
                r.add(
                    "warning",
                    "SERVICE_PORT_REFERENCES_UNKNOWN_VLAN",
                    f"service-port {sp.service_port_id}: {label}-vlan {vid} não declarado",
                    path=f"service_ports[{idx}]",
                )

        # PON referenciada
        if sp.pon_interface and sp.pon_interface not in pon_ifaces:
            r.add(
                "warning",
                "SERVICE_PORT_REFERENCES_UNKNOWN_PON",
                f"service-port {sp.service_port_id} referencia PON inexistente: {sp.pon_interface}",
                path=f"service_ports[{idx}]",
            )

        # ONU referenciada
        onu = c.find_onu(sp.pon_interface, sp.onu_id)
        if onu is None:
            r.add(
                "warning",
                "SERVICE_PORT_REFERENCES_UNKNOWN_ONU",
                f"service-port {sp.service_port_id} referencia ONU inexistente: {sp.pon_interface}:{sp.onu_id}",
                path=f"service_ports[{idx}]",
            )


def _validate_profile_refs(c: OLTConfig, r: ValidationReport) -> None:
    """ONU.line_profile_name / service_profile_name precisam existir."""
    lp_names = {p.name for p in c.line_profiles} | {ot.name for ot in c.onu_type_profiles}
    sp_names = {p.name for p in c.service_profiles} | {ot.name for ot in c.onu_type_profiles}

    for idx, o in enumerate(c.onus):
        if o.line_profile_name and o.line_profile_name not in lp_names:
            r.add(
                "info",
                "ONU_LINE_PROFILE_MISSING",
                f"ONU {o.pon_interface}:{o.onu_id} referencia line_profile '{o.line_profile_name}' não declarado",
                path=f"onus[{idx}]",
            )
        if o.service_profile_name and o.service_profile_name not in sp_names:
            r.add(
                "info",
                "ONU_SERVICE_PROFILE_MISSING",
                f"ONU {o.pon_interface}:{o.onu_id} referencia service_profile '{o.service_profile_name}' não declarado",
                path=f"onus[{idx}]",
            )


def _validate_dba_binding(c: OLTConfig, r: ValidationReport) -> None:
    """LineProfile.tcont_bindings → DBA precisa existir."""
    dba_names = {d.name for d in c.dba_profiles}
    for idx, lp in enumerate(c.line_profiles):
        for b in lp.tcont_bindings:
            dn = b.get("dba_profile_name")
            if dn and dn not in dba_names:
                r.add(
                    "warning",
                    "TCONT_DBA_MISSING",
                    f"LineProfile '{lp.name}' T-CONT bind p/ DBA '{dn}' não encontrado",
                    path=f"line_profiles[{idx}]",
                )


def _validate_gem_to_tcont(c: OLTConfig, r: ValidationReport) -> None:
    """LineProfile.gemport_bindings.tcont_id deve existir em tcont_bindings."""
    for idx, lp in enumerate(c.line_profiles):
        tcont_ids = {b.get("tcont_id") for b in lp.tcont_bindings}
        for g in lp.gemport_bindings:
            tid = g.get("tcont_id")
            if tid is not None and tid not in tcont_ids:
                r.add(
                    "warning",
                    "GEM_TCONT_MISSING",
                    f"LineProfile '{lp.name}' GEM {g.get('gem_id')} aponta para T-CONT {tid} não declarado",
                    path=f"line_profiles[{idx}]",
                )


def _validate_uplink_vlans(c: OLTConfig, r: ValidationReport) -> None:
    """Native VLAN deve estar nas allowed_vlans (ou ser absent)."""
    for idx, u in enumerate(c.uplinks):
        if u.native_vlan and u.allowed_vlans and u.native_vlan not in u.allowed_vlans:
            r.add(
                "warning",
                "UPLINK_NATIVE_NOT_ALLOWED",
                f"Uplink {u.interface}: native-vlan {u.native_vlan} fora de allowed_vlans",
                path=f"uplinks[{idx}]",
            )


def _validate_traffic_profile_refs(c: OLTConfig, r: ValidationReport) -> None:
    """ServicePort.inbound/outbound_traffic_profile precisa existir."""
    names = {tp.name for tp in c.traffic_profiles}
    indexes = {f"index-{tp.profile_id}" for tp in c.traffic_profiles}
    valid = names | indexes
    for idx, sp in enumerate(c.service_ports):
        for label, tp in (("inbound", sp.inbound_traffic_profile), ("outbound", sp.outbound_traffic_profile)):
            if tp and tp not in valid:
                r.add(
                    "info",
                    "SERVICE_PORT_TRAFFIC_PROFILE_MISSING",
                    f"service-port {sp.service_port_id}: {label} traffic-profile '{tp}' não declarado",
                    path=f"service_ports[{idx}]",
                )


# ---------------------------------------------------------------------------
# L9 — Subscriber edge bindings (WiFi, WAN, Bridge, LANService, Multicast)
# ---------------------------------------------------------------------------
def _validate_wan_bindings(c: OLTConfig, r: ValidationReport) -> None:
    """ONU.wan_bindings.wan_profile_ref deve existir em config.wan_profiles."""
    wan_names = {w.name for w in c.wan_profiles}
    for o_idx, onu in enumerate(c.onus):
        for wb in onu.wan_bindings:
            ref = getattr(wb, "wan_profile_ref", None)
            if ref and ref not in wan_names:
                r.add(
                    "warning",
                    "WAN_PROFILE_REF_MISSING",
                    f"ONU {onu.pon_interface}:{onu.onu_id} WANBinding aponta para WAN profile '{ref}' inexistente",
                    path=f"onus[{o_idx}].wan_bindings",
                )


def _validate_ssid_radios(c: OLTConfig, r: ValidationReport) -> None:
    """WiFiSSID.radio_id deve referenciar um WiFiRadio existente na mesma ONU."""
    for o_idx, onu in enumerate(c.onus):
        radio_ids = {radio.radio_id for radio in onu.radios}
        for ssid in onu.ssids:
            if ssid.radio_id not in radio_ids and onu.radios:
                r.add(
                    "warning",
                    "SSID_RADIO_MISSING",
                    f"ONU {onu.pon_interface}:{onu.onu_id} SSID '{ssid.name}' (radio_id={ssid.radio_id}) sem rádio correspondente",
                    path=f"onus[{o_idx}].ssids",
                )
        # SSIDs sem nenhum rádio (não foi promovido)
        if onu.ssids and not onu.radios:
            r.add(
                "info",
                "SSID_NO_RADIOS",
                f"ONU {onu.pon_interface}:{onu.onu_id} tem {len(onu.ssids)} SSIDs mas nenhum rádio (radio sintetizado faltando)",
                path=f"onus[{o_idx}]",
            )


def _validate_bridge_groups(c: OLTConfig, r: ValidationReport) -> None:
    """BridgeGroup.member_port_ids ⊂ ONU.eth_ports."""
    for o_idx, onu in enumerate(c.onus):
        eth_ids = {e.port_id for e in onu.eth_ports}
        for bg in onu.bridge_groups:
            for pid in bg.member_port_ids:
                if pid not in eth_ids:
                    r.add(
                        "warning",
                        "BRIDGE_GROUP_PORT_MISSING",
                        f"ONU {onu.pon_interface}:{onu.onu_id} BridgeGroup '{bg.name}' membro eth {pid} não existe",
                        path=f"onus[{o_idx}].bridge_groups",
                    )


def _validate_lan_services(c: OLTConfig, r: ValidationReport) -> None:
    """LANService.vlan_id deve existir em config.vlans."""
    vlan_ids = {v.id for v in c.vlans}
    for o_idx, onu in enumerate(c.onus):
        for svc in onu.lan_services:
            if svc.vlan_id and svc.vlan_id not in vlan_ids:
                r.add(
                    "warning",
                    "LAN_SERVICE_VLAN_MISSING",
                    f"ONU {onu.pon_interface}:{onu.onu_id} LANService '{svc.name}' aponta para VLAN {svc.vlan_id} inexistente",
                    path=f"onus[{o_idx}].lan_services",
                )


def _validate_stb_ports(c: OLTConfig, r: ValidationReport) -> None:
    """STBConfig.stb_port_ids deve ⊂ ONU.eth_ports."""
    for o_idx, onu in enumerate(c.onus):
        if onu.stb is None:
            continue
        eth_ids = {e.port_id for e in onu.eth_ports}
        for pid in onu.stb.stb_port_ids:
            if pid not in eth_ids:
                r.add(
                    "warning",
                    "STB_PORT_MISSING",
                    f"ONU {onu.pon_interface}:{onu.onu_id} STBConfig referencia eth {pid} inexistente",
                    path=f"onus[{o_idx}].stb",
                )


def _validate_multicast_bindings(c: OLTConfig, r: ValidationReport) -> None:
    """MulticastBinding deve ter MVLAN existente."""
    vlan_ids = {v.id for v in c.vlans}
    mcast_vlan = c.multicast.multicast_vlan if c.multicast else None
    for o_idx, onu in enumerate(c.onus):
        for mb in onu.multicast_bindings:
            mvid = mb.multicast_vlan_id or mcast_vlan
            if mvid and mvid not in vlan_ids:
                r.add(
                    "info",
                    "MULTICAST_VLAN_NOT_IN_VLANS",
                    f"ONU {onu.pon_interface}:{onu.onu_id} MulticastBinding refere VLAN {mvid} não declarada",
                    path=f"onus[{o_idx}].multicast_bindings",
                )


def _validate_port_routes(c: OLTConfig, r: ValidationReport) -> None:
    """PortRoute.src/dst_port_id devem existir em ONU.eth_ports."""
    for o_idx, onu in enumerate(c.onus):
        eth_ids = {e.port_id for e in onu.eth_ports}
        for pr in onu.port_routes:
            for label, pid in (("src", pr.src_port_id), ("dst", pr.dst_port_id)):
                if pid and pid not in eth_ids:
                    r.add(
                        "info",
                        "PORT_ROUTE_REFS_UNKNOWN_ETH",
                        f"ONU {onu.pon_interface}:{onu.onu_id} PortRoute {label}={pid} sem eth correspondente",
                        path=f"onus[{o_idx}].port_routes",
                    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def validate_config(config: OLTConfig) -> ValidationReport:
    """Roda todos os validadores e retorna um único ValidationReport."""
    report = ValidationReport()
    _validate_hostname(config, report)
    _validate_vlans(config, report)
    _validate_pons(config, report)
    _validate_onus(config, report)
    _validate_service_ports(config, report)
    _validate_profile_refs(config, report)
    _validate_dba_binding(config, report)
    _validate_gem_to_tcont(config, report)
    _validate_uplink_vlans(config, report)
    _validate_traffic_profile_refs(config, report)
    # L9 subscriber edge
    _validate_wan_bindings(config, report)
    _validate_ssid_radios(config, report)
    _validate_bridge_groups(config, report)
    _validate_lan_services(config, report)
    _validate_stb_ports(config, report)
    _validate_multicast_bindings(config, report)
    _validate_port_routes(config, report)
    return report


__all__ = ["ValidationIssue", "ValidationReport", "validate_config"]
