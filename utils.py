import create_pool
from typing import Iterable
import msgspec


decoder = msgspec.json.Decoder()
encoder = msgspec.json.Encoder()


async def events_enabled(peer_id):
    pool = create_pool.pool
    async with pool.acquire() as conn:
        res = await conn.fetchrow(
            "SELECT enabled FROM users WHERE peer_id = $1",
            peer_id
        )
    if res is not None:
        if res['enabled']:
            return True
        else:
            return False


async def find_all_fields(peer_id) -> dict:
    pool = create_pool.pool
    async with pool.acquire() as conn:
        res = await conn.fetchrow(
            "SELECT fields FROM users WHERE peer_id=$1", peer_id
        )
        fields = res['fields']
    if fields is not None:
        return decoder.decode(res['fields'].encode("utf-8"))
    return {}


async def add_field(place: Iterable, name, peer_id) -> dict:
    pool = create_pool.pool
    async with pool.acquire() as conn:
        res = await conn.fetchrow(
            "SELECT fields FROM users WHERE peer_id=$1", peer_id
        )
        fields = decoder.decode(res['fields'].encode("utf-8"))

        if name in fields:
            return "Это имя занято, попробуйте другое"

        fields[name] = place
        fields = encoder.encode(fields).decode("utf-8")
        await conn.execute(
            "UPDATE users SET fields=$1 WHERE peer_id=$2",
            fields, peer_id
        )


async def drop_field(name, peer_id):
    pool = create_pool.pool
    async with pool.acquire() as conn:
        res = await conn.fetchrow(
            "SELECT fields FROM users WHERE peer_id=$1", peer_id
        )
        fields: dict = decoder.decode(res['fields'].encode("utf-8"))

        if name in fields:
            fields.pop(name)
        else:
            return "Такой территории не существует!"

        fields = encoder.encode(fields).decode("utf-8")
        await conn.execute(
            "UPDATE users SET fields=$1 WHERE peer_id=$2",
            fields, peer_id
        )


async def pixel_in_field(new_pixels, peer_id):
    fields = await find_all_fields(peer_id)
    if len(fields) == 0:
        return False

    is_in_field = False
    for pixel in new_pixels:
        for field in fields.items():
            place = field[1]
            same_x = pixel['x'] > place[0] and pixel['x'] < place[2]
            same_y = pixel['y'] > place[1] and pixel['y'] < place[3]
            if same_x and same_y:
                is_in_field = field[0]
                break

    return is_in_field
