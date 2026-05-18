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

# Conteúdo nativo de ont-lineprofile gpon:
#   tcont 1 dba-profile-id 10
#   gem add 1 eth tcont 1
#   gem mapping 1 0 vlan 100
#   gem mapping 2 0 vlan 200
RX_LP_TCONT_DBA = re.compile(
    r"^\s*tcont\s+(\d+)\s+dba-profile-id\s+(\d+)", re.IGNORECASE
)
RX_LP_GEM_ADD = re.compile(
    r"^\s*gem\s+add\s+(\d+)\s+(eth|tdm)?\s*tcont\s+(\d+)", re.IGNORECASE
)
RX_LP_GEM_MAPPING = re.compile(
    r"^\s*gem\s+mapping\s+(\d+)\s+(\d+)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_LP_MAPPING_MODE = re.compile(
    r"^\s*mapping-mode\s+(\S+)", re.IGNORECASE
)
# Bloco `onu-type` (Huawei profile global de tipo de ONU)
RX_ONU_TYPE = re.compile(
    r"^\s*onu-type\s+(\S+)\s+", re.IGNORECASE
)
RX_ONU_TYPE_IF = re.compile(
    r"^\s*onu-type-if\s+(\S+)\s+", re.IGNORECASE
)
# SNMP global
RX_SNMP_SERVER = re.compile(
    r"^\s*snmp-server\s+", re.IGNORECASE
)
RX_SNMP_AGENT = re.compile(
    r"^\s*snmp-agent\s+", re.IGNORECASE
)
# Fragmentos órfãos (r069, tr069 truncados quando linha é cortada)
RX_HUAWEI_GARBAGE = re.compile(r"^\s*[a-z0-9]{1,5}\s*$")

