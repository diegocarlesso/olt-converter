"""
QoS, Multicast, IGMP e OMCI.
"""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.models.base import DomainModel


class QoSPolicy(DomainModel):
    name: str
    priority: int = 0
    cir: Optional[int] = None
    pir: Optional[int] = None
    description: Optional[str] = None


class QoSAttachment(DomainModel):
    """Vincula uma policy de QoS a um par slot/port (Fiberhome WOS)."""

    slot: int
    port: int
    attached_profiles: list[int] = Field(default_factory=list)
    description: Optional[str] = None


class IGMPConfig(DomainModel):
    enabled: bool = False
    mode: str = "snooping"        # snooping | proxy | router
    fast_leave: bool = False
    querier_enabled: bool = False
    static_groups: list[dict] = Field(default_factory=list)


class MulticastConfig(DomainModel):
    enabled: bool = False
    igmp: Optional[IGMPConfig] = None
    multicast_vlan: Optional[int] = None
    program_table: list[dict] = Field(default_factory=list)


class OMCIConfig(DomainModel):
    home_gateway_config_method: str = "omci"
    auto_provisioning: bool = True
    anti_rogue_ont: bool = True
    interoperability_flags: list[str] = Field(default_factory=list)


__all__ = [
    "QoSPolicy",
    "QoSAttachment",
    "IGMPConfig",
    "MulticastConfig",
    "OMCIConfig",
]
