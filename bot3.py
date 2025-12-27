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
    id INTEGER UNIQUE,
    name TEXT,
    topic TEXT
)
""")
conn.commit()

conn2 = sqlite3.connect("users.db", check_same_thread=False)  # Важно для aiogram!
cursor2 = conn2.cursor()
cursor2.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER UNIQUE,
    name TEXT,
    sends INTEGER DEFAULT 0,
    adminkaccess INTEGER DEFAULT 0,
    accesslevel INTEGER DEFAULT 0,
    MessageText TEXT DEFAULT ''
)
""")
conn2.commit()

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

async def send_to_chat(chat_info, sender_id):
    global count_send
    # случайная задержка
    dmin, dmax = chat_info["delay"]
    delay = random.uniform(dmin, dmax)
    entity = await client.get_entity(chat_info["chat"])
    cursor2.execute("SELECT MessageText FROM users WHERE id = ?", (sender_id,))
    # MESSAGE_TEXT = cursor2.fetchone()
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


# 2214571044 1389592608  1445645481  1609700474 -1002867352447
MESSAGE_TEXT = """Здравствуйте!
Я делаю домашние торты на заказ.
Нежные начинки, мягкие кремы, красивый и аккуратный дизайн — всё вручную и с любовью.

Фото моих работ — ниже 👇
Если вам нужен торт на праздник или просто к чаю, напишите мне в личку 💛"""
PHOTOS_FOLDER = "photos"

is_running = False

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
        if chat_id == 1637080440:
            continue
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
                "INSERT OR IGNORE INTO users (id, name, topic) VALUES (?, ?, ?)",
                (user_id, name, topic_found)
            )
            conn.commit()
            log(f"Добавлен чат: {name} ID: {user_id}, topic: {topic_found}", "DEBUG")

##############################################
###########################################333
#               AIOGRAM                   #
##############################################
###########################################333

# ====================== Проверка админа ======================
def check_admin(user_id: int) -> bool:
    cursor2.execute("SELECT accesslevel FROM users WHERE id = ?", (user_id,))
    result = cursor2.fetchone()
    if result and result[0] >= 1:  # accesslevel >= 1 — админ
        return True
    return False

# Функция, которая будет получать сообщения через MTProto и отправлять их в aiogram
def get_keyboard(is_admin: bool = False):
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔄 Собрать чаты")
    kb.button(text="🚀 Запустить рассылку")
    kb.button(text="⛔ Остановить рассылку")
    kb.button(text="📊 Статус")
    kb.adjust(2)
    if is_admin:
        return kb.as_markup(resize_keyboard=True)
    else:
        # Для обычных пользователей — можно убрать кнопки или оставить только статус
        return kb.as_markup(resize_keyboard=True)  # или None, если скрыть

# ====================== /start ======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or "Без имени"

    # Добавляем пользователя в базу, если его нет
    cursor2.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    if not cursor2.fetchone():
        cursor2.execute(
            "INSERT OR IGNORE INTO users (id, name, sends, adminkaccess, accesslevel) VALUES (?, ?, 0, 0, 0)",
            (user_id, full_name)
        )
        conn2.commit()
        log(f"Новый пользователь добавлен: {user_id} ({full_name})", "INFO")

    is_adm = check_admin(user_id)

    welcome_text = (
        "👋 <b>Привет!</b>\n\n"
        "Я помогаю в рассылке по чатам Telegram.\n"
    )

    if is_adm:
        welcome_text += "🔥 Ты — <b>админ</b>! Полный доступ к управлению."
    else:
        welcome_text += "Ты обычный пользователь. Некоторые функции доступны только админам."

    await message.answer(
        welcome_text,
        reply_markup=get_keyboard(is_adm),
        parse_mode="HTML"
    )

# ====================== Сбор чатов ======================
@dp.message(lambda m: m.text == "🔄 Собрать чаты")
async def collect_chats(message: types.Message):
    if not check_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав на эту команду.")
        return

    await message.answer("🔄 <b>Запускаю сбор чатов...</b>\nЭто может занять некоторое время.", parse_mode="HTML")
    await senduu()  # твоя функция сбора
    await message.answer("✅ <b>Сбор чатов завершён!</b>\nВсе группы добавлены в базу.", parse_mode="HTML")

# ====================== Запуск рассылки ======================
@dp.message(lambda m: m.text == "🚀 Запустить рассылку")
async def start_broadcast(message: types.Message):
    user_id = message.from_user.id
    if not check_admin(user_id):
        await message.answer("❌ Доступ запрещён. Обратитесь к нанаилу.")
        return

    await message.answer("🚀 <b>Запускаю рассылку...</b>\nЮзербот начал отправку по всем чатам.", parse_mode="HTML")
    await sendmessage()  # твоя функция рассылки

    # Увеличиваем счётчик рассылок
    cursor2.execute("UPDATE users SET sends = sends + 1 WHERE id = ?", (user_id,))
    conn2.commit()

    await message.answer("✅ <b>Рассылка заверщина!</b>\nСледите за логами в консоли.", parse_mode="HTML")

# ====================== Остановка ======================
@dp.message(lambda m: m.text == "⛔ Остановить рассылку")
async def stop_broadcast(message: types.Message):
    if not check_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав.")
        return

    global is_running
    if is_running:
        is_running = False
        await message.answer("⛔ <b>Рассылка остановлена вручную.</b>", parse_mode="HTML")
    else:
        await message.answer("ℹ️ Рассылка и так не запущена.")

# ====================== Статус ======================
@dp.message(lambda m: m.text == "📊 Статус")
async def status(message: types.Message):
    user_id = message.from_user.id

    cursor2.execute("SELECT name, sends, accesslevel FROM users WHERE id = ?", (user_id,))
    result = cursor2.fetchone()

    if not result:
        await message.answer("Вы ещё не зарегистрированы в системе.")
        return

    name, sends, level = result

    level_name = "Обычный пользователь"
    if level >= 1:
        level_name = "🔥 Администратор"

    # Количество чатов в базе
    cursor.execute("SELECT COUNT(*) FROM users")
    chats_count = cursor.fetchone()[0]

    await message.answer(
        f"<b>📊 Ваша статистика</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"🆔 <b>ID:</b> {user_id}\n"
        f"📤 <b>Запущено рассылок:</b> {sends}\n"
        f"🔑 <b>Уровень доступа:</b> {level_name} (уровень {level})\n"
        f"💬 <b>Чатов в базе:</b> {chats_count}\n"
        f"🚀 <b>Рассылка активна:</b> {'Да' if is_running else 'Нет'}",
        parse_mode="HTML"
    )

# Запускаем клиент telethon и бота aiogram
async def main():
    await client.start()
    await dp.start_polling(bot)
    print("Бот запущен.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())