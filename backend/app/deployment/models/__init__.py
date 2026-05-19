"""
Deployment Topology Models — L2

Modelos do hardware e topologia do OLT destino.
Baseados no spec de DEPLOYMENT_TARGET_ARCHITECTURE.md §3.1.

Status: SKELETON — tipos definidos, sem lógica de negócio.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class FrameKind(str, Enum):
    MAIN = "main"
    EXPANSION = "expansion"
    STANDALONE = "standalone"


class SlotKind(str, Enum):
    CONTROL = "control"
    UPLINK = "uplink"
    SERVICE = "service"
    PON = "pon"
    POWER = "power"
    FAN = "fan"
    RESERVED = "reserved"


class BoardKind(str, Enum):
    GPON_LINE = "gpon_line"
    XGSPON_LINE = "xgspon_line"
    UPLINK = "uplink"
    CONTROL = "control"
    SERVICE_SWITCH = "service_switch"
    POWER = "power"
    FAN = "fan"


class PortKind(str, Enum):
    GPON = "gpon"
    XGSPON = "xgspon"
    ETHERNET = "ethernet"
    SFP = "sfp"
    XFP = "xfp"
    QSFP = "qsfp"


class OperationalState(str, Enum):
    NORMAL = "normal"
    FAULT = "fault"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class LogicalPortKind(str, Enum):
    LAG = "lag"
    SVI = "svi"
    TUNNEL = "tunnel"


class ProfileLifecycle(str, Enum):
    """Lifecycle states para profiles deployáveis (§9)."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    LINKED = "linked"
    FROZEN = "frozen"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ProfileOrigin(str, Enum):
    """Como o profile entrou no catálogo (§9.4)."""
    IMPORTED = "imported"
    SYNTHESISED = "synthesised"
    CLONED = "cloned"
    MANUAL = "manual"
    PROMOTED = "promoted"


class ConstraintKind(str, Enum):
    SLOT_RESERVED = "slot_reserved"
    BOARD_FORBIDDEN = "board_forbidden"
    UPLINK_REQUIRED = "uplink_required"
    NUMBERING_RULE = "numbering_rule"
    PROFILE_RULE = "profile_rule"


class IdNamespace(str, Enum):
    SERVICE_PORT = "service_port"
    DBA_PROFILE = "dba_profile"
    ONT_LINEPROFILE = "ont_lineprofile"
    ONT_SRVPROFILE = "ont_srvprofile"
    TRAFFIC_TABLE = "traffic_table"
    WAN_PROFILE = "wan_profile"


# ── Models ───────────────────────────────────────────────────────────────

class PortAddr(BaseModel):
    """Endereço físico de uma porta: (chassis, slot, port_index)."""
    chassis: int = 0
    slot: int
    port_index: int


class IdRange(BaseModel):
    """Range de IDs permitido por um namespace."""
    min_id: int
    max_id: int
    reserved: list[int] = Field(default_factory=list)


class NumberingRules(BaseModel):
    """Regras de numeração por vendor/modelo (§3.1)."""
    interface_format: dict[str, str] = Field(default_factory=dict)
    id_ranges: dict[str, IdRange] = Field(default_factory=dict)
    reserved_ids: dict[str, list[int]] = Field(default_factory=dict)
    naming_conventions: dict[str, str] = Field(default_factory=dict)


class PhysicalPort(BaseModel):
    """Porta física de um board."""
    port_id: PortAddr
    port_kind: PortKind
    speed_capability: list[str] = Field(default_factory=list)
    admin_state: str = "up"
    description: Optional[str] = None


class DeploymentBoard(BaseModel):
    """Board instalado em um slot do chassis."""
    slot_id: int
    board_type: str
    board_kind: BoardKind
    port_count: int = 0
    admin_state: str = "up"
    operational_state: OperationalState = OperationalState.UNKNOWN
    ports: list[PhysicalPort] = Field(default_factory=list)


class Slot(BaseModel):
    """Slot do chassis."""
    slot_id: int
    slot_kind: SlotKind
    allowed_board_types: list[str] = Field(default_factory=list)
    board: Optional[DeploymentBoard] = None


class Chassis(BaseModel):
    """Chassis do equipamento."""
    chassis_id: int = 0
    frame_kind: FrameKind = FrameKind.STANDALONE
    total_slots: int = 0


class FirmwareDescriptor(BaseModel):
    """Descritor de firmware."""
    version_family: str
    patch_level: Optional[str] = None
    capability_pack_ref: Optional[str] = None


class LogicalPort(BaseModel):
    """Porta lógica (LAG, SVI, etc.)."""
    name: str
    kind: LogicalPortKind
    members: list[PortAddr] = Field(default_factory=list)


class DeploymentConstraint(BaseModel):
    """Constraint declarado pelo capability pack ou operador."""
    kind: ConstraintKind
    scope: str
    predicate: str = ""
    severity: str = "mandatory"
    reason: str = ""


class DeploymentTarget(BaseModel):
    """
    Digital twin do OLT destino.
    Independente de qualquer configuração específica.
    """
    target_id: str
    vendor: str
    model: str
    firmware: Optional[FirmwareDescriptor] = None
    chassis: Chassis = Field(default_factory=Chassis)
    slots: list[Slot] = Field(default_factory=list)
    boards: list[DeploymentBoard] = Field(default_factory=list)
    physical_ports: list[PhysicalPort] = Field(default_factory=list)
    logical_ports: list[LogicalPort] = Field(default_factory=list)
    numbering_rules: Optional[NumberingRules] = None
    constraints: list[DeploymentConstraint] = Field(default_factory=list)


__all__ = [
    "FrameKind", "SlotKind", "BoardKind", "PortKind", "OperationalState",
    "LogicalPortKind", "ProfileLifecycle", "ProfileOrigin",
    "ConstraintKind", "IdNamespace",
    "PortAddr", "IdRange", "NumberingRules", "PhysicalPort",
    "DeploymentBoard", "Slot", "Chassis", "FirmwareDescriptor",
    "LogicalPort", "DeploymentConstraint", "DeploymentTarget",
]
