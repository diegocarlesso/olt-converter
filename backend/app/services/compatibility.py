"""
Compatibility Matrix — controle e mensuração de fidelidade operacional.

Define, *declarativamente*, o nível de suporte de cada **feature GPON/XPON**
em cada direção (vendor origem → vendor destino):

    FULL       → o pipeline parseia, equivale e renderiza com fidelidade total
    PARTIAL    → cobertura existe mas com perdas ou pré-condições
    NONE       → não suportado nem na origem nem no destino
    UNSUPPORTED → estritamente bloqueado (vendor destino não tem o conceito)

Cada célula carrega `confidence` (0..1) que reflete:

  * parser_coverage  — quão completamente o parser extrai a feature
  * renderer_coverage — quão completamente o renderer emite a feature
  * equivalence_coverage — se há mapeamento semântico real (não só sintático)

A média ponderada dessas três coberturas vira `semantic_fidelity_score`,
exibido no relatório.

A meta é dar visibilidade total ao operador: cada conversão diz, *antes
mesmo de rodar*, o que será preservado, o que será perdido e o que precisa
de revisão.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.models import Vendor


class SupportLevel(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class FeatureCapability:
    """Capacidade de um vendor para uma feature, nas duas pontas (parse/render)."""

    feature: str
    parser_coverage: float        # 0..1
    renderer_coverage: float      # 0..1
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompatibilityCell:
    """Resultado da combinação (source, target, feature)."""

    source: Vendor
    target: Vendor
    feature: str
    level: SupportLevel
    confidence: float
    parser_coverage: float
    renderer_coverage: float
    equivalence_coverage: float
    semantic_fidelity: float
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "source": self.source.value,
            "target": self.target.value,
            "feature": self.feature,
            "level": self.level.value,
            "confidence": round(self.confidence, 2),
            "parser_coverage": round(self.parser_coverage, 2),
            "renderer_coverage": round(self.renderer_coverage, 2),
            "equivalence_coverage": round(self.equivalence_coverage, 2),
            "semantic_fidelity": round(self.semantic_fidelity, 2),
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# Catálogo declarativo de features
# ---------------------------------------------------------------------------
FEATURES = (
    "hostname",
    "vlan",
    "service_vlan",
    "vlan_translation",
    "qinq",
    "uplink",
    "uplink_lacp",
    "static_route",
    "mgmt_vlan_ip",
    "boards",
    "pon",
    "onu_auth",            # serial/SN + line/service profile
    "onu_admin_state",
    "onu_eth_ports",       # portas Ethernet da ONU
    "onu_native_vlan",
    "onu_user_vlan",
    "gem_tcont",
    "dba_profile",
    "traffic_profile",
    "line_profile",
    "service_profile",
    "service_port",
    "multicast_igmp",
    "multicast_gem",
    "wan_profile",
    "pppoe_session",
    "ipoe_session",
    "policy_route",
    "snmp",
    "ssh_cipher_detail",
    "aaa_radius",
    "users",
    "qos_attachment",
    "omci_provisioning",
    "stb_ports",
    "ssid_binding",
    # L9 subscriber edge — recém promovido a modelos formais
    "subscriber_edge_uni",         # EthernetPort com bridge_mode/lan_service
    "subscriber_edge_wifi",        # WiFiRadio + WiFiSSID (per-ONU)
    "subscriber_edge_bridge_group", # BridgeGroup (eth agregadas em bridge)
    "subscriber_edge_wan_binding", # WANBinding (ONU→WAN profile + mode)
    "subscriber_edge_lan_service", # LANService (data/iptv/voip por UNI)
    "subscriber_edge_stb",         # STBConfig (porta STB dedicada IPTV)
    "subscriber_edge_multicast",   # MulticastBinding (IGMP/MVLAN per-ONU)
    "subscriber_edge_port_route",  # PortRoute (Huawei ont port route)
)


# Capabilities (parser/renderer) por vendor — preenchidas com base no estado
# atual dos parsers e renderers desta implementação.
#
# Valores baseados em inspeção do código real e dos backups disponíveis.
VENDOR_CAPABILITIES: dict[Vendor, dict[str, FeatureCapability]] = {
    Vendor.FIBERHOME: {
        "hostname": FeatureCapability("hostname", 1.0, 1.0),
        "vlan": FeatureCapability("vlan", 1.0, 0.9, ("add vlan vlan_begin/vlan_end + allslot",)),
        "service_vlan": FeatureCapability("service_vlan", 1.0, 1.0, ("conceito nativo do WOS",)),
        "vlan_translation": FeatureCapability("vlan_translation", 0.3, 0.3, ("implícito via cs profile",)),
        "qinq": FeatureCapability("qinq", 0.2, 0.2, ("flag global apenas",)),
        "uplink": FeatureCapability("uplink", 1.0, 1.0),
        "uplink_lacp": FeatureCapability("uplink_lacp", 0.2, 0.2, ("upbak_trunk não modelado",)),
        "static_route": FeatureCapability("static_route", 1.0, 1.0),
        "mgmt_vlan_ip": FeatureCapability("mgmt_vlan_ip", 1.0, 1.0),
        "boards": FeatureCapability("boards", 1.0, 1.0),
        "pon": FeatureCapability("pon", 0.8, 0.6, ("PONs inferidas via card_auth + whitelist",)),
        "onu_auth": FeatureCapability("onu_auth", 1.0, 1.0, ("set white phy addr completo",)),
        "onu_admin_state": FeatureCapability("onu_admin_state", 0.3, 0.3),
        "onu_eth_ports": FeatureCapability("onu_eth_ports", 0.2, 0.4, ("derivado do cs profile (lan1g)",)),
        "onu_native_vlan": FeatureCapability("onu_native_vlan", 0.1, 0.5, ("não declarado no save WOS",)),
        "onu_user_vlan": FeatureCapability("onu_user_vlan", 0.1, 0.5),
        "gem_tcont": FeatureCapability("gem_tcont", 0.1, 0.4, ("runtime; não no save",)),
        "dba_profile": FeatureCapability("dba_profile", 0.1, 0.7, ("síntese cobre",)),
        "traffic_profile": FeatureCapability("traffic_profile", 0.0, 0.5),
        "line_profile": FeatureCapability("line_profile", 0.1, 0.4),
        "service_profile": FeatureCapability("service_profile", 0.7, 0.8, ("derivado de cs onu profile",)),
        "service_port": FeatureCapability("service_port", 0.0, 0.5, ("não no save; inferido",)),
        "multicast_igmp": FeatureCapability("multicast_igmp", 0.0, 0.0),
        "multicast_gem": FeatureCapability("multicast_gem", 0.0, 0.0),
        "wan_profile": FeatureCapability("wan_profile", 0.0, 0.0),
        "pppoe_session": FeatureCapability("pppoe_session", 0.0, 0.0),
        "ipoe_session": FeatureCapability("ipoe_session", 0.0, 0.0),
        "policy_route": FeatureCapability("policy_route", 0.0, 0.0),
        "snmp": FeatureCapability("snmp", 0.2, 0.2),
        "ssh_cipher_detail": FeatureCapability("ssh_cipher_detail", 0.0, 0.0),
        "aaa_radius": FeatureCapability("aaa_radius", 1.0, 1.0),
        "users": FeatureCapability("users", 1.0, 0.5, ("hashes preservados; render parcial",)),
        "qos_attachment": FeatureCapability("qos_attachment", 0.8, 0.5),
        "omci_provisioning": FeatureCapability("omci_provisioning", 0.5, 0.5),
        "stb_ports": FeatureCapability("stb_ports", 0.0, 0.0),
        "ssid_binding": FeatureCapability("ssid_binding", 0.0, 0.0),
        # L9 — Fiberhome WOS forte em wancfg+ssid+pppoe per-ONU
        "subscriber_edge_uni":          FeatureCapability("subscriber_edge_uni", 0.6, 0.4, ("eth ports derivadas do cs profile",)),
        "subscriber_edge_wifi":         FeatureCapability("subscriber_edge_wifi", 0.9, 0.7, ("set wifi_serv_wlan",)),
        "subscriber_edge_bridge_group": FeatureCapability("subscriber_edge_bridge_group", 0.2, 0.3),
        "subscriber_edge_wan_binding":  FeatureCapability("subscriber_edge_wan_binding", 0.85, 0.6, ("set wancfg",)),
        "subscriber_edge_lan_service":  FeatureCapability("subscriber_edge_lan_service", 0.3, 0.3),
        "subscriber_edge_stb":          FeatureCapability("subscriber_edge_stb", 0.0, 0.0),
        "subscriber_edge_multicast":    FeatureCapability("subscriber_edge_multicast", 0.0, 0.0),
        "subscriber_edge_port_route":   FeatureCapability("subscriber_edge_port_route", 0.0, 0.0),
    },
    Vendor.HUAWEI: {
        "hostname": FeatureCapability("hostname", 1.0, 1.0),
        "vlan": FeatureCapability("vlan", 1.0, 1.0, ("vlan smart/common",)),
        "service_vlan": FeatureCapability("service_vlan", 0.0, 0.0, ("não tem conceito direto",)),
        "vlan_translation": FeatureCapability("vlan_translation", 0.9, 0.9, ("port vlan eth translation",)),
        "qinq": FeatureCapability("qinq", 0.3, 0.3),
        "uplink": FeatureCapability("uplink", 0.9, 0.9, ("derivado de port vlan",)),
        "uplink_lacp": FeatureCapability("uplink_lacp", 0.5, 0.3, ("link-aggregation parseado parcial",)),
        "static_route": FeatureCapability("static_route", 0.5, 0.5),
        "mgmt_vlan_ip": FeatureCapability("mgmt_vlan_ip", 1.0, 1.0, ("interface vlanif",)),
        "boards": FeatureCapability("boards", 1.0, 1.0),
        "pon": FeatureCapability("pon", 1.0, 1.0),
        "onu_auth": FeatureCapability("onu_auth", 1.0, 1.0, ("ont add omci",)),
        "onu_admin_state": FeatureCapability("onu_admin_state", 0.5, 0.5),
        "onu_eth_ports": FeatureCapability("onu_eth_ports", 0.8, 0.8, ("ont-port pots/eth/catv/wifi",)),
        "onu_native_vlan": FeatureCapability("onu_native_vlan", 0.6, 0.8, ("via service-port",)),
        "onu_user_vlan": FeatureCapability("onu_user_vlan", 0.9, 0.9, ("multi-service user-vlan",)),
        "gem_tcont": FeatureCapability("gem_tcont", 0.9, 0.9, ("ont-lineprofile",)),
        "dba_profile": FeatureCapability("dba_profile", 1.0, 1.0),
        "traffic_profile": FeatureCapability("traffic_profile", 1.0, 1.0, ("traffic table ip index",)),
        "line_profile": FeatureCapability("line_profile", 1.0, 1.0),
        "service_profile": FeatureCapability("service_profile", 1.0, 1.0),
        "service_port": FeatureCapability("service_port", 1.0, 1.0),
        "multicast_igmp": FeatureCapability("multicast_igmp", 0.0, 0.0, ("não capturado ainda",)),
        "multicast_gem": FeatureCapability("multicast_gem", 0.0, 0.0),
        "wan_profile": FeatureCapability("wan_profile", 0.9, 0.7, ("ont wan-profile",)),
        "pppoe_session": FeatureCapability("pppoe_session", 0.0, 0.0),
        "ipoe_session": FeatureCapability("ipoe_session", 0.0, 0.0),
        "policy_route": FeatureCapability("policy_route", 0.8, 0.6, ("policy-route-profile",)),
        "snmp": FeatureCapability("snmp", 0.3, 0.3),
        "ssh_cipher_detail": FeatureCapability("ssh_cipher_detail", 0.3, 0.0, ("parser não captura ainda",)),
        "aaa_radius": FeatureCapability("aaa_radius", 0.4, 0.3),
        "users": FeatureCapability("users", 0.3, 0.3),
        "qos_attachment": FeatureCapability("qos_attachment", 0.5, 0.3),
        "omci_provisioning": FeatureCapability("omci_provisioning", 1.0, 1.0),
        "stb_ports": FeatureCapability("stb_ports", 0.0, 0.0),
        "ssid_binding": FeatureCapability("ssid_binding", 0.0, 0.0),
        # L9 — Huawei: ont port native-vlan, ont wan-config, srvprofile port-vlan
        "subscriber_edge_uni":          FeatureCapability("subscriber_edge_uni", 0.85, 0.85, ("ont port native-vlan, ont-srvprofile",)),
        "subscriber_edge_wifi":         FeatureCapability("subscriber_edge_wifi", 0.4, 0.3, ("via ont-srvprofile ssid",)),
        "subscriber_edge_bridge_group": FeatureCapability("subscriber_edge_bridge_group", 0.5, 0.5),
        "subscriber_edge_wan_binding":  FeatureCapability("subscriber_edge_wan_binding", 0.9, 0.85, ("ont wan-profile + ont wan-config",)),
        "subscriber_edge_lan_service":  FeatureCapability("subscriber_edge_lan_service", 0.7, 0.7, ("service-port multi-service",)),
        "subscriber_edge_stb":          FeatureCapability("subscriber_edge_stb", 0.0, 0.0),
        "subscriber_edge_multicast":    FeatureCapability("subscriber_edge_multicast", 0.0, 0.0),
        "subscriber_edge_port_route":   FeatureCapability("subscriber_edge_port_route", 0.9, 0.5, ("ont port route",)),
    },
    Vendor.ZTE: {
        "hostname": FeatureCapability("hostname", 1.0, 1.0),
        "vlan": FeatureCapability("vlan", 1.0, 1.0),
        "service_vlan": FeatureCapability("service_vlan", 0.0, 0.0),
        "vlan_translation": FeatureCapability("vlan_translation", 0.7, 0.7),
        "qinq": FeatureCapability("qinq", 0.4, 0.4),
        "uplink": FeatureCapability("uplink", 1.0, 1.0),
        "uplink_lacp": FeatureCapability("uplink_lacp", 0.3, 0.3),
        "static_route": FeatureCapability("static_route", 0.4, 0.4),
        "mgmt_vlan_ip": FeatureCapability("mgmt_vlan_ip", 1.0, 1.0, ("interface vlan",)),
        "boards": FeatureCapability("boards", 0.3, 0.3),
        "pon": FeatureCapability("pon", 1.0, 1.0, ("gpon_olt/gpon_onu",)),
        "onu_auth": FeatureCapability("onu_auth", 1.0, 1.0, ("serial-number + sp/lp",)),
        "onu_admin_state": FeatureCapability("onu_admin_state", 0.8, 0.8),
        "onu_eth_ports": FeatureCapability("onu_eth_ports", 1.0, 1.0, ("bloco ethernet completo",)),
        "onu_native_vlan": FeatureCapability("onu_native_vlan", 1.0, 1.0),
        "onu_user_vlan": FeatureCapability("onu_user_vlan", 0.6, 0.6),
        "gem_tcont": FeatureCapability("gem_tcont", 0.7, 0.7),
        "dba_profile": FeatureCapability("dba_profile", 0.7, 0.7),
        "traffic_profile": FeatureCapability("traffic_profile", 0.4, 0.4),
        "line_profile": FeatureCapability("line_profile", 0.8, 0.8),
        "service_profile": FeatureCapability("service_profile", 0.8, 0.8),
        "service_port": FeatureCapability("service_port", 1.0, 1.0),
        "multicast_igmp": FeatureCapability("multicast_igmp", 0.0, 0.0),
        "multicast_gem": FeatureCapability("multicast_gem", 0.0, 0.0),
        "wan_profile": FeatureCapability("wan_profile", 0.0, 0.0),
        "pppoe_session": FeatureCapability("pppoe_session", 0.0, 0.0),
        "ipoe_session": FeatureCapability("ipoe_session", 0.0, 0.0),
        "policy_route": FeatureCapability("policy_route", 0.0, 0.0),
        "snmp": FeatureCapability("snmp", 0.3, 0.3),
        "ssh_cipher_detail": FeatureCapability("ssh_cipher_detail", 0.0, 0.0),
        "aaa_radius": FeatureCapability("aaa_radius", 0.3, 0.3),
        "users": FeatureCapability("users", 0.2, 0.2),
        "qos_attachment": FeatureCapability("qos_attachment", 0.3, 0.3),
        "omci_provisioning": FeatureCapability("omci_provisioning", 0.8, 0.8),
        "stb_ports": FeatureCapability("stb_ports", 0.0, 0.0),
        "ssid_binding": FeatureCapability("ssid_binding", 0.0, 0.0),
        # L9 — ZTE: pon-onu-mng com vlan port eth_0/N, switchport-bind, ssid, wan
        "subscriber_edge_uni":          FeatureCapability("subscriber_edge_uni", 0.95, 0.85, ("vlan port eth_0/N mode tag",)),
        "subscriber_edge_wifi":         FeatureCapability("subscriber_edge_wifi", 0.85, 0.5, ("ssid auth wpa wifi_0/N",)),
        "subscriber_edge_bridge_group": FeatureCapability("subscriber_edge_bridge_group", 0.8, 0.6, ("switchport-bind veip",)),
        "subscriber_edge_wan_binding":  FeatureCapability("subscriber_edge_wan_binding", 0.85, 0.5, ("wan N ethuni, pppoe inline",)),
        "subscriber_edge_lan_service":  FeatureCapability("subscriber_edge_lan_service", 0.7, 0.6, ("service NAME gemport",)),
        "subscriber_edge_stb":          FeatureCapability("subscriber_edge_stb", 0.0, 0.0),
        "subscriber_edge_multicast":    FeatureCapability("subscriber_edge_multicast", 0.0, 0.0),
        "subscriber_edge_port_route":   FeatureCapability("subscriber_edge_port_route", 0.0, 0.0),
    },
    Vendor.DATACOM: {
        "hostname": FeatureCapability("hostname", 1.0, 1.0),
        "vlan": FeatureCapability("vlan", 1.0, 1.0),
        "service_vlan": FeatureCapability("service_vlan", 0.0, 0.0),
        "vlan_translation": FeatureCapability("vlan_translation", 0.6, 0.6),
        "qinq": FeatureCapability("qinq", 0.4, 0.4),
        "uplink": FeatureCapability("uplink", 1.0, 1.0),
        "uplink_lacp": FeatureCapability("uplink_lacp", 0.5, 0.5),
        "static_route": FeatureCapability("static_route", 0.4, 0.4),
        "mgmt_vlan_ip": FeatureCapability("mgmt_vlan_ip", 0.5, 0.5),
        "boards": FeatureCapability("boards", 0.0, 0.0),
        "pon": FeatureCapability("pon", 1.0, 1.0),
        "onu_auth": FeatureCapability("onu_auth", 0.8, 0.8),
        "onu_admin_state": FeatureCapability("onu_admin_state", 0.4, 0.4),
        "onu_eth_ports": FeatureCapability("onu_eth_ports", 0.5, 0.5),
        "onu_native_vlan": FeatureCapability("onu_native_vlan", 0.5, 0.5),
        "onu_user_vlan": FeatureCapability("onu_user_vlan", 0.5, 0.5),
        "gem_tcont": FeatureCapability("gem_tcont", 0.6, 0.6),
        "dba_profile": FeatureCapability("dba_profile", 1.0, 1.0),
        "traffic_profile": FeatureCapability("traffic_profile", 0.4, 0.4),
        "line_profile": FeatureCapability("line_profile", 0.7, 0.7),
        "service_profile": FeatureCapability("service_profile", 0.8, 0.8),
        "service_port": FeatureCapability("service_port", 0.5, 0.5),
        "multicast_igmp": FeatureCapability("multicast_igmp", 0.0, 0.0),
        "multicast_gem": FeatureCapability("multicast_gem", 0.0, 0.0),
        "wan_profile": FeatureCapability("wan_profile", 0.0, 0.0),
        "pppoe_session": FeatureCapability("pppoe_session", 0.0, 0.0),
        "ipoe_session": FeatureCapability("ipoe_session", 0.0, 0.0),
        "policy_route": FeatureCapability("policy_route", 0.0, 0.0),
        "snmp": FeatureCapability("snmp", 0.0, 0.0),
        "ssh_cipher_detail": FeatureCapability("ssh_cipher_detail", 0.0, 0.0),
        "aaa_radius": FeatureCapability("aaa_radius", 0.0, 0.0),
        "users": FeatureCapability("users", 0.0, 0.0),
        "qos_attachment": FeatureCapability("qos_attachment", 0.0, 0.0),
        "omci_provisioning": FeatureCapability("omci_provisioning", 0.7, 0.7),
        "stb_ports": FeatureCapability("stb_ports", 0.0, 0.0),
        "ssid_binding": FeatureCapability("ssid_binding", 0.0, 0.0),
        # L9 — Datacom DmOS via profile onu + mapper
        "subscriber_edge_uni":          FeatureCapability("subscriber_edge_uni", 0.6, 0.6, ("profile onu mapper",)),
        "subscriber_edge_wifi":         FeatureCapability("subscriber_edge_wifi", 0.0, 0.0),
        "subscriber_edge_bridge_group": FeatureCapability("subscriber_edge_bridge_group", 0.4, 0.4),
        "subscriber_edge_wan_binding":  FeatureCapability("subscriber_edge_wan_binding", 0.3, 0.3),
        "subscriber_edge_lan_service":  FeatureCapability("subscriber_edge_lan_service", 0.4, 0.4),
        "subscriber_edge_stb":          FeatureCapability("subscriber_edge_stb", 0.0, 0.0),
        "subscriber_edge_multicast":    FeatureCapability("subscriber_edge_multicast", 0.0, 0.0),
        "subscriber_edge_port_route":   FeatureCapability("subscriber_edge_port_route", 0.0, 0.0),
    },
}


# Cobertura semântica explícita por feature (independente do par específico).
# 1.0 = mesma feature semanticamente em ambos os vendors
# 0.5 = feature análoga mas com perda de detalhes
# 0.0 = feature exclusiva de um lado
EQUIVALENCE_COVERAGE: dict[str, float] = {
    "hostname": 1.0,
    "vlan": 0.95,
    "service_vlan": 0.4,        # só Fiberhome tem o conceito nativo
    "vlan_translation": 0.8,
    "qinq": 0.7,
    "uplink": 0.9,
    "uplink_lacp": 0.7,
    "static_route": 1.0,
    "mgmt_vlan_ip": 0.95,
    "boards": 0.5,              # tipos de board são vendor-specific
    "pon": 0.95,
    "onu_auth": 0.95,
    "onu_admin_state": 0.9,
    "onu_eth_ports": 0.7,       # cada vendor expressa diferente
    "onu_native_vlan": 0.85,
    "onu_user_vlan": 0.7,
    "gem_tcont": 0.8,
    "dba_profile": 0.8,
    "traffic_profile": 0.8,
    "line_profile": 0.75,
    "service_profile": 0.75,
    "service_port": 0.85,
    "multicast_igmp": 0.6,
    "multicast_gem": 0.5,
    "wan_profile": 0.4,         # Huawei-específico em grande parte
    "pppoe_session": 0.3,
    "ipoe_session": 0.3,
    "policy_route": 0.3,
    "snmp": 1.0,
    "ssh_cipher_detail": 1.0,
    "aaa_radius": 0.9,
    "users": 0.8,
    "qos_attachment": 0.6,
    "omci_provisioning": 1.0,
    "stb_ports": 0.4,
    "ssid_binding": 0.3,
    # L9 subscriber edge — equivalência semântica entre vendors
    "subscriber_edge_uni": 0.85,            # EthernetPort é universal
    "subscriber_edge_wifi": 0.75,           # SSID/auth/encrypt universais; campos variam
    "subscriber_edge_bridge_group": 0.7,    # Bridge groups variam entre vendors
    "subscriber_edge_wan_binding": 0.65,    # Modos PPPoE/IPoE/DHCP equivalentes; sintaxe varia
    "subscriber_edge_lan_service": 0.75,    # data/iptv/voip universais
    "subscriber_edge_stb": 0.6,             # Conceito equivalente, sintaxe varia muito
    "subscriber_edge_multicast": 0.6,
    "subscriber_edge_port_route": 0.4,      # Huawei-específico em grande parte
}


# ---------------------------------------------------------------------------
# Cálculo das células
# ---------------------------------------------------------------------------
def _level_from_score(score: float) -> SupportLevel:
    if score >= 0.85:
        return SupportLevel.FULL
    if score >= 0.45:
        return SupportLevel.PARTIAL
    if score > 0.0:
        return SupportLevel.NONE
    return SupportLevel.UNSUPPORTED


def cell(source: Vendor, target: Vendor, feature: str) -> CompatibilityCell:
    """Calcula a célula de compatibilidade para um único triplet."""
    src_cap = VENDOR_CAPABILITIES.get(source, {}).get(feature)
    tgt_cap = VENDOR_CAPABILITIES.get(target, {}).get(feature)
    equiv = EQUIVALENCE_COVERAGE.get(feature, 0.5)

    if src_cap is None or tgt_cap is None:
        return CompatibilityCell(
            source=source, target=target, feature=feature,
            level=SupportLevel.UNSUPPORTED,
            confidence=0.0,
            parser_coverage=0.0, renderer_coverage=0.0,
            equivalence_coverage=0.0, semantic_fidelity=0.0,
        )

    parser_c = src_cap.parser_coverage
    renderer_c = tgt_cap.renderer_coverage
    # Fidelidade semântica = média ponderada (parser pesa 30%, renderer 30%, equiv 40%)
    fidelity = parser_c * 0.3 + renderer_c * 0.3 + equiv * 0.4
    # Confidence = produto (regra do "elo mais fraco")
    confidence = (parser_c * renderer_c * equiv) ** (1 / 3) if (parser_c * renderer_c * equiv) > 0 else 0.0
    notes = tuple(set(src_cap.notes + tgt_cap.notes))
    return CompatibilityCell(
        source=source, target=target, feature=feature,
        level=_level_from_score(fidelity),
        confidence=confidence,
        parser_coverage=parser_c,
        renderer_coverage=renderer_c,
        equivalence_coverage=equiv,
        semantic_fidelity=fidelity,
        notes=notes,
    )


def matrix(features: Optional[list[str]] = None) -> dict:
    """
    Gera a matriz completa: vendor × vendor × feature → CompatibilityCell.

    `features` permite filtrar (default: todas).
    """
    feats = features or list(FEATURES)
    out: dict[str, dict[str, dict[str, dict]]] = {}
    vendors = [Vendor.FIBERHOME, Vendor.ZTE, Vendor.HUAWEI, Vendor.DATACOM]
    for src in vendors:
        out[src.value] = {}
        for tgt in vendors:
            if src == tgt:
                continue
            out[src.value][tgt.value] = {}
            for feat in feats:
                out[src.value][tgt.value][feat] = cell(src, tgt, feat).to_dict()
    return out


# ---------------------------------------------------------------------------
# Scores globais
# ---------------------------------------------------------------------------
def vendor_scores(vendor: Vendor) -> dict[str, float]:
    """
    Resume a maturidade dos parsers/renderers de um vendor.

      - parser_coverage_score : média das parser_coverage de todas as features
      - renderer_completeness_score : média das renderer_coverage
    """
    caps = VENDOR_CAPABILITIES.get(vendor, {})
    if not caps:
        return {"parser_coverage_score": 0.0, "renderer_completeness_score": 0.0}
    parser_avg = sum(c.parser_coverage for c in caps.values()) / len(caps)
    render_avg = sum(c.renderer_coverage for c in caps.values()) / len(caps)
    return {
        "parser_coverage_score": round(parser_avg, 3),
        "renderer_completeness_score": round(render_avg, 3),
    }


def conversion_score(source: Vendor, target: Vendor) -> dict[str, float | int]:
    """Resume um par origem→destino."""
    if source == target:
        return {"semantic_fidelity_score": 1.0, "full": 0, "partial": 0, "none": 0}
    cells = [cell(source, target, f) for f in FEATURES]
    fidelity = sum(c.semantic_fidelity for c in cells) / len(cells)
    levels = {lvl.value: 0 for lvl in SupportLevel}
    for c in cells:
        levels[c.level.value] += 1
    return {
        "semantic_fidelity_score": round(fidelity, 3),
        "FULL": levels[SupportLevel.FULL.value],
        "PARTIAL": levels[SupportLevel.PARTIAL.value],
        "NONE": levels[SupportLevel.NONE.value],
        "UNSUPPORTED": levels[SupportLevel.UNSUPPORTED.value],
    }


__all__ = [
    "SupportLevel",
    "FeatureCapability",
    "CompatibilityCell",
    "FEATURES",
    "VENDOR_CAPABILITIES",
    "EQUIVALENCE_COVERAGE",
    "cell",
    "matrix",
    "vendor_scores",
    "conversion_score",
]
