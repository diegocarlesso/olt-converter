"""
Parser Fiberhome WOS (AN5516-04/06, AN5006, AN5116-06B)
=======================================================

Cobre a sintaxe real do firmware WOS observada em backups de produção
(`BACKUP-FIBERHOME.txt`). Mapeia para o modelo universal preservando:

  - Hierarquia: PON → ONU (via slot/port/onu_id no whitelist)
  - Bindings: ONU → ONUType (via `ty` em set white phy addr)
  - ServiceVLAN como entidade lógica separada das VLANs simples
  - Boards com tipo de card (gpon-line | switch | uplink | fan | power)
  - Uplinks com slot/port/admin/interface-type
  - Static routes, RADIUS, users, QoS attachments
  - Management VLAN com IP atribuído

Tudo não-reconhecido vai para `raw_unparsed`.
"""
from __future__ import annotations

import re
from typing import Optional

from app.models import (
    AAAConfig,
    AdminState,
    Board,
    DBAType,
    LACPMode,
    OLTConfig,
    ONU,
    ONUTypeProfile,
    OperationMode,
    PON,
    PortConfig,
    PortType,
    QoSAttachment,
    RadiusServer,
    ServicePort,
    ServiceProfile,
    ServiceType,
    ServiceVLAN,
    StaticRoute,
    TrunkMode,
    Uplink,
    User,
    Vendor,
    VLAN,
    VLANMode,
)
from app.parsers.base import BaseParser, ParserResult
from app.parsers.registry import register_parser
from app.utils.logger import get_logger
from app.utils.text import safe_int

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Regex (todos pré-compilados; nomeados para clareza)
# ---------------------------------------------------------------------------
RX_SYS_NAME = re.compile(r"^\s*!\s*system\s+name\s*:\s*(.+?)\s*$", re.IGNORECASE)
RX_HOSTNAME = re.compile(r"^\s*hostname\s+(\S+)", re.IGNORECASE)

