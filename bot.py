
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1T6br7eOJXTueLCWyVeLqscqIpZcPBcxUC6HwXWdsD5c/edit#gid=0").sheet1

ALL_BOXES = [
    "Бокс 1 C195с", "Бокс 2 A185б", "Бокс 3", "Бокс 4", "Бокс 5",
    "Бокс 6", "Бокс 7", "Бокс 8", "Бокс 11 Sport", "Бокс 10 LUX"
]

START_DATE, END_DATE, SELECT_BOX, GET_NAME, GET_PHONE = range(5)

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Введите дату начала аренды (в формате ДД.ММ.ГГГГ):")
    return START_DATE

def get_start_date(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['start_date'] = datetime.strptime(update.message.text, "%d.%m.%Y").date()
        update.message.reply_text("Введите дату окончания аренды (в формате ДД.ММ.ГГГГ):")
        return END_DATE
    except ValueError:
        update.message.reply_text("Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):")
        return START_DATE

def get_end_date(update: Update, context: CallbackContext) -> int:
    try:
        end_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
        start_date = context.user_data['start_date']
        if end_date < start_date:
            update.message.reply_text("Дата окончания не может быть раньше даты начала. Попробуйте снова:")
            return END_DATE
        context.user_data['end_date'] = end_date

        all_records = sheet.get_all_records()
        busy_boxes = set()
        for row in all_records:
            b = row.get("Бокс")
            date_from = row.get("Дата начала")
            date_to = row.get("Дата окончания")
            if b and date_from and date_to:
                d1 = datetime.strptime(date_from, "%d.%m.%Y").date()
                d2 = datetime.strptime(date_to, "%d.%m.%Y").date()
                if not (end_date < d1 or start_date > d2):
                    busy_boxes.add(b)

        available_boxes = [box for box in ALL_BOXES if box not in busy_boxes]
        if not available_boxes:
            update.message.reply_text("К сожалению, нет свободных боксов на выбранные даты.")
            return ConversationHandler.END

        context.user_data['available_boxes'] = available_boxes
        keyboard = [[box] for box in available_boxes]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        update.message.reply_text("Выберите доступный бокс:", reply_markup=reply_markup)
        return SELECT_BOX
    except ValueError:
        update.message.reply_text("Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):")
        return END_DATE

def select_box(update: Update, context: CallbackContext) -> int:
    context.user_data['box'] = update.message.text
    update.message.reply_text("Введите ваше имя:")
    return GET_NAME

def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text("Введите ваш номер телефона:")
    return GET_PHONE

def get_phone(update: Update, context: CallbackContext) -> int:
    context.user_data['phone'] = update.message.text
    name = context.user_data['name']
    phone = context.user_data['phone']
    box = context.user_data['box']
    start_date = context.user_data['start_date'].strftime("%d.%m.%Y")
    end_date = context.user_data['end_date'].strftime("%d.%m.%Y")

    sheet.append_row([name, phone, box, start_date, end_date])
    update.message.reply_text(f"Спасибо, {name}! Вы забронировали {box} с {start_date} по {end_date}.")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Процесс отменён.")
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_DATE: [MessageHandler(Filters.text & ~Filters.command, get_start_date)],
            END_DATE: [MessageHandler(Filters.text & ~Filters.command, get_end_date)],
            SELECT_BOX: [MessageHandler(Filters.text & ~Filters.command, select_box)],
            GET_NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            GET_PHONE: [MessageHandler(Filters.text & ~Filters.command, get_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
