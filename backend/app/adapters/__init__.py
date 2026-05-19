"""
Adapters — Bounded Context Boundaries

Módulos adaptadores que traduzem tipos e contratos entre bounded contexts.
Cada adapter é o ÚNICO ponto de travessia entre camadas.

Invariante: um tipo de L1 nunca é importado diretamente em L2+.
Ele passa pelo adapter correspondente.

Status: Adapter L1→L2 skeleton definido. Demais conforme roadmap.
"""
from __future__ import annotations

from typing import Optional

from app.models import OLTConfig, Vendor
from app.deployment.models import (
    DeploymentTarget,
    Chassis,
    Slot,
    SlotKind,
    DeploymentBoard,
    BoardKind,
    FirmwareDescriptor,
)


def semantic_to_deployment_target(
    config: OLTConfig,
    target_id: Optional[str] = None,
) -> DeploymentTarget:
    """
    Adapter L1 → L2: constrói um DeploymentTarget especulativo
    a partir do OLTConfig semântico.

    Usado como fallback quando o operador não declarou um target real.
    Todos os campos carregam provenance=DEFAULT, needs_review=True.

    Este é o shim de backwards compatibility descrito em §6.5 do
    DEPLOYMENT_TARGET_ARCHITECTURE.md.
    """
    import uuid

    tid = target_id or f"speculative-{uuid.uuid4().hex[:8]}"

    # Derivar slots/boards do que o parser capturou
    slots = []
    boards = []
    for b in config.boards:
        slot = Slot(
            slot_id=b.slot_id,
            slot_kind=SlotKind.PON if "gp" in (b.board_type or "").lower() else SlotKind.SERVICE,
            allowed_board_types=[b.board_type] if b.board_type else [],
            board=DeploymentBoard(
                slot_id=b.slot_id,
                board_type=b.board_type or "unknown",
                board_kind=BoardKind.GPON_LINE if "gp" in (b.board_type or "").lower() else BoardKind.UPLINK,
                port_count=0,
                admin_state=b.admin_state.value if hasattr(b.admin_state, "value") else str(b.admin_state),
            ),
        )
        slots.append(slot)
        if slot.board:
            boards.append(slot.board)

    return DeploymentTarget(
        target_id=tid,
        vendor=config.vendor.value if hasattr(config.vendor, "value") else str(config.vendor),
        model=config.model or "unknown",
        firmware=FirmwareDescriptor(version_family=config.firmware or "unknown") if config.firmware else None,
        chassis=Chassis(chassis_id=0, total_slots=max(len(slots), 1)),
        slots=slots,
        boards=boards,
    )


__all__ = ["semantic_to_deployment_target"]
