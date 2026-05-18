"""
Parser ZTE C300 / C320 / C600
=============================

Sintaxe ZXAN observada nos backups reais (OLT-ZTE-*, PROVISIONAR_ONU):

  !<mim>
  !<system-config>
  hostname OLT-XYZ
  !</system-config>
  !<if-intf>
  interface gei-1/1/5
    description UPLINK
    no shutdown
  $
  interface xgei-1/1/1 ...
  interface gpon_olt-1/3/1
  interface gpon_onu-1/3/1:1
  $
  !</if-intf>

  interface gpon 1/1/2
   onu 0
    serial-number ZTEGD70EF916
    service-profile SP-PPPOE line-profile LP-PPPOE
    ethernet 1
     negotiation
     no shutdown
     native vlan vlan-id 200
    !
   !
  !
  service-port 1 gpon 1/1/2 onu 0 gem 1 match vlan vlan-id 200 action vlan replace vlan-id 200
  vlan 100
   name CLIENTES

O parser mantém contexto hierárquico (gpon → onu → ethernet) e arquiva linhas
não-mapeadas em `raw_unparsed`.
"""
from __future__ import annotations

import re
from typing import Optional

from app.models import (
    AdminState,
    EthernetPort,
    OLTConfig,
    ONU,
    OperationMode,
    PON,
    PortType,
    ServicePort,
    ServicePortAction,
    TrunkMode,
    Uplink,
    Vendor,
    VLAN,
    VLANMode,
)
from app.parsers.base import BaseParser, ParserResult
from app.parsers.registry import register_parser
from app.utils.logger import get_logger
from app.utils.text import iter_clean_lines, parse_interface_path, safe_int

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------
RX_HOSTNAME = re.compile(r"^\s*hostname\s+(\S+)", re.IGNORECASE)
RX_IF_ETH = re.compile(
    r"^\s*interface\s+(gei|xgei|10ge|40ge|100ge)-(\d+/\d+/\d+)", re.IGNORECASE
)
RX_IF_PON_DECL = re.compile(
    r"^\s*interface\s+(?:gpon_olt-|gpon-olt_)(\d+/\d+/\d+)", re.IGNORECASE
)
RX_IF_ONU_DECL = re.compile(
    r"^\s*interface\s+(?:gpon_onu-|gpon-onu_)(\d+/\d+/\d+):(\d+)", re.IGNORECASE
)
# Bloco gpon-onu_ contém os mesmos comandos que pon-onu-mng (em ZTE C600 com nova syntax)
RX_IF_GPON_ONU_BLOCK = re.compile(
    r"^\s*interface\s+gpon-onu_(\d+/\d+/\d+):(\d+)\s*$", re.IGNORECASE
)
RX_IF_GPON_PROV = re.compile(
    r"^\s*interface\s+gpon\s+(\d+/\d+/\d+)\s*$", re.IGNORECASE
)
RX_ONU_BLOCK = re.compile(r"^\s*onu\s+(\d+)\s*$", re.IGNORECASE)
RX_SN = re.compile(r"^\s*serial-number\s+(\S+)", re.IGNORECASE)
RX_SP_LP = re.compile(
    r"service-profile\s+(\S+)\s+line-profile\s+(\S+)", re.IGNORECASE
)
RX_NATIVE_VLAN = re.compile(
    r"native\s+vlan\s+vlan-id\s+(\d+)", re.IGNORECASE
)
RX_ETH_BLOCK = re.compile(r"^\s*ethernet\s+(\d+)\s*$", re.IGNORECASE)
RX_SERVICE_PORT = re.compile(
    r"^\s*service-port\s+(\d+)\s+gpon\s+(\d+/\d+/\d+)\s+onu\s+(\d+)\s+gem\s+(\d+)\s+"
    r"match\s+vlan\s+vlan-id\s+(\d+)\s+action\s+vlan\s+(\S+)\s+vlan-id\s+(\d+)"
    r"(?:\s+user-vlan\s+vlan-id\s+(\d+))?",
    re.IGNORECASE,
)
RX_VLAN_DEF = re.compile(r"^\s*vlan\s+(\d+)\s*$", re.IGNORECASE)
RX_VLAN_NAME = re.compile(r"^\s*name\s+(.+)\s*$", re.IGNORECASE)
RX_INTERFACE_VLAN = re.compile(
    r"^\s*interface\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_IP_ADDRESS = re.compile(
    r"^\s*ip\s+address\s+(\S+)\s+(\S+)", re.IGNORECASE
)
RX_NO_SHUTDOWN = re.compile(r"^\s*no\s+shutdown\s*$", re.IGNORECASE)
RX_SHUTDOWN = re.compile(r"^\s*shutdown\s*$", re.IGNORECASE)
RX_DESC = re.compile(r"^\s*description\s+(.+)$", re.IGNORECASE)
RX_NEGOTIATION = re.compile(r"^\s*negotiation\s*$", re.IGNORECASE)
RX_BLOCK_END = re.compile(r"^\s*(\$|!|\!)\s*$")

