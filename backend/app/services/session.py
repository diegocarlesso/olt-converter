"""
SessionRuntime — runtime semântico server-side por sessão do operador.

Cada sessão contém:
  * Snapshot canonical do OLTConfig (após parse + infer + synth + promote)
  * Indexes semanticos (entity_id -> entity, type -> [entities])
  * Validation graph (issues indexadas por entity)
  * Render cache (por vendor target, invalidado ao patchar)
  * Audit log (lista append-only de patches aplicados)
  * Dirty entity set (para repintar UI seletivamente)
  * Snapshots para undo/redo (deepcopy)

Patches:
  {"op": "update", "entity_type": "EthernetPort",
   "entity_id": "pon-1/1/3:12:eth1", "field": "native_vlan", "value": 300}

API publica:
  create_session(text)          -> session_id
  get_session(session_id)       -> SessionRuntime
  drop_session(session_id)      -> None

  session.projection()          -> tree projection lightweight
  session.get_entity(t, id)     -> entity dict + provenance + bindings
  session.apply_patch(patch)    -> ApplyResult(validation_delta, render_invalid, audit_entry)
  session.undo() / redo()
  session.snapshot(label) / restore(snap_id)
  session.render(vendor)        -> str (cacheado)
  session.audit()               -> list[AuditEntry]
"""
from __future__ import annotations

import copy
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Optional

from app.models import OLTConfig, Vendor
from app.renderers import get_renderer
from app.services.conversion import parse_config
from app.services.equivalence import harmonize_for
from app.services.inference import infer_service_ports
from app.services.promotion import promote_subscriber_edge
from app.services.remapping import remap_for
from app.services.synthesis import (
    synthesize_dba_profiles,
    synthesize_traffic_profiles,
)
from app.services.validator import validate_config
from app.utils.logger import get_logger

log = get_logger(__name__)

_SESSIONS: dict[str, "SessionRuntime"] = {}
_LOCK = RLock()


# Tipos suportados para edicao via patch + como localiza-los
_ENTITY_INDEX_SPEC: dict[str, dict[str, Any]] = {
    "VLAN":          {"collection": "vlans",            "key": lambda e: f"vlan-{e.id}"},
    "PON":           {"collection": "pons",             "key": lambda e: e.interface},
    "ONU":           {"collection": "onus",             "key": lambda e: f"{e.pon_interface}:{e.onu_id}"},
    "ServicePort":   {"collection": "service_ports",    "key": lambda e: f"sp-{e.service_port_id}"},
    "Uplink":        {"collection": "uplinks",          "key": lambda e: e.interface},
    "DBAProfile":    {"collection": "dba_profiles",     "key": lambda e: f"dba-{e.profile_id}"},
    "TrafficProfile":{"collection": "traffic_profiles", "key": lambda e: f"tt-{e.profile_id}"},
    "LineProfile":   {"collection": "line_profiles",    "key": lambda e: f"lp-{e.profile_id}"},
    "ServiceProfile":{"collection": "service_profiles", "key": lambda e: f"sp-prof-{e.profile_id}"},
    "WANProfile":    {"collection": "wan_profiles",     "key": lambda e: e.name},
}


@dataclass
class AuditEntry:
    ts: float
    op: str
    entity_type: str
    entity_id: str
    field: Optional[str]
    old_value: Any
    new_value: Any
    by_source: str = "MANUAL"


@dataclass
class Snapshot:
    snap_id: str
    label: str
    ts: float
    config: OLTConfig


