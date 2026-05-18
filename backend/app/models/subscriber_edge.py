"""
Subscriber edge — modelos formais para semântica de UNI / WiFi / WAN / bridge.

Esta camada (L9) promove dados que viviam em `ONU.extra_vendor` para
entidades **semanticamente conscientes**, com:

  * tipagem forte
  * proveniência rastreável
  * participação na compatibility matrix
  * validação cruzada
  * preservação de bindings entre vendors

Princípio: "promotion by recurrence" — só formalizamos o que aparece
recorrentemente em múltiplos vendors. Vendor quirks específicos continuam
em `extra_vendor` como escape hatch.

Entidades:

  * WiFiRadio          — rádio 2.4GHz/5GHz/6GHz
  * WiFiSSID           — SSID, auth, encryption, hidden, bound radio/uni
  * BridgeGroup        — agregação L2 de portas UNI em modo bridge
  * WANBinding         — vínculo ONU→WAN profile (bridge/router/pppoe/ipoe)
  * LANService         — serviço por UNI (data/iptv/voip)
  * STBConfig          — porta(s) UNI dedicada(s) ao set-top-box (IPTV)
  * MulticastBinding   — ONU subscrita a um serviço multicast
  * PortRoute          — rota explícita entre portas (ont port route)

Bindings preservados (referência por nome ou id estável):

  EthernetPort ↔ BridgeGroup ↔ LANService
  EthernetPort ↔ WANBinding ↔ WANProfile
  EthernetPort ↔ SSID (em ONUs com WiFi integrado)
  EthernetPort ↔ STBConfig
  ONU ↔ MulticastBinding ↔ MulticastConfig.mvlan
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import DomainModel
from app.models.provenance import Provenance


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class BridgeMode(str, Enum):
    """Modo de operação L2/L3 de uma UNI ou ONU como um todo."""

    BRIDGE = "bridge"
    ROUTER = "router"
    MIXED = "mixed"            # UNI bridge + WiFi router (comum em residencial)
    UNKNOWN = "unknown"


class WANMode(str, Enum):
    """Mode da conexão WAN."""

    BRIDGE = "bridge"
    DHCP = "dhcp"
    STATIC_IP = "static-ip"
    PPPOE = "pppoe"
    IPOE = "ipoe"
    UNKNOWN = "unknown"


class WiFiBand(str, Enum):
    BAND_2_4G = "2.4ghz"
    BAND_5G = "5ghz"
    BAND_6G = "6ghz"
    UNKNOWN = "unknown"


class WiFiAuthMode(str, Enum):
    OPEN = "open"
    WEP = "wep"
    WPA = "wpa"
    WPA_PSK = "wpa-psk"
    WPA2_PSK = "wpa2-psk"
    WPA3_PSK = "wpa3-psk"
    WPA2_ENTERPRISE = "wpa2-enterprise"
    UNKNOWN = "unknown"


class LANServiceType(str, Enum):
    DATA = "data"
    IPTV = "iptv"
    VOIP = "voip"
    MANAGEMENT = "management"
    CCTV = "cctv"
    OTHER = "other"


# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------
class WiFiRadio(DomainModel):
    """
    Rádio físico de uma ONU GPON com WiFi integrado.

    Cada ONU pode ter 0..N rádios (ex: dual-band tem 2: 2.4G + 5G).
    SSIDs são vinculados ao rádio por `WiFiSSID.radio_id`.
    """

    radio_id: int = Field(..., ge=0, description="Índice do rádio na ONU (0=2.4G, 1=5G)")
    band: WiFiBand = WiFiBand.BAND_2_4G
    enabled: bool = True
    channel: Optional[int] = None
    tx_power_dbm: Optional[int] = None
    bandwidth_mhz: Optional[int] = None   # 20, 40, 80, 160
    standard: Optional[str] = None        # 802.11ac, 802.11ax
    country: Optional[str] = None
    provenance: Optional[Provenance] = None


class WiFiSSID(DomainModel):
    """
    SSID configurado em uma ONU GPON (no rádio WiFi integrado).
    """

    ssid_id: int = Field(..., ge=0, description="Índice do SSID (0..7 por rádio)")
    radio_id: int = Field(..., ge=0)
    name: Optional[str] = None
    enabled: bool = True
    hidden: bool = False
    auth_mode: WiFiAuthMode = WiFiAuthMode.WPA2_PSK
    encryption: Optional[str] = None      # aes, tkip, aes+tkip
    key_present: bool = False             # NUNCA armazenar chave em claro
    max_clients: Optional[int] = None
    isolation: bool = False               # client isolation
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    # Vínculo ao serviço lógico
    lan_service_ref: Optional[str] = Field(
        None, description="Nome da LANService que este SSID serve"
    )
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# Bridge / LAN
# ---------------------------------------------------------------------------
class BridgeGroup(DomainModel):
    """
    Grupo de bridge — agregação L2 de portas UNI da ONU.

    Em modo bridge, várias UNIs podem compartilhar a mesma bridge,
    aceitando tagged/untagged conforme a VLAN bound.
    """

    group_id: int = Field(..., ge=0)
    name: Optional[str] = None
    member_port_ids: list[int] = Field(default_factory=list)   # eth_port.port_id
    member_ssid_ids: list[int] = Field(default_factory=list)   # ssid.ssid_id
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    isolation_enabled: bool = False
    provenance: Optional[Provenance] = None


class LANService(DomainModel):
    """
    Serviço lógico entregue à UNI (data/iptv/voip/etc.).

    Conecta o conceito de "tipo de serviço" do operador com os bindings
    técnicos (VLAN, GEM, traffic profile, bridge/router mode).
    """

    name: str
    service_type: LANServiceType = LANServiceType.DATA
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    gem_id: Optional[int] = Field(None, ge=0)
    bridge_mode: BridgeMode = BridgeMode.BRIDGE
    traffic_profile_ref: Optional[str] = None
    member_port_ids: list[int] = Field(default_factory=list)
    member_ssid_ids: list[int] = Field(default_factory=list)
    multicast_enabled: bool = False
    provenance: Optional[Provenance] = None


class STBConfig(DomainModel):
    """
    Configuração de set-top-box: identifica quais UNIs são STB e o serviço
    IPTV vinculado.
    """

    stb_port_ids: list[int] = Field(default_factory=list)
    iptv_vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    multicast_profile_ref: Optional[str] = None
    igmp_proxy_enabled: bool = True
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# WAN / Subscriber session
# ---------------------------------------------------------------------------
class WANBinding(DomainModel):
    """
    Binding ONU → WAN profile com sessão subscrita.

    Suporta os 4 modos clássicos: bridge, dhcp, pppoe, ipoe.
    """

    binding_id: int = Field(..., ge=0)
    mode: WANMode = WANMode.BRIDGE
    wan_profile_ref: Optional[str] = Field(
        None, description="Nome do WANProfile (Huawei) ou equivalente"
    )
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    user_vlan: Optional[int] = Field(None, ge=1, le=4094)
    priority: Optional[int] = Field(None, ge=0, le=7)
    nat_enabled: bool = False
    # PPPoE-specific
    pppoe_user: Optional[str] = None
    pppoe_password_present: bool = False
    # IP stack
    ip_stack_mode: Optional[str] = None   # ipv4, ipv6, dual-stack
    ipv6_src_type: Optional[str] = None   # dhcpv6, slaac
    prefix_src_type: Optional[str] = None
    # Binding às UNIs / SSIDs que recebem este serviço
    bound_port_ids: list[int] = Field(default_factory=list)
    bound_ssid_ids: list[int] = Field(default_factory=list)
    # Policy route opcional
    policy_route_profile_ref: Optional[str] = None
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# Multicast
# ---------------------------------------------------------------------------
class MulticastBinding(DomainModel):
    """
    Binding ONU → serviço multicast.

    Referencia o `MulticastConfig.multicast_vlan` global ou um perfil
    específico de IGMP.
    """

    binding_id: int = Field(..., ge=0)
    multicast_vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    igmp_proxy: bool = True
    fast_leave: bool = False
    program_list_ref: Optional[str] = None
    bound_port_ids: list[int] = Field(default_factory=list)
    bound_ssid_ids: list[int] = Field(default_factory=list)
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# Routing por porta
# ---------------------------------------------------------------------------
class PortRoute(DomainModel):
    """
    Rota explícita entre UNI da ONU (Huawei `ont port route`).
    """

    src_port_id: int = Field(..., ge=0)
    dst_port_id: int = Field(..., ge=0)
    enabled: bool = True
    description: Optional[str] = None
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# Container de alto nível
# ---------------------------------------------------------------------------
class SubscriberEdge(DomainModel):
    """
    Container "edge" de uma ONU — agrega todos os aspectos subscriber-facing.

    Pode ser usado pela UI como um único objeto editável. As listas internas
    referenciam objetos formais (não strings) para preservar consistência.
    """

    bridge_groups: list[BridgeGroup] = Field(default_factory=list)
    lan_services: list[LANService] = Field(default_factory=list)
    wan_bindings: list[WANBinding] = Field(default_factory=list)
    radios: list[WiFiRadio] = Field(default_factory=list)
    ssids: list[WiFiSSID] = Field(default_factory=list)
    stb: Optional[STBConfig] = None
    multicast_bindings: list[MulticastBinding] = Field(default_factory=list)
    port_routes: list[PortRoute] = Field(default_factory=list)


__all__ = [
    "BridgeMode",
    "WANMode",
    "WiFiBand",
    "WiFiAuthMode",
    "LANServiceType",
    "WiFiRadio",
    "WiFiSSID",
    "BridgeGroup",
    "LANService",
    "STBConfig",
    "WANBinding",
    "MulticastBinding",
    "PortRoute",
    "SubscriberEdge",
]
