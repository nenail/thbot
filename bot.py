# bot.py

import asyncio
import json  # ←←←←← Добавил импорт!
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ====================== Конфиг ======================
BOT_TOKEN = "8398051425:AAEK_I4nVms_fM1z7o30OJWNBZWyOixgDyE"
ADMIN_ID = 8172845069  # ←←←←← ТВОЙ TELEGRAM ID от @userinfobot !!!

API_URL = "http://127.0.0.1:5000"  # Локально — не меняй
SECRET_TOKEN = "user114"  # Тот же, что в userbot.py

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====================== Клавиатура ======================
def get_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔄 Собрать чаты")
    kb.button(text="🚀 Запустить рассылку")
    kb.button(text="⛔ Остановить рассылку")
    kb.button(text="📊 Статус")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# ====================== Функция запроса к Flask ======================


# ====================== Хэндлеры ======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещён.")
        return
    await message.answer(
        "👋 <b>Панель управления юзерботом</b>\n\n"
        "Используй кнопки ниже для управления рассылкой и сбором чатов.",
        reply_markup=get_keyboard(),
        parse_mode="HTML"
    )

@dp.message(lambda m: m.text == "🔄 Собрать чаты")
async def collect_chats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Запускаю сбор чатов в юзерботе...")
    result = await send_request("/collect_chats")

    if result.get("status") == "success":
        text = f"✅ Сбор завершён!\nДобавлено новых чатов: {result.get('added', 0)}"
    else:
        text = f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}"

    await message.answer(text)

@dp.message(lambda m: m.text == "🚀 Запустить рассылку")
async def start_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🚀 Отправляю команду на запуск рассылки...")
    result = await send_request("/start_broadcast")

    if result.get("status") == "success":
        text = "✅ Рассылка успешно запущена!\nЮзербот начал отправку."
    elif result.get("status") == "error" and "Уже запущена" in result.get("message", ""):
        text = "⚠️ Рассылка уже идёт!"
    else:
        text = f"❌ Ошибка запуска: {result.get('message', 'Неизвестно')}"

    await message.answer(text)

@dp.message(lambda m: m.text == "⛔ Остановить рассылку")
async def stop_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("⛔ Отправляю команду остановки...")
    result = await send_request("/stop_broadcast")

    text = result.get("message", "Команда отправлена.")
    await message.answer(f"⛔ {text}")

@dp.message(lambda m: m.text == "📊 Статус")
async def status(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📊 Запрашиваю статус у юзербота...")
    result = await send_request("/status")

    if result.get("status") == "error":
        await message.answer(f"❌ Ошибка: {result.get('message')}")
        return

    running = "✅ Идёт" if result.get("running") else "⛔ Не запущена"
    total = result.get("total_chats", 0)
    sent = result.get("sent_this_time", 0)

    text = (
        f"<b>📊 Статус юзербота</b>\n\n"
        f"Рассылка: {running}\n"
        f"Отправлено в этой сессии: {sent}\n"
        f"Всего чатов в базе: {total}"
    )
    await message.answer(text, parse_mode="HTML")

# ====================== Запуск ======================
async def main():
    print("🤖 Aiogram-бот (панель управления) запущен.")
    print("Убедись, что юзербот с Flask запущен (python userbot.py)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())