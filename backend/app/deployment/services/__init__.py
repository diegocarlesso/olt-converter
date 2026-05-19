"""
Deployment Services — Skeleton

Serviços do Deployment Orchestrator.
Cada serviço será implementado conforme o roadmap Phase 1-5.

Status: SKELETON — contratos definidos, sem implementação.
"""
from __future__ import annotations

from typing import Optional

from app.deployment.models import DeploymentTarget


class TargetStore:
    """
    Armazenamento de DeploymentTargets.
    Phase 1: in-memory + filesystem-backed.
    """

    _targets: dict[str, DeploymentTarget] = {}

    @classmethod
    def save(cls, target: DeploymentTarget) -> str:
        cls._targets[target.target_id] = target
        return target.target_id

    @classmethod
    def get(cls, target_id: str) -> Optional[DeploymentTarget]:
        return cls._targets.get(target_id)

    @classmethod
    def list_all(cls) -> list[dict]:
        return [
            {"target_id": t.target_id, "vendor": t.vendor, "model": t.model}
            for t in cls._targets.values()
        ]

    @classmethod
    def delete(cls, target_id: str) -> bool:
        return cls._targets.pop(target_id, None) is not None


class TopologyIngestion:
    """
    Ingestão de topologia a partir de show-command dumps.
    Phase 2: Huawei MA5800, depois ZTE/Fiberhome/Datacom.
    """

    @staticmethod
    def ingest(raw_text: str, vendor: str, model: str) -> dict:
        """Placeholder — será implementado no Phase 2."""
        return {
            "status": "not_implemented",
            "message": f"Ingestion for {vendor}/{model} is planned for Phase 2",
        }


class CatalogueStore:
    """
    Armazenamento do catálogo de profiles deployáveis.
    Phase 3: foundation.
    """

    @staticmethod
    def status() -> dict:
        return {
            "status": "skeleton",
            "message": "Catalogue store planned for Phase 3",
        }


class BindingResolver:
    """
    Resolver do Mapping Graph — produz PhysicalBindingPlan.
    Phase 4: resolver + IdAllocator.
    """

    @staticmethod
    def status() -> dict:
        return {
            "status": "skeleton",
            "message": "Binding resolver planned for Phase 4",
        }


class IdAllocator:
    """
    Alocação centralizada de IDs com provenance.
    Phase 4: parte do resolver.
    """

    @staticmethod
    def status() -> dict:
        return {
            "status": "skeleton",
            "message": "ID allocator planned for Phase 4",
        }


__all__ = [
    "TargetStore",
    "TopologyIngestion",
    "CatalogueStore",
    "BindingResolver",
    "IdAllocator",
]
