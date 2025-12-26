import asyncio
import random
import os
import sqlite3
import json
from datetime import datetime

from colorama import Fore, Style, init
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from telethon import TelegramClient, errors

# ====================== Инициализация ======================
init(autoreset=True)

# Твои данные
BOT_TOKEN = "8398051425:AAEK_I4nVms_fM1z7o30OJWNBZWyOixgDyE"  # от BotFather
ADMIN_ID = 5945948586  # ←←← ТВОЙ ID от @userinfobot !!!

# Юзербот данные (из config.json или здесь)

# Путь к config.json для тем (если есть)
config_path = "config.json"
topics = {}
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        topics = config.get("topics", {})

topics = config["topics"]
API_ID = config["api_id"]
API_HASH = config["api_hash"]
PHONE = config["phone"]
delay_range = config.get("delay", [0.5, 1])

# База данных
conn = sqlite3.connect("chats.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER UNIQUE,
    name TEXT,
    topic TEXT
)
""")
conn.commit()

def log(msg: str, level: str = "INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": Fore.GREEN, "WARN": Fore.YELLOW, "ERROR": Fore.RED, "DEBUG": Fore.CYAN}
    color = colors.get(level.upper(), Fore.WHITE)
    print(f"{color}[{now}] [{level}] {msg}{Style.RESET_ALL}")

# ====================== Telethon юзербот ======================
client = TelegramClient("session", API_ID, API_HASH)

# Глобальные флаги
is_running = False
count_send = 0

MESSAGE_TEXT = """Здравствуйте!
Я делаю домашние торты на заказ.
Нежные начинки, мягкие кремы, красивый и аккуратный дизайн — всё вручную и с любовью.
Фото моих работ — ниже 👇
Если вам нужен торт на праздник или просто к чаю, напишите мне в личку 💛"""

PHOTOS_FOLDER = "photos"

# Очередь задач для юзербота (чтобы не блокировать aiogram)
task_queue = asyncio.Queue()

# ====================== Функции юзербота ======================
async def check_last_messages(chat_id: int) -> bool:
    my_id = (await client.get_me()).id
    try:
        messages = await client.get_messages(chat_id, limit=2)
        for msg in messages:
            if msg.sender_id == my_id:
                return False
        return True
    except:
        return True

async def send_to_chat(chat_info: dict):
    global count_send
    chat_id = chat_info["chat"]
    delay = random.uniform(0.8, 2.5)
    await asyncio.sleep(delay)

    try:
        entity = await client.get_entity(chat_id)
        name = entity.title or getattr(entity, "first_name", str(chat_id))

        if not await check_last_messages(chat_id):
            log(f"Пропускаю {name} — последнее от меня", "DEBUG")
            return

        photos = [os.path.join(PHOTOS_FOLDER, f) for f in os.listdir(PHOTOS_FOLDER) if os.path.isfile(os.path.join(PHOTOS_FOLDER, f))]

        if photos:
            await client.send_file(entity, photos, caption=MESSAGE_TEXT)
        else:
            await client.send_message(entity, MESSAGE_TEXT)

        count_send += 1
        log(f"Отправлено в {name}", "INFO")
    except errors.FloodWaitError as e:
        log(f"FloodWait {e.seconds} сек", "WARN")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        log(f"Ошибка в {chat_id}: {e}", "ERROR")

async def collect_chats_task(reply_to: int = None):
    await client.send_message('me', "🔄 Собираю чаты...")
    count_added = 0
    dialogs = await client.get_dialogs()

    for dialog in dialogs:
        entity = dialog.entity
        if hasattr(entity, "megagroup") or (hasattr(entity, "group") and entity.group):
            chat_id = entity.id
            name = dialog.name or "Без названия"
            name_lower = name.lower()
            topic_found = "неизвестно"
            for topic, keywords in topics.items():
                if any(word.lower() in name_lower for word in keywords):
                    topic_found = topic
                    break

            cursor.execute("INSERT OR IGNORE INTO users (id, name, topic) VALUES (?, ?, ?)", (chat_id, name, topic_found))
            if cursor.rowcount > 0:
                count_added += 1

    conn.commit()
    result = f"✅ Сбор завершён. Добавлено: {count_added}. Всего: {cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]}"
    await client.send_message('me', result)
    if reply_to:
        await bot.send_message(reply_to, result)

async def start_broadcast_task(reply_to: int = None):
    global is_running, count_send
    if is_running:
        if reply_to:
            await bot.send_message(reply_to, "Рассылка уже идёт!")
        return

    is_running = True
    count_send = 0
    await client.send_message('me', "🚀 Начинаю рассылку...")

    cursor.execute("SELECT id FROM users")
    chats = cursor.fetchall()

    for (chat_id,) in chats:
        if not is_running:
            break
        await send_to_chat({"chat": chat_id})

    is_running = False
    result = f"✅ Завершено! Отправлено: {count_send}"
    await client.send_message('me', result)
    if reply_to:
        await bot.send_message(reply_to, result)

# Фоновый воркер юзербота
async def userbot_worker():
    await client.start(phone=PHONE)
    log("Юзербот подключён и работает в фоне", "INFO")
    while True:
        task = await task_queue.get()
        await task()
        task_queue.task_done()

# ====================== Aiogram бот ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Собрать чаты")
    builder.button(text="🚀 Запустить рассылку")
    builder.button(text="⛔ Стоп рассылка")
    builder.button(text="📊 Статистика чатов")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Доступ запрещён")
        return
    await message.answer("👋 Админ-панель юзербота готова!", reply_markup=get_admin_keyboard())

@dp.message(lambda m: m.text == "🔄 Собрать чаты")
async def collect(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Запускаю сбор чатов...")
    await task_queue.put(lambda: collect_chats_task(reply_to=message.from_user.id))

@dp.message(lambda m: m.text == "🚀 Запустить рассылку")
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Запускаю рассылку...")
    await task_queue.put(lambda: start_broadcast_task(reply_to=message.from_user.id))

@dp.message(lambda m: m.text == "⛔ Стоп рассылка")
async def stop_broadcast(message: types.Message):
    global is_running
    if message.from_user.id != ADMIN_ID:
        return
    if is_running:
        is_running = False
        await message.answer("Рассылка остановлена")
    else:
        await message.answer("Рассылка не запущена")

@dp.message(lambda m: m.text == "📊 Статистика чатов")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await message.answer(f"В базе: {count} чатов")

# ====================== Запуск ======================
async def main():
    log("Запуск связки бот + юзербот", "INFO")
    asyncio.create_task(userbot_worker())
    await asyncio.sleep(8)  # ждём подключения юзербота
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())