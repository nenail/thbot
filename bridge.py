# bridge.py
# Этот файл импортируется и в bot.py, и в userbot.py

import asyncio
import random
from userbot import client, cursor, log  # импортируем клиент, курсор и лог из юзербота

is_running = False
count_send = 0

# ==================== ФУНКЦИЯ РАССЫЛКИ ====================
async def start_broadcast(text: str = None):
    global is_running, count_send
    if is_running:
        await client.send_message('me', "⚠️ Рассылка уже идёт!")
        return {"status": "error", "message": "Рассылка уже запущена"}

    is_running = True
    count_send = 0

    default_text = "📢 Рассылка от админа через управляющего бота!"
    broadcast_text = text or default_text

    await client.send_message('me', f"🚀 Старт рассылки\nТекст:\n{broadcast_text}")

    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()

    success_count = 0
    for (user_id,) in users:
        if not is_running:
            break
        try:
            await client.send_message(user_id, broadcast_text)
            success_count += 1
            count_send += 1
            await asyncio.sleep(random.uniform(0.8, 2.5))
        except Exception as e:
            log(f"Не удалось отправить {user_id}: {e}", "WARN")

    is_running = False
    result = f"✅ Рассылка завершена. Отправлено: {success_count}/{len(users)}"
    await client.send_message('me', result)
    return {"status": "success", "sent": success_count, "total": len(users), "message": result}

# ==================== ОСТАНОВКА РАССЫЛКИ ====================
async def stop_broadcast():
    global is_running
    if not is_running:
        return {"status": "info", "message": "Рассылка и так не запущена"}
    
    is_running = False
    await client.send_message('me', "⛔ Рассылка принудительно остановлена админом")
    return {"status": "success", "message": "Рассылка остановлена"}

# ==================== СТАТИСТИКА ====================
async def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT sends FROM users")  # если есть счётчик
    # или просто общее количество
    
    return {
        "status": "success",
        "total_users": total_users,
        "last_broadcast": count_send  # или сохраняй в БД
    }

# ==================== ОЧИСТКА БАЗЫ (пример) ====================
async def clear_database():
    cursor.execute("DELETE FROM users")
    conn.commit()  # если conn в userbot глобальный
    await client.send_message('me', "🗑️ База пользователей очищена")
    return {"status": "success", "message": "База очищена"}

# ==================== ДОБАВИТЬ В ЧЁРНЫЙ СПИСОК и т.д. ====================
# Добавляй сюда любые функции, какие захочешь