from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UniversalModel(BaseModel):
    metadata: dict[str, Any] | None = None


class VLANMode(str, Enum):
    NATIVE = "native"
    TAGGED = "tagged"


class VLAN(UniversalModel):
    vlan_id: int
    name: str | None = None
    mode: VLANMode = VLANMode.TAGGED


class DBAProfile(UniversalModel):
    name: str
    profile_type: str
    assured_kbps: int | None = None
    max_kbps: int | None = None


class TrafficProfile(UniversalModel):
    name: str
    upstream_kbps: int | None = None
    downstream_kbps: int | None = None


class QoSProfile(UniversalModel):
    name: str
    priority: int | None = None
    traffic_profile: str | None = None


class MulticastProfile(UniversalModel):
    name: str
    igmp_version: str | None = None


class TCONT(UniversalModel):
    tcont_id: int
    dba_profile: str | None = None


class GEMPort(UniversalModel):
    gem_id: int
    tcont_id: int


class ONU(UniversalModel):
    pon_ref: str
    onu_id: int
    serial_number: str | None = None
    native_vlan: int | None = None
    tagged_vlans: list[int] = Field(default_factory=list)
    tconts: list[TCONT] = Field(default_factory=list)
    gem_ports: list[GEMPort] = Field(default_factory=list)


class PON(UniversalModel):
    name: str
    onus: list[ONU] = Field(default_factory=list)


class ServiceBinding(UniversalModel):
    binding_id: int
    vlan_id: int
    pon_ref: str
    onu_id: int
    gem_id: int | None = None


class WANService(UniversalModel):
    name: str
    onu_ref: str
    vlan_id: int | None = None


class PPPoEService(WANService):
    username: str | None = None


class IPoEService(WANService):
    dhcp: bool = True


class Uplink(UniversalModel):
    name: str
    allowed_vlans: list[int] = Field(default_factory=list)
    native_vlan: int | None = None


class OLTConfig(UniversalModel):
    vendor: str
    model: str | None = None
    vlans: list[VLAN] = Field(default_factory=list)
    pons: list[PON] = Field(default_factory=list)
    onus: list[ONU] = Field(default_factory=list)
    service_bindings: list[ServiceBinding] = Field(default_factory=list)
    dba_profiles: list[DBAProfile] = Field(default_factory=list)
    traffic_profiles: list[TrafficProfile] = Field(default_factory=list)
    qos_profiles: list[QoSProfile] = Field(default_factory=list)
    multicast_profiles: list[MulticastProfile] = Field(default_factory=list)
    wan_services: list[WANService] = Field(default_factory=list)
    pppoe_services: list[PPPoEService] = Field(default_factory=list)
    ipoe_services: list[IPoEService] = Field(default_factory=list)
    uplinks: list[Uplink] = Field(default_factory=list)
