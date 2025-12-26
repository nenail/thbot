import asyncio
import logging
import sqlite3
from datetime import datetime

from colorama import Fore, Style, init
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from bridge import start_broadcast, stop_broadcast, get_stats, clear_database
from telethon import TelegramClient, events


# Настройки для подключения к Telegram API через библиотеку telethon
api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'
client = TelegramClient('session_name', api_id, api_hash)
# Инициализация colorama для Windows
init(autoreset=True)

# Токен бота
BOT_TOKEN = "8398051425:AAEK_I4nVms_fM1z7o30OJWNBZWyOixgDyE"

# Красивое логирование
def log(msg: str, level: str = "INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.CYAN
    }
    color = colors.get(level.upper(), Fore.WHITE)
    print(f"{color}[{now}] [{level}] {msg}{Style.RESET_ALL}")

logging.basicConfig(level=logging.INFO)

# Глобальные переменные для БД (будут инициализированы позже)
conn = None
cursor = None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ------------------- Инициализация базы данных -------------------
def init_db():
    global conn, cursor
    conn = sqlite3.connect("users.db", check_same_thread=False)  # Важно для aiogram!
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        sends INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    log("База данных инициализирована", "INFO")


# ------------------- Регистрация пользователя -------------------
def register_user(user_id: int):
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (id, sends) VALUES (?, 0)", (user_id,))
        conn.commit()
        log(f"Новый пользователь добавлен: {user_id}", "INFO")


# ------------------- Клавиатуры -------------------
def get_main_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Главное меню")
    builder.button(text="ℹ️ О боте")
    builder.button(text="⚙️ Настройки")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_main_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Поиск", callback_data="search")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="🎁 Акции", callback_data="promos")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(2)
    return builder.as_markup()


def get_back_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    return builder.as_markup()


# ------------------- Хэндлеры -------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(message.from_user.id)
    
    await message.answer(
        "Привет! 👋\nЯ бот с менюшками и статистикой рассылок.\nВыбери действие:",
        reply_markup=get_main_reply_keyboard()
    )
    await message.answer("Главное меню:", reply_markup=get_main_inline_keyboard())


# Временно закомментировал /send, пока нет функции sendmessage
# Если хочешь рассылку — скажи, добавлю правильно
@dp.message(Command("send"))
async def cmd_send(message: types.Message):
    text = message.text[len("/send"):].strip()
    result = await start_broadcast(text if text else None)
    await message.answer(result["message"])


@dp.message(lambda message: message.text == "📋 Главное меню")
async def main_menu_reply(message: types.Message):
    await message.answer("Главное меню:", reply_markup=get_main_inline_keyboard())


@dp.message(lambda message: message.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    await message.answer(
        "🤖 Это тестовый бот на aiogram 3.x\n"
        "Функции: меню, статистика, база пользователей SQLite\n"
        "В разработке: рассылка, настройки и многое другое!",
        reply_markup=get_back_inline_keyboard()
    )


@dp.message(lambda message: message.text == "⚙️ Настройки")
async def settings(message: types.Message):
    await message.answer("Настройки в разработке 🚧", reply_markup=get_back_inline_keyboard())


# ------------------- Инлайн-кнопки -------------------
@dp.callback_query(lambda c: c.data == "search")
async def callback_search(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔍 Раздел поиска.\nПока просто заглушка — скоро добавлю функционал!",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
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


@dp.callback_query(lambda c: c.data == "promos")
async def callback_promos(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎁 Акции и спецпредложения\nСкоро здесь будут крутые бонусы!",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "help")
async def callback_help(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "❓ Помощь:\n\n"
        "• Кнопки снизу — постоянное меню\n"
        "• Инлайн-кнопки — навигация по разделам\n"
        "• /start — перезапустить бота\n"
        "• Статистика — показывает твои данные",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "back_to_main")
async def callback_back(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Вернулись в главное меню:",
        reply_markup=get_main_inline_keyboard()
    )
    await callback.answer()


# ------------------- Запуск бота -------------------
async def main():
    init_db()  # Инициализируем базу только здесь!
    log("Бот успешно запущен и готов к работе!", "INFO")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())