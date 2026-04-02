from telegram import Update
from telegram.ext import ContextTypes
from src.api_client import get_currency_rate, get_all_rates
from src.config import (
    MAIN_KEYBOARD,
    DIRECTION_KEYBOARD,
    CURRENCY_KEYBOARD,
    BACK_KEYBOARD,
    CURRENCY_MAPPING
)

# Функции для логирования (добавляем)
def log_conversion(user_name, user_last_name, amount, result, currency_from, currency_to):
    """Логирование конвертации"""
    print(f"💰 КОНВЕРТАЦИЯ: {user_name} {user_last_name} | {amount:.2f} {currency_from} → {result:.2f} {currency_to}")

def log_to_console(user, user_name, user_last_name, amount, result, currency_from, currency_to):
    """Дополнительное логирование"""
    print(f"📊 ДЕТАЛИ: Пользователь @{user.username or 'no_username'} | {currency_from} → {currency_to} | Сумма: {amount} | Результат: {result:.2f}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    print(f"✅ Команда /start получена! Пользователь {user_name} {user_last_name}")

    context.user_data['state'] = 'main_menu'

    welcome_text = (
        f"👋 Привет, {user_name} {user_last_name if user_last_name else ''}!\n\n"
        f"Я бот для конвертации валют Беларусь Банк 💰\n\n"
        f"📌 Доступны два режима конвертации:\n"
        f"1️⃣ 🇧🇾 BYN → 💱 Иностранная валюта\n"
        f"2️⃣ 💱 Иностранная валюта → 🇧🇾 BYN\n\n"
        f"Доступные валюты:\n"
        f"🇺🇸 USD - Доллар США\n"
        f"🇪🇺 EUR - Евро\n"
        f"🇷🇺 RUB - Российский рубль\n"
        f"🇨🇳 CNY - Китайский юань\n\n"
        f"Выберите действие в меню ниже:"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=MAIN_KEYBOARD
    )


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_name = update.message.from_user.first_name
    user_last_name = update.message.from_user.last_name
    user = update.message.from_user

    current_state = context.user_data.get('state', 'main_menu')

    if text == "💰 Конвертация валюты":
        context.user_data['state'] = 'direction_selection'
        await update.message.reply_text(
            "Выберите направление конвертации:",
            reply_markup=DIRECTION_KEYBOARD
        )

    elif text == "📊 Все курсы":
        rates = get_all_rates()
        if rates:
            message = "📊 Текущие курсы валют (Беларусь Банк):\n\n"
            for currency, rate in rates.items():
                flag = "🇺🇸" if currency == "USD" else "🇪🇺" if currency == "EUR" else "🇷🇺" if currency == "RUB" else "🇨🇳"
                message += f"{flag} 1 {currency} = {rate:.2f} BYN\n"
        else:
            message = "❌ Не удалось получить курсы валют"

        await update.message.reply_text(
            message,
            reply_markup=MAIN_KEYBOARD
        )

    elif text == "❓ Помощь":
        help_text = (
            "📚 Как пользоваться ботом:\n\n"
            "1️⃣ Нажмите '💰 Конвертация валюты'\n"
            "2️⃣ Выберите направление:\n"
            "   • 🇧🇾 BYN → 💱 (из рублей в иностранную)\n"
            "   • 💱 → 🇧🇾 BYN (из иностранной в рубли)\n"
            "3️⃣ Выберите валюту\n"
            "4️⃣ Введите сумму\n"
            "5️⃣ Получите результат!\n\n"
            "📊 'Все курсы' - показать все текущие курсы\n"
            "🔙 'Назад' - вернуться в предыдущее меню"
        )
        await update.message.reply_text(
            help_text,
            reply_markup=MAIN_KEYBOARD
        )

    elif text == "🔙 Назад":
        if current_state == 'currency_selection':
            context.user_data['state'] = 'direction_selection'
            await update.message.reply_text(
                "Выберите направление конвертации:",
                reply_markup=DIRECTION_KEYBOARD
            )
        else:
            context.user_data['state'] = 'main_menu'
            context.user_data.pop('direction', None)
            context.user_data.pop('selected_currency', None)
            context.user_data.pop('awaiting_amount', None)
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=MAIN_KEYBOARD
            )

    elif text == "🇧🇾 BYN → 💱 Иностранная":
        context.user_data['direction'] = 'byn_to_foreign'
        context.user_data['state'] = 'currency_selection'
        await update.message.reply_text(
            "Выберите валюту для конвертации из BYN:",
            reply_markup=CURRENCY_KEYBOARD
        )

    elif text == "💱 Иностранная → 🇧🇾 BYN":
        context.user_data['direction'] = 'foreign_to_byn'
        context.user_data['state'] = 'currency_selection'
        await update.message.reply_text(
            "Выберите валюту для конвертации в BYN:",
            reply_markup=CURRENCY_KEYBOARD
        )

    elif text in CURRENCY_MAPPING:
        selected_currency = CURRENCY_MAPPING[text]
        direction = context.user_data.get('direction')

        if not direction:
            await update.message.reply_text(
                "Сначала выберите направление конвертации!",
                reply_markup=DIRECTION_KEYBOARD
            )
            return

        context.user_data['selected_currency'] = selected_currency
        context.user_data['state'] = 'awaiting_amount'

        rate = get_currency_rate(selected_currency)
        rate_text = f"{rate:.2f}" if rate else "не доступен"

        if direction == 'byn_to_foreign':
            await update.message.reply_text(
                f"Вы выбрали: 🇧🇾 BYN → {text}\n"
                f"💰 Текущий курс: 1 {selected_currency} = {rate_text} BYN\n\n"
                f"Введите сумму в BYN для конвертации в {selected_currency}:",
                reply_markup=BACK_KEYBOARD
            )
        else:
            await update.message.reply_text(
                f"Вы выбрали: {text} → 🇧🇾 BYN\n"
                f"💰 Текущий курс: 1 {selected_currency} = {rate_text} BYN\n\n"
                f"Введите сумму в {selected_currency} для конвертации в BYN:",
                reply_markup=BACK_KEYBOARD
            )

    elif current_state == 'awaiting_amount' and context.user_data.get('selected_currency'):
        try:
            amount = float(text)
            selected_currency = context.user_data['selected_currency']
            direction = context.user_data.get('direction')

            rate = get_currency_rate(selected_currency)

            if rate:
                if direction == 'byn_to_foreign':
                    result = amount / rate
                    result_text = (
                        f"✅ Результат конвертации:\n\n"
                        f"🇧🇾 {amount:.2f} BYN = {result:.2f} {selected_currency}\n"
                        f"📈 Курс: 1 {selected_currency} = {rate:.2f} BYN\n\n"
                        f"Что делаем дальше?"
                    )
                    log_conversion(user_name, user_last_name, amount, result,
                                   currency_from="BYN", currency_to=selected_currency)
                else:
                    result = amount * rate
                    result_text = (
                        f"✅ Результат конвертации:\n\n"
                        f"{amount:.2f} {selected_currency} = 🇧🇾 {result:.2f} BYN\n"
                        f"📈 Курс: 1 {selected_currency} = {rate:.2f} BYN\n\n"
                        f"Что делаем дальше?"
                    )
                    log_conversion(user_name, user_last_name, amount, result,
                                   currency_from=selected_currency, currency_to="BYN")

                await update.message.reply_text(
                    result_text,
                    reply_markup=CURRENCY_KEYBOARD
                )

                log_to_console(user, user_name, user_last_name, amount, result,
                               currency_from="BYN" if direction == 'byn_to_foreign' else selected_currency,
                               currency_to=selected_currency if direction == 'byn_to_foreign' else "BYN")

                context.user_data['state'] = 'currency_selection'
                context.user_data.pop('selected_currency')

            else:
                await update.message.reply_text(
                    f"❌ Не удалось получить курс для {selected_currency}",
                    reply_markup=CURRENCY_KEYBOARD
                )

        except ValueError:
            await update.message.reply_text(
                f"❌ Пожалуйста, введите число!\n"
                f"Пример: 100, 50.5, 1000",
                reply_markup=BACK_KEYBOARD
            )

    else:
        await update.message.reply_text(
            "🤔 Я не понимаю эту команду.\n"
            "Используйте кнопки меню для навигации:",
            reply_markup=MAIN_KEYBOARD
        )