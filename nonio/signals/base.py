"""Protocolo común de señal (FR-001, FR-003).

Dos familias independientes: Fast-DetectGPT mira la curvatura de la distribución
de un solo modelo; Binoculars mira el desacuerdo entre dos. Fallan por motivos
distintos, que es lo que hace útil exigirles acuerdo (FR-007).
"""

from __future__ import annotations

from typing import Protocol

import torch

__all__ = ["SignalScorer", "SignalOutput"]


class SignalOutput:
    """Valores por token de una señal, para agregarlos por bloque sin repasar."""

    __slots__ = ("name", "per_token", "expected_range")

    def __init__(self, name: str, per_token: torch.Tensor, expected_range: tuple[float, float]):
        self.name = name
        self.per_token = per_token
        self.expected_range = expected_range

    def aggregate(self, lo: int, hi: int) -> float:
        """Media de la señal sobre las posiciones [lo, hi)."""
        segment = self.per_token[lo:hi]
        if segment.numel() == 0:
            return float("nan")
        return float(segment.mean())


class SignalScorer(Protocol):
    name: str
    expected_range: tuple[float, float]

    def score(
        self, observer_logits: torch.Tensor, performer_logits: torch.Tensor, labels: torch.Tensor
    ) -> SignalOutput: ...