RX_CARD = re.compile(r"^\s*set\s+card_auth\s+slot\s+(\d+)\s+type\s+(\S+)", re.IGNORECASE)
RX_UPLINK_STATE = re.compile(
    r"^\s*set\s+uplink\s+slot\s+(\d+)\s+port\s+(\d+)\s+(enable|disable)\s*$", re.IGNORECASE
)
RX_UPLINK_IFACE = re.compile(
    r"^\s*set\s+uplink\s+slot\s+(\d+)\s+port\s+(\d+)\s+Interface\s+(\S+)", re.IGNORECASE
)
RX_MGMT_VLAN = re.compile(r"^\s*set\s+manage_vlan\s+(\d+)\s+(\S+)", re.IGNORECASE)
RX_MGMT_VLAN_IP = re.compile(
    r"^\s*set\s+manage\s+vlan\s+name\s+(\S+)\s+ip\s+(\S+)", re.IGNORECASE
)
RX_ADD_VLAN_UP = re.compile(
    r"^\s*add\s+vlan\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)\s+(tag|untag)\s+uplink\s+slot\s+(\d+)\s+port\s+(\d+)",
    re.IGNORECASE,
)
RX_ADD_VLAN_ALL = re.compile(
    r"^\s*add\s+vlan\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)\s+(tag|untag)\s+allslot\s+(\d+)",
    re.IGNORECASE,
)
RX_SVC_CREATE = re.compile(r"^\s*create\s+service_vlan\s+(\d+)", re.IGNORECASE)
RX_SVC_META = re.compile(
    r"^\s*set\s+service_vlan\s+(\d+)\s+(\S+)\s+type\s+(\S+)", re.IGNORECASE
)
RX_SVC_RANGE = re.compile(
    r"^\s*set\s+service_vlan\s+(\d+)\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)",
    re.IGNORECASE,
)
RX_STATIC_ROUTE = re.compile(
    r"^\s*add\s+static\s+route\s+destination\s+(\S+)\s+gateway\s+(\S+)\s+mask\s+(\S+)",
    re.IGNORECASE,
)
RX_RADIUS_IP = re.compile(
    r"^\s*radius\s+server\s+ip-address\s+(\S+)\s+key\s+(\S+)", re.IGNORECASE
)
RX_RADIUS_PARAM = re.compile(
    r"^\s*radius\s+server\s+ip-address\s+(\S+)\s+(auth-port|acct-port|timeout|retransmit)\s+(\S+)",
    re.IGNORECASE,
)
RX_RADIUS_BIND = re.compile(r"^\s*radius\s+server\s+bind\s+(\S+)", re.IGNORECASE)
RX_USER_ADD = re.compile(
    r"^\s*user\s+add\s+(\S+)\s+login-password\s+(\S+)", re.IGNORECASE
)
RX_USER_ROLE = re.compile(
    r"^\s*user\s+role\s+(\S+)\s+(\S+)\s+enable-password\s+(\S+)", re.IGNORECASE
)
RX_CS_PROFILE = re.compile(
    r"^\s*add\s+cs\s+onu\s+profile\s+name\s+(\S+)\s+onutype\s+(\d+)\s+pontype\s+(\d+)"
    r"(?:\s+onucapa\s+(\d+))?(?:\s+lan1g\s+(\d+))?(?:\s+lan10g\s+(\d+))?"
    r"(?:\s+pots\s+(\d+))?",
    re.IGNORECASE,
)
RX_CS_PROFILE_OPT = re.compile(
    r"^\s*add\s+cs\s+onu\s+profile\s+option\s+(\S+)\s+(\S+)(?:\s+end)?",
    re.IGNORECASE,
)
RX_CS_PROFILE_EID = re.compile(
    r"^\s*add\s+cs\s+onu\s+profile\s+option\s+eid\s+(\S+)(?:\s+end)?",
    re.IGNORECASE,
)
RX_WHITE_PHY = re.compile(
    r"^\s*set\s+white\s+phy\s+addr\s+(\S+)\s+pas\s+(\S+)\s+ac\s+add\s+"
    r"sl\s+(\d+)\s+p\s+(\d+)\s+o\s+(\d+)\s+ty\s+(\S+)",
    re.IGNORECASE,
)
RX_QOS_ATTACH = re.compile(
    r"^\s*set\s+slot\s+(\d+)\s+port\s+(\d+)\s+attach(?:\s+(.+))?", re.IGNORECASE
)
RX_FDB_AGE = re.compile(r"^\s*set\s+fdb\s+agingtime\s+(\d+)", re.IGNORECASE)
RX_AAA_MODE = re.compile(r"^\s*aaa\s+accounting-mode\s+(\S+)", re.IGNORECASE)
RX_LINEID_CIRC = re.compile(r"^\s*set\s+circuit_id\s+format\s+(\S+)", re.IGNORECASE)
RX_LINEID_REMOTE = re.compile(r"^\s*set\s+remote_id\s+(\S+)", re.IGNORECASE)

