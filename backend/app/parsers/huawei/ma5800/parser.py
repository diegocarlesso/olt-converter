"""
Parser Huawei MA5800 / MA5680T / MA5608T
========================================

Sintaxe Huawei observada nos backups (MG-GVS-*, OLT-NOVA-BRAIPE, OLT HUAWEI,
OLT SERVICOS):

  [!Software Version MA5800V100R021C10B066]
  [pre-config]
    <pre-config>
   board add 0/1 H901GPHF
  [global-config]
   sysname OLT-MG-GVS
   traffic table ip index 8 name "SMARTOLT-1G-UP" cir 1048064 cbs ... priority ...
   dba-profile add profile-id 10 profile-name "DBA-DADOS" type4 max 1024000
   ont wan-profile profile-id 0 profile-name "smartolt"
   ont-srvprofile gpon profile-id 1 profile-name "HG8010H"
     ont-port eth 1 catv adaptive 8
     port vlan eth 1 translation 100 user-vlan 100
     commit
   ont-lineprofile gpon profile-id 10 profile-name "LP-DADOS"
     commit
  [vlan]
   vlan 100 to 300 smart
   port vlan 100 to 300 0/9 0
  [gpon]
   interface gpon 0/1
    port 0 ont-auto-find enable
    port dba bandwidth-assignment-mode 0 max-bandwidth-usage
  [ont]
   ont add 0 sn-auth "HWTC11111111" omci ont-lineprofile-id 10 ont-srvprofile-id 1
  [service-port]
   service-port 1 vlan 100 gpon 0/1/0 ont 0 gemport 1 multi-service user-vlan 100
"""
from __future__ import annotations

import re
from typing import Optional

