from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from api_client import get_usd_rate
from logger import log_conversion, log_to_console
from config import CURRENCY_KEYBOARD_BUTTONS

currency_keyboard = ReplyKeyboardMarkup(CURRENCY_KEYBOARD_BUTTONS, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    print(f"✅ Команда /start получена! Пользователь {user_name} {user_last_name}")
    if user_last_name != None:
        await update.message.reply_text(f"Привет  {user_name} {user_last_name}!")

    else:
        await update.message.reply_text(f"Привет {user_name}!", reply_markup=currency_keyboard)


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    user = update.message.from_user

    # Обработка нажатия на кнопку
    if text == "💰Расчет валюты":
        context.user_data['awaiting_amount'] = True
        await update.message.reply_text(
            "Введите сумму в BYN для конвертации в USD:",
            reply_markup=currency_keyboard
        )
        return

    # Обработка ввода суммы
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(text)
            rate = get_usd_rate()

            if rate:
                result = amount / rate

                # Отправка результата пользователю
                await update.message.reply_text(
                    f"Беларусь Банк 💚\n"
                    f"{amount} BYN = {result:.2f} USD\n"
                    f"(Курс: {rate:.2f})"
                )

                # Логирование
                log_conversion(user_name, user_last_name, amount, result)
                log_to_console(user, user_name, user_last_name, amount, result)

            else:
                await update.message.reply_text("❌ Не удалось получить курс")

            context.user_data['awaiting_amount'] = False

        except ValueError:
            await update.message.reply_text(
                "❌ Это не число! Пожалуйста, введите число",
                reply_markup=currency_keyboard
            )