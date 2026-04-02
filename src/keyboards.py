from telegram import ReplyKeyboardMarkup, KeyboardButton

# Создаем отдельные кнопки
button_convert = KeyboardButton("💰 Конвертация валюты")
button_rates = KeyboardButton("📊 Все курсы")
button_help = KeyboardButton("❓ Помощь")
button_back = KeyboardButton("🔙 Назад")

# Кнопки выбора направления
button_byn_to_foreign = KeyboardButton("🇧🇾 BYN → 💱 Иностранная")
button_foreign_to_byn = KeyboardButton("💱 Иностранная → 🇧🇾 BYN")

# Кнопки валют (для обоих режимов)
button_usd = KeyboardButton("🇺🇸 USD")
button_eur = KeyboardButton("🇪🇺 EUR")
button_rub = KeyboardButton("🇷🇺 RUB")
button_cny = KeyboardButton("🇨🇳 CNY")

# Главное меню
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [button_convert],
        [button_rates, button_help]
    ],
    resize_keyboard=True
)

# Меню выбора направления конвертации
DIRECTION_KEYBOARD = ReplyKeyboardMarkup(
    [
        [button_byn_to_foreign],
        [button_foreign_to_byn],
        [button_back]
    ],
    resize_keyboard=True
)

# Меню выбора валюты
CURRENCY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [button_usd, button_eur],
        [button_rub, button_cny],
        [button_back]
    ],
    resize_keyboard=True
)

# Меню с кнопкой "Назад"
BACK_KEYBOARD = ReplyKeyboardMarkup(
    [[button_back]],
    resize_keyboard=True
)

# Словарь для соответствия кнопок и кодов валют
CURRENCY_MAPPING = {
    "🇺🇸 USD": "USD",
    "🇪🇺 EUR": "EUR",
    "🇷🇺 RUB": "RUB",
    "🇨🇳 CNY": "CNY"
}