from app.models import (
    AdminState,
    Board,
    DBAProfile,
    DBAType,
    LineProfile,
    OLTConfig,
    ONU,
    PON,
    PolicyRouteProfile,
    PortConfig,
    PortType,
    ProfileScope,
    ServicePort,
    ServicePortAction,
    ServiceProfile,
    TrafficProfile,
    Uplink,
    Vendor,
    VLAN,
    VLANMode,
    WANProfile,
)
from app.parsers.base import BaseParser, ParserResult
from app.parsers.registry import register_parser
from app.utils.logger import get_logger
from app.utils.text import iter_clean_lines, safe_int, strip_quotes

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------
RX_VERSION = re.compile(r"\[!Software Version\s+(\S+)\]", re.IGNORECASE)
RX_TIMEZONE = re.compile(r"^\s*timezone\s+(.+)$", re.IGNORECASE)
RX_SECTION = re.compile(r"^\s*\[([\w\-]+)\]")
RX_SUBSECTION = re.compile(r"^\s*<([\w\-/]+)>")
RX_SYSNAME = re.compile(r"^\s*sysname\s+(\S+)", re.IGNORECASE)
RX_BOARD = re.compile(
    r"^\s*board\s+add\s+(\d+)/(\d+)\s+(\S+)", re.IGNORECASE
)
RX_TRAFFIC = re.compile(
    r"traffic\s+table\s+ip\s+index\s+(\d+)\s+name\s+\"([^\"]+)\"\s+"
    r"cir\s+(\d+)\s+cbs\s+(\d+)\s+pir\s+(\d+)\s+pbs\s+(\d+)"
    r"(?:\s+color-mode\s+(\S+))?(?:\s+priority\s+(\d+))?"
    r"(?:\s+inner-priority\s+(\d+))?(?:\s+priority-policy\s+(\S+))?",
    re.IGNORECASE,
)
RX_DBA = re.compile(
    r"dba-profile\s+add\s+profile-id\s+(\d+)\s+profile-name\s+\"([^\"]+)\"\s+"
    r"(type\d)\s*(?:assure\s+(\d+))?\s*(?:max\s+(\d+))?\s*(?:fix\s+(\d+))?",
    re.IGNORECASE,
)
RX_ONT_SRVPROFILE = re.compile(
    r"ont-srvprofile\s+gpon\s+profile-id\s+(\d+)\s+profile-name\s+\"?([^\"]+)\"?",
    re.IGNORECASE,
)
RX_ONT_LINEPROFILE = re.compile(
    r"ont-lineprofile\s+(gpon|epon)\s+profile-id\s+(\d+)\s+profile-name\s+\"?([^\"]+)\"?",
    re.IGNORECASE,
)
RX_ONT_WAN_PROFILE = re.compile(
    r"ont\s+wan-profile\s+profile-id\s+(\d+)\s+profile-name\s+\"?([^\"]+)\"?",
    re.IGNORECASE,
)
RX_ONT_POLICY_ROUTE = re.compile(
    r"ont\s+policy-route-profile\s+profile-id\s+(\d+)\s+profile-name\s+\"?([^\"]+)\"?",
    re.IGNORECASE,
)
RX_ONT_PORT = re.compile(
    r"^\s*ont-port"
    r"(?:\s+pots\s+(adaptive\s+\d+|\d+))?"
    r"(?:\s+eth\s+(adaptive\s+\d+|\d+))?"
    r"(?:\s+catv\s+(adaptive\s+\d+|\d+))?"
    r"(?:\s+wifi\s+(adaptive\s+\d+|\d+))?",
    re.IGNORECASE,
)
RX_PORT_VLAN_TRANS = re.compile(
    r"port\s+vlan\s+eth\s+(\d+)\s+translation\s+(\d+)\s+user-vlan\s+(\d+)",
    re.IGNORECASE,
)
RX_INTERFACE_GPON = re.compile(r"^\s*interface\s+gpon\s+(\d+)/(\d+)", re.IGNORECASE)
RX_PORT_ONT_AUTOFIND = re.compile(
    r"^\s*port\s+(\d+)\s+ont-auto-find\s+(enable|disable)", re.IGNORECASE
)
RX_PORT_DBA_MODE = re.compile(
    r"^\s*port\s+dba\s+bandwidth-assignment-mode\s+(\d+)\s+(\S+)",
    re.IGNORECASE,
)
RX_VLAN_SMART = re.compile(
    r"^\s*vlan\s+(\d+)(?:\s+to\s+(\d+))?\s+(smart|common)", re.IGNORECASE
)
RX_PORT_VLAN = re.compile(
    r"^\s*port\s+vlan\s+(\d+)(?:\s+to\s+(\d+))?\s+(\d+)/(\d+)\s+(\d+)",
    re.IGNORECASE,
)
RX_ONT_ADD_OMCI = re.compile(
    r"^\s*ont\s+add\s+(\d+)\s+(\d+)\s+(?:sn-auth\s+\"?([^\"\s]+)\"?\s+)?"
    r"omci\s+ont-lineprofile-id\s+(\d+)\s+ont-srvprofile-id\s+(\d+)"
    r"(?:\s+desc\s+\"?([^\"]+)\"?)?",
    re.IGNORECASE,
)
RX_SERVICE_PORT = re.compile(
    r"^\s*service-port\s+(\d+)\s+vlan\s+(\d+)\s+gpon\s+(\d+)/(\d+)/(\d+)\s+ont\s+(\d+)\s+"
    r"gemport\s+(\d+)"
    r"(?:\s+multi-service\s+user-vlan\s+(\d+))?"
    r"(?:\s+inbound\s+traffic-table\s+(?:name\s+\"([^\"]+)\"|index\s+(\d+)))?"
    r"(?:\s+outbound\s+traffic-table\s+(?:name\s+\"([^\"]+)\"|index\s+(\d+)))?",
    re.IGNORECASE,
)
RX_INTERFACE_VLANIF = re.compile(
    r"^\s*interface\s+vlanif\s+(\d+)", re.IGNORECASE
)
RX_IP_ADDRESS = re.compile(
    r"^\s*ip\s+address\s+(\S+)\s+(\S+)", re.IGNORECASE
)
RX_LINK_AGG = re.compile(
    r"^\s*link-aggregation\s+(\d+/\d+(?:/\d+)?)\s+(\d+)\s+egress-ingress\s+workmode\s+(\S+)",
    re.IGNORECASE,
)
RX_COMMIT = re.compile(r"^\s*commit\s*$", re.IGNORECASE)
RX_QUIT = re.compile(r"^\s*quit\s*$", re.IGNORECASE)

