"""Elección de la base de datos según las variables de entorno."""

from database import url_base_datos


def test_sin_variables_usa_sqlite_local(monkeypatch):
    monkeypatch.delenv("AGROCOLAB_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert url_base_datos() == "sqlite:///./agrocolab.db"


def test_database_url_de_render(monkeypatch):
    monkeypatch.delenv("AGROCOLAB_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://usuario:clave@host:5432/agrocolab")
    assert url_base_datos() == "postgresql+psycopg://usuario:clave@host:5432/agrocolab"


def test_database_url_con_opciones(monkeypatch):
    monkeypatch.delenv("AGROCOLAB_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:c@ep-algo.neon.tech/agrocolab?sslmode=require")
    assert url_base_datos() == "postgresql+psycopg://u:c@ep-algo.neon.tech/agrocolab?sslmode=require"


def test_las_pruebas_tienen_prioridad(monkeypatch):
    monkeypatch.setenv("AGROCOLAB_DB_URL", "sqlite:///temporal.db")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:c@host/produccion")
    assert url_base_datos() == "sqlite:///temporal.db"
