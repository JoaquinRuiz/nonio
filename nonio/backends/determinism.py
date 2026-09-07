"""Determinismo (FR-006, R-008).

Dos promesas distintas, y se nombran distinto:

- **Determinismo (FR-006):** misma máquina, misma configuración, misma entrada →
  salida idéntica. Es lo que se consigue aquí.
- **Reproducibilidad (SC-003):** entre máquinas se declara una banda de
  tolerancia. Prometer identidad bit a bit entre CPUs distintas sería falso.
"""

from __future__ import annotations

import os
import random

__all__ = ["configure_determinism", "ROUND_DECIMALS"]

# Los valores publicados se redondean para absorber la variación de orden de
# reducción entre distintos números de hilos y bibliotecas BLAS (SC-003).
ROUND_DECIMALS = 6

_SEED = 0


def configure_determinism(seed: int = _SEED) -> None:
    """Fija semillas y desactiva rutas no deterministas."""
    import torch

    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.set_grad_enabled(False)