# Noise: linhas que conhecemos e queremos descartar silenciosamente
_NOISE: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^\s*$",
        r"^\s*!.*$",
        r"^\s*-+\s*$",
        r"^\s*end\s*$",
        r"^\s*y\s*$",
        r"^\s*cli\s+debug\s+",
        r"^\s*idle-timeout\s+",
        r"^\s*terminal\s+length\s+",
        r"^\s*set\s+new\s+cmd\s+",
        r"^\s*set\s+auto_save\s+",
        r"^\s*set\s+sys_apply_flag\s+",
        r"^\s*set\s+optical-module\s+",
        r"^\s*set\s+upbak_trunk\s+",
        r"^\s*set\s+rx-down\s+",
        r"^\s*set\s+crc\s+protect\s+",
        r"^\s*set\s+priority\s+mode\s+",
        r"^\s*set\s+vlan\s+\d+\s+ipv4\s+mtu\s+",
        r"^\s*set\s+ld_macmv\s+",
        r"^\s*set\s+log\s+save_interval",
        r"^\s*raio-format\s+",
        r"^\s*set\s+dhcp\s+",
        r"^\s*set\s+arp\s+",
        r"^\s*set\s+pppoe",
        r"^\s*set\s+lineid",
        r"^\s*set\s+exception-",
        r"^\s*set\s+core-card",
        r"^\s*set\s+ftp\s+",
        r"^\s*set\s+hcu\s+",
        r"^\s*set\s+onu_ability_set_config\s+",
        r"^\s*set\s+version_cfg\s+",
        r"^\s*set\s+pppoe_white_list\s+",
        r"^\s*set\s+whitelist\s+reg\s+",
        r"^\s*add\s+servm\s+pro\s+",
        r"^\s*set\s+manage_vlan\s+\d+\s+ipv4",
        r"^\s*set\s+debugip\s+",
    ]
)

# Mapa de cartões Fiberhome → categoria semântica
_CARD_KIND: dict[str, str] = {
    "gc8b": "gpon-line",
    "gcob": "gpon-line",
    "hswa": "switch",
    "hu1a": "uplink",
    "fan": "fan",
    "pwr": "power",
}


def _is_noise(line: str) -> bool:
    return any(p.match(line) for p in _NOISE)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
