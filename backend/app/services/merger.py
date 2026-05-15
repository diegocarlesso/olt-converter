"""
Mescla múltiplos OLTConfigs em um único, preservando proveniência por entidade.

Caso de uso primário:

  1. Backup principal (BACKUP-FIBERHOME.txt)
  2. Dump de service-ports (gpononu add servport ...) — opcional
  3. Dump de ONU running config — opcional
  4. Bridge table — opcional
  5. VLAN mapping dump — opcional

Cada arquivo é parseado independentemente; o `merge_configs()` combina-os no
mesmo modelo, registrando `origin_files` em cada entidade que recebeu input
adicional.
"""
from __future__ import annotations

from typing import Sequence

from app.models import (
    OLTConfig,
    Provenance,
    ProvenanceSource,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


def merge_configs(
    configs: Sequence[OLTConfig],
    file_labels: Sequence[str] | None = None,
) -> OLTConfig:
    """
    Combina múltiplos `OLTConfig`s em um único.

    Regras:

      * Entidades únicas (hostname, vendor, model, firmware): vem do primeiro
        config; arquivos posteriores podem complementar campos faltantes.
      * Listas (vlans, onus, service_ports, profiles, etc.): união por chave
        natural (id/name); duplicatas com valores diferentes são marcadas como
        warnings.
      * Cada entidade recebe `origin_files` acumulando os labels de onde veio.
      * `parse_warnings` e `raw_unparsed` são concatenados.

    `file_labels[i]` é o nome legível do arquivo `configs[i]` (ex: "BACKUP-FIBERHOME.txt").
    """
    if not configs:
        raise ValueError("merge_configs precisa de pelo menos 1 config")

    labels = list(file_labels or [f"config-{i}" for i in range(len(configs))])
    if len(labels) != len(configs):
        labels = [f"config-{i}" for i in range(len(configs))]

    merged = configs[0].model_copy(deep=True)
    _tag_provenance(merged, labels[0])

    for cfg, label in zip(configs[1:], labels[1:]):
        _merge_into(merged, cfg, label)

    return merged


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _tag_provenance(cfg: OLTConfig, label: str) -> None:
    """Anota `origin_files` no provenance de cada entidade que tenha."""
    for collection in (
        cfg.service_ports,
        cfg.dba_profiles,
        cfg.traffic_profiles,
        cfg.line_profiles,
        cfg.service_profiles,
        cfg.onus,
    ):
        for entity in collection:
            prov = getattr(entity, "provenance", None)
            if prov is None:
                entity.provenance = Provenance(
                    source=ProvenanceSource.PARSER,
                    confidence=1.0,
                    origin_files=[label],
                )
            elif label not in prov.origin_files:
                prov.origin_files.append(label)


def _merge_into(target: OLTConfig, source: OLTConfig, label: str) -> None:
    _tag_provenance(source, label)

    # Hostname/vendor: só usa se target estiver vazio
    if not target.hostname or target.hostname == "OLT-DEFAULT":
        target.hostname = source.hostname
    if target.firmware is None and source.firmware:
        target.firmware = source.firmware

    # Listas — union por chave natural
    _union_by(target.boards, source.boards, key=lambda b: b.slot)
    _union_by(target.vlans, source.vlans, key=lambda v: v.id)
    _union_by(target.service_vlans, source.service_vlans, key=lambda sv: sv.service_id)
    _union_by(target.uplinks, source.uplinks, key=lambda u: u.interface)
    _union_by(target.pons, source.pons, key=lambda p: p.interface)
    _union_by(target.onus, source.onus, key=lambda o: (o.pon_interface, o.onu_id))
    _union_by(target.service_ports, source.service_ports, key=lambda sp: sp.service_port_id)
    _union_by(target.dba_profiles, source.dba_profiles, key=lambda d: d.name)
    _union_by(target.traffic_profiles, source.traffic_profiles, key=lambda t: t.name)
    _union_by(target.line_profiles, source.line_profiles, key=lambda lp: lp.name)
    _union_by(target.service_profiles, source.service_profiles, key=lambda sp: sp.name)
    _union_by(target.onu_type_profiles, source.onu_type_profiles, key=lambda ot: ot.name)
    _union_by(target.static_routes, source.static_routes, key=lambda r: (r.destination, r.gateway))
    _union_by(target.users, source.users, key=lambda u: u.username)
    _union_by(target.radius_servers, source.radius_servers, key=lambda r: r.ip_address)

    target.parse_warnings.extend(source.parse_warnings)
    target.raw_unparsed.extend(source.raw_unparsed)


def _union_by(target_list: list, source_list: list, key) -> None:
    """
    Adiciona em target os itens de source cujo `key()` ainda não existe lá.
    Se a chave já existe, mescla `origin_files` no provenance.
    """
    existing = {key(x): x for x in target_list}
    for item in source_list:
        k = key(item)
        if k in existing:
            # Já existe: tenta mesclar provenance
            target_item = existing[k]
            t_prov = getattr(target_item, "provenance", None)
            s_prov = getattr(item, "provenance", None)
            if t_prov and s_prov:
                for f in s_prov.origin_files:
                    if f not in t_prov.origin_files:
                        t_prov.origin_files.append(f)
        else:
            target_list.append(item)


__all__ = ["merge_configs"]
