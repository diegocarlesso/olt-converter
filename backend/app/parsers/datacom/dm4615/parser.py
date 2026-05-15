"""
Parser Datacom DM4615 / DM4610 (DmOS)
=====================================

DmOS é hierárquico, indentado (similar a Cisco/Juniper). Estrutura típica:

    hostname OLT-DATACOM
    !
    dot1q
     vlan 100
      name CLIENTES
     !
    !
    interface ten-gigabit-ethernet 1/1/9
     description UPLINK
     no shutdown
    !
    gpon
     profile dba DBA-DADOS
      maximum-bandwidth 1024000
     !
     profile t-cont TC-1G dba DBA-DADOS
     !
     profile gem-port GEM-100 t-cont TC-1G
     !
     profile onu BRIDGE-100
      mapper 1
       gem-port GEM-100 vlan 100
      !
     !
     interface gpon 1/1/1
      onu 1 serial-number DACMxxxxxxxx
       profile BRIDGE-100
      !
     !
    !
"""
from __future__ import annotations

import re
from typing import Optional

from app.models import (
    DBAProfile,
    DBAType,
    LineProfile,
    OLTConfig,
    ONU,
    PON,
    PortType,
    ServicePort,
    ServiceProfile,
    Uplink,
    Vendor,
    VLAN,
)
from app.parsers.base import BaseParser, ParserResult
from app.parsers.registry import register_parser
from app.utils.logger import get_logger
from app.utils.text import iter_clean_lines, safe_int

log = get_logger(__name__)

RX_HOSTNAME = re.compile(r"^\s*hostname\s+(\S+)", re.IGNORECASE)
RX_VLAN = re.compile(r"^\s*vlan\s+(\d+)\s*$", re.IGNORECASE)
RX_NAME = re.compile(r"^\s*name\s+(.+?)\s*$", re.IGNORECASE)
RX_IF_GPON = re.compile(r"^\s*interface\s+gpon\s+(\d+/\d+/\d+)", re.IGNORECASE)
RX_IF_TEN = re.compile(
    r"^\s*interface\s+(ten-gigabit-ethernet|gigabit-ethernet|hundred-gigabit-ethernet)\s+(\d+/\d+/\d+)",
    re.IGNORECASE,
)
RX_DBA_PROFILE = re.compile(r"^\s*profile\s+dba\s+(\S+)", re.IGNORECASE)
RX_MAX_BW = re.compile(r"^\s*maximum-bandwidth\s+(\d+)", re.IGNORECASE)
RX_ASSURED_BW = re.compile(r"^\s*assured-bandwidth\s+(\d+)", re.IGNORECASE)
RX_FIX_BW = re.compile(r"^\s*fixed-bandwidth\s+(\d+)", re.IGNORECASE)
RX_TCONT_PROFILE = re.compile(
    r"^\s*profile\s+t-cont\s+(\S+)\s+dba\s+(\S+)", re.IGNORECASE
)
RX_GEM_PROFILE = re.compile(
    r"^\s*profile\s+gem-port\s+(\S+)\s+t-cont\s+(\S+)", re.IGNORECASE
)
RX_ONU_PROFILE = re.compile(r"^\s*profile\s+onu\s+(\S+)", re.IGNORECASE)
RX_ONU_LINE = re.compile(
    r"^\s*onu\s+(\d+)\s+serial-number\s+(\S+)", re.IGNORECASE
)
RX_PROFILE_REF = re.compile(r"^\s*profile\s+(\S+)\s*$", re.IGNORECASE)


