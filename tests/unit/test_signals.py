"""Propiedades de las dos señales, comprobadas sin modelos.

No se contrastan contra cifras publicadas porque esas cifras dependen del par de
modelos concreto (R-003): un número de la literatura obtenido con Falcon-7B no
dice nada sobre Qwen2.5-0.5B. Lo que sí se puede fijar aquí son las propiedades
matemáticas que definen cada señal, con logits sintéticos de forma conocida.
"""

from __future__ import annotations

import pytest
import torch

from nonio.signals.binoculars import Binoculars
from nonio.signals.fast_detect_gpt import FastDetectGPT


def _logits(n_tokens: int, vocab: int, *, peaked: bool, seed: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    base = torch.randn(n_tokens, vocab, generator=g)
    return base * (8.0 if peaked else 0.5)


def test_fast_detect_gpt_devuelve_un_valor_por_par_de_tokens():
    logits = _logits(10, 50, peaked=False)
    labels = torch.randint(0, 50, (10,), generator=torch.Generator().manual_seed(1))
    out = FastDetectGPT().score(logits, logits, labels)
    assert out.per_token.shape == (9,)


def test_binoculars_devuelve_un_valor_por_par_de_tokens():
    obs = _logits(10, 50, peaked=False, seed=2)
    per = _logits(10, 50, peaked=False, seed=3)
    labels = torch.randint(0, 50, (10,), generator=torch.Generator().manual_seed(1))
    out = Binoculars().score(obs, per, labels)
    assert out.per_token.shape == (9,)


def test_la_curvatura_es_alta_cuando_el_token_es_el_mas_probable():
    """El núcleo de Fast-DetectGPT: texto que el modelo habría elegido puntúa alto."""
    vocab, n = 50, 12
    logits = _logits(n, vocab, peaked=True, seed=4)

    # Alineamiento causal: logits[t] predice labels[t+1]. Tomar el argmax de
    # todas las posiciones y pasarlo tal cual desplaza el objetivo una posición.
    argmax = torch.zeros(n, dtype=torch.long)
    argmax[1:] = logits[:-1].argmax(dim=-1)

    esperados = FastDetectGPT().score(logits, logits, argmax)

    g = torch.Generator().manual_seed(9)
    aleatorios = torch.randint(0, vocab, (n,), generator=g)
    inesperados = FastDetectGPT().score(logits, logits, aleatorios)

    assert esperados.per_token.mean() > inesperados.per_token.mean()


def test_binoculars_normaliza_por_dificultad_intrinseca():
    """FR-002: al dividir por la cross-perplexity, subir la dificultad de todo el
    texto no debe desplazar el ratio tanto como desplazaría a la perplejidad sola.
    """
    vocab, n = 60, 14
    labels = torch.randint(0, vocab, (n,), generator=torch.Generator().manual_seed(5))

    facil = _logits(n, vocab, peaked=True, seed=6)
    dificil = facil * 0.25  # misma forma, distribución más plana

    b = Binoculars()
    r_facil = b.score(facil, facil, labels).per_token.mean().abs()
    r_dificil = b.score(dificil, dificil, labels).per_token.mean().abs()

    ppl_facil = -torch.log_softmax(facil[:-1], -1).gather(-1, labels[1:].unsqueeze(-1)).mean().abs()
    ppl_dificil = (
        -torch.log_softmax(dificil[:-1], -1).gather(-1, labels[1:].unsqueeze(-1)).mean().abs()
    )

    deriva_ratio = (r_dificil - r_facil).abs() / r_facil.clamp_min(1e-9)
    deriva_ppl = (ppl_dificil - ppl_facil).abs() / ppl_facil.clamp_min(1e-9)
    assert deriva_ratio < deriva_ppl, "el ratio debe ser más estable que la perplejidad cruda"


def test_las_dos_senales_son_independientes():
    """FR-001: no deben ser la misma métrica con otro nombre."""
    vocab, n = 80, 40
    obs = _logits(n, vocab, peaked=True, seed=7)
    per = _logits(n, vocab, peaked=True, seed=8)
    labels = torch.randint(0, vocab, (n,), generator=torch.Generator().manual_seed(11))

    a = FastDetectGPT().score(obs, per, labels).per_token
    b = Binoculars().score(obs, per, labels).per_token
    corr = torch.corrcoef(torch.stack([a, b]))[0, 1].abs()
    assert corr < 0.95, f"señales casi colineales (r={corr:.3f}): no son independientes"


@pytest.mark.parametrize("scorer", [FastDetectGPT(), Binoculars()])
def test_ningun_valor_es_nan_ni_infinito(scorer):
    vocab, n = 40, 16
    obs = _logits(n, vocab, peaked=True, seed=12)
    per = _logits(n, vocab, peaked=False, seed=13)
    labels = torch.randint(0, vocab, (n,), generator=torch.Generator().manual_seed(14))
    out = scorer.score(obs, per, labels)
    assert torch.isfinite(out.per_token).all()
