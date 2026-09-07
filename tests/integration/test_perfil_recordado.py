"""FR-019 — el perfil elegido se recuerda entre invocaciones."""

from __future__ import annotations

import pytest

from nonio import config
from nonio.backends.profiles import DEFAULT_PROFILE_ID, PROFILES

pytestmark = pytest.mark.integration


@pytest.fixture
def config_aislada(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def test_sin_configuracion_no_hay_perfil_recordado(config_aislada):
    assert config.get_default_profile() is None


def test_el_perfil_elegido_persiste(config_aislada):
    otro = next(p for p in PROFILES if p != DEFAULT_PROFILE_ID)
    config.set_default_profile(otro)
    assert config.get_default_profile() == otro
    assert config.config_path().exists()


def test_no_se_recuerda_un_perfil_inexistente(config_aislada):
    with pytest.raises(KeyError):
        config.set_default_profile("no-existe")
    assert config.get_default_profile() is None


def test_una_configuracion_corrupta_no_revienta(config_aislada):
    p = config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ esto no es json", encoding="utf-8")
    assert config.get_default_profile() is None
