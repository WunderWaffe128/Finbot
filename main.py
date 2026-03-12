from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import requests
from datetime import datetime

BOT_TOKEN = ""

currency_keyboard = [["💰Расчет валюты"]]
currency_keyboard = ReplyKeyboardMarkup(currency_keyboard, resize_keyboard=True)

def get_usd():
    try:
        url = "https://belarusbank.by/api/kursExchange"
        response = requests.get(url)
        print(f"✅ Статус ответа : {response.status_code}")
        if response.status_code == 200:
            print("✅ Сайт доступен!")
            data = response.json()
            bank = data[0]
            usd_rate = float(bank["USD_out"])
            return usd_rate
        else:
            print("❌ Сайт не отвечает")
    except Exception as e:
        print(f"❌ Ошибка:{e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    print(f"✅ Команда /start получена! Пользователь {user_name} {user_last_name}")
    if user_last_name != None:
        await update.message.reply_text(f"Привет  {user_name} {user_last_name}!")

    else:
        await update.message.reply_text(f"Привет {user_name}!", reply_markup=currency_keyboard)


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    user = update.message.from_user
    if text == "💰Расчет валюты":
        context.user_data['awaiting_amount'] = True
        await update.message.reply_text("Введите сумму для конвертации:", reply_markup=currency_keyboard)
        return
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(text)
            rate = get_usd()
            if rate:
                result = amount/rate
                await update.message.reply_text(f"Беларусь Банк 💚 \n {amount} BYN = {result:.2f} USD\n (Курс: {rate:.2f})")
                log_to_file(user_name, user_last_name, amount, result)
                print(f"Время: [{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] Пользователь: {user.id, user_name,user_last_name},"
                       f" Сумма: {amount} BYN, Получил: {result:.2f} USD\n")
            else:
                await update.message.reply_text("❌ Нет удалось получить курс")
            context.user_data['awaiting_amount'] = False
        except ValueError:
            pass
            await update.message.reply_text("❌ Это не число! Пожалуйста введите число")
            return

def log_to_file(user_name, user_last_name, amount, result):
    try:
        current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        last_name = user_last_name if user_last_name else ""
        with open('bot.log.txt', 'a', encoding='utf-8') as file:
            file.write(f"Время: [{current_time}] Пользователь: {user_name, user_last_name},"
                       f" Сумма: {amount} BYN, Получил: {result} USD\n")
    except Exception as e:
        print(f"❌ Ошибка записи в файл: {e}")
if __name__ == "__main__":
    print("🚀 Запускаю бота...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    print("✅ Бот запущен!")
    app.run_polling()



"""await update.message.reply_text("❌ Такой команды нету! Нажмите на кнопку или /start")"""