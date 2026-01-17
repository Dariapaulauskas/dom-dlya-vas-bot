import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

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
        "Чтобы подготовить для Вас информацию по запросу, задам несколько вопросов:\n\n"
    )
    await update.message.reply_text("Как могу к Вам обращаться?")
    return NAME

# Имя
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    user = update.message.from_user
    context.user_data['user_id'] = user.id
    context.user_data['username'] = f"@{user.username}" if user.username else "нет"

    keyboard = [
        ["Нужен расчёт проекта"],
        ["Задать вопрос / Получить консультацию"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("❓ Что Вы хотите?", reply_markup=reply_markup)
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
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
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
    # Инициализируем список выбранных опций
    context.user_data['selected_options'] = []
    keyboard = [
        ["Установка на сваи"],
        ["Утепление пола"],
        ["Утепление кровли"],
        ["Своё описание"],
        ["Далее →"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("💡 Что ещё важно? (можно выбрать несколько)", reply_markup=reply_markup)
    return OPTIONS

# Опции — множественный выбор
async def options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Далее →":
        # Завершаем выбор
        selected = context.user_data.get('selected_options', [])
        if "Своё описание" in selected:
            await update.message.reply_text("Напишите Ваш комментарий или пожелания")
            return CUSTOM_DESC
        else:
            context.user_data['options'] = ", ".join(selected) if selected else "—"
            await send_summary(update, context)
            return ConversationHandler.END

    elif text == "Своё описание":
        # Добавляем в список, но не завершаем
        if "Своё описание" not in context.user_data['selected_options']:
            context.user_data['selected_options'].append(text)
        await update.message.reply_text("Выберите ещё или нажмите «Далее →»")

    else:
        # Добавляем любую другую опцию
        if text not in context.user_data['selected_options']:
            context.user_data['selected_options'].append(text)
        await update.message.reply_text("Выберите ещё или нажмите «Далее →»")

    return OPTIONS

# Своё описание
async def custom_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['custom_desc'] = update.message.text
    selected = context.user_data.get('selected_options', [])
    context.user_data['options'] = ", ".join([opt for opt in selected if opt != "Своё описание"])
    await send_summary(update, context)
    return ConversationHandler.END

# Отправка итога
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

    client_msg = (
        f"✅ Спасибо, {name}!\n\n"
        f"Ваш запрос передан менеджеру.\n\n"
        f"⏱️ В рабочее время (9:00–18:00 МСК) Вы получите:\n"
        f"— информацию по проекту;\n"
        f"— ответ на вопрос.\n\n"
        f"Все коммуникации — через этот чат."
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
            PURPOSE: [
                MessageHandler(filters.Regex("^(Нужен расчёт проекта|Задать вопрос / Получить консультацию)$"), purpose)
            ],
            BUILDING_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, building_type)
            ],
            REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, size)],
            OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, options)],
            CUSTOM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_desc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
