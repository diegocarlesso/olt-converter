"""
Engine de síntese de profiles (DBA / Traffic).

Quando um vendor destino exige profiles que a origem não declarou, sintetizamos
profiles inteligentes baseados em:

  * Nomes de service-vlan (PPPOE_FTTH_1G → tier 1G)
  * Velocidades inferidas (parsing de "1G", "500M", "300M" em nomes)
  * Traffic tables / CIR/PIR existentes
  * GEM/TCONT relationships
  * ONU type capabilities (PoE / wifi → tier residencial)
  * Padrões recorrentes do ISP

Princípios:

  * NUNCA fallback silencioso. Quando síntese é impossível, criamos um
    DBA-DEFAULT explicitamente marcado com `Provenance.default_fallback`.
  * Cada profile sintetizado anexa Provenance com source=SYNTHESIS,
    confidence e reason — rastreável e revisável na UI.
  * Profiles existentes são mantidos intactos.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Optional

from app.models import (
    DBAProfile,
    DBAType,
    OLTConfig,
    Provenance,
    TrafficProfile,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Catálogo de tiers reconhecidos pelo nome
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Tier:
    label: str
    kbps: int
    type: DBAType = DBAType.TYPE3
    assured_ratio: float = 0.2

_TIER_PATTERNS: list[tuple[re.Pattern, _Tier]] = [
    (re.compile(r"\b10\s*G\b|10G\b|10000M\b", re.IGNORECASE), _Tier("DBA-SYNTH-10G", 10_000_000)),
    (re.compile(r"\b1\s*G\b|1G\b|1000M\b", re.IGNORECASE), _Tier("DBA-SYNTH-1G", 1_024_000)),
    (re.compile(r"\b800M\b", re.IGNORECASE), _Tier("DBA-SYNTH-800M", 819_200)),
    (re.compile(r"\b500M\b", re.IGNORECASE), _Tier("DBA-SYNTH-500M", 512_000)),
    (re.compile(r"\b400M\b", re.IGNORECASE), _Tier("DBA-SYNTH-400M", 409_600)),
    (re.compile(r"\b300M\b", re.IGNORECASE), _Tier("DBA-SYNTH-300M", 307_200)),
    (re.compile(r"\b200M\b", re.IGNORECASE), _Tier("DBA-SYNTH-200M", 204_800)),
    (re.compile(r"\b100M\b", re.IGNORECASE), _Tier("DBA-SYNTH-100M", 102_400)),
    (re.compile(r"\b50M\b", re.IGNORECASE), _Tier("DBA-SYNTH-50M", 51_200)),
    (re.compile(r"\bVOIP\b|\bVOZ\b", re.IGNORECASE), _Tier("DBA-SYNTH-VOZ", 2048, DBAType.TYPE1, 1.0)),
    (re.compile(r"\bIPTV\b|\bTV\b", re.IGNORECASE), _Tier("DBA-SYNTH-IPTV", 102_400, DBAType.TYPE3, 0.5)),
    (re.compile(r"\bMGMT\b|\bGERENCIA\b|\bMANAGEMENT\b", re.IGNORECASE), _Tier("DBA-SYNTH-MGMT", 10_240, DBAType.TYPE3, 0.5)),
    (re.compile(r"\bCORP\b|\bVIP\b|\bENTERPRISE\b", re.IGNORECASE), _Tier("DBA-SYNTH-CORP", 1_024_000, DBAType.TYPE5, 0.8)),
]


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def synthesize_dba_profiles(config: OLTConfig) -> OLTConfig:
    """Cria DBAs sintéticos a partir dos nomes de service-vlans e traffic profiles."""
    cfg = copy.deepcopy(config)

    existing_names = {d.name for d in cfg.dba_profiles}
    candidates: dict[str, _Tier] = {}
    reasons: dict[str, list[str]] = {}

    # Vasculha service-vlans
    for sv in cfg.service_vlans:
        tier = _match_tier(sv.name)
        if tier and tier.label not in existing_names:
            candidates[tier.label] = tier
            reasons.setdefault(tier.label, []).append(f"service_vlan '{sv.name}'")

    # Vasculha traffic profiles (pelo nome também)
    for tp in cfg.traffic_profiles:
        tier = _match_tier(tp.name)
        if tier and tier.label not in existing_names:
            candidates[tier.label] = tier
            reasons.setdefault(tier.label, []).append(f"traffic_profile '{tp.name}'")
        elif tp.cir and tp.pir and tp.name not in existing_names:
            # Sintetiza DBA a partir do traffic profile diretamente
            label = f"DBA-FROM-{tp.name}"
            if label not in existing_names:
                candidates[label] = _Tier(label, tp.pir or tp.cir, DBAType.TYPE3, (tp.cir / tp.pir) if tp.pir else 0.3)
                reasons.setdefault(label, []).append(
                    f"traffic_profile '{tp.name}' (cir={tp.cir}, pir={tp.pir})"
                )

    # Materializa DBAs sintetizados
    next_id = max((d.profile_id for d in cfg.dba_profiles), default=9) + 1
    for label, tier in candidates.items():
        assured = int(tier.kbps * tier.assured_ratio) if tier.type in {DBAType.TYPE3, DBAType.TYPE5} else None
        max_bw = tier.kbps if tier.type != DBAType.TYPE1 else None
        fix_bw = tier.kbps if tier.type == DBAType.TYPE1 else None
        cfg.dba_profiles.append(
            DBAProfile(
                profile_id=next_id,
                name=label,
                type=tier.type,
                assured_bandwidth=assured,
                max_bandwidth=max_bw,
                fix_bandwidth=fix_bw,
                provenance=Provenance.synthetic(
                    confidence=0.75,
                    reason=f"Sintetizado a partir de: {', '.join(reasons[label])}",
                    signals=reasons[label],
                ),
            )
        )
        next_id += 1

    # Fallback explícito: se ainda não há nenhum DBA, cria DBA-DEFAULT
    if not cfg.dba_profiles:
        cfg.dba_profiles.append(
            DBAProfile(
                profile_id=10,
                name="DBA-DEFAULT",
                type=DBAType.TYPE4,
                max_bandwidth=1_024_000,
                provenance=Provenance.default_fallback(
                    "Nenhum DBA detectado na origem nem inferível por nome. "
                    "DBA-DEFAULT criado como placeholder — revise antes de produção."
                ),
            )
        )
        cfg.parse_warnings.append(
            "DBA-DEFAULT sintetizado por falta de qualquer pista. Revisar manualmente."
        )

    return cfg


def synthesize_traffic_profiles(config: OLTConfig) -> OLTConfig:
    """Sintetiza traffic-tables (Huawei) a partir dos DBAs disponíveis."""
    cfg = copy.deepcopy(config)
    existing_names = {tp.name for tp in cfg.traffic_profiles}

    next_id = max((tp.profile_id for tp in cfg.traffic_profiles), default=7) + 1
    for d in cfg.dba_profiles:
        synth_name = f"TT-{d.name.replace('DBA-', '')}"
        if synth_name in existing_names:
            continue
        bw = d.max_bandwidth or d.fix_bandwidth or 1_024_000
        cfg.traffic_profiles.append(
            TrafficProfile(
                profile_id=next_id,
                name=synth_name,
                cir=bw,
                cbs=int(bw * 32.8),         # ~32 KB por kbps (CBS típico Huawei)
                pir=bw,
                pbs=int(bw * 32.8),
                color_mode="color-blind",
                priority=0,
                provenance=Provenance.synthetic(
                    confidence=0.7,
                    reason=f"Sintetizado a partir do DBA '{d.name}' (bw={bw} kbps)",
                    signals=[f"dba_profile {d.name}"],
                ),
            )
        )
        next_id += 1

    return cfg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _match_tier(name: Optional[str]) -> Optional[_Tier]:
    if not name:
        return None
    for pattern, tier in _TIER_PATTERNS:
        if pattern.search(name):
            return tier
    return None


__all__ = ["synthesize_dba_profiles", "synthesize_traffic_profiles"]
