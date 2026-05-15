"""
Configuração de sistema: boards, usuários, AAA/RADIUS, NTP, logging, SSH,
SNMP.
"""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.models.base import DomainModel
from app.models.enums import AdminState


class Board(DomainModel):
    """Card físico instalado num slot da OLT."""

    slot: int
    board_type: str          # ex: gc8b, gcob, hswa, H901GPHF
    kind: Optional[str] = None  # gpon-line | switch | uplink | fan | power | unknown
    description: Optional[str] = None
    admin_state: AdminState = AdminState.UP


class User(DomainModel):
    """Usuário local da OLT — senha nunca serializada por completo."""

    username: str
    level: str = "admin"         # admin | operator | viewer | localadmin
    password_hash: Optional[str] = Field(
        None,
        description="Hash original (não em claro). Renderer pode emitir placeholder.",
    )


class RadiusServer(DomainModel):
    ip_address: str
    auth_port: int = 1812
    acct_port: int = 1813
    key: Optional[str] = None
    timeout_seconds: int = 3
    retransmit: int = 3
    source_ip: Optional[str] = None


class AAAConfig(DomainModel):
    accounting_mode: str = "none"       # none | start-stop | radius
    authentication_mode: str = "local"  # local | radius | tacacs
    authorization_mode: str = "local"


class NTPServer(DomainModel):
    ip_address: str
    preferred: bool = False


class SSHConfig(DomainModel):
    enabled: bool = True
    ciphers: list[str] = Field(default_factory=list)
    macs: list[str] = Field(default_factory=list)
    key_exchanges: list[str] = Field(default_factory=list)
    dh_min_len: int = 2048


class SNMPCommunity(DomainModel):
    community: str
    permission: str = "ro"   # ro | rw


class SNMPConfig(DomainModel):
    enabled: bool = True
    location: Optional[str] = None
    contact: Optional[str] = None
    communities: list[SNMPCommunity] = Field(default_factory=list)
    trap_hosts: list[str] = Field(default_factory=list)


class LoggingConfig(DomainModel):
    save_interval_min: int = 1440
    syslog_servers: list[str] = Field(default_factory=list)


class LineIDConfig(DomainModel):
    """DHCP option-82 / PPPoE+ / DHCPv6 option-18/37 — line identifier."""

    circuit_id_format: str = "default"
    remote_id_enabled: bool = False
    pppoe_plus_enabled: bool = False
    dhcp_option82_enabled: bool = False
    dhcp_option18_enabled: bool = False
    dhcp_option37_enabled: bool = False


__all__ = [
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
]