# --- Huawei MA5800 runtime ONU commands (top-level, fora de profile) ----
# ont port route slot port eth port enable
RX_ONT_PORT_ROUTE_GLOBAL = re.compile(
    r"^\s*ont\s+port\s+route\s+(\d+)\s+(\d+)\s+eth\s+(\d+)\s+(enable|disable)",
    re.IGNORECASE,
)
# ont port native-vlan slot port eth port vlan vid priority p
RX_ONT_PORT_NATIVE_VLAN = re.compile(
    r"^\s*ont\s+port\s+native-vlan\s+(\d+)\s+(\d+)\s+eth\s+(\d+)\s+vlan\s+(\d+)"
    r"(?:\s+priority\s+(\d+))?",
    re.IGNORECASE,
)
# ont internet-config slot port ip-index N
RX_ONT_INTERNET_CFG = re.compile(
    r"^\s*ont\s+internet-config\s+(\d+)\s+(\d+)\s+ip-index\s+(\d+)",
    re.IGNORECASE,
)
# ont wan-config slot port ip-index N profile-id N
RX_ONT_WAN_CONFIG = re.compile(
    r"^\s*ont\s+wan-config\s+(\d+)\s+(\d+)\s+ip-index\s+(\d+)\s+profile-id\s+(\d+)",
    re.IGNORECASE,
)
# ont policy-route-config slot port profile-id N
RX_ONT_POLICY_ROUTE_CFG = re.compile(
    r"^\s*ont\s+policy-route-config\s+(\d+)\s+(\d+)\s+profile-id\s+(\d+)",
    re.IGNORECASE,
)
# ont ipconfig slot port ip-index N pppoe vlan N priority N user-account username X password Y
RX_ONT_IPCONFIG = re.compile(
    r"^\s*ont\s+ipconfig\s+(\d+)\s+(\d+)\s+ip-index\s+(\d+)",
    re.IGNORECASE,
)
# port N ont-password-renew extra N
RX_PORT_ONT_RENEW = re.compile(
    r"^\s*port\s+(\d+)\s+ont-password-renew\s+extra\s+(\d+)",
    re.IGNORECASE,
)
# board-template start X
RX_BOARD_TEMPLATE = re.compile(r"^\s*board-template\s+", re.IGNORECASE)
# omcc encrypt on/off
RX_OMCC = re.compile(r"^\s*omcc\s+", re.IGNORECASE)
# discover-period new-onu N miss-onu N
RX_DISCOVER_PERIOD = re.compile(r"^\s*discover-period\s+", re.IGNORECASE)
# linktrap enable/disable
RX_LINKTRAP = re.compile(r"^\s*linktrap\s+", re.IGNORECASE)
# tr069-management enable
RX_TR069_MGMT_CMD = re.compile(r"^\s*tr069-management\s+", re.IGNORECASE)
# port vlan iphost translation N user-vlan N
RX_PORT_VLAN_IPHOST = re.compile(
    r"^\s*port\s+vlan\s+iphost\s+translation\s+(\d+)\s+user-vlan\s+(\d+)",
    re.IGNORECASE,
)
# port vlan eth N translation N user-vlan N (fora de srvprofile context)
RX_PORT_VLAN_ETH_GLOBAL = re.compile(
    r"^\s*port\s+vlan\s+eth\s+(\d+)\s+translation\s+(\d+)\s+user-vlan\s+(\d+)",
    re.IGNORECASE,
)
# vlan port eth_0/N mode hybrid (variação que apareceu no MARIANA)
RX_VLAN_PORT_HYBRID = re.compile(
    r"^\s*vlan\s+port\s+eth_0/(\d+)\s+mode\s+(hybrid|trunk|access)",
    re.IGNORECASE,
)
# traffic-table index N (referência a traffic-table existente)
RX_TRAFFIC_REF = re.compile(
    r"^\s*traffic-table\s+(?:index|name)\s+\S+",
    re.IGNORECASE,
)
# interface vport-X/Y.Z:N (já tratado em ZTE; em Huawei é noise)
RX_IF_VPORT_HW = re.compile(r"^\s*interface\s+vport-", re.IGNORECASE)
# name gpon-olt_X/Y/Z (descrição livre)
RX_NAME_GPON = re.compile(r"^\s*name\s+gpon-olt_", re.IGNORECASE)
# MAC address table entries: 14ab.02af.b03e N Dynamic xgei_1/...
RX_MAC_TABLE = re.compile(
    r"^\s*[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}\s+\d+\s+(?:Dynamic|Static)",
    re.IGNORECASE,
)
# Linhas de continuação que sobraram (first-login-info, "-----", etc.)
RX_LEFTOVER_QUOTE = re.compile(r"^\s*[\"-]{1,10}\s*$")
# monitor uplink-port
RX_MONITOR_UPLINK = re.compile(r"^\s*monitor\s+uplink-port\s+", re.IGNORECASE)

# Verbos típicos de comando Huawei MA5800 — usados para detectar continuação.
# IMPORTANTE: não incluir prefixos curtos como "ont-" porque eles fazem
# `ont-srvprofile-id` (que é PARÂMETRO de `ont add`, não comando)
# ser tratado como nova linha. Use verbos EXATOS específicos.
_HUAWEI_COMMAND_VERBS = (
    "sysname", "system", "terminal", "traffic", "dba-profile",
    "ont",                       # ont add / ont wan-profile / ont policy-route
    "ont-srvprofile",            # definição de service profile (top-level)
    "ont-lineprofile",           # definição de line profile (top-level)
    "ont-port",                  # ont-port pots/eth/catv/wifi
    "ont-wan-profile",           # bloco
    "ont-policy-route-profile",  # bloco
    "interface", "service-port", "vlan", "port", "board", "board-template",
    "ip", "static-route",
    "xpon", "gpon", "commit", "quit", "service", "switch", "link-aggregation",
    "snmp", "ssh", "ntp", "aaa", "radius", "sysmode", "timezone",
    "raio-format", "stp", "lldp", "erps", "ddos", "dhcp", "pppoe", "igmp",
    "multicast", "alarm", "license", "ipv6", "lacp", "monitor", "save", "undo",
    "tdm",
)


