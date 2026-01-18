import logging, io, requests, base64, aiosqlite
import os
from dotenv import load_dotenv
load_dotenv()
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
SERVER_URL = "http://127.0.0.1:8000"
DB_NAME = "bot_data.db"

logging.basicConfig(level=logging.INFO)

# --- БАЗА ДАННЫХ (Оставляем как было) ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
            (id INTEGER PRIMARY KEY, checks_count INTEGER DEFAULT 0)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS global_stats 
            (name TEXT PRIMARY KEY, value INTEGER DEFAULT 0)''')
        await db.execute("INSERT OR IGNORE INTO global_stats (name, value) VALUES ('total_checks', 0)")
        await db.commit()

async def update_user_stats(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        await db.execute("UPDATE users SET checks_count = checks_count + 1 WHERE id = ?", (user_id,))
        await db.execute("UPDATE global_stats SET value = value + 1 WHERE name = 'total_checks'")
        await db.commit()

async def get_stats(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT checks_count FROM users WHERE id = ?", (user_id,)) as cursor:
            user_row = await cursor.fetchone()
        async with db.execute("SELECT value FROM global_stats WHERE name = 'total_checks'") as cursor:
            global_row = await cursor.fetchone()
        return (user_row[0] if user_row else 0), (global_row[0] if global_row else 0)

# --- ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📝 Проверить текст"), KeyboardButton("👤 Мой профиль")],
        [KeyboardButton("📊 Глобальная стата")]
        # Кнопку "Проверить фото" можно убрать, так как пользователь просто присылает фото
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "👋 Привет! Я AI Detector.\n\n"
        "🔸 Пришли мне **ФОТО**, и я найду на нем следы ИИ.\n"
        "🔸 Пришли мне **ТЕКСТ**, и я скажу, кто его написал.",
        reply_markup=reply_markup
    )

# Обработка статистики (без изменений)
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_checks, _ = await get_stats(user_id)
    await update.message.reply_text(f"👤 **Твой профиль:**\n🆔 ID: `{user_id}`\n✅ Проверок: `{user_checks}`", parse_mode="Markdown")

async def show_global_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, total_checks = await get_stats(0)
    await update.message.reply_text(f"📊 **Всего проверок:** `{total_checks}`", parse_mode="Markdown")

# === ОБРАБОТКА ФОТО (Клиент к API) ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return
    status_msg = await update.message.reply_text("⏳ Анализирую фото через сервер...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Отправляем на сервер FastAPI
        files = {'file': ('img.jpg', io.BytesIO(photo_bytes), 'image/jpeg')}
        # Используем таймаут, чтобы бот не вис
        response = requests.post(f"{SERVER_URL}/upload", files=files, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            ai_val = data.get("ai_probability", 0)
            if ai_val <= 1.0: ai_val *= 100 # Корректировка процентов
            
            verdict = "⚠️ СКОРЕЕ ВСЕГО ИИ" if ai_val > 50 else "✅ ЭТО ЧЕЛОВЕК"
            img_b64 = data.get("image_base64")

            if img_b64:
                await update_user_stats(update.effective_user.id)
                final_img = io.BytesIO(base64.b64decode(img_b64))
                await update.message.reply_photo(
                    photo=final_img,
                    caption=f"📊 **Результат:**\nИИ: `{ai_val:.1f}%` \nВердикт: **{verdict}**",
                    parse_mode="Markdown"
                )
                await status_msg.delete()
        else:
            await status_msg.edit_text(f"❌ Сервер вернул ошибку: {response.status_code}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка соединения: {e}")

# === НОВАЯ ФУНКЦИЯ: ОБРАБОТКА ТЕКСТА (Клиент к API) ===
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Игнорируем нажатия кнопок меню (чтобы не отправлять их на проверку)
    if user_text in ["👤 Мой профиль", "📊 Глобальная стата", "📝 Проверить текст", "📸 Проверить фото"]:
        if user_text == "📝 Проверить текст":
            await update.message.reply_text("Просто пришли мне текст следующим сообщением!")
        return

    # Проверяем длину
    if len(user_text) < 10:
        await update.message.reply_text("Текст слишком короткий для анализа (минимум 10 символов).")
        return

    status_msg = await update.message.reply_text("⏳ Читаю текст...")

    try:
        # Формируем JSON для отправки на API
        payload = {"text": user_text}
        
        # Стучимся в твой FastAPI (main.py)
        response = requests.post(f"{SERVER_URL}/detect-text", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                score = data.get("ai_score", 0)
                label = data.get("label", "Неизвестно")
                
                await update_user_stats(update.effective_user.id)
                await status_msg.edit_text(
                    f"📝 **Анализ текста:**\n\n"
                    f"🏷 Вердикт: **{label}**\n"
                    f"🤖 Вероятность ИИ: `{score}%`",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text("Ошибка при обработке на сервере.")
        else:
            await status_msg.edit_text(f"Ошибка сервера: {response.status_code}")
            
    except Exception as e:
        await status_msg.edit_text(f"Не удалось связаться с сервером: {e}")


# --- ЗАПУСК ---
async def post_init(application):
    await init_db()

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    
    # Кнопки меню
    app.add_handler(MessageHandler(filters.Text(["👤 Мой профиль"]), show_profile))
    app.add_handler(MessageHandler(filters.Text(["📊 Глобальная стата"]), show_global_stats))
    
    # Обработчики контента
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # ВАЖНО: Этот хэндлер ловит ВЕСЬ остальной текст и считает его запросом на проверку
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("🤖 Бот-клиент запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()