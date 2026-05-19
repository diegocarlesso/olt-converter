"""
Engineering Workspace — Bounded Context (EVOLUTION LAYER)

Superfícies para o operador interagir com o sistema:
  - Visual editing (via frontend)
  - Profile studio
  - Topology mapping
  - CLI diff
  - Deployment sessions

Status: SKELETON — contratos definidos para o frontend consumir.
        A implementação é incremental conforme o roadmap Phase 6+.
"""
from __future__ import annotations


class WorkspaceStatus:
    """Status do Engineering Workspace."""

    SURFACES = {
        "semantic_model": "active",
        "runtime_explorer": "active",
        "entity_inspector": "active",
        "cli_preview": "active",
        "target_manager": "planned",
        "catalogue_studio": "planned",
        "binding_graph": "planned",
        "deployment_cockpit": "planned",
    }

    @classmethod
    def status(cls) -> dict:
        return {
            "bounded_context": "engineering_workspace",
            "surfaces": cls.SURFACES,
            "active_count": sum(1 for s in cls.SURFACES.values() if s == "active"),
            "planned_count": sum(1 for s in cls.SURFACES.values() if s == "planned"),
        }


__all__ = ["WorkspaceStatus"]