class SessionRuntime:
    """
    Container de runtime semântico. Thread-safe atraves de _lock.
    """

    def __init__(self, session_id: str, raw_text: str, config: OLTConfig,
                 source_vendor: Vendor, parser_warnings: list[str],
                 unparsed_lines: list[str]):
        self.session_id = session_id
        self.created_at = time.time()
        self.raw_text = raw_text
        self.config = config
        self.source_vendor = source_vendor
        self.parser_warnings = parser_warnings
        self.unparsed_lines = unparsed_lines

        self._lock = RLock()
        self._render_cache: dict[str, str] = {}  # vendor -> rendered cli
        self._audit: list[AuditEntry] = []
        self._undo_stack: list[Snapshot] = []
        self._redo_stack: list[Snapshot] = []
        self._snapshots: dict[str, Snapshot] = {}
        self._dirty_entity_ids: set[str] = set()
        self._validation_cache: Optional[dict[str, Any]] = None

    # ---------------------------------------------------------------- indexes
    def _iter_entities(self):
        for etype, spec in _ENTITY_INDEX_SPEC.items():
            for e in getattr(self.config, spec["collection"], []) or []:
                yield etype, spec["key"](e), e

    def _find_entity(self, entity_type: str, entity_id: str):
        spec = _ENTITY_INDEX_SPEC.get(entity_type)
        if not spec:
            return None
        for e in getattr(self.config, spec["collection"], []) or []:
            if spec["key"](e) == entity_id:
                return e
        return None

    # ---------------------------------------------------------------- proj
    def projection(self) -> dict:
        """
        Projection leve para o Runtime Explorer: estrutura de arvore com
        chaves e contadores, sem o payload completo das entidades.
        """
        with self._lock:
            onus_by_pon: dict[str, list[dict]] = {}
            for o in self.config.onus:
                eth_count = len(o.eth_ports)
                wan_count = len(o.wan_bindings)
                ssid_count = len(o.ssids)
                radio_count = len(o.radios)
                bg_count = len(o.bridge_groups)
                pr_count = len(o.port_routes)
                prov = getattr(o, "provenance", None)
                onus_by_pon.setdefault(o.pon_interface, []).append({
                    "type": "ONU",
                    "id": f"{o.pon_interface}:{o.onu_id}",
                    "label": f"ONU {o.onu_id} {o.serial_number or ''}",
                    "subtitle": o.description or o.onu_type or "",
                    "counts": {
                        "eth": eth_count, "wan": wan_count, "ssid": ssid_count,
                        "radio": radio_count, "bg": bg_count, "pr": pr_count,
                    },
                    "provenance": {"source": prov.source.value if prov else "parser",
                                   "confidence": prov.confidence if prov else 1.0,
                                   "needs_review": prov.needs_review if prov else False},
                })
            pons_node = []
            for p in self.config.pons:
                pons_node.append({
                    "type": "PON",
                    "id": p.interface,
                    "label": p.interface,
                    "subtitle": p.description or "",
                    "count": len(onus_by_pon.get(p.interface, [])),
                    "children": onus_by_pon.get(p.interface, []),
                })
            vlans_node = [{
                "type": "VLAN", "id": f"vlan-{v.id}",
                "label": f"VLAN {v.id}",
                "subtitle": v.name or "",
            } for v in self.config.vlans]
            sps_node = [{
                "type": "ServicePort", "id": f"sp-{sp.service_port_id}",
                "label": f"sp {sp.service_port_id}",
                "subtitle": f"{sp.pon_interface}:{sp.onu_id} vlan {sp.match_vlan}",
                "provenance": {"source": sp.provenance.source.value if sp.provenance else "parser",
                               "confidence": sp.provenance.confidence if sp.provenance else 1.0,
                               "needs_review": sp.provenance.needs_review if sp.provenance else False},
            } for sp in self.config.service_ports]
            uplinks_node = [{
                "type": "Uplink", "id": u.interface, "label": u.interface,
                "subtitle": ",".join(map(str, u.allowed_vlans[:5])) + ("..." if len(u.allowed_vlans) > 5 else ""),
            } for u in self.config.uplinks]
            profiles_node = []
            for d in self.config.dba_profiles:
                profiles_node.append({"type": "DBAProfile", "id": f"dba-{d.profile_id}",
                                      "label": d.name, "subtitle": d.type.value})
            for t in self.config.traffic_profiles:
                profiles_node.append({"type": "TrafficProfile", "id": f"tt-{t.profile_id}",
                                      "label": t.name, "subtitle": f"cir={t.cir} pir={t.pir}"})
            for lp in self.config.line_profiles:
                profiles_node.append({"type": "LineProfile", "id": f"lp-{lp.profile_id}",
                                      "label": lp.name, "subtitle": f"id {lp.profile_id}"})

            return {
                "session_id": self.session_id,
                "hostname": self.config.hostname,
                "source_vendor": self.source_vendor.value,
                "stats": self.config.stats(),
                "tree": [
                    {"key": "vlans",    "label": "VLANs",         "count": len(vlans_node),    "children": vlans_node[:500]},
                    {"key": "pons",     "label": "PONs / ONUs",   "count": len(pons_node),     "children": pons_node},
                    {"key": "service_ports", "label": "Service Ports", "count": len(sps_node), "children": sps_node[:500]},
                    {"key": "uplinks",  "label": "Uplinks",       "count": len(uplinks_node),  "children": uplinks_node},
                    {"key": "profiles", "label": "Profiles",      "count": len(profiles_node), "children": profiles_node},
                ],
                "validation": self._cached_validation()["summary"],
                "dirty_entities": list(self._dirty_entity_ids)[:200],
                "audit_size": len(self._audit),
            }

    def get_entity(self, entity_type: str, entity_id: str) -> Optional[dict]:
        with self._lock:
            e = self._find_entity(entity_type, entity_id)
            if e is None:
                return None
            payload = e.model_dump() if hasattr(e, "model_dump") else dict(e.__dict__)
            # Reune cross-bindings para Inspector
            bindings = self._compute_bindings(entity_type, e)
            # Validation issues que mencionam este entity_id
            issues = [i for i in self._cached_validation()["issues"]
                      if entity_id in (i.get("location") or "")]
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "data": payload,
                "bindings": bindings,
                "validation_issues": issues,
                "dirty": entity_id in self._dirty_entity_ids,
            }

    def _compute_bindings(self, entity_type: str, e) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if entity_type == "VLAN":
            out["service_ports"] = [
                {"id": f"sp-{sp.service_port_id}", "label": f"sp {sp.service_port_id} @ {sp.pon_interface}:{sp.onu_id}"}
                for sp in self.config.service_ports if sp.match_vlan == e.id
            ][:100]
            out["uplinks_allowing"] = [
                {"id": u.interface, "label": u.interface}
                for u in self.config.uplinks if e.id in u.allowed_vlans
            ]
        elif entity_type == "ONU":
            out["service_ports"] = [
                {"id": f"sp-{sp.service_port_id}", "label": f"sp {sp.service_port_id} vlan {sp.match_vlan}"}
                for sp in self.config.service_ports
                if sp.pon_interface == e.pon_interface and sp.onu_id == e.onu_id
            ]
            out["wan_bindings"] = [{"id": f"wb-{w.binding_id}", "label": f"{w.mode.value if hasattr(w.mode, 'value') else w.mode} (id {w.binding_id})"} for w in e.wan_bindings]
            out["ssids"] = [{"id": f"ssid-{s.ssid_id}", "label": s.name or f"ssid {s.ssid_id}"} for s in e.ssids]
            out["bridge_groups"] = [{"id": f"bg-{bg.group_id}", "label": bg.name or f"bg {bg.group_id}"} for bg in e.bridge_groups]
            out["port_routes"] = [{"id": f"pr-{pr.src_port_id}-{pr.dst_port_id}", "label": f"eth {pr.src_port_id}"} for pr in e.port_routes]
        return out

    # ---------------------------------------------------------------- patch
    def apply_patch(self, patch: dict) -> dict:
        """
        Aplica patch. Atualmente suportado: op=update em entity_type/entity_id/field.
        Retorna delta: {ok, validation_delta, render_invalid (vendors), audit_entry, impacted_entity_ids}.
        """
        with self._lock:
            op = patch.get("op", "update")
            etype = patch.get("entity_type")
            eid = patch.get("entity_id")
            fld = patch.get("field")
            new_val = patch.get("value")
            if op != "update":
                return {"ok": False, "error": f"unsupported op: {op}"}
            e = self._find_entity(etype, eid)
            if e is None:
                return {"ok": False, "error": f"entity not found: {etype}/{eid}"}
            if not hasattr(e, fld):
                return {"ok": False, "error": f"unknown field {fld} on {etype}"}

            # Snapshot para undo
            self._push_undo(label=f"before {etype}.{fld} = {new_val}")

            old_val = getattr(e, fld)
            try:
                setattr(e, fld, new_val)  # Pydantic v2 valida_assignment
            except Exception as exc:
                self._pop_undo()  # revert snapshot stack
                return {"ok": False, "error": f"validation failed: {exc!r}"}

            # Atualiza provenance da entidade para MANUAL
            try:
                from app.models import Provenance
                from app.models.provenance import ProvenanceSource
                if hasattr(e, "provenance"):
                    e.provenance = Provenance(
                        source=ProvenanceSource.MANUAL, confidence=1.0,
                        reason=f"Editado via UI: {fld} = {new_val}",
                        needs_review=False,
                    )
            except Exception:
                pass

            self._dirty_entity_ids.add(eid)
            self._validation_cache = None
            self._render_cache.clear()
            self._redo_stack.clear()

            audit = AuditEntry(
                ts=time.time(), op=op, entity_type=etype, entity_id=eid,
                field=fld, old_value=str(old_val)[:200], new_value=str(new_val)[:200],
            )
            self._audit.append(audit)
            log.info("session_patch_applied", session_id=self.session_id,
                     entity_type=etype, entity_id=eid, field=fld)

            new_val_summary = self._cached_validation()["summary"]
            return {
                "ok": True,
                "audit_entry": audit.__dict__,
                "validation_summary": new_val_summary,
                "render_invalid": list(self._render_cache.keys()) or "all",
                "impacted_entity_ids": [eid],
            }

    # ---------------------------------------------------------------- undo/redo
    def _push_undo(self, label: str) -> None:
        snap = Snapshot(snap_id=uuid.uuid4().hex[:8], label=label,
                        ts=time.time(), config=copy.deepcopy(self.config))
        self._undo_stack.append(snap)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def _pop_undo(self) -> None:
        if self._undo_stack:
            self._undo_stack.pop()

    def undo(self) -> dict:
        with self._lock:
            if not self._undo_stack:
                return {"ok": False, "error": "nothing to undo"}
            redo_snap = Snapshot(snap_id=uuid.uuid4().hex[:8], label="redo",
                                 ts=time.time(), config=copy.deepcopy(self.config))
            self._redo_stack.append(redo_snap)
            snap = self._undo_stack.pop()
            self.config = snap.config
            self._validation_cache = None
            self._render_cache.clear()
            return {"ok": True, "restored_label": snap.label}

    def redo(self) -> dict:
        with self._lock:
            if not self._redo_stack:
                return {"ok": False, "error": "nothing to redo"}
            self._push_undo(label="pre-redo")
            snap = self._redo_stack.pop()
            self.config = snap.config
            self._validation_cache = None
            self._render_cache.clear()
            return {"ok": True}

    def snapshot(self, label: str) -> dict:
        with self._lock:
            snap = Snapshot(snap_id=uuid.uuid4().hex[:8], label=label,
                            ts=time.time(), config=copy.deepcopy(self.config))
            self._snapshots[snap.snap_id] = snap
            return {"snap_id": snap.snap_id, "label": snap.label, "ts": snap.ts}

    def list_snapshots(self) -> list[dict]:
        return [{"snap_id": s.snap_id, "label": s.label, "ts": s.ts}
                for s in self._snapshots.values()]

    def restore(self, snap_id: str) -> dict:
        with self._lock:
            snap = self._snapshots.get(snap_id)
            if not snap:
                return {"ok": False, "error": "snapshot not found"}
            self._push_undo(label=f"pre-restore-{snap_id}")
            self.config = copy.deepcopy(snap.config)
            self._validation_cache = None
            self._render_cache.clear()
            return {"ok": True}

    # ---------------------------------------------------------------- render
    def render(self, target_vendor: Vendor) -> dict:
        with self._lock:
            v = target_vendor.value if hasattr(target_vendor, "value") else str(target_vendor)
            if v in self._render_cache:
                return {"vendor": v, "rendered": self._render_cache[v], "cached": True}
            # harmonize + remap + render
            harmonized = harmonize_for(self.config, target_vendor)
            remapped, _ = remap_for(harmonized, target_vendor)
            renderer = get_renderer(target_vendor)()
            rendered = renderer.render(remapped)
            self._render_cache[v] = rendered
            return {"vendor": v, "rendered": rendered, "cached": False}

    # ---------------------------------------------------------------- validation
    def _cached_validation(self) -> dict:
        if self._validation_cache is not None:
            return self._validation_cache
        report = validate_config(self.config)
        issues = []
        for i in report.issues:
            issues.append({
                "code": i.code,
                "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                "message": i.message,
                "location": getattr(i, "location", None),
            })
        self._validation_cache = {
            "summary": report.by_severity(),
            "issues": issues,
            "top_codes": Counter(i["code"] for i in issues).most_common(10),
        }
        return self._validation_cache

    def validation(self) -> dict:
        with self._lock:
            return self._cached_validation()

    def audit(self) -> list[dict]:
        with self._lock:
            return [a.__dict__ for a in self._audit[-200:]]


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------
def create_session(raw_text: str, vendor: Optional[Vendor] = None) -> SessionRuntime:
    parsed = parse_config(raw_text, vendor)
    enriched = infer_service_ports(parsed.config)
    enriched = synthesize_dba_profiles(enriched)
    enriched = synthesize_traffic_profiles(enriched)
    enriched = promote_subscriber_edge(enriched)
    session_id = uuid.uuid4().hex[:12]
    runtime = SessionRuntime(
        session_id=session_id, raw_text=raw_text, config=enriched,
        source_vendor=parsed.config.vendor,
        parser_warnings=parsed.warnings,
        unparsed_lines=parsed.unparsed_lines,
    )
    with _LOCK:
        _SESSIONS[session_id] = runtime
    log.info("session_created", session_id=session_id,
             vendor=parsed.config.vendor.value, onus=len(enriched.onus))
    return runtime


def get_session(session_id: str) -> Optional[SessionRuntime]:
    with _LOCK:
        return _SESSIONS.get(session_id)


def drop_session(session_id: str) -> bool:
    with _LOCK:
        return _SESSIONS.pop(session_id, None) is not None


def list_sessions() -> list[dict]:
    with _LOCK:
        return [
            {
                "session_id": s.session_id, "created_at": s.created_at,
                "vendor": s.source_vendor.value, "hostname": s.config.hostname,
                "onus": len(s.config.onus),
            }
            for s in _SESSIONS.values()
        ]


__all__ = [
    "SessionRuntime", "create_session", "get_session",
    "drop_session", "list_sessions", "AuditEntry",
]
