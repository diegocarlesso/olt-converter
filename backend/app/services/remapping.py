"""
ID Remapping engine — determinístico, com policies, collision avoidance,
dry-run e persistência de tabela.

Problema: cada vendor tem ranges/reservas diferentes para:

  * ONU id            (Fiberhome: 1..128; ZTE: 0..127; Huawei GPON: 0..127;
                        XGS-PON: 0..255)
  * service-port id   (ZTE: 1..n grande; Huawei: 1..n; Fiberhome: 1..1024)
  * GEM port          (idem)
  * VLAN reservada    (Huawei: 4093 mgmt; alguns ZTE: VLAN 1 default)

Princípios:

  1. Determinismo: dado o mesmo OLTConfig + policy, sempre produz a mesma
     tabela de remap.
  2. Collision-free: nunca remapeia para um id já usado, nem para um id
     na lista de reservados.
  3. Preservação dos bindings: quando renumeramos ONU, todos service-ports
     que referenciam (pon, onu_id) são atualizados; quando renumeramos
     service-port, mantemos consistência interna.
  4. Provenance: cada remap fica com `Provenance(source=SYNTHESIS,
     reason="remap onu_id 128→127 — out of GPON standard")`.
  5. Dry-run: o operador pode pedir só o plano (`apply=False`) e revisar.
  6. Persistência: a tabela `RemappingTable` pode ser anexada ao OLTConfig
     e consultada pela UI (old_id ↔ new_id por categoria).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from app.models import (
    AdminState,
    OLTConfig,
    Provenance,
    Vendor,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Policies por vendor/modelo
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RemappingPolicy:
    """Constraints de IDs por vendor."""

    vendor: Vendor
    model: str
    onu_id_min: int = 0
    onu_id_max: int = 127
    service_port_id_min: int = 1
    service_port_id_max: int = 65535
    gem_id_min: int = 0
    gem_id_max: int = 4095
    vlan_reserved: tuple[int, ...] = ()           # VLANs reservadas pelo vendor
    line_profile_id_min: int = 1
    line_profile_id_max: int = 99
    service_profile_id_min: int = 1
    service_profile_id_max: int = 99


POLICIES: dict[tuple[Vendor, str], RemappingPolicy] = {
    # Huawei GPON padrão (MA5800): onu_id 0..127, line/srv profile ids pequenos
    (Vendor.HUAWEI, "MA5800"): RemappingPolicy(
        vendor=Vendor.HUAWEI, model="MA5800",
        onu_id_min=0, onu_id_max=127,
        line_profile_id_max=200, service_profile_id_max=200,
        vlan_reserved=(4093,),
    ),
    (Vendor.HUAWEI, "MA5680T"): RemappingPolicy(
        vendor=Vendor.HUAWEI, model="MA5680T",
        onu_id_min=0, onu_id_max=127,
        vlan_reserved=(4093,),
    ),
    # ZTE C600 / C320 / C300
    (Vendor.ZTE, "C600"): RemappingPolicy(
        vendor=Vendor.ZTE, model="C600",
        onu_id_min=0, onu_id_max=127,
    ),
    (Vendor.ZTE, "C320"): RemappingPolicy(
        vendor=Vendor.ZTE, model="C320",
        onu_id_min=0, onu_id_max=127,
    ),
    # Fiberhome AN5516 numera 1..128 (1-based, e até 128)
    (Vendor.FIBERHOME, "AN5516"): RemappingPolicy(
        vendor=Vendor.FIBERHOME, model="AN5516",
        onu_id_min=1, onu_id_max=128,
    ),
    (Vendor.FIBERHOME, "AN6000"): RemappingPolicy(
        vendor=Vendor.FIBERHOME, model="AN6000",
        onu_id_min=0, onu_id_max=255,
    ),
    # Datacom
    (Vendor.DATACOM, "DM4615"): RemappingPolicy(
        vendor=Vendor.DATACOM, model="DM4615",
        onu_id_min=1, onu_id_max=128,
    ),
}


def policy_for(vendor: Vendor, model: Optional[str] = None) -> RemappingPolicy:
    """Retorna policy específica ou um default seguro."""
    if model and (vendor, model) in POLICIES:
        return POLICIES[(vendor, model)]
    # Default por vendor
    defaults = {
        Vendor.HUAWEI: POLICIES[(Vendor.HUAWEI, "MA5800")],
        Vendor.ZTE: POLICIES[(Vendor.ZTE, "C600")],
        Vendor.FIBERHOME: POLICIES[(Vendor.FIBERHOME, "AN5516")],
        Vendor.DATACOM: POLICIES[(Vendor.DATACOM, "DM4615")],
    }
    return defaults.get(vendor, RemappingPolicy(vendor=vendor, model="generic"))


# ---------------------------------------------------------------------------
# Tabela de remap
# ---------------------------------------------------------------------------
@dataclass
class RemapEntry:
    category: str          # "onu_id" | "service_port_id" | "line_profile_id" | …
    scope: str             # ex: "pon-1/1/5" para ONU; "global" para profile
    old_id: int
    new_id: int
    reason: str
    confidence: float = 0.9   # remap determinístico tem confiança alta


@dataclass
class RemappingTable:
    """Tabela completa de transformações aplicadas."""

    target_vendor: str
    target_model: str
    entries: list[RemapEntry] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def add(self, entry: RemapEntry) -> None:
        self.entries.append(entry)

    def lookup(self, category: str, scope: str, old_id: int) -> Optional[int]:
        for e in self.entries:
            if e.category == category and e.scope == scope and e.old_id == old_id:
                return e.new_id
        return None

    def to_dict(self) -> dict:
        return {
            "target_vendor": self.target_vendor,
            "target_model": self.target_model,
            "entries": [
                {
                    "category": e.category,
                    "scope": e.scope,
                    "old_id": e.old_id,
                    "new_id": e.new_id,
                    "reason": e.reason,
                    "confidence": e.confidence,
                }
                for e in self.entries
            ],
            "collisions": self.collisions,
            "skipped": self.skipped,
            "summary": {
                "total_remapped": len(self.entries),
                "by_category": {
                    cat: sum(1 for e in self.entries if e.category == cat)
                    for cat in {e.category for e in self.entries}
                },
            },
        }


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def remap_for(
    config: OLTConfig,
    target_vendor: Vendor,
    target_model: Optional[str] = None,
    apply: bool = True,
) -> tuple[OLTConfig, RemappingTable]:
    """
    Aplica remapping no `config` para o target_vendor/model.

    Quando `apply=False`, retorna o config inalterado mas a tabela com o
    plano completo (dry-run). Útil para a UI mostrar antes de confirmar.
    """
    policy = policy_for(target_vendor, target_model)
    table = RemappingTable(target_vendor=target_vendor.value, target_model=policy.model)

    cfg = copy.deepcopy(config) if apply else config

    _remap_onus(cfg, policy, table, apply=apply)
    _remap_service_ports(cfg, policy, table, apply=apply)
    _remap_line_profiles(cfg, policy, table, apply=apply)
    _remap_service_profiles(cfg, policy, table, apply=apply)
    _flag_reserved_vlans(cfg, policy, table)

    log.info(
        "remap_done",
        target=target_vendor.value,
        apply=apply,
        total=len(table.entries),
        collisions=len(table.collisions),
    )
    return cfg, table


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _remap_onus(
    cfg: OLTConfig,
    policy: RemappingPolicy,
    table: RemappingTable,
    apply: bool,
) -> None:
    """
    Renumera ONUs cujo id está fora do range do destino.

    Estratégia: dentro de cada PON, manda IDs out-of-range para o
    primeiro id livre do range em ordem crescente. Determinístico
    porque processa ONUs em ordem estável (slot, pon, onu_id).
    """
    # Agrupa ONUs por PON
    by_pon: dict[str, list] = {}
    for onu in cfg.onus:
        by_pon.setdefault(onu.pon_interface, []).append(onu)

    for pon_iface, onus in by_pon.items():
        used_ids = {o.onu_id for o in onus if policy.onu_id_min <= o.onu_id <= policy.onu_id_max}
        free_iter = (i for i in range(policy.onu_id_min, policy.onu_id_max + 1) if i not in used_ids)

        for onu in sorted(onus, key=lambda o: o.onu_id):
            if policy.onu_id_min <= onu.onu_id <= policy.onu_id_max:
                continue  # já está dentro

            new_id = next(free_iter, None)
            if new_id is None:
                # PON cheia → marca collision
                table.collisions.append(
                    f"PON {pon_iface}: ONU {onu.onu_id} sem id livre "
                    f"no range {policy.onu_id_min}-{policy.onu_id_max}. "
                    "Considere mover ONU para outra PON."
                )
                continue

            old_id = onu.onu_id
            entry = RemapEntry(
                category="onu_id",
                scope=pon_iface,
                old_id=old_id,
                new_id=new_id,
                reason=(
                    f"ONU id={old_id} excede range "
                    f"{policy.onu_id_min}-{policy.onu_id_max} de "
                    f"{policy.vendor.value}/{policy.model}; remapeada para {new_id}"
                ),
            )
            table.add(entry)

            if apply:
                onu.onu_id = new_id
                # Provenance: anota o remap
                prov = onu.provenance or Provenance.parsed()
                prov.reason = (prov.reason + " | " if prov.reason else "") + entry.reason
                prov.needs_review = True
                onu.provenance = prov
                # Propaga para todos os service-ports daquela ONU
                for sp in cfg.service_ports:
                    if sp.pon_interface == pon_iface and sp.onu_id == old_id:
                        sp.onu_id = new_id


def _remap_service_ports(
    cfg: OLTConfig,
    policy: RemappingPolicy,
    table: RemappingTable,
    apply: bool,
) -> None:
    """Garante service-port ids dentro do range, sem duplicidade."""
    used = {sp.service_port_id for sp in cfg.service_ports}
    next_free = policy.service_port_id_min

    for sp in cfg.service_ports:
        if policy.service_port_id_min <= sp.service_port_id <= policy.service_port_id_max:
            continue
        while next_free in used and next_free <= policy.service_port_id_max:
            next_free += 1
        if next_free > policy.service_port_id_max:
            table.collisions.append(
                f"service-port {sp.service_port_id} sem id livre no range "
                f"{policy.service_port_id_min}-{policy.service_port_id_max}"
            )
            continue
        old_id = sp.service_port_id
        new_id = next_free
        entry = RemapEntry(
            category="service_port_id",
            scope="global",
            old_id=old_id,
            new_id=new_id,
            reason=(
                f"service-port id={old_id} fora do range "
                f"{policy.service_port_id_min}-{policy.service_port_id_max}"
            ),
        )
        table.add(entry)
        if apply:
            sp.service_port_id = new_id
            used.add(new_id)
            used.discard(old_id)
            prov = sp.provenance or Provenance.parsed()
            prov.reason = (prov.reason + " | " if prov.reason else "") + entry.reason
            prov.needs_review = True
            sp.provenance = prov
        next_free += 1


def _remap_line_profiles(
    cfg: OLTConfig,
    policy: RemappingPolicy,
    table: RemappingTable,
    apply: bool,
) -> None:
    _remap_profile_ids(
        items=cfg.line_profiles,
        category="line_profile_id",
        policy=policy,
        id_min=policy.line_profile_id_min,
        id_max=policy.line_profile_id_max,
        table=table,
        apply=apply,
        on_remap=lambda old, new: _propagate_lp_id(cfg, old, new),
    )


def _remap_service_profiles(
    cfg: OLTConfig,
    policy: RemappingPolicy,
    table: RemappingTable,
    apply: bool,
) -> None:
    _remap_profile_ids(
        items=cfg.service_profiles,
        category="service_profile_id",
        policy=policy,
        id_min=policy.service_profile_id_min,
        id_max=policy.service_profile_id_max,
        table=table,
        apply=apply,
        on_remap=lambda old, new: _propagate_sp_id(cfg, old, new),
    )


def _remap_profile_ids(items, category, policy, id_min, id_max, table, apply, on_remap):
    used = {it.profile_id for it in items}
    next_free = id_min
    for it in items:
        if id_min <= it.profile_id <= id_max:
            continue
        while next_free in used and next_free <= id_max:
            next_free += 1
        if next_free > id_max:
            table.collisions.append(
                f"{category} {it.profile_id} sem id livre no range {id_min}-{id_max}"
            )
            continue
        old_id, new_id = it.profile_id, next_free
        entry = RemapEntry(
            category=category,
            scope="global",
            old_id=old_id,
            new_id=new_id,
            reason=(
                f"{category} id={old_id} fora do range {id_min}-{id_max} "
                f"de {policy.vendor.value}/{policy.model}"
            ),
        )
        table.add(entry)
        if apply:
            it.profile_id = new_id
            used.add(new_id)
            used.discard(old_id)
            prov = getattr(it, "provenance", None) or Provenance.parsed()
            prov.reason = (prov.reason + " | " if prov.reason else "") + entry.reason
            prov.needs_review = True
            it.provenance = prov
            on_remap(old_id, new_id)
        next_free += 1


def _propagate_lp_id(cfg: OLTConfig, old: int, new: int) -> None:
    for onu in cfg.onus:
        if onu.line_profile_id == old:
            onu.line_profile_id = new


def _propagate_sp_id(cfg: OLTConfig, old: int, new: int) -> None:
    for onu in cfg.onus:
        if onu.service_profile_id == old:
            onu.service_profile_id = new


def _flag_reserved_vlans(
    cfg: OLTConfig,
    policy: RemappingPolicy,
    table: RemappingTable,
) -> None:
    """Apenas registra warning para VLANs que colidem com reservas do destino."""
    for v in cfg.vlans:
        if v.id in policy.vlan_reserved:
            table.skipped.append(
                f"VLAN {v.id} é reservada por {policy.vendor.value}/{policy.model}. "
                "Considere renumerá-la manualmente."
            )


__all__ = [
    "RemappingPolicy",
    "RemapEntry",
    "RemappingTable",
    "POLICIES",
    "policy_for",
    "remap_for",
]
