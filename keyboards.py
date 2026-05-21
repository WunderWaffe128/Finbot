# keyboards.py
from telegram import ReplyKeyboardMarkup, KeyboardButton

button_convert = KeyboardButton("💰 Конвертация валюты")
button_rates = KeyboardButton("📊 Лучшие курсы банков")
button_predict = KeyboardButton("🔮 Прогноз курса") # НОВАЯ КНОПКА
button_city = KeyboardButton("🏙️ Выбор города")
button_time = KeyboardButton("⏰ Время рассылки")
button_help = KeyboardButton("❓ Помощь")
button_back = KeyboardButton("🔙 Назад")

button_byn_to_foreign = KeyboardButton("🇧🇾 BYN → 💱 Иностранная")
button_foreign_to_byn = KeyboardButton("💱 Иностранная → 🇧🇾 BYN")

button_usd = KeyboardButton("🇺🇸 USD")
button_eur = KeyboardButton("🇪🇺 EUR")
button_rub = KeyboardButton("🇷🇺 RUB")
button_cny = KeyboardButton("🇨🇳 CNY")

# Кнопки выбора времени
t_07 = KeyboardButton("07:00")
t_08 = KeyboardButton("08:00")
t_09 = KeyboardButton("09:00")
t_10 = KeyboardButton("10:00")
t_11 = KeyboardButton("11:00")
t_off = KeyboardButton("❌ Отключить рассылку")

# Обновленное главное меню
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[button_convert], [button_rates, button_predict], [button_city, button_time], [button_help]],
    resize_keyboard=True
)

DIRECTION_KEYBOARD = ReplyKeyboardMarkup([[button_byn_to_foreign], [button_foreign_to_byn], [button_back]], resize_keyboard=True)
CURRENCY_KEYBOARD = ReplyKeyboardMarkup([[button_usd, button_eur], [button_rub, button_cny], [button_back]], resize_keyboard=True)
BACK_KEYBOARD = ReplyKeyboardMarkup([[button_back]], resize_keyboard=True)

button_minsk = KeyboardButton("Минск")
button_gomel = KeyboardButton("Гомель")
button_brest = KeyboardButton("Брест")
button_grodno = KeyboardButton("Гродно")
button_mogilev = KeyboardButton("Могилёв")
button_vitebsk = KeyboardButton("Витебск")
CITY_KEYBOARD = ReplyKeyboardMarkup([[button_minsk, button_gomel], [button_brest, button_grodno], [button_mogilev, button_vitebsk], [button_back]], resize_keyboard=True)

TIME_KEYBOARD = ReplyKeyboardMarkup([[t_07, t_08, t_09], [t_10, t_11, t_off], [button_back]], resize_keyboard=True)
