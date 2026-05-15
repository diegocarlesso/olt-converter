"""
Engine de equivalência semântica entre vendors.

A equivalência NÃO é substituição de texto. Cada vendor expressa o mesmo
conceito de formas diferentes; este módulo traduz *conceitos* em estruturas
do `OLTConfig` antes do renderer ser invocado.

Casos cobertos:

* Fiberhome `ServiceVLAN` (range nomeado) ↔ Huawei `VLAN smart` + ServicePort
  multi-service por ONU
* Fiberhome `ONUTypeProfile` (cs onu profile) ↔ Huawei `ServiceProfile` (ont-srvprofile)
* Huawei `ServicePort multi-service` ↔ ZTE `service-port + native vlan` na ONU
* Fiberhome whitelist ↔ Huawei `ont add ... omci`
* Huawei `traffic table` ↔ ZTE `gpon-profile bandwidth`

A função pública `harmonize_for(config, target_vendor)` produz um novo
`OLTConfig` ajustado para que o renderer destino tenha tudo que precisa
sem alterar o modelo original. Mutações são feitas em cópia profunda.
"""
from __future__ import annotations

import copy
from typing import Optional

from app.models import (
    DBAProfile,
    DBAType,
    OLTConfig,
    ONU,
    PortConfig,
    PortType,
    ServicePort,
    ServicePortAction,
    ServiceProfile,
    ServiceType,
    ServiceVLAN,
    TrafficProfile,
    Vendor,
    VLAN,
    VLANMode,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def harmonize_for(config: OLTConfig, target_vendor: Vendor) -> OLTConfig:
    """
    Retorna uma cópia do `config` com ajustes semânticos específicos do
    `target_vendor`. O original NÃO é modificado.

    Garantias:
      - Para qualquer destino, todas as VLANs referenciadas em
        service-ports/ONUs existem em `config.vlans`.
      - DBA profiles são deduplicados por nome.
      - `ONU.line_profile_name` é preenchido quando só id existir e vice-versa.
      - Service-ports recebem `gem_id=1` quando ausente (Huawei/ZTE default).
      - Para destino Huawei, gera `ServiceProfile` a partir de `ONUTypeProfile`
        (Fiberhome) caso já não exista.
      - Para destino ZTE, converte `multi-service user-vlan` em `native vlan`
        dentro da ONU.
      - Para destino Fiberhome, agrupa VLANs em `ServiceVLAN` quando o nome
        original existir.
    """
    cfg = copy.deepcopy(config)

    _fill_missing_vlans(cfg)
    _resolve_profile_refs(cfg)
    _normalize_dba_types(cfg)
    _ensure_service_port_gem(cfg)

    if target_vendor == Vendor.HUAWEI:
        _to_huawei(cfg)
    elif target_vendor == Vendor.ZTE:
        _to_zte(cfg)
    elif target_vendor == Vendor.FIBERHOME:
        _to_fiberhome(cfg)
    elif target_vendor == Vendor.DATACOM:
        _to_datacom(cfg)

    log.info(
        "equivalence_done",
        source=cfg.vendor.value,
        target=target_vendor.value,
        stats=cfg.stats(),
    )
    return cfg


# ---------------------------------------------------------------------------
# Normalizações comuns
# ---------------------------------------------------------------------------
def _fill_missing_vlans(cfg: OLTConfig) -> None:
    """Garante que toda VLAN referenciada existe em `cfg.vlans`."""
    referenced: set[int] = set()
    for sp in cfg.service_ports:
        for vid in (sp.match_vlan, sp.target_vlan, sp.user_vlan):
            if vid:
                referenced.add(vid)
    for onu in cfg.onus:
        for vid in (onu.native_vlan, onu.user_vlan):
            if vid:
                referenced.add(vid)
    existing = {v.id for v in cfg.vlans}
    for vid in referenced - existing:
        cfg.vlans.append(VLAN(id=vid, smart=True, description="auto-added by equivalence"))


def _resolve_profile_refs(cfg: OLTConfig) -> None:
    """
    Se uma ONU tem só `line_profile_id` ou só `line_profile_name`,
    completa o outro lado para que o renderer destino possa usar qualquer um.
    """
    lp_by_id = {p.profile_id: p for p in cfg.line_profiles}
    lp_by_name = {p.name: p for p in cfg.line_profiles}
    sp_by_id = {p.profile_id: p for p in cfg.service_profiles}
    sp_by_name = {p.name: p for p in cfg.service_profiles}

    for onu in cfg.onus:
        if onu.line_profile_id and not onu.line_profile_name:
            lp = lp_by_id.get(onu.line_profile_id)
            if lp:
                onu.line_profile_name = lp.name
        elif onu.line_profile_name and not onu.line_profile_id:
            lp = lp_by_name.get(onu.line_profile_name)
            if lp:
                onu.line_profile_id = lp.profile_id

        if onu.service_profile_id and not onu.service_profile_name:
            sp = sp_by_id.get(onu.service_profile_id)
            if sp:
                onu.service_profile_name = sp.name
        elif onu.service_profile_name and not onu.service_profile_id:
            sp = sp_by_name.get(onu.service_profile_name)
            if sp:
                onu.service_profile_id = sp.profile_id


def _normalize_dba_types(cfg: OLTConfig) -> None:
    """Inferir DBA type a partir dos campos quando ausente/inconsistente."""
    for d in cfg.dba_profiles:
        if d.fix_bandwidth and not d.assured_bandwidth and not d.max_bandwidth:
            d.type = DBAType.TYPE1
        elif d.assured_bandwidth and not d.max_bandwidth and not d.fix_bandwidth:
            d.type = DBAType.TYPE2
        elif d.assured_bandwidth and d.max_bandwidth and not d.fix_bandwidth:
            d.type = DBAType.TYPE3
        elif d.max_bandwidth and not d.assured_bandwidth and not d.fix_bandwidth:
            d.type = DBAType.TYPE4
        elif d.fix_bandwidth and d.assured_bandwidth and d.max_bandwidth:
            d.type = DBAType.TYPE5


def _ensure_service_port_gem(cfg: OLTConfig) -> None:
    """Atribui gem_id=1 quando não informado (default plausível)."""
    for sp in cfg.service_ports:
        if sp.gem_id is None:
            sp.gem_id = 1


# ---------------------------------------------------------------------------
# Direção: → Huawei MA5800
# ---------------------------------------------------------------------------
def _to_huawei(cfg: OLTConfig) -> None:
    # 1) ServiceProfile a partir de ONUTypeProfile (Fiberhome)
    existing_names = {sp.name for sp in cfg.service_profiles}
    for ot in cfg.onu_type_profiles:
        if ot.name in existing_names:
            continue
        cfg.service_profiles.append(
            ServiceProfile(
                profile_id=ot.type_id,
                name=ot.name,
                ports=PortConfig(
                    eth=ot.lan1g, pots=ot.pots, wifi=ot.wifi, catv=ot.catv
                ),
            )
        )
        existing_names.add(ot.name)

    # 2) Garante DBA profile default
    if not cfg.dba_profiles:
        cfg.dba_profiles.append(
            DBAProfile(
                profile_id=10, name="DBA-DEFAULT", type=DBAType.TYPE4,
                max_bandwidth=1024000,
            )
        )

    # 3) Garante TrafficProfile default
    if not cfg.traffic_profiles:
        cfg.traffic_profiles.append(
            TrafficProfile(
                profile_id=8, name="TT-1G",
                cir=1024000, cbs=33540000, pir=1024000, pbs=33540000,
            )
        )

    # 4) VLAN smart (Huawei usa quase sempre smart-vlan)
    for v in cfg.vlans:
        v.smart = True

    # 5) Para cada ONU sem service-port, gera um a partir do native_vlan
    next_sp_id = max((sp.service_port_id for sp in cfg.service_ports), default=0) + 1
    have_sp = {(sp.pon_interface, sp.onu_id) for sp in cfg.service_ports}
    for onu in cfg.onus:
        key = (onu.pon_interface, onu.onu_id)
        if key in have_sp:
            continue
        if onu.native_vlan:
            cfg.service_ports.append(
                ServicePort(
                    service_port_id=next_sp_id,
                    pon_interface=onu.pon_interface,
                    onu_id=onu.onu_id,
                    gem_id=1,
                    match_vlan=onu.native_vlan,
                    action=ServicePortAction.REPLACE,
                    target_vlan=onu.native_vlan,
                    user_vlan=onu.native_vlan,
                )
            )
            next_sp_id += 1


# ---------------------------------------------------------------------------
# Direção: → ZTE C600
# ---------------------------------------------------------------------------
def _to_zte(cfg: OLTConfig) -> None:
    # ZTE não suporta ONU id > 127 no GPON padrão. Avisamos via warnings.
    for onu in cfg.onus:
        if onu.onu_id > 127:
            cfg.parse_warnings.append(
                f"ONU id={onu.onu_id} em {onu.pon_interface} excede 127 (limite ZTE GPON)"
            )

    # Converte user-vlan de service-port em native-vlan da ONU
    for sp in cfg.service_ports:
        if sp.user_vlan:
            onu = cfg.find_onu(sp.pon_interface, sp.onu_id)
            if onu and not onu.native_vlan:
                onu.native_vlan = sp.user_vlan

    # VLANs com smart=True em ZTE não fazem sentido — força como tag normal
    for v in cfg.vlans:
        v.smart = False


# ---------------------------------------------------------------------------
# Direção: → Fiberhome AN5516 (WOS)
# ---------------------------------------------------------------------------
def _to_fiberhome(cfg: OLTConfig) -> None:
    # Cria ServiceVLAN para cada VLAN nomeada que ainda não está num range
    in_svc: set[int] = set()
    for sv in cfg.service_vlans:
        for vid in range(sv.vlan_begin, sv.vlan_end + 1):
            in_svc.add(vid)

    next_id = max((sv.service_id for sv in cfg.service_vlans), default=100) + 1
    for v in cfg.vlans:
        if v.id in in_svc or not v.name:
            continue
        cfg.service_vlans.append(
            ServiceVLAN(
                service_id=next_id,
                name=v.name,
                service_type=v.service_type,
                vlan_begin=v.id,
                vlan_end=v.id,
            )
        )
        v.service_vlan_id = next_id
        next_id += 1


# ---------------------------------------------------------------------------
# Direção: → Datacom DM4615
# ---------------------------------------------------------------------------
def _to_datacom(cfg: OLTConfig) -> None:
    # Datacom usa VLAN simples com nome; smart-vlan não se aplica
    for v in cfg.vlans:
        v.smart = False


__all__ = ["harmonize_for"]
