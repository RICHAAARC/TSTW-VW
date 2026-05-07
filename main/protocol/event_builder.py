"""
文件用途：构建阶段 0 的 event plan。
File purpose: Build the governed event plan for stage 0.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from main.attacks.identity_attack_placeholder import IdentityAttackPlaceholder
from main.attacks.temporal import TemporalAttackPlaceholder
from main.protocol.split_builder import SplitPlanEntry


@dataclass(frozen=True)
class EventPlanEntry:
    """功能：定义阶段 0 event plan 条目。

    Stage-0 event plan entry.

    Args:
        event_id: Base event identifier.
        sample_id: Stable sample identifier.
        split: Governed split name.
        sample_role: Governed sample role.
        attack_name: Governed attack name.
        attack_params: Governed attack params.
        attack_object: Materialized attack scaffold.

    Returns:
        None.
    """

    event_id: str
    sample_id: str
    split: str
    sample_role: str
    attack_name: str
    attack_params: dict[str, Any]
    attack_object: IdentityAttackPlaceholder | TemporalAttackPlaceholder


def build_event_plan(
    split_plan: list[SplitPlanEntry],
    attack_registry: list[IdentityAttackPlaceholder | TemporalAttackPlaceholder],
) -> list[EventPlanEntry]:
    """功能：根据 split plan 和 attack registry 构建 event plan。

    Build the shared event plan for stage 0.

    Args:
        split_plan: Shared split plan entries.
        attack_registry: Attack scaffold instances.

    Returns:
        A list of `EventPlanEntry` instances.
    """
    if not isinstance(split_plan, list) or not split_plan:
        raise ValueError("split_plan must be a non-empty list")
    if not isinstance(attack_registry, list) or not attack_registry:
        raise ValueError("attack_registry must be a non-empty list")

    event_plan: list[EventPlanEntry] = []
    for split_plan_entry in split_plan:
        for attack_object in attack_registry:
            event_plan.append(
                EventPlanEntry(
                    event_id=f"{split_plan_entry.sample_id}:{attack_object.attack_name}",
                    sample_id=split_plan_entry.sample_id,
                    split=split_plan_entry.split,
                    sample_role=split_plan_entry.sample_role,
                    attack_name=attack_object.attack_name,
                    attack_params=attack_object.attack_params,
                    attack_object=attack_object,
                )
            )
    return event_plan