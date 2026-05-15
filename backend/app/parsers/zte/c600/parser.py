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
    r"^\s*interface\s+gpon_olt-(\d+/\d+/\d+)", re.IGNORECASE
)
RX_IF_ONU_DECL = re.compile(
    r"^\s*interface\s+gpon_onu-(\d+/\d+/\d+):(\d+)", re.IGNORECASE
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

        for line in iter_clean_lines(config_text):
            stripped = line.strip()

            # ------------------------------------------------------------ end
            if RX_BLOCK_END.match(line):
                # Termina blocos (gpon→onu→eth fecha de fora pra dentro)
                if current_eth is not None:
                    current_eth = None
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
                if not any(o.onu_id == onu_id for o in pon.onus):
                    onu = ONU(
                        pon_interface=pon_iface,
                        onu_id=onu_id,
                        slot=comps.get("slot"),
                        pon_port=comps.get("port"),
                    )
                    pon.onus.append(onu)
                    config.onus.append(onu)
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

            # ------------------------------------------------------------ noise / unhandled
            if stripped and not stripped.startswith(("!", "#")):
                unparsed.append(line)

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info("zte_parse_done", hostname=config.hostname, stats=config.stats())
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
