"""
Enums canônicos do modelo universal.

Todos os enums herdam de `str` para serem JSON-serializáveis e comparáveis
diretamente com literais string em parsers/renderers.
"""
from __future__ import annotations

from enum import Enum


class Vendor(str, Enum):
    FIBERHOME = "fiberhome"
    ZTE = "zte"
    HUAWEI = "huawei"
    DATACOM = "datacom"
    UNKNOWN = "unknown"


class AdminState(str, Enum):
    UP = "up"
    DOWN = "down"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class PortType(str, Enum):
    GE = "ge"           # 1 Gbps electrical/optical
    XGE = "xge"         # 10 Gbps
    XXGE = "xxge"       # 40/100 Gbps
    GPON = "gpon"
    EPON = "epon"
    XGSPON = "xgs-pon"
    SERDES = "serdes"
    UNKNOWN = "unknown"


class TrunkMode(str, Enum):
    ACCESS = "access"
    TRUNK = "trunk"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class LACPMode(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    STATIC = "static"
    NONE = "none"


class VLANMode(str, Enum):
    TAG = "tag"
    UNTAG = "untag"
    TRANSPARENT = "transparent"
    TRANSLATION = "translation"
    QINQ = "qinq"


class ServiceType(str, Enum):
    """Tipo lógico de uma service-vlan / serviço end-to-end."""

    DATA = "data"
    IPTV = "iptv"
    VOIP = "voip"
    CNC = "cnc"
    MULTICAST = "multicast"
    MANAGEMENT = "management"
    OTHER = "other"


class OperationMode(str, Enum):
    BRIDGE = "bridge"
    ROUTER = "router"
    PPPOE = "pppoe"
    IPOE = "ipoe"
    OMCI = "omci"
    UNKNOWN = "unknown"


class DBAType(str, Enum):
    """Tipos de DBA conforme spec GPON e dialetos dos vendors."""

    TYPE1 = "type1"     # Fixed
    TYPE2 = "type2"     # Assured
    TYPE3 = "type3"     # Assured + Max
    TYPE4 = "type4"     # Max only (best-effort)
    TYPE5 = "type5"     # Fixed + Assured + Max


class ServicePortAction(str, Enum):
    REPLACE = "replace"
    STRIP = "strip"
    TRANSLATE = "translate"
    TRANSPARENT = "transparent"
    QINQ_ADD = "qinq-add"
    QINQ_STRIP = "qinq-strip"


class FlowDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BOTH = "both"


class ProfileScope(str, Enum):
    """Tecnologia em que o profile se aplica."""

    GPON = "gpon"
    EPON = "epon"
    XGSPON = "xgs-pon"
    XPON = "xpon"
    GLOBAL = "global"


__all__ = [
    "Vendor",
    "AdminState",
    "PortType",
    "TrunkMode",
    "LACPMode",
    "VLANMode",
    "ServiceType",
    "OperationMode",
    "DBAType",
    "ServicePortAction",
    "FlowDirection",
    "ProfileScope",
]
