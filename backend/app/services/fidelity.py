from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FidelityScore:
    semantic_fidelity_percent: int
    unsupported_features: int
    lossy_features: int
    warnings: int


class FidelityScoreCalculator:
    @staticmethod
    def calculate(unsupported: int, lossy: int, warnings: int, total_features: int = 100) -> FidelityScore:
        penalty = unsupported * 5 + lossy * 3 + warnings
        score = max(0, total_features - penalty)
        return FidelityScore(score, unsupported, lossy, warnings)
