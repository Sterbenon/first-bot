import os
import time
from telegram import Update, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.error import TelegramError, Conflict
import pandas as pd
import logging
import asyncio  # Імпортуємо asyncio

# Налаштування логування
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), "data.xls")
products_cache = {}

# Список ID авторизованих користувачів для оновлення файлу
AUTHORIZED_USER_IDS = {111111111}  # Замініть на реальні ID користувачів

# Завантаження продуктів з Excel
def load_products():
    try:
        df = pd.read_excel(PRODUCTS_FILE, dtype=str)
        logging.info("Фактичні назви стовпців у файлі: %s", df.columns)
        products = {}
        required_columns = ['Артикул', 'Назва', 'Склад', 'Одиниця виміру']
        if all(col in df.columns for col in required_columns):
            for _, row in df.iterrows():
                article = str(row['Артикул']).strip()
                products[article] = {
                    "name": str(row['Назва']).strip(),
                    "stock": str(row['Склад']).strip(),
                    "unit": str(row['Одиниця виміру']).strip()
                }
        else:
            logging.error("Відсутні необхідні стовпці.")
            return {}
        return products
    except FileNotFoundError:
        logging.error("Файл '%s' не знайдено.", PRODUCTS_FILE)
        return {}
    except Exception as e:
        logging.error("Помилка при читанні файлу: %s", e, exc_info=True) # Додано exc_info=True
        return {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("👋 Введи артикул товару (наприклад: 00107), і я покажу інформацію.")
    except Exception as e:
        logging.error(f"Помилка в start: {e}", exc_info=True)

# Команда /restart
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if user_id in AUTHORIZED_USER_IDS:
            global products_cache
            products_cache = load_products()
            await update.message.reply_text("🔄 Дані оновлено з файлу!")
        else:
            await update.message.reply_text("🚫 Ви не маєте прав для оновлення даних.")
    except Exception as e:
        logging.error(f"Помилка в restart: {e}", exc_info=True)

# Обробка тексту (артикулу)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        article = update.message.text.strip()
        await send_product_info(update, article)
    except Exception as e:
        logging.error(f"Помилка в handle_text: {e}", exc_info=True)

# Відправити інформацію про товар
async def send_product_info(update: Update, article: str):
    global products_cache
    try:
        item = products_cache.get(article)
        if item:
            msg = (
                f"Артикул: {article}\n"
                f"Назва: {item['name']}\n"
                f"Залишок на складі: {item['stock']}\n"
                f"Одиниця виміру: {item['unit']}"
            )
        else:
            msg = "Товар з таким артикулом не знайдено."
        await update.message.reply_text(msg)
    except Exception as e:
        logging.error(f"Помилка в send_product_info: {e}", exc_info=True)

# Обробка завантаженого Excel-файлу
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if user_id in AUTHORIZED_USER_IDS:
            document: Document = update.message.document
            if document.file_name.endswith(".xls") or document.file_name.endswith(".xlsx"):
                file_path = PRODUCTS_FILE
                new_file = await document.get_file()
                await new_file.download_to_drive(file_path)
                global products_cache
                products_cache = load_products()
                await update.message.reply_text("✅ Файл отримано та дані оновлено.")
            else:
                await update.message.reply_text("⚠️ Надішли, будь ласка, файл у форматі .xls або .xlsx")
        else:
            await update.message.reply_text("🚫 Ви не маєте прав для завантаження файлів оновлення.")
    except Exception as e:
        logging.error(f"Помилка в handle_document: {e}", exc_info=True)

# Запуск бота
def main():
    global products_cache
    products_cache = load_products()

    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build() # Замініть YOUR_BOT_TOKEN на свій токен

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logging.info("Бот запускається...")
    try:
        app.run_polling(poll_interval=2.0, timeout=10)
        logging.info("Бот зупинено.")
    except Conflict as ce:
        logging.error("Конфлікт: %s. Бот не може бути запущений.", ce)
    except TelegramError as te:
        logging.error("Помилка Telegram: %s", te)
    except KeyboardInterrupt:
        logging.info("Бот зупинено користувачем.")
    except Exception as e:
        logging.error("Інша помилка: %s", e, exc_info=True) # Додано exc_info=True

    # Коректне завершення роботи Application
    try:
        asyncio.run(app.shutdown())
    except RuntimeError:
        # Цикл подій вже може бути закритим, ігноруємо помилку
        pass

if __name__ == '__main__':
    print("Бот запущено та готовий до роботи!")
    main()