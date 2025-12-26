from telethon import TelegramClient, events, errors
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime
from colorama import Fore, Style, init

import asyncio
import json
import os
import sqlite3
import random

config_path = os.path.join(os.path.dirname(__file__), "config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

topics = config["topics"]
api_id = config["api_id"]
api_hash = config["api_hash"]
phone = config["phone"]
delay_range = config.get("delay", [0.5, 1])
ADMIN_ID = config["admin_id"]
# Настройки для подключения к Telegram API через библиотеку telethon

client = TelegramClient('session_name', api_id, api_hash)

# Настройки для подключения к Telegram API через библиотеку aiogram
bot_token = '8398051425:AAEK_I4nVms_fM1z7o30OJWNBZWyOixgDyE'
bot = Bot(token=bot_token)
dp = Dispatcher()
chat_id = 8172845069

conn = sqlite3.connect("chats.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER,
    name TEXT,
    topic TEXT,
    sends INTEGER DEFAULT 0
)
""")
conn.commit()

conn2 = sqlite3.connect("users.db", check_same_thread=False)  # Важно для aiogram!
cursor2 = conn2.cursor()
cursor2.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    sends INTEGER DEFAULT 0,
    adminkaccess INTEGER DEFAULT 0
)
""")
conn2.commit()
log("База данных инициализирована", "INFO")

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
is_running = False
count_send = 0
# 2214571044 1389592608  1445645481  1609700474 -1002867352447
MESSAGE_TEXT = """Здравствуйте!
Я делаю домашние торты на заказ.
Нежные начинки, мягкие кремы, красивый и аккуратный дизайн — всё вручную и с любовью.

Фото моих работ — ниже 👇
Если вам нужен торт на праздник или просто к чаю, напишите мне в личку 💛"""
PHOTOS_FOLDER = "photos"


async def sendmessage():
    global count_send
    global is_running
    if is_running:
        return

    is_running = True
    log("Начинаю рассылку...", "INFO")

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
    count_send = 0


async def senduu():
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

##############################################
###########################################333
#               AIOGRAM                   #
##############################################
###########################################333

# Функция, которая будет получать сообщения через MTProto и отправлять их в aiogram
@client.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    text = message.text
    # Отправляем сообщение в aiogram

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    entity = await client.get_entity(chat_id)
    user_id = callback.from_user.id
    cursor2.execute("SELECT sends FROM users WHERE id = ?", (user_id,))
    result = cursor2.fetchone()
    sends_count = result[2] if result else 0
    sends_count2 = sends_count + 1
    await message.answer(
        "👋 <b>Панель управления юзерботом</b>\n\n"
    )

def get_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔄 Собрать чаты")
    kb.button(text="🚀 Запустить рассылку")
    kb.button(text="⛔ Остановить рассылку")
    kb.button(text="📊 Статус")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@dp.message(lambda m: m.text == "🔄 Собрать чаты")
async def collect_chats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Запускаю сбор чатов в юзерботе...")
    await senduu()

    text = f"✅ Сбор завершён!"
    await message.answer(text)

@dp.message(lambda m: m.text == "🚀 Запустить рассылку")
async def start_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🚀 Отправляю команду на запуск рассылки...")
    await sendmessage()
    user_id = callback.from_user.id
    cursor.execute("SELECT sends FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    sends_count = result[2] if result else 0
    sends_count2 = sends_count + 1
    cursor.execute(
    "UPDATE users SET sends = ? WHERE id = ?",
    (sends_count2, user_id)
    )
    conn.commit()
   
    text = "✅ Рассылка успешно запущена!\nЮзербот начал отправку."
    await message.answer(text)

@dp.message(lambda m: m.text == "📊 Статус")
async def status(message: types.Message):
    user_id = callback.from_user.id
    register_user(user_id)
    
    cursor.execute("SELECT sends FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    sends_count = result[0] if result else 0
    
    await callback.message.edit_text(
        f"📊 Ваша статистика:\n\n"
        f"🆔 ID: {user_id}\n"
        f"📤 Количество рассылок: {sends_count}\n\n"
        f"(Это поле будет расти, когда добавим рассылку)",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()

# Запускаем клиент telethon и бота aiogram
async def main():
    await client.start()
    await dp.start_polling(bot)
    print("Бот запущен.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())