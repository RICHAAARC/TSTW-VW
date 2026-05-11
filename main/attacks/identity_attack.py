"""
文件用途：提供 identity no-op attack 的基础实现。
File purpose: Provide the identity no-op attack implementation.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.schema import LatentSample


class IdentityAttack:
    """功能：返回不修改样本的 identity attack。
    Identity attack implementation that leaves samples unchanged.

    Args:
        attack_name: Stable attack name.
        attack_params: Attack parameter payload.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if not isinstance(attack_name, str) or not attack_name:
            raise ValueError("attack_name must be a non-empty string")
        if not isinstance(attack_params, dict):
            raise TypeError("attack_params must be a dictionary")
        self.attack_name = attack_name
        self.attack_params = attack_params

    def apply(self, sample: LatentSample) -> LatentSample:
        """功能：返回原样本，表示不施加攻击。
        Return the input sample unchanged.

        Args:
            sample: Input latent sample.

        Returns:
            The unchanged latent sample.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        return sample


IdentityAttackPlaceholder = IdentityAttack