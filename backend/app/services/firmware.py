"""
Abstração de firmware/modelo.

Diferentes modelos do mesmo vendor têm dialetos CLI distintos:

  - Huawei MA5608T  vs  MA5800-X7  vs  MA5680T
  - ZTE C320        vs  C600       vs  C300
  - Fiberhome WOS (AN5516) vs AN6000 (sintaxe nova `ont add`)

Esta camada expõe `pick_variant(vendor, firmware, model)` que retorna um
dicionário com flags que o renderer consulta para escolher variantes
sintáticas. Manter aqui evita poluir o `OLTConfig` com lógica de vendor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Vendor


@dataclass(frozen=True)
class FirmwareVariant:
    """Conjunto de flags que controlam variações de saída do renderer."""

    name: str
    # Sintaxe de service-port
    service_port_uses_multi_service: bool = True
    # Suporta ONU ids > 127 (XGS-PON / Fiberhome)
    onu_id_supports_above_127: bool = False
    # Sintaxe `ont add slot port onu_id ...` (Huawei novo) vs `onu add ...`
    ont_add_style: str = "huawei-omci"     # huawei-omci | fiberhome-onu-add | none
    # Profiles support: ont-srvprofile, ont-lineprofile, ont-wan-profile
    supports_ont_srvprofile: bool = True
    supports_ont_lineprofile: bool = True
    supports_ont_wan_profile: bool = True
    # smart-vlan vs vlan comum
    vlan_default_smart: bool = True


_VARIANTS: dict[tuple[Vendor, str], FirmwareVariant] = {
    # Huawei
    (Vendor.HUAWEI, "MA5800"): FirmwareVariant(
        name="MA5800",
        service_port_uses_multi_service=True,
        onu_id_supports_above_127=True,
        ont_add_style="huawei-omci",
    ),
    (Vendor.HUAWEI, "MA5680T"): FirmwareVariant(
        name="MA5680T",
        service_port_uses_multi_service=True,
        onu_id_supports_above_127=False,
        ont_add_style="huawei-omci",
    ),
    (Vendor.HUAWEI, "MA5608T"): FirmwareVariant(
        name="MA5608T",
        service_port_uses_multi_service=True,
        onu_id_supports_above_127=False,
        ont_add_style="huawei-omci",
    ),
    # ZTE
    (Vendor.ZTE, "C600"): FirmwareVariant(
        name="C600",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=False,
        ont_add_style="none",
        vlan_default_smart=False,
    ),
    (Vendor.ZTE, "C320"): FirmwareVariant(
        name="C320",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=False,
        ont_add_style="none",
        vlan_default_smart=False,
    ),
    (Vendor.ZTE, "C300"): FirmwareVariant(
        name="C300",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=False,
        ont_add_style="none",
        vlan_default_smart=False,
    ),
    # Fiberhome
    (Vendor.FIBERHOME, "AN5516"): FirmwareVariant(
        name="AN5516",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=True,
        ont_add_style="fiberhome-onu-add",
        supports_ont_srvprofile=False,
        supports_ont_lineprofile=False,
        vlan_default_smart=False,
    ),
    (Vendor.FIBERHOME, "AN6000"): FirmwareVariant(
        name="AN6000",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=True,
        ont_add_style="huawei-omci",  # sintaxe nova
        supports_ont_srvprofile=True,
        supports_ont_lineprofile=True,
        vlan_default_smart=True,
    ),
    # Datacom
    (Vendor.DATACOM, "DM4615"): FirmwareVariant(
        name="DM4615",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=False,
        ont_add_style="none",
        vlan_default_smart=False,
    ),
    (Vendor.DATACOM, "DM4610"): FirmwareVariant(
        name="DM4610",
        service_port_uses_multi_service=False,
        onu_id_supports_above_127=False,
        ont_add_style="none",
        vlan_default_smart=False,
    ),
}


def pick_variant(
    vendor: Vendor,
    model: Optional[str] = None,
    firmware: Optional[str] = None,
) -> FirmwareVariant:
    """
    Retorna a variante mais específica conhecida. Cai para um default seguro
    do vendor se modelo desconhecido.
    """
    if model and (vendor, model) in _VARIANTS:
        return _VARIANTS[(vendor, model)]

    # heurísticas com firmware
    if firmware:
        fw_lower = firmware.lower()
        for (v, m), variant in _VARIANTS.items():
            if v == vendor and m.lower() in fw_lower:
                return variant

    # default por vendor
    defaults = {
        Vendor.HUAWEI: _VARIANTS[(Vendor.HUAWEI, "MA5800")],
        Vendor.ZTE: _VARIANTS[(Vendor.ZTE, "C600")],
        Vendor.FIBERHOME: _VARIANTS[(Vendor.FIBERHOME, "AN5516")],
        Vendor.DATACOM: _VARIANTS[(Vendor.DATACOM, "DM4615")],
    }
    return defaults.get(vendor, FirmwareVariant(name="generic"))


__all__ = ["FirmwareVariant", "pick_variant"]
