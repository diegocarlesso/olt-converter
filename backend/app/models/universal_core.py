from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UniversalModel(BaseModel):
    metadata: dict[str, Any] | None = None


class VLAN(UniversalModel):
    vlan_id: int
    name: str | None = None


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


class DBAProfile(UniversalModel):
    name: str
    profile_type: str


class TrafficProfile(UniversalModel):
    name: str
    upstream_kbps: int | None = None
    downstream_kbps: int | None = None


class WANProfile(UniversalModel):
    name: str
    mode: str


class Uplink(UniversalModel):
    name: str
    allowed_vlans: list[int] = Field(default_factory=list)


class OLTConfig(UniversalModel):
    vendor: str
    model: str | None = None
    vlans: list[VLAN] = Field(default_factory=list)
    pons: list[PON] = Field(default_factory=list)
    onus: list[ONU] = Field(default_factory=list)
    service_bindings: list[ServiceBinding] = Field(default_factory=list)
    dba_profiles: list[DBAProfile] = Field(default_factory=list)
    traffic_profiles: list[TrafficProfile] = Field(default_factory=list)
    wan_profiles: list[WANProfile] = Field(default_factory=list)
    uplinks: list[Uplink] = Field(default_factory=list)