# --- ZTE real-world syntax revelada pelo fidelity_report ----------------
# Bloco `pon-onu-mng gpon-onu_1/3/1:5` agrupa toda a config de provisionamento
# de uma ONU específica (gemport, tcont, service, switchport-bind, etc.).
RX_PON_ONU_MNG = re.compile(
    r"^\s*pon-onu-mng\s+(?:gpon-onu_|gpon_onu-)(\d+/\d+/\d+):(\d+)", re.IGNORECASE
)
# Dentro do bloco:
RX_GEMPORT_TCONT = re.compile(
    r"^\s*gemport\s+(\d+)\s+(?:name\s+(\S+)\s+)?tcont\s+(\d+)", re.IGNORECASE
)
RX_TCONT_PROFILE = re.compile(
    r"^\s*tcont\s+(\d+)(?:\s+name\s+(\S+))?\s+profile\s+(\S+)", re.IGNORECASE
)
RX_TCONT_GAP = re.compile(
    r"^\s*tcont\s+(\d+)\s+gap\s+(\S+)", re.IGNORECASE
)
RX_SERVICE_GEMPORT = re.compile(
    r"^\s*service\s+(\S+)\s+gemport\s+(\d+)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_SWITCHPORT_BIND = re.compile(
    r"^\s*switchport-bind\s+switch_0/(\d+)\s+(veip|iphost)\s+(\d+)", re.IGNORECASE
)
RX_DHCP_ETHUNI = re.compile(
    r"^\s*dhcp-ip\s+ethuni\s+eth_0/(\d+)\s+from-onu", re.IGNORECASE
)
RX_VLAN_PORT_ETH = re.compile(
    r"^\s*vlan\s+port\s+eth_0/(\d+)\s+mode\s+(tag|untag|trunk)\s+vlan\s+(\d+)",
    re.IGNORECASE,
)
RX_ONU_TYPE_SN = re.compile(
    r"^\s*onu\s+(\d+)\s+type\s+(\S+)\s+sn\s+(\S+)", re.IGNORECASE
)
RX_SN_BIND = re.compile(r"^\s*sn-bind\s+(enable|disable)\s+(\S+)", re.IGNORECASE)

# Sintaxe alternativa de service-port (mais comum no backup real):
#   service-port 1 vport 1 user-vlan 100 vlan 100
RX_SERVICE_PORT_VPORT = re.compile(
    r"^\s*service-port\s+(\d+)\s+vport\s+(\d+)\s+user-vlan\s+(\d+)\s+vlan\s+(\d+)",
    re.IGNORECASE,
)

# Ruído / extras
RX_SECURITY_MGMT = re.compile(r"^\s*security-mgmt\s+", re.IGNORECASE)
RX_TR069_MGMT = re.compile(r"^\s*tr069-mgmt\s+", re.IGNORECASE)
RX_FIREWALL = re.compile(r"^\s*firewall\s+", re.IGNORECASE)
RX_WIFI_BLOCK = re.compile(r"^\s*(wifi|wlan)\s+", re.IGNORECASE)

