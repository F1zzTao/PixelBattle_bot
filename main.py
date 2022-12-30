import socketio
from loguru import logger
from vkbottle.bot import Bot, Message

import create_pool
from config import TOKEN
from utils import (add_field, drop_field, events_enabled, find_all_fields,
                   pixel_in_field)

sio = socketio.AsyncClient()
bot = Bot(TOKEN)
conn = None


# Socket.io handlers
@sio.event
async def connect():
    logger.info("Connection estabilished")


@sio.on("*")
async def all_messages(event, data):
    logger.info(f'New event ({event}): {data}')

    send_to = []
    pool = create_pool.pool
    async with pool.acquire() as conn:
        res = await conn.fetch(
            "SELECT peer_id, enabled FROM users"
        )
    for chat in res:
        if chat['enabled'] == False:
            continue

        must_react = await pixel_in_field(data['pixels'], chat['peer_id'])
        if must_react is not False:
            send_to.append((chat['peer_id'], must_react))

    if len(send_to) > 0:
        pixel_info = ""
        for pixel in data['pixels']:
            pixel_info += f"x: {pixel['x']}, y: {pixel['y']}\n"

        for chat in send_to:
            await bot.api.messages.send(
                message=f"Пиксель на арте {chat[1]}:\n{pixel_info}",
                random_id=0,
                peer_id=chat[0]
            )


@sio.event
async def disconnect():
    logger.info('Disconnected from server')


# VKBottle handlers
@bot.on.message(text="!ивенты")
async def enable_events(message: Message):
    are_events_enabled = await events_enabled(message.peer_id)

    pool = create_pool.pool
    async with pool.acquire() as conn:
        if are_events_enabled is False:
            # Events enabled
            await conn.execute(
                "UPDATE users SET enabled = true"
            )
            are_events_enabled = True
        elif are_events_enabled is True:
            # Events disabled
            await conn.execute(
                "UPDATE users SET enabled = false"
            )
            are_events_enabled = False
        else:
            # Chat never enabled events
            await conn.execute(
                "INSERT INTO users (peer_id, enabled) VALUES ($1, true)",
                message.peer_id
            )
            are_events_enabled = True

    if are_events_enabled:
        return "Вы включили ивенты из пб"
    else:
        return "Вы выключили ивенты из пб"


@bot.on.message(text=(
    "!следить <x1:int> <y1:int> <x2:int> <y2:int> <name>",
))
async def search_field(
    message: Message, x1: int, y1: int, x2: int, y2: int, name: str
):
    are_events_enabled = await events_enabled(message.peer_id)
    if are_events_enabled is None:
        return "Вам надо хотя бы раз включить ивенты из пб!"

    if '.' in name:
        return "В названии не может быть точка"

    status = await add_field((x1, y1, x2, y2), name, message.peer_id)
    if status is not None:
        return status

    return "Территория успешно добавлена!"


@bot.on.message(text="!не следить <name>")
async def stop_search_field(message: Message, name: str):
    are_events_enabled = await events_enabled(message.peer_id)
    if are_events_enabled is None:
        return "Вам надо хотя бы раз включить ивенты из пб!"

    status = await drop_field(name, message.peer_id)
    if status is not None:
        return status

    return "Территория успешно удалена"


@bot.on.message(text="!территории")
async def list_all_fields(message: Message):
    are_events_enabled = await events_enabled(message.peer_id)
    if are_events_enabled is None:
        return "Вам надо хотя бы раз включить ивенты из пб!"

    fields = await find_all_fields(message.peer_id)
    if len(fields) == 0:
        return "Вы пока не следите ни за какими территориями!"

    msg = "Вот все ваши территории:\n"
    for i, field in enumerate(fields):
        cur_field = fields[field]
        field_str = (
            f"{cur_field[0]} {cur_field[1]}"
            f" {cur_field[2]} {cur_field[3]}"
        )
        msg += f"{i+1}. {field}: {field_str}\n"
    return msg


if __name__ == "__main__":
    bot.loop_wrapper.on_startup.append(create_pool.init())
    bot.loop_wrapper.add_task(
        sio.connect(
            "wss://mmosg.ru:443",
            socketio_path="mysocket",
            transports=["websocket"]
        )
    )
    bot.run_forever()