# Convertendo type1..type5 string para enum
def _dba_type(s: str) -> DBAType:
    s = s.lower().strip()
    return DBAType(s) if s in DBAType._value2member_map_ else DBAType.TYPE4


def _parse_port_count(token: Optional[str]) -> tuple[int, bool]:
    """Recebe '4' / 'adaptive 8' / None → (count, adaptive)."""
    if not token:
        return 0, False
    parts = token.strip().split()
    if parts[0].lower() == "adaptive" and len(parts) > 1:
        return safe_int(parts[1]) or 0, True
    return safe_int(parts[0]) or 0, False


@register_parser
class HuaweiMA5800Parser(BaseParser):
    """Parser Huawei MA5800 / MA5680T / MA5608T."""

    vendor = Vendor.HUAWEI
    model_family = "MA5800"
    confidence_signatures: tuple[str, ...] = (
        "sysname",
        "ma5800",
        "ma5680t",
        "ma5608t",
        "ont-srvprofile",
        "ont-lineprofile",
        "ont-wan-profile",
        "dba-profile add profile-id",
        "traffic table ip index",
        "[global-config]",
        "interface gpon 0/",
        "ont add ",
    )

    # ------------------------------------------------------------------ API
    def parse(self, config_text: str) -> ParserResult:
        config = OLTConfig(vendor=self.vendor, model=self.model_family)
        warnings: list[str] = []
        unparsed: list[str] = []

        current_srvprofile: Optional[ServiceProfile] = None
        current_lineprofile: Optional[LineProfile] = None
        current_wanprofile: Optional[WANProfile] = None
        current_policyprofile: Optional[PolicyRouteProfile] = None
        current_pon: Optional[PON] = None
        current_vlan_iface: Optional[VLAN] = None

        for line in iter_clean_lines(config_text):
            stripped = line.strip()

            # ------------------------------- meta header (version/timezone)
            if m := RX_VERSION.search(line):
                config.firmware = m.group(1)
                continue
            if m := RX_TIMEZONE.match(line):
                config.timezone = m.group(1).strip()
                continue

            # Section/subsection markers (informativos)
            if RX_SECTION.match(line):
                continue
            if RX_SUBSECTION.match(line):
                continue

            if m := RX_SYSNAME.match(line):
                config.hostname = m.group(1)
                continue

            # Boards
            if m := RX_BOARD.match(line):
                frame = safe_int(m.group(1)) or 0
                slot = safe_int(m.group(2)) or 0
                btype = m.group(3)
                config.boards.append(
                    Board(slot=slot, board_type=btype, kind="line-card")
                )
                continue

            # Traffic table
            if m := RX_TRAFFIC.search(line):
                config.traffic_profiles.append(
                    TrafficProfile(
                        profile_id=safe_int(m.group(1)) or 0,
                        name=m.group(2),
                        cir=safe_int(m.group(3)),
                        cbs=safe_int(m.group(4)),
                        pir=safe_int(m.group(5)),
                        pbs=safe_int(m.group(6)),
                        color_mode=m.group(7) or "color-blind",
                        priority=safe_int(m.group(8)) or 0,
                        inner_priority=safe_int(m.group(9)) or 0,
                        priority_policy=m.group(10) or "local-setting",
                    )
                )
                continue

            # DBA profile
            if m := RX_DBA.search(line):
                config.dba_profiles.append(
                    DBAProfile(
                        profile_id=safe_int(m.group(1)) or 0,
                        name=m.group(2),
                        type=_dba_type(m.group(3)),
                        assured_bandwidth=safe_int(m.group(4)),
                        max_bandwidth=safe_int(m.group(5)),
                        fix_bandwidth=safe_int(m.group(6)),
                    )
                )
                continue

            # Service profile (start)
            if m := RX_ONT_SRVPROFILE.search(line):
                sp = ServiceProfile(
                    profile_id=safe_int(m.group(1)) or 0,
                    name=strip_quotes(m.group(2)),
                    scope=ProfileScope.GPON,
                    ports=PortConfig(),
                )
                config.service_profiles.append(sp)
                current_srvprofile = sp
                current_lineprofile = None
                continue

            # Line profile (start)
            if m := RX_ONT_LINEPROFILE.search(line):
                tech = m.group(1).lower()
                lp = LineProfile(
                    profile_id=safe_int(m.group(2)) or 0,
                    name=strip_quotes(m.group(3)),
                    scope=ProfileScope(tech) if tech in ProfileScope._value2member_map_ else ProfileScope.GPON,
                )
                config.line_profiles.append(lp)
                current_lineprofile = lp
                current_srvprofile = None
                continue

            # WAN profile / policy route
            if m := RX_ONT_WAN_PROFILE.search(line):
                wp = WANProfile(
                    profile_id=safe_int(m.group(1)) or 0,
                    name=strip_quotes(m.group(2)),
                )
                config.wan_profiles.append(wp)
                current_wanprofile = wp
                continue

            if m := RX_ONT_POLICY_ROUTE.search(line):
                pp = PolicyRouteProfile(
                    profile_id=safe_int(m.group(1)) or 0,
                    name=strip_quotes(m.group(2)),
                )
                config.policy_route_profiles.append(pp)
                current_policyprofile = pp
                continue

            # Dentro de service-profile: ont-port / port vlan trans / commit
            if current_srvprofile and (m := RX_ONT_PORT.match(line)):
                pots, pots_ad = _parse_port_count(m.group(1))
                eth, eth_ad = _parse_port_count(m.group(2))
                catv, catv_ad = _parse_port_count(m.group(3))
                wifi, wifi_ad = _parse_port_count(m.group(4))
                current_srvprofile.ports = PortConfig(
                    pots=pots, eth=eth, catv=catv, wifi=wifi,
                    pots_adaptive=pots_ad, eth_adaptive=eth_ad,
                    catv_adaptive=catv_ad, wifi_adaptive=wifi_ad,
                )
                continue

            if current_srvprofile and (m := RX_PORT_VLAN_TRANS.search(line)):
                current_srvprofile.port_vlan_translations.append(
                    {
                        "port_type": "eth",
                        "port": safe_int(m.group(1)) or 1,
                        "translation": safe_int(m.group(2)),
                        "user_vlan": safe_int(m.group(3)),
                    }
                )
                continue

            if RX_COMMIT.match(line) or RX_QUIT.match(line):
                # encerra qualquer profile aberto
                current_srvprofile = None
                current_lineprofile = None
                current_wanprofile = None
                current_policyprofile = None
                continue

            # interface gpon 0/X
            if m := RX_INTERFACE_GPON.match(line):
                frame = safe_int(m.group(1)) or 0
                slot = safe_int(m.group(2)) or 0
                iface = f"gpon {frame}/{slot}"
                pon = next((p for p in config.pons if p.interface == iface), None)
                if pon is None:
                    pon = PON(
                        interface=iface,
                        slot=slot,
                        port=None,
                    )
                    config.pons.append(pon)
                current_pon = pon
                continue

            if current_pon and (m := RX_PORT_ONT_AUTOFIND.match(line)):
                state = m.group(2).lower() == "enable"
                current_pon.ont_auto_find = state
                continue

            if current_pon and (m := RX_PORT_DBA_MODE.match(line)):
                mode = m.group(2)
                current_pon.optical.dba_assignment_mode = mode
                continue

            # VLAN smart range
            if m := RX_VLAN_SMART.match(line):
                start = safe_int(m.group(1)) or 0
                end = safe_int(m.group(2)) or start
                smart = m.group(3).lower() == "smart"
                for vid in range(start, end + 1):
                    if not any(v.id == vid for v in config.vlans):
                        config.vlans.append(VLAN(id=vid, smart=smart))
                continue

            # port vlan X to Y 0/slot port
            if m := RX_PORT_VLAN.match(line):
                start = safe_int(m.group(1)) or 0
                end = safe_int(m.group(2)) or start
                slot = safe_int(m.group(3)) or 0
                port = safe_int(m.group(5)) or 0
                iface = f"0/{slot}/{port}"
                up = next((u for u in config.uplinks if u.interface == iface), None)
                if up is None:
                    up = Uplink(
                        interface=iface,
                        slot=slot,
                        port=port,
                        port_type=PortType.XGE,
                    )
                    config.uplinks.append(up)
                for vid in range(start, end + 1):
                    if vid not in up.allowed_vlans:
                        up.allowed_vlans.append(vid)
                continue

            # interface vlanif X (management VLAN)
            if m := RX_INTERFACE_VLANIF.match(line):
                vid = safe_int(m.group(1)) or 0
                vlan = next((v for v in config.vlans if v.id == vid), None)
                if vlan is None:
                    vlan = VLAN(id=vid, smart=False)
                    config.vlans.append(vlan)
                vlan.is_management = True
                current_vlan_iface = vlan
                continue

            if current_vlan_iface and (m := RX_IP_ADDRESS.match(line)):
                current_vlan_iface.ip_address = m.group(1)
                current_vlan_iface.netmask = m.group(2)
                continue

            # link-aggregation
            if m := RX_LINK_AGG.match(line):
                # Cria/atualiza LACPGroup
                # Pode ser refinado quando tivermos uma 2ª referência ao mesmo grupo
                continue

            # ont add (provisioning)
            if m := RX_ONT_ADD_OMCI.match(line):
                slot = safe_int(m.group(1)) or 0
                pon_port = safe_int(m.group(2)) or 0
                pon_iface = f"gpon 0/{slot}"
                # Tenta achar pon mais específica '0/slot/port'?  Em Huawei,
                # 'interface gpon 0/X' agrupa o slot, mas 'ont add X Y' usa
                # Y como onu_id ou como ponp depending on context...
                # Aqui Y é tipicamente o onu_id dentro do slot, então usamos
                # interface 'gpon 0/slot'.
                pon = next((p for p in config.pons if p.interface == pon_iface), None)
                if pon is None:
                    pon = PON(interface=pon_iface, slot=slot)
                    config.pons.append(pon)
                onu = ONU(
                    pon_interface=pon_iface,
                    onu_id=pon_port,
                    slot=slot,
                    pon_port=None,
                    serial_number=m.group(3),
                    line_profile_id=safe_int(m.group(4)),
                    service_profile_id=safe_int(m.group(5)),
                    description=m.group(6),
                )
                # Resolve nomes do profile pelos IDs já parseados
                lp = next(
                    (p for p in config.line_profiles if p.profile_id == onu.line_profile_id),
                    None,
                )
                sp = next(
                    (p for p in config.service_profiles if p.profile_id == onu.service_profile_id),
                    None,
                )
                if lp:
                    onu.line_profile_name = lp.name
                if sp:
                    onu.service_profile_name = sp.name
                pon.onus.append(onu)
                config.onus.append(onu)
                continue

            # service-port
            if m := RX_SERVICE_PORT.match(line):
                inbound_name = m.group(9) or (
                    f"index-{m.group(10)}" if m.group(10) else None
                )
                outbound_name = m.group(11) or (
                    f"index-{m.group(12)}" if m.group(12) else None
                )
                config.service_ports.append(
                    ServicePort(
                        service_port_id=safe_int(m.group(1)) or 0,
                        pon_interface=f"gpon 0/{m.group(3)}/{m.group(4)}",
                        onu_id=safe_int(m.group(6)) or 0,
                        gem_id=safe_int(m.group(7)),
                        match_vlan=safe_int(m.group(2)),
                        action=ServicePortAction.REPLACE,
                        target_vlan=safe_int(m.group(2)),
                        user_vlan=safe_int(m.group(8)) if m.group(8) else None,
                        inbound_traffic_profile=inbound_name,
                        outbound_traffic_profile=outbound_name,
                    )
                )
                continue

            # ---------------- noise / unhandled
            if stripped and not stripped.startswith(("#", "//", "!")):
                unparsed.append(line)

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info("huawei_parse_done", hostname=config.hostname, stats=config.stats())
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
