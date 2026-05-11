"""
文件用途：根据配置构建阶段 0 的攻击注册表。
File purpose: Build the protocol skeleton runtime attack registry from governed config.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.attacks.identity_attack import IdentityAttack
from main.attacks.temporal import TemporalAttackPlaceholder


def build_attack_registry(
    attack_config: dict[str, Any],
) -> list[IdentityAttack | TemporalAttackPlaceholder]:
    """功能：构建阶段 0 攻击实例列表。

    Build the protocol skeleton runtime attack instance list.

    Args:
        attack_config: Parsed JSON attack config.

    Returns:
        A list of governed attack scaffold instances.
    """
    if not isinstance(attack_config, dict):
        raise TypeError("attack_config must be a dictionary")

    if "attack_matrix_placeholder" in attack_config:
        attack_entries = attack_config.get("attack_matrix_placeholder")
        if not isinstance(attack_entries, list) or not attack_entries:
            raise ValueError("attack_matrix_placeholder must be a non-empty list")

        attack_registry: list[IdentityAttack | TemporalAttackPlaceholder] = []
        for attack_entry in attack_entries:
            if not isinstance(attack_entry, dict):
                raise ValueError("attack entries must be dictionaries")
            attack_registry.append(
                IdentityAttack(
                    attack_name=attack_entry["attack_name_placeholder"],
                    attack_params=attack_entry["attack_params_placeholder"],
                )
            )
        return attack_registry

    attack_entries = attack_config.get("attacks")
    if not isinstance(attack_entries, list) or not attack_entries:
        raise ValueError("attacks must be a non-empty list")

    attack_registry = []
    for attack_entry in attack_entries:
        if not isinstance(attack_entry, dict):
            raise ValueError("attack entries must be dictionaries")
        attack_registry.append(
            TemporalAttackPlaceholder(
                attack_name=attack_entry["attack_name"],
                attack_params=attack_entry["attack_params"],
            )
        )
    return attack_registry