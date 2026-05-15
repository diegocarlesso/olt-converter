"""
Modelo universal `OLTConfig` e seus componentes.

Este package re-exporta tudo a partir dos submódulos para que o resto do
código possa fazer `from app.models import OLTConfig, VLAN, ...` sem se
preocupar com a organização interna.
"""
from app.models.enums import (
    AdminState,
    DBAType,
    FlowDirection,
    LACPMode,
    OperationMode,
    PortType,
    ProfileScope,
    ServicePortAction,
    ServiceType,
    TrunkMode,
    Vendor,
    VLANMode,
)
from app.models.base import DomainModel, StableID
from app.models.provenance import Provenance, ProvenanceSource
from app.models.network import (
    LACPGroup,
    ServiceVLAN,
    StaticRoute,
    Uplink,
    VLAN,
)
from app.models.pon import (
    EthernetPort,
    GEMPort,
    ONU,
    PON,
    PONOpticalParams,
    TCONT,
)
from app.models.profiles import (
    DBAProfile,
    LineProfile,
    ONUTypeProfile,
    PolicyRouteProfile,
    PortConfig,
    ServiceProfile,
    TrafficProfile,
    WANProfile,
)
from app.models.qos import (
    IGMPConfig,
    MulticastConfig,
    OMCIConfig,
    QoSAttachment,
    QoSPolicy,
)
from app.models.services import (
    Bridge,
    IPoESession,
    PPPoESession,
    ServicePort,
    VLANToGEMMapping,
)
from app.models.system import (
    AAAConfig,
    Board,
    LineIDConfig,
    LoggingConfig,
    NTPServer,
    RadiusServer,
    SNMPCommunity,
    SNMPConfig,
    SSHConfig,
    User,
)
from app.models.unified_model import OLTConfig

__all__ = [
    # Core
    "OLTConfig",
    "DomainModel",
    "StableID",
    "Provenance",
    "ProvenanceSource",
    # Enums
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
    # Network
    "VLAN",
    "ServiceVLAN",
    "Uplink",
    "LACPGroup",
    "StaticRoute",
    # PON
    "PON",
    "ONU",
    "EthernetPort",
    "GEMPort",
    "TCONT",
    "PONOpticalParams",
    # Profiles
    "DBAProfile",
    "TrafficProfile",
    "LineProfile",
    "ServiceProfile",
    "WANProfile",
    "PolicyRouteProfile",
    "ONUTypeProfile",
    "PortConfig",
    # Services
    "ServicePort",
    "Bridge",
    "PPPoESession",
    "IPoESession",
    "VLANToGEMMapping",
    # System
    "Board",
    "User",
    "RadiusServer",
    "AAAConfig",
    "NTPServer",
    "SSHConfig",
    "SNMPCommunity",
    "SNMPConfig",
    "LoggingConfig",
    "LineIDConfig",
    # QoS
    "QoSPolicy",
    "QoSAttachment",
    "IGMPConfig",
    "MulticastConfig",
    "OMCIConfig",
]
