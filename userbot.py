# userbot.py

import asyncio
import random
import os
import sqlite3
import json
from datetime import datetime

from colorama import Fore, Style, init
from telethon import TelegramClient, errors
from flask import Flask, request, jsonify

init(autoreset=True)

# ====================== Конфиг ======================
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
phone = config["phone"]
topics = config.get("topics", {})

# ====================== База ======================
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

def log(msg, level="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    color = {"INFO": Fore.GREEN, "WARN": Fore.YELLOW, "ERROR": Fore.RED}.get(level, Fore.WHITE)
    print(f"{color}[{now}] [{level}] {msg}{Style.RESET_ALL}")

# ====================== Telethon ======================
client = TelegramClient("session", api_id, api_hash)

is_running = False
count_send = 0

MESSAGE_TEXT = """Здравствуйте!
Я делаю домашние торты на заказ.
Нежные начинки, мягкие кремы, красивый и аккуратный дизайн — всё вручную и с любовью.
Фото моих работ — ниже 👇
Если вам нужен торт на праздник или просто к чаю, напишите мне в личку 💛"""

PHOTOS_FOLDER = "photos"

# ====================== Логика рассылки и сбора ======================
async def check_last_messages(chat_id):
    my_id = (await client.get_me()).id
    try:
        msgs = await client.get_messages(chat_id, limit=2)
        return not any(msg.sender_id == my_id for msg in msgs if msg.sender_id)
    except:
        return True

async def send_to_chat(chat_id):
    global count_send
    await asyncio.sleep(random.uniform(0.8, 2.5))
    try:
        entity = await client.get_entity(chat_id)
        name = entity.title or getattr(entity, "first_name", str(chat_id))

        if not await check_last_messages(chat_id):
            log(f"Пропуск {name} — последнее от меня", "DEBUG")
            return

        photos = [os.path.join(PHOTOS_FOLDER, f) for f in os.listdir(PHOTOS_FOLDER) if os.path.isfile(os.path.join(PHOTOS_FOLDER, f))]
        if photos:
            await client.send_file(entity, photos, caption=MESSAGE_TEXT)
        else:
            await client.send_message(entity, MESSAGE_TEXT)

        count_send += 1
        log(f"Отправлено: {name}", "INFO")
    except errors.FloodWaitError as e:
        log(f"FloodWait {e.seconds}s", "WARN")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        log(f"Ошибка {chat_id}: {e}", "ERROR")

async def collect_chats():
    count = 0
    dialogs = await client.get_dialogs()
    for d in dialogs:
        e = d.entity
        if hasattr(e, "megagroup") or (hasattr(e, "group") and e.group):
            chat_id = e.id
            name = d.name or "Без названия"
            name_lower = name.lower()
            topic = "неизвестно"
            for t, kw in topics.items():
                if any(word in name_lower for word in kw):
                    topic = t
                    break
            cursor.execute("INSERT OR IGNORE INTO users (id, name, topic) VALUES (?, ?, ?)", (chat_id, name, topic))
            if cursor.rowcount:
                count += 1
    conn.commit()
    return count

async def start_broadcast():
    global is_running, count_send
    if is_running:
        return {"status": "error", "message": "Уже запущена"}
    is_running = True
    count_send = 0
    await client.send_message('me', "🚀 Рассылка запущена через Flask")

    cursor.execute("SELECT id FROM users")
    for (chat_id,) in cursor.fetchall():
        if not is_running:
            break
        await send_to_chat(chat_id)

    is_running = False
    return {"status": "success", "sent": count_send}

# ====================== Flask API ======================
# ====================== Flask API ======================
app = Flask(__name__)

SECRET_TOKEN = "superbot2025"  # ← твой токен

@app.route('/collect_chats', methods=['POST'])
def api_collect():
    token = request.get_json().get("token") if request.is_json else request.args.get("token")
    # if token != SECRET_TOKEN:
    #     log("Неверный токен!", "ERROR")
    #     return jsonify({"error": "Неверный токен"}), 401

    log("Сбор чатов по запросу от бота", "INFO")
    added = asyncio.run(collect_chats())
    return jsonify({"status": "success", "added": added})

@app.route('/start_broadcast', methods=['POST'])
def api_broadcast():
    token = request.get_json().get("token") if request.is_json else request.args.get("token")
    # if token != SECRET_TOKEN:
    #     return jsonify({"error": "Неверный токен"}), 401

    log("Запуск рассылки по API", "INFO")
    result = asyncio.run(start_broadcast())
    return jsonify(result)

@app.route('/stop_broadcast', methods=['POST'])
def api_stop():
    token = request.get_json().get("token") if request.is_json else request.args.get("token")
    # if token != SECRET_TOKEN:
    #     return jsonify({"error": "Неверный токен"}), 401

    global is_running
    is_running = False
    log("Рассылка остановлена по API", "WARN")
    return jsonify({"status": "success", "message": "Рассылка остановлена"})

@app.route('/status', methods=['POST', 'GET'])
def api_status():
    token = request.get_json().get("token") if request.is_json else request.args.get("token")
    # if token != SECRET_TOKEN:
    #     return jsonify({"error": "Неверный токен"}), 401

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return jsonify({
        "running": is_running,
        "total_chats": total,
        "sent_this_time": count_send
    })

# ====================== Запуск ======================
async def main():
    await client.start(phone)
    log("Юзербот запущен", "INFO")
    log("Flask API доступен на http://127.0.0.1:5000", "INFO")
    app.run(port=5000, threaded=True)

if __name__ == "__main__":
    client.loop.run_until_complete(main())