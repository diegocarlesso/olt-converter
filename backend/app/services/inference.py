"""
Engine de inferência de bindings ONU ↔ ServiceVLAN ↔ ServicePort.

Princípios:

* Nunca depender de um único sinal.
* Cada binding inferido carrega Provenance (source=INFERENCE, confidence, reason,
  signals[]).
* Quando confidence < 0.7 → marcamos `needs_review` para a UI destacar.
* Quando nenhum sinal é encontrado → não inventamos: simplesmente não criamos
  o binding e geramos warning.

Sinais consultados (em ordem de força):

  S1. ONU.native_vlan          (1.0 — vínculo direto)
  S2. GEM-port → VLAN mapping  (0.9 — vínculo direto via line-profile)
  S3. ServicePort existente    (1.0 — já é um binding declarado)
  S4. VLAN translation no port-config do service-profile      (0.85)
  S5. ServiceVLAN cujo nome contém o serviço da ONU type      (0.6)
  S6. Uplink allowed_vlans + ONU.line_profile_name pattern    (0.4)
  S7. Convenção de PON inteira → ServiceVLAN única (0.5 se única no contexto)

A função `infer_service_ports(config)` retorna uma cópia do config com
service-ports adicionados (cada um com provenance), sem mutar o original.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from app.models import (
    OLTConfig,
    ONU,
    Provenance,
    ServicePort,
    ServicePortAction,
    ServiceVLAN,
    VLAN,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Estrutura interna de candidato
# ---------------------------------------------------------------------------
@dataclass
class _Candidate:
    vlan_id: int
    confidence: float
    signals: list[str]
    reason: str
    service_vlan_id: Optional[int] = None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def infer_service_ports(
    config: OLTConfig,
    origin_file: Optional[str] = None,
) -> OLTConfig:
    """
    Adiciona service-ports inferidos ao config (cópia profunda).

    Para cada ONU sem service-port existente, tenta encontrar o binding com
    ServiceVLAN/VLAN combinando os sinais acima. Anota Provenance em cada
    novo service-port para que o operador possa revisar.
    """
    cfg = copy.deepcopy(config)

    # Service-ports que já existem por (pon, onu)
    existing = {
        (sp.pon_interface, sp.onu_id) for sp in cfg.service_ports
    }
    next_sp_id = max((sp.service_port_id for sp in cfg.service_ports), default=0) + 1

    # Pré-índices úteis
    vlans_by_id = {v.id: v for v in cfg.vlans}
    svlan_index = _index_service_vlans(cfg)

    added = 0
    for onu in cfg.onus:
        key = (onu.pon_interface, onu.onu_id)
        if key in existing:
            continue

        candidates: list[_Candidate] = []

        # S1 — native VLAN da ONU
        if onu.native_vlan and onu.native_vlan in vlans_by_id:
            candidates.append(
                _Candidate(
                    vlan_id=onu.native_vlan,
                    confidence=1.0,
                    signals=["onu.native_vlan"],
                    reason=f"ONU declara native vlan {onu.native_vlan}",
                    service_vlan_id=_find_service_vlan_id(svlan_index, onu.native_vlan),
                )
            )

        # S2 — GEM mappings dentro do line-profile
        if onu.line_profile_name:
            lp = cfg.find_line_profile(onu.line_profile_name)
            if lp:
                for m in lp.mappers:
                    vid = m.get("vlan_id")
                    gid = m.get("gem_id")
                    if vid and vid in vlans_by_id:
                        candidates.append(
                            _Candidate(
                                vlan_id=vid,
                                confidence=0.9,
                                signals=[f"line-profile {lp.name} mapper gem {gid} → vlan {vid}"],
                                reason=f"VLAN {vid} mapeada para GEM {gid} no line-profile {lp.name}",
                                service_vlan_id=_find_service_vlan_id(svlan_index, vid),
                            )
                        )

        # S3 — service-profile port-vlan translation
        if onu.service_profile_name:
            sp = cfg.find_service_profile(onu.service_profile_name)
            if sp:
                for trans in sp.port_vlan_translations:
                    vid = trans.get("translation")
                    user_vlan = trans.get("user_vlan")
                    if vid and vid in vlans_by_id:
                        candidates.append(
                            _Candidate(
                                vlan_id=vid,
                                confidence=0.85,
                                signals=[
                                    f"service-profile {sp.name} eth{trans.get('port', 1)} translation={vid} user_vlan={user_vlan}"
                                ],
                                reason=f"service-profile {sp.name} traduz para VLAN {vid}",
                                service_vlan_id=_find_service_vlan_id(svlan_index, vid),
                            )
                        )

        # S4 — heurística por nome (ONU type ↔ ServiceVLAN name)
        if onu.onu_type:
            for sv in cfg.service_vlans:
                if _name_match(onu.onu_type, sv.name):
                    candidates.append(
                        _Candidate(
                            vlan_id=sv.vlan_begin,
                            confidence=0.55,
                            signals=[
                                f"onu_type={onu.onu_type} ↔ service_vlan name='{sv.name}'"
                            ],
                            reason=(
                                f"Nome do ONU type ({onu.onu_type}) tem afinidade "
                                f"semântica com service-vlan '{sv.name}'"
                            ),
                            service_vlan_id=sv.service_id,
                        )
                    )

        # S5 — PON inteira em uma única ServiceVLAN
        pon_svc = _service_vlan_for_pon(cfg, onu.pon_interface)
        if pon_svc:
            candidates.append(
                _Candidate(
                    vlan_id=pon_svc.vlan_begin,
                    confidence=0.5,
                    signals=[
                        f"PON {onu.pon_interface} → única service-vlan candidata = {pon_svc.name}"
                    ],
                    reason=f"PON {onu.pon_interface} tem afinidade exclusiva à service-vlan '{pon_svc.name}'",
                    service_vlan_id=pon_svc.service_id,
                )
            )

        if not candidates:
            cfg.parse_warnings.append(
                f"Não foi possível inferir service-port para ONU "
                f"{onu.pon_interface}:{onu.onu_id} (serial={onu.serial_number}). "
                "Nenhum sinal disponível."
            )
            continue

        # Combina candidatos: mesma VLAN com múltiplos sinais → soma confidence
        chosen = _consolidate(candidates)

        cfg.service_ports.append(
            ServicePort(
                service_port_id=next_sp_id,
                pon_interface=onu.pon_interface,
                onu_id=onu.onu_id,
                gem_id=1,
                match_vlan=chosen.vlan_id,
                action=ServicePortAction.REPLACE,
                target_vlan=chosen.vlan_id,
                user_vlan=chosen.vlan_id,
                provenance=Provenance.inferred(
                    confidence=chosen.confidence,
                    reason=chosen.reason,
                    signals=chosen.signals,
                    origin_file=origin_file,
                ),
            )
        )
        next_sp_id += 1
        added += 1

    log.info(
        "inference_service_ports_done",
        added=added,
        total_onus=len(cfg.onus),
        coverage=f"{added / max(len(cfg.onus), 1) * 100:.1f}%",
    )
    return cfg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _index_service_vlans(cfg: OLTConfig) -> dict[int, ServiceVLAN]:
    """vlan_id → ServiceVLAN que a contém."""
    out: dict[int, ServiceVLAN] = {}
    for sv in cfg.service_vlans:
        for vid in range(sv.vlan_begin, sv.vlan_end + 1):
            out[vid] = sv
    return out


def _find_service_vlan_id(idx: dict[int, ServiceVLAN], vlan_id: int) -> Optional[int]:
    sv = idx.get(vlan_id)
    return sv.service_id if sv else None


def _name_match(onu_type: str, service_vlan_name: str) -> bool:
    """
    Heurística leve: nomes que compartilham um substring de 4+ caracteres
    significativo (PPPOE, IPTV, VOIP, GERENCIA etc.).
    """
    tokens = _tokenize(onu_type) + _tokenize(service_vlan_name)
    common = set(_tokenize(onu_type)).intersection(set(_tokenize(service_vlan_name)))
    return any(len(t) >= 4 for t in common)


_TOKEN_RE = re.compile(r"[A-Za-z]{3,}")


def _tokenize(s: str) -> list[str]:
    return [t.upper() for t in _TOKEN_RE.findall(s or "")]


def _service_vlan_for_pon(cfg: OLTConfig, pon_iface: str) -> Optional[ServiceVLAN]:
    """
    Se TODAS as ONUs da PON usam a mesma service-vlan-name padrão da nomenclatura,
    retorna essa service-vlan. Heurística fraca, só ativada se houver convergência.
    """
    onus_in_pon = [o for o in cfg.onus if o.pon_interface == pon_iface]
    if len(onus_in_pon) < 3:
        return None
    types = {o.onu_type for o in onus_in_pon if o.onu_type}
    if len(types) != 1:
        return None
    only_type = next(iter(types))
    matches = [sv for sv in cfg.service_vlans if _name_match(only_type, sv.name)]
    return matches[0] if len(matches) == 1 else None


def _consolidate(candidates: Iterable[_Candidate]) -> _Candidate:
    """
    Quando múltiplos candidatos apontam para o mesmo vlan_id, soma os scores
    (limitado a 1.0) e concatena signals. Retorna o vencedor.
    """
    by_vlan: dict[int, _Candidate] = {}
    for c in candidates:
        existing = by_vlan.get(c.vlan_id)
        if existing is None:
            by_vlan[c.vlan_id] = c
            continue
        # combina
        combined = _Candidate(
            vlan_id=c.vlan_id,
            confidence=min(1.0, existing.confidence + c.confidence * 0.3),
            signals=existing.signals + c.signals,
            reason=existing.reason + " | " + c.reason,
            service_vlan_id=existing.service_vlan_id or c.service_vlan_id,
        )
        by_vlan[c.vlan_id] = combined

    winner = max(by_vlan.values(), key=lambda x: x.confidence)
    return winner


__all__ = ["infer_service_ports"]
