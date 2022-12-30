import asyncpg
from loguru import logger


async def init():
    global pool
    logger.info("Creating pool for database")
    pool = await asyncpg.create_pool(
        user="postgres",
        database="cringe_db"
    )
