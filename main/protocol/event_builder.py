"""
鏂囦欢鐢ㄩ€旓細鏋勫缓闃舵 0 鐨?event plan銆?
File purpose: Build the governed event plan for stage 0.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from main.attacks.identity_attack_placeholder import IdentityAttackPlaceholder
from main.attacks.temporal import TemporalAttackPlaceholder
from main.core.digest import compute_object_digest
from main.protocol.split_builder import SplitPlanEntry


@dataclass(frozen=True)
class EventPlanEntry:
    """鍔熻兘锛氬畾涔夐樁娈?0 event plan 鏉＄洰銆?

    Protocol Skeleton event plan entry.

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
    """鍔熻兘锛氭牴鎹?split plan 鍜?attack registry 鏋勫缓 event plan銆?

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
            for attack_case_id, attack_name, attack_params, attack_case_object in _expand_attack_cases(
                attack_object
            ):
                if (
                    split_plan_entry.sample_role in {"clean_negative", "watermarked_positive"}
                    and attack_name != "no_attack"
                ):
                    continue
                if (
                    split_plan_entry.sample_role in {"attacked_negative", "attacked_positive"}
                    and attack_name == "no_attack"
                ):
                    continue
                event_plan.append(
                    EventPlanEntry(
                        event_id=f"{split_plan_entry.sample_id}:{attack_case_id}",
                        sample_id=split_plan_entry.sample_id,
                        split=split_plan_entry.split,
                        sample_role=split_plan_entry.sample_role,
                        attack_name=attack_name,
                        attack_params=attack_params,
                        attack_object=attack_case_object,
                    )
                )
    return event_plan


def _expand_attack_cases(
    attack_object: IdentityAttackPlaceholder | TemporalAttackPlaceholder,
) -> list[
    tuple[
        str,
        str,
        dict[str, Any],
        IdentityAttackPlaceholder | TemporalAttackPlaceholder,
    ]
]:
    if (
        isinstance(attack_object, TemporalAttackPlaceholder)
        and attack_object.attack_name == "local_clip"
        and isinstance(attack_object.attack_params.get("clip_lengths"), list)
    ):
        expanded_cases = []
        for clip_length in attack_object.attack_params["clip_lengths"]:
            fixed_attack_params = {"clip_length": int(clip_length)}
            expanded_cases.append(
                (
                    f"local_clip_len_{int(clip_length):02d}",
                    "local_clip",
                    fixed_attack_params,
                    TemporalAttackPlaceholder("local_clip", fixed_attack_params),
                )
            )
        return expanded_cases

    attack_params = dict(attack_object.attack_params)
    attack_case_suffix = compute_object_digest(attack_params)[:8] if attack_params else "default"
    return [
        (
            f"{attack_object.attack_name}:{attack_case_suffix}",
            attack_object.attack_name,
            attack_params,
            attack_object,
        )
    ]