from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

import json

config_path = os.path.join(os.path.dirname(__file__), "config.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

topics = config["topics"]
api_id = config["api_id"]
api_hash = config["api_hash"]
phone = config["phone"]
delay_range = config.get("delay", [0.5, 1])
# Настройки для подключения к Telegram API через библиотеку telethon

client = TelegramClient('session_name', api_id, api_hash)

# Настройки для подключения к Telegram API через библиотеку aiogram
bot_token = '8398051425:AAEK_I4nVms_fM1z7o30OJWNBZWyOixgDyE'
bot = Bot(token=bot_token)
dp = Dispatcher(bot)

# Функция, которая будет получать сообщения через MTProto и отправлять их в aiogram
@client.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    chat_id = message.chat_id
    text = message.text
    # Отправляем сообщение в aiogram
    await bot.send_message(chat_id, text)

# Запускаем клиент telethon и бота aiogram
async def main():
    await client.start()
    await bot.send_message(chat_id, 'Bot started')
    await dp.start_polling()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())