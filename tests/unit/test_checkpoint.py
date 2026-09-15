"""Checkpointing de la medición.

Una calibración de salamandra-2b corrió 16 horas, se degradó por paginación y se
mató a propósito. Las 16 horas se perdieron enteras porque `measure_cases` solo
escribía al terminar. Era el mismo error que ya se había corregido en el
manifiesto del corpus —escribir solo al final— y no se aplicó por analogía.
Estos tests existen para que no haya una tercera vez.
"""

from __future__ import annotations

import json

import pytest

from nonio.calibration.corpus import CorpusCase
from nonio.evaluation.calibrate import measure_cases
from nonio.schema.enums import CorpusCategory


class _PairFalso:
    """Par de modelos simulado: mide sin cargar nada."""

    class _Tok:
        def __len__(self):
            return 1000

    tokenizer = _Tok()


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    raiz = tmp_path / "public" / "humano_pre2022"
    raiz.mkdir(parents=True)
    casos = []
    for i in range(12):
        f = raiz / f"c{i}.txt"
        f.write_text("palabra " * 300, encoding="utf-8")
        casos.append(
            CorpusCase(
                id=f"c{i}",
                category=CorpusCategory.HUMANO_PRE2022,
                text_path=f"humano_pre2022/c{i}.txt",
                provenance="test",
                license="Apache-2.0",
                redistributable=True,
            )
        )

    llamadas = {"n": 0}

    def _medir_falso(texto, pair):
        llamadas["n"] += 1

        class M:
            def aggregate(self, a, b):
                return {"binoculars": 0.5, "fast_detect_gpt": 0.5}

        return M()

    monkeypatch.setattr("nonio.evaluation.calibrate.measure", _medir_falso)
    return tmp_path / "public", casos, llamadas


def test_el_checkpoint_se_escribe_durante_la_medicion(corpus, tmp_path):
    root, casos, _ = corpus
    ck = tmp_path / "ck.json"
    measure_cases(casos, root, _PairFalso(), checkpoint=ck, checkpoint_every=5, progress=False)
    assert ck.exists()
    assert len(json.loads(ck.read_text())) == 12


def test_reanuda_sin_remedir(corpus, tmp_path):
    """Lo ya medido no se vuelve a medir: es el punto entero del checkpoint."""
    root, casos, llamadas = corpus
    ck = tmp_path / "ck.json"

    measure_cases(casos, root, _PairFalso(), checkpoint=ck, checkpoint_every=5, progress=False)
    tras_primera = llamadas["n"]
    assert tras_primera == 12

    segunda = measure_cases(
        casos, root, _PairFalso(), checkpoint=ck, checkpoint_every=5, progress=False
    )
    assert llamadas["n"] == tras_primera, "no debe volver a medir nada"
    assert len(segunda) == 12


def test_la_reanudacion_conserva_los_valores(corpus, tmp_path):
    root, casos, _ = corpus
    ck = tmp_path / "ck.json"
    a = measure_cases(casos, root, _PairFalso(), checkpoint=ck, progress=False)
    b = measure_cases(casos, root, _PairFalso(), checkpoint=ck, progress=False)
    por_id = {m.case_id: m for m in b}
    for m in a:
        assert por_id[m.case_id].signals == m.signals
        assert por_id[m.case_id].word_count == m.word_count


def test_una_medicion_parcial_se_conserva(corpus, tmp_path):
    """Simula la muerte a mitad: el checkpoint retiene lo hecho."""
    root, casos, _ = corpus
    ck = tmp_path / "ck.json"
    parciales = [
        {
            "case_id": "c0",
            "category": "humano_pre2022",
            "word_count": 300,
            "signals": {"binoculars": 0.1, "fast_detect_gpt": 0.2},
        }
    ]
    ck.write_text(json.dumps(parciales), encoding="utf-8")

    out = measure_cases(casos, root, _PairFalso(), checkpoint=ck, progress=False)
    recuperado = next(m for m in out if m.case_id == "c0")
    assert recuperado.signals == {"binoculars": 0.1, "fast_detect_gpt": 0.2}
    assert len(out) == 12


def test_la_escritura_es_atomica(corpus, tmp_path):
    """Fichero temporal y replace: un corte a mitad no corrompe el checkpoint."""
    root, casos, _ = corpus
    ck = tmp_path / "ck.json"
    measure_cases(casos, root, _PairFalso(), checkpoint=ck, checkpoint_every=3, progress=False)
    assert not list(tmp_path.glob("*.tmp")), "no debe quedar ningún temporal"
    json.loads(ck.read_text())  # parsea: no quedó a medias


def test_sin_checkpoint_funciona_igual(corpus, tmp_path):
    root, casos, _ = corpus
    out = measure_cases(casos, root, _PairFalso(), progress=False)
    assert len(out) == 12