# Wave 2 — flow / vlan-filter / gem mapping / vport / loop-detect
RX_TCONT_DBA_ID = re.compile(
    r"^\s*tcont\s+(\d+)\s+dba-profile-id\s+(\d+)", re.IGNORECASE
)
RX_GEM_ADD_ETH = re.compile(
    r"^\s*gem\s+add\s+(\d+)\s+eth\s+tcont\s+(\d+)", re.IGNORECASE
)
RX_GEM_MAPPING = re.compile(
    r"^\s*gem\s+mapping\s+(\d+)\s+(\d+)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_FLOW_MODE = re.compile(
    r"^\s*flow\s+mode\s+(\d+)\s+", re.IGNORECASE
)
RX_FLOW_RULE = re.compile(
    r"^\s*flow\s+(\d+)\s+pri\s+(\d+)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_GEMPORT_FLOW = re.compile(
    r"^\s*gemport\s+(\d+)\s+flow\s+(\d+)", re.IGNORECASE
)
RX_VLAN_WAN_TAG = re.compile(
    r"^\s*vlan\s+wan\s+(\d+)\s+mode\s+(tag|untag)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_VLAN_FILTER = re.compile(
    r"^\s*vlan-filter\s+iphost\s+(\d+)\s+pri\s+(\d+)\s+vlan\s+(\d+)", re.IGNORECASE
)
RX_VLAN_FILTER_MODE = re.compile(
    r"^\s*vlan-filter-mode\s+iphost\s+(\d+)\s+", re.IGNORECASE
)
RX_LOOP_DETECT = re.compile(
    r"^\s*loop-detect\s+ethuni\s+eth_0/(\d+)\s+(\S+)", re.IGNORECASE
)
RX_DHCP_INTERNET = re.compile(
    r"^\s*dhcp-ip\s+ethuni\s+eth_0/(\d+)\s+from-internet", re.IGNORECASE
)
RX_IF_VPORT = re.compile(
    r"^\s*interface\s+vport-(\d+/\d+)\.(\d+):(\d+)", re.IGNORECASE
)

# Inside-block: description e name livres (atribuem ao current_mng_onu)
RX_DESC_FREE = re.compile(r"^\s*description\s+(.+)$", re.IGNORECASE)
RX_NAME_FREE = re.compile(r"^\s*name\s+(.+)$", re.IGNORECASE)
# Service-port simplificado (3º dialeto ZTE)
RX_SERVICE_PORT_ALT = re.compile(
    r"^\s*service-port\s+(\d+)\s+user-vlan\s+(\d+)\s+vlan\s+(\d+)\s*$",
    re.IGNORECASE,
)
# ont port route N N eth N enable (Huawei/ZTE ONU bridge routing) — runtime
RX_ONT_PORT_ROUTE = re.compile(
    r"^\s*ont\s+port\s+route\s+(\d+)\s+(\d+)\s+eth\s+(\d+)\s+(enable|disable)",
    re.IGNORECASE,
)
# service NAME gemport N cos N vlan N (variação com COS)
RX_SERVICE_GEMPORT_COS = re.compile(
    r"^\s*service\s+(\S+)\s+gemport\s+(\d+)\s+cos\s+(\d+)\s+vlan\s+(\d+)",
    re.IGNORECASE,
)
# WAN config interno (Huawei/ZTE ONU)
RX_WAN_BIND = re.compile(
    r"^\s*wan\s+(\d+)\s+ethuni\s+([\d,]+)\s+ssid\s+(\d+)\s+service\s+(\S+)",
    re.IGNORECASE,
)
RX_WAN_HOST = re.compile(
    r"^\s*wan\s+(\d+)\s+service\s+(\S+)\s+host\s+(\d+)", re.IGNORECASE
)
# PPPoE per ONU (runtime)
RX_PPPOE_ONU = re.compile(
    r"^\s*pppoe\s+(\d+)\s+nat\s+(\S+)\s+release-timer\s+\S+\s+user\s+(\S+)\s+password\s+(\S+)",
    re.IGNORECASE,
)
# SSID per ONU
RX_SSID_AUTH = re.compile(
    r"^\s*ssid\s+auth\s+wpa\s+wifi_0/(\d+)\s+(\S+)\s+encrypt\s+(\S+)\s+key\s+(\S+)",
    re.IGNORECASE,
)
# sntp config global
RX_SNTP = re.compile(
    r"^\s*sntp\s+time-zone\s+(\S+)\s+master-server\s+(\S+)\s+slave-server\s+(\S+)",
    re.IGNORECASE,
)
# Lines `s` ou `r069` órfãs (truncadas) — apenas noise
RX_GARBAGE_FRAG = re.compile(r"^\s*[a-z]{1,4}\s*$")


