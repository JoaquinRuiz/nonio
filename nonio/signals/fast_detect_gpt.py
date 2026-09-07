"""Curvatura de probabilidad condicional — Fast-DetectGPT (R-001).

Variante sin muestreo del DetectGPT original: sustituye las ~100 perturbaciones
por un paso analítico, lo que la hace viable en CPU y compatible con SC-006.

La curvatura por token es

    (log p(x_t) - mu_t) / sigma_t

donde mu_t y sigma_t son la media y la desviación de la log-probabilidad bajo la
propia distribución del modelo en esa posición. Ambas se obtienen en cerrado
desde los logits, sin muestrear nada.
"""

from __future__ import annotations

import torch

from nonio.signals.base import SignalOutput

__all__ = ["FastDetectGPT"]


class FastDetectGPT:
    name = "fast_detect_gpt"
    expected_range = (-2.0, 6.0)

    def score(
        self,
        observer_logits: torch.Tensor,
        performer_logits: torch.Tensor,  # noqa: ARG002 - señal de un solo modelo
        labels: torch.Tensor,
    ) -> SignalOutput:
        logits = observer_logits[:-1].float()
        targets = labels[1:]

        logprobs = torch.log_softmax(logits, dim=-1)
        probs = logprobs.exp()

        observed = logprobs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)

        # Media y varianza de la log-prob bajo la propia distribución del modelo.
        mu = (probs * logprobs).sum(dim=-1)
        second = (probs * logprobs.square()).sum(dim=-1)
        sigma = (second - mu.square()).clamp_min(1e-12).sqrt()

        curvature = (observed - mu) / sigma
        return SignalOutput(self.name, curvature, self.expected_range)
