"""Carga de la configuración y formato de los montos."""
import pytest

from app.config import Settings
from app.services.cobranza import formato_pesos
from app.templates_config import templates


class TestConfiguracion:
    def test_falta_una_variable_y_dice_cual(self, monkeypatch, tmp_path):
        """Capturando Exception a secas, cualquier problema salía como 'falta el
        .env' y mandaba a buscar donde no era. Ahora nombra lo que falta."""
        from app.config import get_settings
        monkeypatch.chdir(tmp_path)          # sin .env a mano
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        get_settings.cache_clear()
        with pytest.raises(SystemExit) as e:
            get_settings()
        get_settings.cache_clear()
        assert "database_url" in str(e.value) and "secret_key" in str(e.value)

    def test_un_error_ajeno_a_la_config_no_se_disfraza(self, monkeypatch):
        """Es lo que arregla acotar el except a ValidationError. Con un `except
        Exception`, un import roto o un permiso de archivo salían como «falta el
        .env» y mandaban a buscar el problema donde no estaba."""
        import app.config as config

        class Rota:
            def __init__(self, *a, **k):
                raise RuntimeError("el problema real")

        monkeypatch.setattr(config, "Settings", Rota)
        config.get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="el problema real"):
            config.get_settings()
        config.get_settings.cache_clear()

    def test_lee_las_variables_de_entorno(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite://")
        monkeypatch.setenv("SECRET_KEY", "x" * 32)
        monkeypatch.setenv("CLUB_NOMBRE", "Club de Prueba")
        assert Settings().club_nombre == "Club de Prueba"

    def test_no_usa_la_config_vieja_de_pydantic(self):
        """`class Config` está deprecado en Pydantic v2 y se remueve en la v3."""
        assert not hasattr(Settings, "Config")
        assert Settings.model_config.get("env_file") == ".env"


class TestFiltroDeMontos:
    def test_el_filtro_se_llama_monto(self):
        """Se llamaba «pesos» mientras el club cobra en bolivianos."""
        assert "monto" in templates.env.filters
        assert "pesos" not in templates.env.filters

    def test_formatea_en_bolivianos(self):
        assert templates.env.filters["monto"](25000) == "Bs 25.000"
        assert formato_pesos(25000) == "Bs 25.000"
