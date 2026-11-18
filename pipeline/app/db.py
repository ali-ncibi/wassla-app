import asyncpg

from .config import Settings


async def create_pool(settings: Settings) -> asyncpg.Pool:
    return await asyncpg.create_pool(settings.database_url, min_size=2, max_size=12)


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"