@register_parser
class DatacomDM4615Parser(BaseParser):
    vendor = Vendor.DATACOM
    model_family = "DM4615"
    confidence_signatures: tuple[str, ...] = (
        "dmos",
        "datacom",
        "ten-gigabit-ethernet",
        "profile gem-port",
        "profile t-cont",
        "profile onu",
        "interface gpon ",
    )

    def parse(self, config_text: str) -> ParserResult:
        config = OLTConfig(vendor=self.vendor, model=self.model_family)
        warnings: list[str] = []
        unparsed: list[str] = []

        # Contexto pilha (DmOS é indentado; vamos rastrear blocos por '!')
        current_vlan: Optional[VLAN] = None
        current_dba: Optional[DBAProfile] = None
        current_pon: Optional[PON] = None
        current_uplink: Optional[Uplink] = None
        current_onu_profile: Optional[ServiceProfile] = None
        current_onu: Optional[ONU] = None

        for line in iter_clean_lines(config_text):
            stripped = line.strip()

            if stripped == "!":
                current_vlan = None
                current_dba = None
                current_pon = None
                current_uplink = None
                current_onu_profile = None
                current_onu = None
                continue

            if m := RX_HOSTNAME.match(line):
                config.hostname = m.group(1)
                continue

            if m := RX_VLAN.match(line):
                vid = safe_int(m.group(1))
                if vid is not None:
                    current_vlan = VLAN(id=vid)
                    config.vlans.append(current_vlan)
                continue

            if current_vlan and (m := RX_NAME.match(line)):
                current_vlan.name = m.group(1).strip()
                continue

            if m := RX_IF_GPON.match(line):
                path = m.group(1)
                parts = path.split("/")
                slot = safe_int(parts[1]) if len(parts) > 1 else None
                port = safe_int(parts[2]) if len(parts) > 2 else None
                pon = PON(
                    interface=f"gpon {path}",
                    slot=slot,
                    port=port,
                )
                config.pons.append(pon)
                current_pon = pon
                continue

            if m := RX_IF_TEN.match(line):
                tech, path = m.group(1).lower(), m.group(2)
                parts = path.split("/")
                slot = safe_int(parts[1]) if len(parts) > 1 else None
                port = safe_int(parts[2]) if len(parts) > 2 else None
                pt = (
                    PortType.XGE if "ten" in tech
                    else PortType.XXGE if "hundred" in tech
                    else PortType.GE
                )
                u = Uplink(
                    interface=f"{tech} {path}",
                    slot=slot,
                    port=port,
                    port_type=pt,
                )
                config.uplinks.append(u)
                current_uplink = u
                continue

            if m := RX_DBA_PROFILE.match(line):
                current_dba = DBAProfile(
                    profile_id=len(config.dba_profiles) + 1,
                    name=m.group(1),
                    type=DBAType.TYPE4,
                )
                config.dba_profiles.append(current_dba)
                continue

            if current_dba:
                if m := RX_MAX_BW.match(line):
                    current_dba.max_bandwidth = safe_int(m.group(1))
                    continue
                if m := RX_ASSURED_BW.match(line):
                    current_dba.assured_bandwidth = safe_int(m.group(1))
                    if current_dba.max_bandwidth:
                        current_dba.type = DBAType.TYPE3
                    else:
                        current_dba.type = DBAType.TYPE2
                    continue
                if m := RX_FIX_BW.match(line):
                    current_dba.fix_bandwidth = safe_int(m.group(1))
                    current_dba.type = DBAType.TYPE1
                    continue

            if m := RX_TCONT_PROFILE.match(line):
                # T-CONT é um conceito de line-profile em DmOS; criamos um LineProfile
                # se ainda não existir e adicionamos o binding
                tname, dba_name = m.group(1), m.group(2)
                lp = next((p for p in config.line_profiles if p.name == tname), None)
                if lp is None:
                    lp = LineProfile(
                        profile_id=len(config.line_profiles) + 1,
                        name=tname,
                    )
                    config.line_profiles.append(lp)
                lp.tcont_bindings.append({"tcont_id": 1, "dba_profile_name": dba_name})
                continue

            if m := RX_GEM_PROFILE.match(line):
                gname, tname = m.group(1), m.group(2)
                lp = next((p for p in config.line_profiles if p.name == tname), None)
                if lp is None:
                    lp = LineProfile(
                        profile_id=len(config.line_profiles) + 1,
                        name=tname,
                    )
                    config.line_profiles.append(lp)
                lp.gemport_bindings.append(
                    {"gem_id": len(lp.gemport_bindings) + 1, "name": gname, "tcont_id": 1}
                )
                continue

            if m := RX_ONU_PROFILE.match(line):
                sp = ServiceProfile(
                    profile_id=len(config.service_profiles) + 1,
                    name=m.group(1),
                )
                config.service_profiles.append(sp)
                current_onu_profile = sp
                continue

            if current_pon and (m := RX_ONU_LINE.match(line)):
                onu_id = safe_int(m.group(1)) or 0
                onu = ONU(
                    pon_interface=current_pon.interface,
                    onu_id=onu_id,
                    serial_number=m.group(2),
                    slot=current_pon.slot,
                    pon_port=current_pon.port,
                )
                current_pon.onus.append(onu)
                config.onus.append(onu)
                current_onu = onu
                continue

            if current_onu and (m := RX_PROFILE_REF.match(line)):
                pname = m.group(1)
                current_onu.service_profile_name = pname
                continue

            if stripped and not stripped.startswith("!"):
                unparsed.append(line)

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info("datacom_parse_done", hostname=config.hostname, stats=config.stats())
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
