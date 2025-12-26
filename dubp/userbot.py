import asyncio
import random
import os
import sqlite3
from telethon import TelegramClient, events, errors
from colorama import Fore, Style, init
from datetime import datetime

import json

config_path = os.path.join(os.path.dirname(__file__), "config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

topics = config["topics"]
api_id = config["api_id"]
api_hash = config["api_hash"]
phone = config["phone"]
delay_range = config.get("delay", [0.5, 1])


init(autoreset=True)

conn = sqlite3.connect("chats.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id UNIQUE,
    name TEXT,
    topic TEXT
)
""")
conn.commit()


def log(msg, level="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    
    colors = {
        "INFO": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.CYAN
    }
    
    color = colors.get(level.upper(), Fore.WHITE)
    
    print(f"{color}[{now}] [{level}] {msg}{Style.RESET_ALL}")


# api_id = 32209464 #21654385
# api_hash = '9d184d4c82770897061d538136177fb1' #769b741e490f957fe63afe55d6829314
# phone = '+380937932263' 

client = TelegramClient("session", api_id, api_hash)

# флаг для остановки
is_running = False

# список чатов
# targets = [
#     {"chat": 1112976876, "delay": (2, 4)},
#     {"chat": 1704840622, "delay": (2, 4)},
# ]

count_send = 0
# 2214571044 1389592608  1445645481  1609700474 -1002867352447
MESSAGE_TEXT = """Здравствуйте!
Я делаю домашние торты на заказ.
Нежные начинки, мягкие кремы, красивый и аккуратный дизайн — всё вручную и с любовью.

Фото моих работ — ниже 👇
Если вам нужен торт на праздник или просто к чаю, напишите мне в личку 💛"""
PHOTOS_FOLDER = "photos"

async def check_last_messages(chat_id):
    my_id = 8172845069
    # получаем 2 последних сообщения
    messages = await client.get_messages(chat_id, limit=2)
    
    for msg in messages:
        # msg.from_id — это объект типа PeerUser, PeerChat или PeerChannel
        # для простоты можно взять .user_id если это PeerUser
        sender_id = getattr(msg.from_id, 'user_id', None)
        
        if sender_id == my_id:
            return False
        else:
            return True

async def send_to_chat(chat_info):
    global count_send
    # случайная задержка
    dmin, dmax = chat_info["delay"]
    delay = random.uniform(dmin, dmax)
    entity = await client.get_entity(chat_info["chat"])
    try:
        # сначала получаем сущность
        
        # читаем нормальное имя
        name = None
        if hasattr(entity, "title") and entity.title:
            name = entity.title
        elif hasattr(entity, "first_name") and entity.first_name:
            name = entity.first_name
        elif hasattr(entity, "username") and entity.username:
            name = entity.username
        else:
            name = str(chat_info["chat"])

    except Exception as e:
        log(f"Не удалось получить сущность для {chat_info['chat']}: {e}", "WARN")
        return

    # теперь только выводим задержку
    await asyncio.sleep(delay)
    check = await check_last_messages(chat_info["chat"])

    if check:

        try:
            # собираем фотки
            photos = []
            for file in os.listdir(PHOTOS_FOLDER):
                path = os.path.join(PHOTOS_FOLDER, file)
                if os.path.isfile(path):
                    photos.append(path)

            if photos:
                await client.send_file(entity, photos, caption=MESSAGE_TEXT)
            else:
                await client.send_message(entity, MESSAGE_TEXT)
            count_send += 1
            log(f"Отправлено в {name}", "DEBUG")

        except errors.FloodWaitError as e:
            log(f"FloodWaitError при отправке в {name}, жду {e.seconds} сек", "WARN")
        except Exception as e:
            log(f"Ошибка при отправке в {name}: {e}", "ERROR")

    else:
        log(f"Последнее сообщение в {name} от меня, пропускаю.", "DEBUG")

@client.on(events.NewMessage(pattern="!start"))
async def sendmessage(event):
    global count_send
    global is_running
    if is_running:
        await event.reply("Рассылка уже идёт.")
        return

    is_running = True
    log("Начинаю рассылку...", "INFO")
    await event.reply("Начинаю рассылку...")

    # достаём все чаты из базы
    cursor.execute("SELECT id, name FROM users")
    chats = cursor.fetchall()  # вернёт [(id, name), ...]

    for chat_id, chat_name in chats:
        if not is_running:
            break

        # создаём структуру, как в send_to_chat
        chat_info = {
            "chat": chat_id,
            "delay": (0.5, 2)  # можно менять задержку
        }

        await send_to_chat(chat_info)

    is_running = False
    log(f"Готово. Прошёлся по {count_send} группам.", "INFO")
    await event.reply(f"Готово. Прошёлся по {count_send} группам.")
    count_send = 0

@client.on(events.NewMessage(pattern="!start"))
async def sendmessage(event):
    global count_send
    global is_running
    if is_running:
        await event.reply("Рассылка уже идёт.")
        return

    is_running = True
    log("Начинаю рассылку...", "INFO")
    await event.reply("Начинаю рассылку...")

    # достаём все чаты из базы
    cursor.execute("SELECT id, name FROM users")
    chats = cursor.fetchall()  # вернёт [(id, name), ...]

    for chat_id, chat_name in chats:
        if not is_running:
            break

        # создаём структуру, как в send_to_chat
        chat_info = {
            "chat": chat_id,
            "delay": (0.5, 2)  # можно менять задержку
        }

        await send_to_chat(chat_info)

    is_running = False
    log(f"Готово. Прошёлся по {count_send} группам.", "INFO")
    await event.reply(f"Готово. Прошёлся по {count_send} группам.")
    count_send = 0

@client.on(events.NewMessage(pattern="!stop"))
async def stop(event):
    global is_running
    is_running = False
    await event.reply("Останавливаю рассылку.")

@client.on(events.NewMessage(pattern="!chats"))
async def stop(event):
    dialogs = await client.get_dialogs()

    for d in dialogs:
        if d.is_group:
            # Приводим ID к int
            user_id = int(d.entity.id)
            name = str(d.name)
            name2 = name.lower()
            cursor.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (user_id,)  # важно, чтобы это был кортеж с запятой
            )

            # приводим имя к нижнему регистру
            name_lower = name2.lower()
            topic_found = "не известно"

            for topic, keywords in topics.items():
                if any(word.lower() in name_lower for word in keywords):
                    topic_found = topic
                    break

            # вставка в базу
            cursor.execute(
                "INSERT INTO users (id, name, topic) VALUES (?, ?, ?)",
                (user_id, name, topic_found)
            )
            conn.commit()
            log(f"Добавлен чат: {name} ID: {user_id}, topic: {topic_found}", "DEBUG")

        # супергруппы / каналы
        # if d.is_channel and not d.entity.broadcast:
        #     print("Супергруппа:", d.name, "ID:", d.entity.id)

client.start()
log("Бот запущен", "INFO")
client.run_until_disconnected()
