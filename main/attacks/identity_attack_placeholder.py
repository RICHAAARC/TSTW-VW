"""
鏂囦欢鐢ㄩ€旓細鎻愪緵闃舵 0 鐨?identity attack placeholder銆?File purpose: Provide the protocol skeleton runtime identity attack placeholder.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.schema import LatentSample


class IdentityAttackPlaceholder:
    """鍔熻兘锛氳繑鍥炰笉淇敼鏍锋湰鐨?identity attack銆?
    Identity attack placeholder that leaves samples unchanged.

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
        """鍔熻兘锛氳繑鍥炲師鏍锋湰锛岃〃绀轰笉鏂藉姞鏀诲嚮銆?
        Return the input sample unchanged.

        Args:
            sample: Input latent sample.

        Returns:
            The unchanged latent sample.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        return sample