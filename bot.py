import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from flask import Flask, request

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Этапы диалога
NAME, PURPOSE, BUILDING_TYPE, REGION, SIZE, OPTIONS, CUSTOM_DESC = range(7)

# Старт диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте!\n"
        "Это Помощник от компании «ДОМ ДЛЯ ВАС».\n\n"
        "Чтобы подготовить для вас информацию по запросу, задам несколько вопросов:\n\n"
        "Ответьте на те пункты, которые уже понятны — остальное уточним по ходу 😊"
    )
    await update.message.reply_text("👤 Как к вам обращаться?")
    return NAME

# Имя
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    context.user_data['name'] = update.message.text
    context.user_data['user_id'] = user.id
    context.user_data['username'] = f"@{user.username}" if user.username else "нет"
    context.user_data['first_name'] = user.first_name

    keyboard = [
        ["Нужен расчёт проекта"],
        ["Задать вопрос / получить консультацию"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("❓ Что вы хотите?", reply_markup=reply_markup)
    return PURPOSE

# Цель
async def purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    context.user_data['purpose'] = choice

    if "расчёт" in choice.lower():
        keyboard = [
            ["Дачный дом"],
            ["Хозблок / Бытовка"],
            ["Беседка"],
            ["Баня"],
            ["Другое (напишите)"],
            ["Есть готовый проект"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text("🏡 Какое строение интересует?", reply_markup=reply_markup)
        return BUILDING_TYPE
    else:
        await send_summary(update, context)
        return ConversationHandler.END

# Тип строения
async def building_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['building'] = update.message.text
    await update.message.reply_text("📍 Где будет установка?\n(Например: Москва, Красногорск)")
    return REGION

# Регион
async def region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['region'] = update.message.text
    await update.message.reply_text("📐 Укажите желаемые размеры\n(Например: 5×4 м)")
    return SIZE

# Размеры
async def size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['size'] = update.message.text
    keyboard = [
        ["Установка на сваи"],
        ["Утепление пола"],
        ["Утепление кровли"],
        ["Своё описание"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("💡 Что ещё важно? (можно выбрать несколько)", reply_markup=reply_markup)
    return OPTIONS

# Опции
async def options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['options'] = update.message.text
    if "Своё описание" in update.message.text:
        await update.message.reply_text("Напишите ваш комментарий или пожелания")
        return CUSTOM_DESC
    else:
        await send_summary(update, context)
        return ConversationHandler.END

# Своё описание
async def custom_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['custom_desc'] = update.message.text
    await send_summary(update, context)
    return ConversationHandler.END

# Отправка итога админу и клиенту
async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    name = data.get('name', '—')
    user_id = data.get('user_id', '—')
    username = data.get('username', '—')
    purpose = data.get('purpose', '—')
    building = data.get('building', '—')
    region = data.get('region', '—')
    size = data.get('size', '—')
    options = data.get('options', '—')
    custom_desc = data.get('custom_desc', '')

    # Сообщение админу
    admin_msg = (
        f"🔔 НОВЫЙ КЛИЕНТ!\n\n"
        f"Имя: {name}\n"
        f"Telegram: {username} (ID: {user_id})\n"
        f"Цель: {purpose}\n"
        f"Строение: {building}\n"
        f"Регион: {region}\n"
        f"Размеры: {size}\n"
        f"Опции: {options}\n"
        f"{'Описание: ' + custom_desc if custom_desc else ''}\n\n"
        f"👉 Открыть чат: tg://user?id={user_id}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
    except Exception as e:
        logging.error(f"Не удалось отправить админу: {e}")

    # Сообщение клиенту
    client_msg = (
        f"✅ Спасибо, {name}!\n\n"
        f"Ваш запрос передан менеджеру.\n\n"
        f"⏱️ В рабочее время (9:00–18:00 МСК) вы получите:\n"
        f"— информацию по проекту (если запрашивали расчёт);\n"
        f"— ответ на вопрос (если нужна консультация).\n\n"
        f"Все коммуникации проходят через этот чат.\n"
        f"Если что-то срочное — напишите прямо здесь."
    )
    await update.message.reply_text(client_msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purpose)],
            BUILDING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, building_type)],
            REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, size)],
            OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, options)],
            CUSTOM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_desc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск webhook
    port = int(os.environ.get("PORT", 8000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"https://dom-dlya-vas-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