@register_parser
class ZTEC600Parser(BaseParser):
    """Parser para ZTE ZXAN C300 / C320 / C600 (e variantes)."""

    vendor = Vendor.ZTE
    model_family = "C600"
    confidence_signatures: tuple[str, ...] = (
        "gpon_olt-",
        "gpon_onu-",
        "interface gei-",
        "interface xgei-",
        "!<system-config>",
        "service-port ",
        "ZTEG",
        "zxan",
    )

    # ------------------------------------------------------------------ API
    def parse(self, config_text: str) -> ParserResult:
        config = OLTConfig(vendor=self.vendor, model=self.model_family)
        warnings: list[str] = []
        unparsed: list[str] = []

        # ---------- contexto hierárquico
        current_pon_iface: Optional[str] = None
        current_onu: Optional[ONU] = None
        current_eth: Optional[EthernetPort] = None
        current_uplink: Optional[Uplink] = None
        current_vlan_iface: Optional[VLAN] = None
        in_vlan_block: Optional[VLAN] = None
        # Bloco `pon-onu-mng gpon-onu_X/Y/Z:N` aponta para uma ONU específica
        current_mng_onu: Optional[ONU] = None
        # Estado parcial de gemport/tcont/service dentro do mng block
        mng_state: dict = {}   # {gemports: [...], tconts: [...], services: [...]}

        for line in iter_clean_lines(config_text):
            stripped = line.strip()

            # ------------------------------------------------------------ end
            if RX_BLOCK_END.match(line):
                # Termina blocos por precedência: mais aninhado primeiro
                if current_eth is not None:
                    current_eth = None
                elif current_mng_onu is not None:
                    current_mng_onu = None
                    mng_state = {}
                elif current_onu is not None:
                    current_onu = None
                elif current_pon_iface is not None:
                    current_pon_iface = None
                elif current_uplink is not None:
                    current_uplink = None
                elif current_vlan_iface is not None:
                    current_vlan_iface = None
                elif in_vlan_block is not None:
                    in_vlan_block = None
                continue

            # ------------------------------------------------------------ hostname
            if m := RX_HOSTNAME.match(line):
                config.hostname = m.group(1)
                continue

            # ------------------------------------------------------------ interface vlan X (interface L3)
            if m := RX_INTERFACE_VLAN.match(line):
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

            # ------------------------------------------------------------ interface uplink
            if m := RX_IF_ETH.match(line):
                ifname, path = m.group(1).lower(), m.group(2)
                comps = parse_interface_path(path)
                pt = PortType.XGE if ifname.startswith(("x", "10", "40")) else PortType.GE
                u = Uplink(
                    interface=f"{ifname}-{path}",
                    slot=comps.get("slot"),
                    port=comps.get("port"),
                    port_type=pt,
                    mode=TrunkMode.TRUNK,
                )
                config.uplinks.append(u)
                current_uplink = u
                continue

            # ------------------------------------------------------------ PON declaration (if-intf list)
            if m := RX_IF_PON_DECL.match(line):
                path = m.group(1)
                comps = parse_interface_path(path)
                iface = f"gpon_olt-{path}"
                if not any(p.interface == iface for p in config.pons):
                    config.pons.append(
                        PON(
                            interface=iface,
                            slot=comps.get("slot"),
                            port=comps.get("port"),
                        )
                    )
                continue

            # ------------------------------------------------------------ ONU declaration (if-intf list)
            # NOTA IMPORTANTE: em ZTE C600, `interface gpon-onu_X/Y/Z:N`
            # NÃO é só uma declaração — é o bloco de provisionamento da ONU.
            # Logo abaixo seguem `sn-bind`, `tcont`, `gemport`, `service`, etc.
            # Portanto também setamos current_mng_onu para que esses
            # comandos inner sejam capturados (recupera ~5700 linhas reais).
            if m := RX_IF_ONU_DECL.match(line):
                path = m.group(1)
                onu_id = safe_int(m.group(2)) or 0
                comps = parse_interface_path(path)
                pon_iface = f"gpon_olt-{path}"
                pon = next((p for p in config.pons if p.interface == pon_iface), None)
                if pon is None:
                    pon = PON(
                        interface=pon_iface,
                        slot=comps.get("slot"),
                        port=comps.get("port"),
                    )
                    config.pons.append(pon)
                onu = next((o for o in pon.onus if o.onu_id == onu_id), None)
                if onu is None:
                    onu = ONU(
                        pon_interface=pon_iface,
                        onu_id=onu_id,
                        slot=comps.get("slot"),
                        pon_port=comps.get("port"),
                    )
                    pon.onus.append(onu)
                    config.onus.append(onu)
                # ABRE o bloco mng — próximas linhas (sn-bind/tcont/gemport/...)
                # serão processadas como inner content
                current_mng_onu = onu
                mng_state = {"gemports": [], "tconts": [], "services": [], "eth": []}
                continue

            # ------------------------------------------------------------ interface gpon X/Y/Z (ONU provisioning block)
            if m := RX_IF_GPON_PROV.match(line):
                current_pon_iface = m.group(1)
                continue

            if current_pon_iface and (m := RX_ONU_BLOCK.match(line)):
                onu_id = safe_int(m.group(1)) or 0
                comps = parse_interface_path(current_pon_iface)
                pon_iface = f"gpon_olt-{current_pon_iface}"
                pon = next((p for p in config.pons if p.interface == pon_iface), None)
                if pon is None:
                    pon = PON(
                        interface=pon_iface,
                        slot=comps.get("slot"),
                        port=comps.get("port"),
                    )
                    config.pons.append(pon)
                onu = next((o for o in pon.onus if o.onu_id == onu_id), None)
                if onu is None:
                    onu = ONU(
                        pon_interface=pon_iface,
                        onu_id=onu_id,
                        slot=comps.get("slot"),
                        pon_port=comps.get("port"),
                    )
                    pon.onus.append(onu)
                    config.onus.append(onu)
                current_onu = onu
                continue

            # ------------------------------------------------------------ ONU details
            if current_onu and (m := RX_SN.match(line)):
                current_onu.serial_number = m.group(1)
                continue

            if current_onu and (m := RX_SP_LP.search(line)):
                current_onu.service_profile_name = m.group(1)
                current_onu.line_profile_name = m.group(2)
                continue

            if current_onu and (m := RX_NATIVE_VLAN.search(line)):
                vid = safe_int(m.group(1))
                if vid is not None:
                    current_onu.native_vlan = vid
                continue

            if current_onu and (m := RX_ETH_BLOCK.match(line)):
                pid = safe_int(m.group(1)) or 1
                eth = next(
                    (e for e in current_onu.eth_ports if e.port_id == pid),
                    None,
                )
                if eth is None:
                    eth = EthernetPort(port_id=pid)
                    current_onu.eth_ports.append(eth)
                current_eth = eth
                continue

            # Dentro de bloco ethernet
            if current_eth:
                if RX_NEGOTIATION.match(line):
                    current_eth.negotiation_auto = True
                    continue
                if RX_NO_SHUTDOWN.match(line):
                    current_eth.admin_state = AdminState.UP
                    continue
                if RX_SHUTDOWN.match(line):
                    current_eth.admin_state = AdminState.DOWN
                    continue
                if m := RX_NATIVE_VLAN.search(line):
                    vid = safe_int(m.group(1))
                    if vid is not None:
                        current_eth.native_vlan = vid
                    continue

            # ------------------------------------------------------------ uplink details
            if current_uplink:
                if RX_NO_SHUTDOWN.match(line):
                    current_uplink.admin_state = AdminState.UP
                    current_uplink.enabled = True
                    continue
                if RX_SHUTDOWN.match(line):
                    current_uplink.admin_state = AdminState.DOWN
                    current_uplink.enabled = False
                    continue
                if m := RX_DESC.match(line):
                    current_uplink.description = m.group(1).strip()
                    continue

            # ------------------------------------------------------------ vlan X block
            if (m := RX_VLAN_DEF.match(line)) and not stripped.lower().startswith("interface"):
                vid = safe_int(m.group(1)) or 0
                vlan = next((v for v in config.vlans if v.id == vid), None)
                if vlan is None:
                    vlan = VLAN(id=vid, smart=False)
                    config.vlans.append(vlan)
                in_vlan_block = vlan
                continue

            if in_vlan_block and (m := RX_VLAN_NAME.match(line)):
                in_vlan_block.name = m.group(1).strip()
                continue

            # ------------------------------------------------------------ service-port
            if m := RX_SERVICE_PORT.match(line):
                action_str = m.group(6).lower()
                try:
                    action_enum = ServicePortAction(action_str)
                except ValueError:
                    action_enum = ServicePortAction.REPLACE
                user_vlan = safe_int(m.group(8)) if m.group(8) else None
                config.service_ports.append(
                    ServicePort(
                        service_port_id=safe_int(m.group(1)) or 0,
                        pon_interface=f"gpon_olt-{m.group(2)}",
                        onu_id=safe_int(m.group(3)) or 0,
                        gem_id=safe_int(m.group(4)),
                        match_vlan=safe_int(m.group(5)),
                        action=action_enum,
                        target_vlan=safe_int(m.group(7)),
                        user_vlan=user_vlan,
                    )
                )
                continue

            # ------------------------------------------------------------ service-port vport (forma comum no backup real)
            if m := RX_SERVICE_PORT_VPORT.match(line):
                config.service_ports.append(
                    ServicePort(
                        service_port_id=safe_int(m.group(1)) or 0,
                        pon_interface="(vport)",
                        onu_id=safe_int(m.group(2)) or 0,
                        gem_id=None,
                        match_vlan=safe_int(m.group(4)),
                        action=ServicePortAction.REPLACE,
                        target_vlan=safe_int(m.group(4)),
                        user_vlan=safe_int(m.group(3)),
                    )
                )
                continue

            # ------------------------------------------------------------ pon-onu-mng OR interface gpon-onu_ (ZTE C600 syntax nova)
            mng_match = RX_PON_ONU_MNG.match(line) or RX_IF_GPON_ONU_BLOCK.match(line)
            if mng_match:
                pon_path = mng_match.group(1)
                onu_id = safe_int(mng_match.group(2)) or 0
                pon_iface = f"gpon_olt-{pon_path}"
                onu = next(
                    (o for o in config.onus
                     if o.pon_interface == pon_iface and o.onu_id == onu_id),
                    None,
                )
                if onu is None:
                    pon = next((p for p in config.pons if p.interface == pon_iface), None)
                    if pon is None:
                        pon = PON(interface=pon_iface, port_type=PortType.GPON)
                        config.pons.append(pon)
                    onu = ONU(pon_interface=pon_iface, onu_id=onu_id)
                    pon.onus.append(onu)
                    config.onus.append(onu)
                current_mng_onu = onu
                mng_state = {"gemports": [], "tconts": [], "services": [], "eth": []}
                # Como reaproveitamos o "interface" para entrar no bloco mng,
                # invalidamos current_pon_iface para não capturar block-end errado
                continue

            # ------------------------------------------------------------ onu N type X sn Y (ZTE bridge config-mode)
            if m := RX_ONU_TYPE_SN.match(line):
                if current_pon_iface:
                    pon_iface = f"gpon_olt-{current_pon_iface}"
                    onu_id = safe_int(m.group(1)) or 0
                    onu_type = m.group(2)
                    sn = m.group(3)
                    onu = next(
                        (o for o in config.onus
                         if o.pon_interface == pon_iface and o.onu_id == onu_id),
                        None,
                    )
                    if onu is None:
                        pon = next((p for p in config.pons if p.interface == pon_iface), None)
                        if pon is None:
                            pon = PON(interface=pon_iface, port_type=PortType.GPON)
                            config.pons.append(pon)
                        onu = ONU(pon_interface=pon_iface, onu_id=onu_id)
                        pon.onus.append(onu)
                        config.onus.append(onu)
                    onu.onu_type = onu_type
                    onu.serial_number = sn
                continue

            # ------------------------------------------------------------ Conteúdo dentro do pon-onu-mng block
            if current_mng_onu:
                if m := RX_GEMPORT_TCONT.match(line):
                    from app.models import GEMPort
                    current_mng_onu.gemports.append(
                        GEMPort(
                            gem_id=safe_int(m.group(1)) or 0,
                            name=m.group(2),
                            tcont_id=safe_int(m.group(3)) or 0,
                        )
                    )
                    continue
                if m := RX_TCONT_PROFILE.match(line):
                    from app.models import TCONT
                    current_mng_onu.tconts.append(
                        TCONT(
                            tcont_id=safe_int(m.group(1)) or 0,
                            name=m.group(2),
                            dba_profile_name=m.group(3),
                        )
                    )
                    continue
                if RX_TCONT_GAP.match(line):
                    continue   # ignora detalhes de gap
                if m := RX_SERVICE_GEMPORT.match(line):
                    # service NAME gemport N vlan N → binding implícito do
                    # service-port (futura síntese)
                    name = m.group(1)
                    gid = safe_int(m.group(2)) or 0
                    vid = safe_int(m.group(3)) or 0
                    # Atribui VLAN ao gemport correspondente
                    for g in current_mng_onu.gemports:
                        if g.gem_id == gid:
                            g.vlan_id = vid
                            g.name = g.name or name
                    continue
                if m := RX_SWITCHPORT_BIND.match(line):
                    eth_id = safe_int(m.group(1)) or 1
                    # cria EthernetPort se ainda não existir
                    eth = next(
                        (e for e in current_mng_onu.eth_ports if e.port_id == eth_id),
                        None,
                    )
                    if eth is None:
                        eth = EthernetPort(port_id=eth_id)
                        current_mng_onu.eth_ports.append(eth)
                    current_mng_onu.extra_vendor.setdefault("switchport_bind", []).append({
                        "eth": eth_id, "bind_type": m.group(2), "bind_id": safe_int(m.group(3)),
                    })
                    continue
                if m := RX_VLAN_PORT_ETH.match(line):
                    eth_id = safe_int(m.group(1)) or 1
                    mode = m.group(2).lower()
                    vid = safe_int(m.group(3)) or 0
                    eth = next(
                        (e for e in current_mng_onu.eth_ports if e.port_id == eth_id),
                        None,
                    )
                    if eth is None:
                        eth = EthernetPort(port_id=eth_id)
                        current_mng_onu.eth_ports.append(eth)
                    if mode == "tag":
                        if vid not in eth.tagged_vlans:
                            eth.tagged_vlans.append(vid)
                    elif mode == "untag":
                        eth.native_vlan = vid
                    continue
                if RX_DHCP_ETHUNI.match(line):
                    continue
                if RX_DHCP_INTERNET.match(line):
                    continue
                if RX_SN_BIND.match(line):
                    continue
                if RX_SECURITY_MGMT.match(line) or RX_TR069_MGMT.match(line) or RX_FIREWALL.match(line):
                    continue
                if RX_WIFI_BLOCK.match(line):
                    current_mng_onu.wifi_enabled = True
                    continue
                # description / name livres atribuem à ONU
                if m := RX_DESC_FREE.match(line):
                    current_mng_onu.description = m.group(1).strip()
                    continue
                if m := RX_NAME_FREE.match(line):
                    if not current_mng_onu.description:
                        current_mng_onu.description = m.group(1).strip()
                    continue
                # service NAME gemport N cos N vlan N
                if m := RX_SERVICE_GEMPORT_COS.match(line):
                    gid = safe_int(m.group(2)) or 0
                    vid = safe_int(m.group(4)) or 0
                    for g in current_mng_onu.gemports:
                        if g.gem_id == gid:
                            g.vlan_id = vid
                    continue
                # ont port route
                if RX_ONT_PORT_ROUTE.match(line):
                    current_mng_onu.extra_vendor.setdefault("port_routes", []).append(stripped)
                    continue
                # WAN binding / WAN service host
                if RX_WAN_BIND.match(line) or RX_WAN_HOST.match(line):
                    current_mng_onu.extra_vendor.setdefault("wan_bindings", []).append(stripped)
                    continue
                # PPPoE per ONU
                if m := RX_PPPOE_ONU.match(line):
                    current_mng_onu.mode = OperationMode.PPPOE
                    current_mng_onu.extra_vendor.setdefault("pppoe", []).append({
                        "index": safe_int(m.group(1)),
                        "nat": m.group(2),
                        "user": m.group(3),
                        "password_present": m.group(4) != "null",
                    })
                    continue
                # SSID per ONU
                if m := RX_SSID_AUTH.match(line):
                    current_mng_onu.wifi_enabled = True
                    current_mng_onu.extra_vendor.setdefault("ssids", []).append({
                        "radio": safe_int(m.group(1)),
                        "auth": m.group(2),
                        "encrypt": m.group(3),
                        "key_present": m.group(4) != "null",
                    })
                    continue
                # Wave 2 — tcont N dba-profile-id N (sintaxe alternativa)
                if m := RX_TCONT_DBA_ID.match(line):
                    from app.models import TCONT
                    tid = safe_int(m.group(1)) or 0
                    dba_id = safe_int(m.group(2)) or 0
                    existing = next(
                        (t for t in current_mng_onu.tconts if t.tcont_id == tid),
                        None,
                    )
                    if existing is None:
                        current_mng_onu.tconts.append(
                            TCONT(tcont_id=tid, dba_profile_id=dba_id)
                        )
                    else:
                        existing.dba_profile_id = dba_id
                    continue
                # Wave 2 — gem add N eth tcont N (Huawei-style line-profile content)
                if m := RX_GEM_ADD_ETH.match(line):
                    from app.models import GEMPort
                    current_mng_onu.gemports.append(
                        GEMPort(
                            gem_id=safe_int(m.group(1)) or 0,
                            tcont_id=safe_int(m.group(2)) or 0,
                        )
                    )
                    continue
                # Wave 2 — gem mapping N N vlan N (mapeamento VLAN→GEM)
                if m := RX_GEM_MAPPING.match(line):
                    gid = safe_int(m.group(1)) or 0
                    vid = safe_int(m.group(3)) or 0
                    for g in current_mng_onu.gemports:
                        if g.gem_id == gid:
                            g.vlan_id = vid
                    continue
                # Wave 2 — flow / vlan-filter / vlan wan
                if (RX_FLOW_MODE.match(line) or RX_FLOW_RULE.match(line)
                        or RX_GEMPORT_FLOW.match(line) or RX_VLAN_WAN_TAG.match(line)
                        or RX_VLAN_FILTER.match(line) or RX_VLAN_FILTER_MODE.match(line)):
                    # Marca como capturado mas sem modelagem rica ainda
                    current_mng_onu.extra_vendor.setdefault("raw_flow_rules", []).append(stripped)
                    continue
                # Wave 2 — loop-detect ethuni
                if m := RX_LOOP_DETECT.match(line):
                    eth_id = safe_int(m.group(1)) or 1
                    eth = next(
                        (e for e in current_mng_onu.eth_ports if e.port_id == eth_id),
                        None,
                    )
                    if eth is None:
                        eth = EthernetPort(port_id=eth_id)
                        current_mng_onu.eth_ports.append(eth)
                    enabled = m.group(2).lower() in {"enable", "on"}
                    eth_extra = current_mng_onu.extra_vendor.setdefault("loop_detect", {})
                    eth_extra[eth_id] = enabled
                    continue

            # ------------------------------------------------------------ vlan port eth_0/N mode tag vlan N (fora do mng)
            if m := RX_VLAN_PORT_ETH.match(line):
                continue   # já tratado dentro do mng; fora dele é noise

            # ------------------------------------------------------------ interface vport-X/Y.Z:N (declaração de VPORT)
            if RX_IF_VPORT.match(line):
                # Já capturado pelo service-port vport equivalente; ignora
                continue

            # ------------------------------------------------------------ service-port simplificado (3º dialeto)
            if m := RX_SERVICE_PORT_ALT.match(line):
                config.service_ports.append(
                    ServicePort(
                        service_port_id=safe_int(m.group(1)) or 0,
                        pon_interface="(alt)",
                        onu_id=0,
                        match_vlan=safe_int(m.group(3)),
                        action=ServicePortAction.REPLACE,
                        target_vlan=safe_int(m.group(3)),
                        user_vlan=safe_int(m.group(2)),
                    )
                )
                continue

            # ------------------------------------------------------------ sntp / dns / outros globais (noise)
            if RX_SNTP.match(line):
                continue

            # ------------------------------------------------------------ fragmentos de uma letra (s, r069, etc.)
            if RX_GARBAGE_FRAG.match(line):
                continue

            # ------------------------------------------------------------ noise / unhandled
            if stripped and not stripped.startswith(("!", "#")):
                unparsed.append(line)

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info("zte_parse_done", hostname=config.hostname, stats=config.stats())
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
