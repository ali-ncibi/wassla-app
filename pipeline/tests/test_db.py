from app import db as db_mod


def test_vector_literal() -> None:
    assert db_mod.vector_literal([0.1, 1, -2.5]) == "[0.1,1.0,-2.5]"
    assert db_mod.vector_literal([]) == "[]"


async def test_create_pool_uses_settings_and_bounds(monkeypatch) -> None:
    captured = {}

    async def fake_create_pool(dsn, **kwargs):
        captured["dsn"] = dsn
        captured.update(kwargs)
        return "pool-sentinel"

    monkeypatch.setattr(db_mod.asyncpg, "create_pool", fake_create_pool)
    from .conftest import make_settings

    pool = await db_mod.create_pool(make_settings(database_url="postgresql://u:p@h:5432/db"))
    assert pool == "pool-sentinel"
    assert captured == {"dsn": "postgresql://u:p@h:5432/db", "min_size": 2, "max_size": 12}