def _join_continuations(text: str) -> str:
    """
    Junta linhas continuação em backups Huawei dumped no terminal (que quebra em
    col 80). Heurística: linha em col 1 que NÃO começa com um verbo de comando
    nem com header `#`/`[`/`<` é tratada como continuação da anterior.
    """
    out: list[str] = []
    for raw in text.splitlines():
        if not out:
            out.append(raw)
            continue
        # Header / section marker → sempre nova linha
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "[", "<")):
            out.append(raw)
            continue
        # Em coluna 1 (sem indentação) — pode ser continuação
        if raw and not raw.startswith((" ", "\t")):
            first_token = stripped.split(maxsplit=1)[0].lower()
            # Match EXATO contra a lista (não use startswith — `ont-srvprofile-id`
            # quebraria contra `ont-srvprofile`). Verbos com hífen são tokens
            # inteiros pré-validados.
            if first_token in _HUAWEI_COMMAND_VERBS:
                out.append(raw)
                continue
            # Caso contrário, é continuação: junta na linha anterior
            out[-1] = out[-1].rstrip() + " " + stripped
            continue
        out.append(raw)
    return "\n".join(out)

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


def _resolve_onu_for_l9(config, current_pon, group1: int, group2: int):
    """
    Within `interface gpon 0/SLOT`, L9 commands are `<verb> PORT ONT_ID ...`.
    SLOT comes from current_pon. We look up the ONU by (slot, pon_port, onu_id).
    Fallback (rare backups): if no match, try (slot, pon_port=group1, onu_id=group2)
    against any ONU regardless of pon_iface.
    """
    if current_pon is None or current_pon.slot is None:
        return None
    slot = current_pon.slot
    pon_port, ont_id = group1, group2
    for o in config.onus:
        if o.slot == slot and o.pon_port == pon_port and o.onu_id == ont_id:
            return o
    return None




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
        # Junta linhas de continuação (terminal-wrapped em col 80)
        config_text = _join_continuations(config_text)
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

            # Conteúdo NATIVO de ont-lineprofile (tcont/gem add/gem mapping)
            if current_lineprofile:
                if m := RX_LP_TCONT_DBA.match(line):
                    current_lineprofile.tcont_bindings.append({
                        "tcont_id": safe_int(m.group(1)) or 0,
                        "dba_profile_id": safe_int(m.group(2)),
                    })
                    continue
                if m := RX_LP_GEM_ADD.match(line):
                    current_lineprofile.gemport_bindings.append({
                        "gem_id": safe_int(m.group(1)) or 0,
                        "tech": m.group(2) or "eth",
                        "tcont_id": safe_int(m.group(3)) or 0,
                    })
                    continue
                if m := RX_LP_GEM_MAPPING.match(line):
                    current_lineprofile.mappers.append({
                        "gem_id": safe_int(m.group(1)) or 0,
                        "queue": safe_int(m.group(2)) or 0,
                        "vlan_id": safe_int(m.group(3)) or 0,
                    })
                    continue
                if RX_LP_MAPPING_MODE.match(line):
                    continue   # mapping-mode é metadado

            # Conteúdo runtime dentro de srvprofile/wanprofile/lineprofile:
            # description / ont port route / service / wan / ssid / pppoe
            current_profile_ctx = (
                current_srvprofile or current_lineprofile or current_wanprofile
            )
            if current_profile_ctx:
                low_strip = stripped.lower()
                if low_strip.startswith(("description ", "name ")):
                    # Atribui description ao profile atual se ainda não existe
                    rest = stripped.split(maxsplit=1)
                    if len(rest) > 1 and not getattr(current_profile_ctx, "description", None):
                        try:
                            setattr(current_profile_ctx, "description", rest[1].strip())
                        except Exception:  # noqa: BLE001
                            pass
                    continue
                if low_strip.startswith(("ont port route ", "ont port native-vlan ",
                                         "service ", "wan ", "ssid ", "pppoe ",
                                         "static-config", "ip-host", "port-list",
                                         "loop-detect", "dhcp-ip", "ipv4-source",
                                         "tr069", "lan-port-pvc")):
                    # captura em raw_meta — preserva para auditoria sem modelar
                    bag = getattr(current_profile_ctx, "extra_vendor", None)
                    if bag is None:
                        bag = {}
                        try:
                            current_profile_ctx.extra_vendor = bag
                        except Exception:  # noqa: BLE001
                            pass
                    bag.setdefault("raw_lines", []).append(stripped)
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
            # Huawei MA5800 syntax:
            #   <inside `interface gpon 0/SLOT`>
            #   ont add PON_PORT ONT_ID sn-auth "SN" omci ont-lineprofile-id ... ont-srvprofile-id ...
            # SLOT comes from current_pon context. m.group(1) = PON_PORT, m.group(2) = ONT_ID.
            if m := RX_ONT_ADD_OMCI.match(line):
                pon_port = safe_int(m.group(1)) or 0
                ont_id = safe_int(m.group(2)) or 0
                slot = current_pon.slot if current_pon and current_pon.slot is not None else 0
                pon_iface = current_pon.interface if current_pon else f"gpon 0/{slot}"
                pon = current_pon
                if pon is None:
                    pon = next((p for p in config.pons if p.interface == pon_iface), None)
                if pon is None:
                    pon = PON(interface=pon_iface, slot=slot)
                    config.pons.append(pon)
                onu = ONU(
                    pon_interface=pon_iface,
                    onu_id=ont_id,
                    slot=slot,
                    pon_port=pon_port,
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

            # ---------------- Huawei runtime ONU bindings
            # Inside `interface gpon 0/SLOT`, commands are `<verb> PORT ONT_ID ...`
            # ont port route port ont_id eth N enable
            if m := RX_ONT_PORT_ROUTE_GLOBAL.match(line):
                g1 = safe_int(m.group(1)) or 0
                g2 = safe_int(m.group(2)) or 0
                eth = safe_int(m.group(3))
                enabled = m.group(4).lower() == "enable"
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None and eth is not None:
                    onu.extra_vendor.setdefault("port_routes", []).append(
                        {"eth": eth, "enabled": enabled}
                    )
                continue
            # ont port native-vlan port ont_id eth N vlan V priority P
            if m := RX_ONT_PORT_NATIVE_VLAN.match(line):
                g1 = safe_int(m.group(1)) or 0
                g2 = safe_int(m.group(2)) or 0
                eth_id = safe_int(m.group(3)) or 1
                vid = safe_int(m.group(4))
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None and vid:
                    from app.models import EthernetPort
                    eth = next(
                        (e for e in onu.eth_ports if e.port_id == eth_id), None
                    )
                    if eth is None:
                        eth = EthernetPort(port_id=eth_id)
                        onu.eth_ports.append(eth)
                    eth.native_vlan = vid
                continue
            # ont internet-config / wan-config / policy-route-config / ipconfig
            # Populam extra_vendor para promotion engine materializar WANBinding L9.
            if m := RX_ONT_WAN_CONFIG.match(line):
                g1 = safe_int(m.group(1)) or 0; g2 = safe_int(m.group(2)) or 0
                ip_index = safe_int(m.group(3)); profile_id = safe_int(m.group(4))
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None:
                    onu.extra_vendor.setdefault("wan_config_hw", []).append({"ip_index": ip_index, "profile_id": profile_id})
                continue
            if m := RX_ONT_INTERNET_CFG.match(line):
                g1 = safe_int(m.group(1)) or 0; g2 = safe_int(m.group(2)) or 0
                ip_index = safe_int(m.group(3))
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None:
                    onu.extra_vendor.setdefault("internet_config_hw", []).append({"ip_index": ip_index})
                continue
            if m := RX_ONT_POLICY_ROUTE_CFG.match(line):
                g1 = safe_int(m.group(1)) or 0; g2 = safe_int(m.group(2)) or 0
                profile_id = safe_int(m.group(3))
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None:
                    onu.extra_vendor.setdefault("policy_route_config_hw", []).append({"profile_id": profile_id})
                continue
            if m := RX_ONT_IPCONFIG.match(line):
                g1 = safe_int(m.group(1)) or 0; g2 = safe_int(m.group(2)) or 0
                ip_index = safe_int(m.group(3))
                onu = _resolve_onu_for_l9(config, current_pon, g1, g2)
                if onu is not None:
                    # Tenta detectar pppoe inline (user-account username "X" password "Y")
                    is_pppoe = " pppoe " in line.lower()
                    user = None
                    if is_pppoe:
                        import re as _re
                        um = _re.search(r"user-account\s+username\s+\"([^\"]+)\"", line, _re.IGNORECASE)
                        if um:
                            user = um.group(1)
                    onu.extra_vendor.setdefault("ipconfig_hw", []).append({
                        "ip_index": ip_index,
                        "mode": "pppoe" if is_pppoe else "static_or_dhcp",
                        "pppoe_user": user,
                    })
                continue
            # port N ont-password-renew
            if RX_PORT_ONT_RENEW.match(line):
                continue
            # board-template / omcc / discover-period / linktrap / tr069-management
            if (RX_BOARD_TEMPLATE.match(line) or RX_OMCC.match(line)
                    or RX_DISCOVER_PERIOD.match(line) or RX_LINKTRAP.match(line)
                    or RX_TR069_MGMT_CMD.match(line)):
                continue
            # port-vlan globais (fora de srvprofile)
            if RX_PORT_VLAN_IPHOST.match(line) or RX_PORT_VLAN_ETH_GLOBAL.match(line):
                continue
            # vlan port eth_0/N mode hybrid
            if RX_VLAN_PORT_HYBRID.match(line):
                continue
            # traffic-table referência
            if RX_TRAFFIC_REF.match(line):
                continue
            # interface vport-X/Y.Z:N
            if RX_IF_VPORT_HW.match(line):
                continue
            # name gpon-olt_X/Y/Z (descrição da PON)
            if RX_NAME_GPON.match(line):
                continue
            # MAC address table entries
            if RX_MAC_TABLE.match(line):
                continue
            # Restos de continuações (first-login-info "-----", etc.)
            if RX_LEFTOVER_QUOTE.match(line):
                continue
            # monitor uplink-port traffic/pppoe
            if RX_MONITOR_UPLINK.match(line):
                continue

            # ---------------- SNMP / onu-type / fragments
            if RX_SNMP_SERVER.match(line) or RX_SNMP_AGENT.match(line):
                # captura permissiva — SNMP em SNMPConfig será refinado depois
                if config.snmp is None:
                    from app.models import SNMPConfig
                    config.snmp = SNMPConfig()
                # Não modelado em detalhe agora, mas registra
                continue
            if RX_ONU_TYPE.match(line) or RX_ONU_TYPE_IF.match(line):
                # Bloco onu-type — informativo, não modelado
                continue
            if RX_HUAWEI_GARBAGE.match(line):
                continue   # fragmentos órfãos r069, tr069 truncado

            # ---------------- noise / unhandled
            if stripped and not stripped.startswith(("#", "//", "!")):
                unparsed.append(line)

        # Pós-resolução: line-profile.tcont_bindings com dba_profile_id sem
        # dba_profile_name → lookup pelo id e popular o nome
        dba_id_to_name = {d.profile_id: d.name for d in config.dba_profiles}
        for lp in config.line_profiles:
            for binding in lp.tcont_bindings:
                if "dba_profile_id" in binding and not binding.get("dba_profile_name"):
                    name = dba_id_to_name.get(binding["dba_profile_id"])
                    if name:
                        binding["dba_profile_name"] = name

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info("huawei_parse_done", hostname=config.hostname, stats=config.stats())
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