@register_parser
class FiberhomeAN5516Parser(BaseParser):
    """Parser Fiberhome WOS — AN5516-04/06 e AN5006."""

    vendor = Vendor.FIBERHOME
    model_family = "AN5516"
    confidence_signatures: tuple[str, ...] = (
        "set service_vlan",
        "set card_auth slot",
        "set white phy addr",
        "set uplink slot",
        "add vlan vlan_begin",
        "create service_vlan",
        "fhtt",
        "module config:",
        "wos system config file",
        "add cs onu profile",
    )

    # ------------------------------------------------------------------ Entrada
    def parse(self, config_text: str) -> ParserResult:
        config = OLTConfig(vendor=self.vendor, model=self.model_family)
        warnings: list[str] = []
        unparsed: list[str] = []

        # Acumuladores ---------------------------------------------------
        seen_uplinks: dict[tuple[int, int], Uplink] = {}
        seen_pons: dict[tuple[int, int], PON] = {}
        partial_svc: dict[int, dict] = {}
        cs_profile_buf: Optional[ONUTypeProfile] = None
        pending_radius: dict[str, RadiusServer] = {}

        # Detecta firmware do header se presente
        if "WOS system config" in config_text:
            config.firmware = "WOS"

        for raw in config_text.splitlines():
            line = raw.rstrip()

            # hostname está em comentário Fiberhome
            if m := RX_SYS_NAME.match(line):
                config.hostname = m.group(1).strip()
                continue

            if _is_noise(line):
                continue

            if m := RX_HOSTNAME.match(line):
                config.hostname = m.group(1)
                continue

            # ------------ Boards ------------------------------------------
            if m := RX_CARD.match(line):
                slot = safe_int(m.group(1)) or 0
                board_type = m.group(2).lower()
                kind = _CARD_KIND.get(board_type, "unknown")
                config.boards.append(
                    Board(slot=slot, board_type=board_type, kind=kind)
                )
                # board GPON cria PON virtual em port=0 só pra fixar contexto
                if kind == "gpon-line":
                    pon_key = (slot, 0)
                    seen_pons.setdefault(
                        pon_key,
                        PON(
                            interface=f"pon-1/{slot}/0",
                            slot=slot,
                            port=0,
                            port_type=PortType.GPON,
                            description=f"AN5516 PON board ({board_type})",
                        ),
                    )
                continue

            # ------------ Uplinks -----------------------------------------
            if m := RX_UPLINK_STATE.match(line):
                slot = safe_int(m.group(1)) or 0
                port = safe_int(m.group(2)) or 0
                key = (slot, port)
                state = m.group(3).lower() == "enable"
                up = seen_uplinks.get(key) or Uplink(
                    interface=f"uplink-{slot}/{port}",
                    slot=slot,
                    port=port,
                    port_type=PortType.XGE,
                    mode=TrunkMode.TRUNK,
                )
                up.admin_state = AdminState.UP if state else AdminState.DOWN
                up.enabled = state
                seen_uplinks[key] = up
                continue

            if m := RX_UPLINK_IFACE.match(line):
                slot = safe_int(m.group(1)) or 0
                port = safe_int(m.group(2)) or 0
                key = (slot, port)
                up = seen_uplinks.get(key) or Uplink(
                    interface=f"uplink-{slot}/{port}",
                    slot=slot,
                    port=port,
                    port_type=PortType.XGE,
                )
                up.description = f"Interface: {m.group(3)}"
                seen_uplinks[key] = up
                continue

            # ------------ Management VLAN ---------------------------------
            if m := RX_MGMT_VLAN.match(line):
                vid = safe_int(m.group(1))
                if vid is not None:
                    config.vlans.append(
                        VLAN(
                            id=vid,
                            name=m.group(2),
                            is_management=True,
                            description="Management VLAN",
                            service_type=ServiceType.MANAGEMENT,
                        )
                    )
                continue

            if m := RX_MGMT_VLAN_IP.match(line):
                name = m.group(1)
                ipmask = m.group(2)
                ip, _, mask = ipmask.partition("/")
                vlan = next(
                    (
                        v
                        for v in config.vlans
                        if v.name == name and v.is_management
                    ),
                    None,
                )
                if vlan:
                    vlan.ip_address = ip
                    vlan.netmask = mask
                continue

            # ------------ VLAN ranges -------------------------------------
            if m := RX_ADD_VLAN_UP.match(line):
                start = safe_int(m.group(1)) or 0
                end = safe_int(m.group(2)) or start
                tagged = m.group(3).lower() == "tag"
                slot = safe_int(m.group(4)) or 0
                port = safe_int(m.group(5)) or 0
                key = (slot, port)
                up = seen_uplinks.setdefault(
                    key,
                    Uplink(
                        interface=f"uplink-{slot}/{port}",
                        slot=slot,
                        port=port,
                        port_type=PortType.XGE,
                        mode=TrunkMode.TRUNK,
                    ),
                )
                for vid in range(start, end + 1):
                    if vid not in up.allowed_vlans:
                        up.allowed_vlans.append(vid)
                    if not any(v.id == vid for v in config.vlans):
                        config.vlans.append(
                            VLAN(
                                id=vid,
                                mode=VLANMode.TAG if tagged else VLANMode.UNTAG,
                                smart=False,
                            )
                        )
                continue

            if m := RX_ADD_VLAN_ALL.match(line):
                start = safe_int(m.group(1)) or 0
                end = safe_int(m.group(2)) or start
                tagged = m.group(3).lower() == "tag"
                for vid in range(start, end + 1):
                    if not any(v.id == vid for v in config.vlans):
                        config.vlans.append(
                            VLAN(
                                id=vid,
                                mode=VLANMode.TAG if tagged else VLANMode.UNTAG,
                                smart=False,
                            )
                        )
                continue

            # ------------ Service VLANs -----------------------------------
            if m := RX_SVC_CREATE.match(line):
                sid = safe_int(m.group(1)) or 0
                partial_svc.setdefault(sid, {"service_id": sid})
                continue

            if m := RX_SVC_META.match(line):
                sid = safe_int(m.group(1)) or 0
                partial_svc.setdefault(sid, {"service_id": sid})
                partial_svc[sid]["name"] = m.group(2)
                stype = m.group(3).lower()
                partial_svc[sid]["service_type"] = (
                    ServiceType(stype) if stype in ServiceType._value2member_map_ else ServiceType.OTHER
                )
                continue

            if m := RX_SVC_RANGE.match(line):
                sid = safe_int(m.group(1)) or 0
                start = safe_int(m.group(2)) or 0
                end = safe_int(m.group(3)) or start
                pdata = partial_svc.setdefault(sid, {"service_id": sid})
                pdata["vlan_begin"] = start
                pdata["vlan_end"] = end
                # materializa a ServiceVLAN agora que temos os 3 dados
                if all(k in pdata for k in ("name", "service_type", "vlan_begin", "vlan_end")):
                    config.service_vlans.append(
                        ServiceVLAN(
                            service_id=pdata["service_id"],
                            name=pdata["name"],
                            service_type=pdata["service_type"],
                            vlan_begin=pdata["vlan_begin"],
                            vlan_end=pdata["vlan_end"],
                        )
                    )
                    # Marca as VLANs com link à service_vlan
                    for vid in range(pdata["vlan_begin"], pdata["vlan_end"] + 1):
                        existing = next((v for v in config.vlans if v.id == vid), None)
                        if existing:
                            existing.service_vlan_id = pdata["service_id"]
                            if not existing.name:
                                existing.name = pdata["name"]
                            existing.service_type = pdata["service_type"]
                        else:
                            config.vlans.append(
                                VLAN(
                                    id=vid,
                                    name=pdata["name"],
                                    service_type=pdata["service_type"],
                                    service_vlan_id=pdata["service_id"],
                                )
                            )
                continue

            # ------------ Static Routes -----------------------------------
            if m := RX_STATIC_ROUTE.match(line):
                config.static_routes.append(
                    StaticRoute(
                        destination=m.group(1),
                        gateway=m.group(2),
                        netmask=m.group(3),
                    )
                )
                continue

            # ------------ RADIUS -----------------------------------------
            if m := RX_RADIUS_IP.match(line):
                ip = m.group(1)
                key = m.group(2)
                rs = pending_radius.setdefault(ip, RadiusServer(ip_address=ip))
                rs.key = key
                continue
            if m := RX_RADIUS_PARAM.match(line):
                ip = m.group(1)
                param = m.group(2).lower()
                val = safe_int(m.group(3))
                rs = pending_radius.setdefault(ip, RadiusServer(ip_address=ip))
                if val is not None:
                    if param == "auth-port":
                        rs.auth_port = val
                    elif param == "acct-port":
                        rs.acct_port = val
                    elif param == "timeout":
                        rs.timeout_seconds = val
                    elif param == "retransmit":
                        rs.retransmit = val
                continue
            if m := RX_RADIUS_BIND.match(line):
                source = m.group(1)
                for rs in pending_radius.values():
                    rs.source_ip = source
                continue

            # ------------ Users -------------------------------------------
            if m := RX_USER_ADD.match(line):
                config.users.append(
                    User(username=m.group(1), password_hash=m.group(2))
                )
                continue
            if m := RX_USER_ROLE.match(line):
                u = next((u for u in config.users if u.username == m.group(1)), None)
                if u:
                    u.level = m.group(2).lower()
                continue

            # ------------ ONU Type Profile (cs profile) -------------------
            if m := RX_CS_PROFILE.match(line):
                cs_profile_buf = ONUTypeProfile(
                    type_id=safe_int(m.group(2)) or 0,
                    name=m.group(1),
                    onu_type_code=safe_int(m.group(2)),
                    pon_type_code=safe_int(m.group(3)),
                    capability_code=safe_int(m.group(4)),
                    lan1g=safe_int(m.group(5)) or 0,
                    lan10g=safe_int(m.group(6)) or 0,
                    pots=safe_int(m.group(7)) or 0,
                )
                config.onu_type_profiles.append(cs_profile_buf)
                # Também cria um ServiceProfile equivalente para preservar
                # a noção semântica de "tipo de cliente"
                config.service_profiles.append(
                    ServiceProfile(
                        profile_id=cs_profile_buf.type_id,
                        name=cs_profile_buf.name,
                        ports=PortConfig(
                            eth=cs_profile_buf.lan1g,
                            pots=cs_profile_buf.pots,
                        ),
                    )
                )
                continue

            if m := RX_CS_PROFILE_EID.match(line):
                if cs_profile_buf:
                    cs_profile_buf.eid = m.group(1)
                continue
            if m := RX_CS_PROFILE_OPT.match(line):
                if cs_profile_buf:
                    key, val = m.group(1).lower(), m.group(2)
                    if key == "wifi":
                        cs_profile_buf.wifi = safe_int(val) or 0
                    else:
                        cs_profile_buf.extra_vendor = getattr(cs_profile_buf, "extra_vendor", {}) or {}
                continue

            # ------------ ONUs whitelist ----------------------------------
            if m := RX_WHITE_PHY.match(line):
                serial = m.group(1)
                password = m.group(2)
                slot = safe_int(m.group(3)) or 0
                pon_port = safe_int(m.group(4)) or 0
                onu_id = safe_int(m.group(5)) or 0
                onu_type = m.group(6)
                pon_iface = f"pon-1/{slot}/{pon_port}"
                pon_key = (slot, pon_port)

                pon = seen_pons.get(pon_key)
                if pon is None:
                    pon = PON(
                        interface=pon_iface,
                        slot=slot,
                        port=pon_port,
                        port_type=PortType.GPON,
                    )
                    seen_pons[pon_key] = pon

                onu = ONU(
                    pon_interface=pon_iface,
                    onu_id=onu_id,
                    slot=slot,
                    pon_port=pon_port,
                    serial_number=serial,
                    password=None if password.lower() == "null" else password,
                    onu_type=onu_type,
                    line_profile_name=onu_type,    # vínculo lógico ao tipo
                    service_profile_name=onu_type,
                    mode=OperationMode.BRIDGE,
                )
                pon.onus.append(onu)
                config.onus.append(onu)
                continue

            # ------------ QoS attachments --------------------------------
            if m := RX_QOS_ATTACH.match(line):
                slot = safe_int(m.group(1)) or 0
                port = safe_int(m.group(2)) or 0
                raw_attach = m.group(3) or ""
                profiles = [
                    safe_int(tok) for tok in raw_attach.split() if safe_int(tok) is not None
                ]
                config.qos_attachments.append(
                    QoSAttachment(slot=slot, port=port, attached_profiles=[p for p in profiles if p is not None])
                )
                continue

            # ------------ Lineid / AAA ------------------------------------
            if RX_AAA_MODE.match(line) or RX_LINEID_CIRC.match(line) or RX_LINEID_REMOTE.match(line):
                # Capturados em campo de sistema simplificado
                if m := RX_LINEID_CIRC.match(line):
                    config.line_id.circuit_id_format = m.group(1)
                if m := RX_LINEID_REMOTE.match(line):
                    config.line_id.remote_id_enabled = m.group(1).lower() == "enable"
                if m := RX_AAA_MODE.match(line):
                    config.aaa.accounting_mode = m.group(1)
                continue

            # FDB aging — não temos campo no modelo, ignora
            if RX_FDB_AGE.match(line):
                continue

            # Linha não-mapeada
            stripped = line.strip()
            if stripped:
                unparsed.append(line)

        # Consolida acumuladores ----------------------------------------
        config.uplinks = sorted(seen_uplinks.values(), key=lambda u: (u.slot or 0, u.port or 0))
        config.pons = sorted(seen_pons.values(), key=lambda p: (p.slot or 0, p.port or 0))
        config.radius_servers = list(pending_radius.values())

        config.parse_warnings = warnings
        config.raw_unparsed = unparsed
        log.info(
            "fiberhome_wos_parse_done",
            hostname=config.hostname,
            stats=config.stats(),
        )
        return ParserResult(config=config, warnings=warnings, unparsed_lines=unparsed)
