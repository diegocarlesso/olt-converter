from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class UniversalModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: dict[str, Any] | None = None


class VLANMode(str, Enum):
    NATIVE = "native"
    TAGGED = "tagged"
    QINQ = "qinq"


class DBAProfile(UniversalModel):
    name: str
    profile_type: str
    assured_kbps: int | None = None
    max_kbps: int | None = None


class TrafficProfile(UniversalModel):
    name: str
    upstream_kbps: int | None = None
    downstream_kbps: int | None = None


class SchedulerProfile(UniversalModel):
    name: str
    algorithm: str
    weight: int | None = None


class QoSProfile(UniversalModel):
    name: str
    priority: int | None = None
    traffic_profile: str | None = None
    scheduler_profile: str | None = None


class IGMPProfile(UniversalModel):
    name: str
    version: str
    fast_leave: bool = False


class MulticastProfile(UniversalModel):
    name: str
    igmp_profile: str | None = None


class NativeVLANPolicy(UniversalModel):
    vlan_id: int


class VLANTranslationPolicy(UniversalModel):
    customer_vlan: int
    service_vlan: int


class TCONT(UniversalModel):
    tcont_id: int
    dba_profile: str | None = None


class GEMPort(UniversalModel):
    gem_id: int
    tcont_id: int
    vlan_translation: VLANTranslationPolicy | None = None


class WANService(UniversalModel):
    name: str
    onu_ref: str
    vlan_id: int | None = None


class PPPoEService(WANService):
    username: str | None = None


class IPoEService(WANService):
    dhcp: bool = True


class ServicePort(UniversalModel):
    service_port_id: int
    customer_vlan: int
    service_vlan: int
    uplink: str


class ServiceBinding(UniversalModel):
    binding_id: int
    customer_vlan: int
    service_vlan: int
    uplink: str = "unknown-uplink"
    traffic_profile: str | None = None
    gem_id: int | None = None
    pon_ref: str | None = None
    onu_id: int | None = None


class VLAN(UniversalModel):
    vlan_id: int
    name: str | None = None
    mode: VLANMode = VLANMode.TAGGED


class ONU(UniversalModel):
    pon_ref: str
    onu_id: int
    serial_number: str | None = None
    native_vlan_policy: NativeVLANPolicy | None = None
    tagged_vlans: list[int] = Field(default_factory=list)
    tconts: list[TCONT] = Field(default_factory=list)
    gem_ports: list[GEMPort] = Field(default_factory=list)
    wan_services: list[WANService] = Field(default_factory=list)
    pppoe_services: list[PPPoEService] = Field(default_factory=list)
    ipoe_services: list[IPoEService] = Field(default_factory=list)
    qos_profiles: list[str] = Field(default_factory=list)
    multicast_profiles: list[str] = Field(default_factory=list)


class PON(UniversalModel):
    name: str
    onus: list[ONU] = Field(default_factory=list)


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
    service_ports: list[ServicePort] = Field(default_factory=list)
    service_bindings: list[ServiceBinding] = Field(default_factory=list)
    dba_profiles: list[DBAProfile] = Field(default_factory=list)
    traffic_profiles: list[TrafficProfile] = Field(default_factory=list)
    scheduler_profiles: list[SchedulerProfile] = Field(default_factory=list)
    qos_profiles: list[QoSProfile] = Field(default_factory=list)
    igmp_profiles: list[IGMPProfile] = Field(default_factory=list)
    multicast_profiles: list[MulticastProfile] = Field(default_factory=list)
    wan_services: list[WANService] = Field(default_factory=list)
    pppoe_services: list[PPPoEService] = Field(default_factory=list)
    ipoe_services: list[IPoEService] = Field(default_factory=list)
    uplinks: list[Uplink] = Field(default_factory=list)
