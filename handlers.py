# handlers.py
from telegram import Update
from telegram.ext import ContextTypes
from api_client import get_real_bank_rates, get_best_rates_summary, predict_future_rates
from logger import log_conversion, log_to_console
from db_manager import save_user_setting, get_user_data

# ПРАВИЛЬНЫЙ ИМПОРТ НАСТРОЕК
from bot_config import CURRENCY_MAPPING, CITIES_MAPPING

# ПРАВИЛЬНЫЙ ИМПОРТ КЛАВИАТУР (раньше тут была ошибка!)
from keyboards import (
    MAIN_KEYBOARD, DIRECTION_KEYBOARD, CURRENCY_KEYBOARD,
    BACK_KEYBOARD, CITY_KEYBOARD, TIME_KEYBOARD
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user_setting(user.id, city_slug="minsk", time_pref="09:00")
    context.user_data['state'] = 'main_menu'

    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я агрегатор реальных курсов валют в банках Беларуси 💰\n\n"
        f"🏙️ Твой город: **Минск**\n"
        f"⏰ Время рассылки: **09:00**\n\n"
        f"✨ *Новая фича:* Теперь я умею анализировать рынок и делать прогнозы курсов!\n\n"
        f"Используй меню ниже:"
    )
    await update.message.reply_text(welcome_text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    user_name = user.first_name
    user_last_name = user.last_name or ""
    current_state = context.user_data.get('state', 'main_menu')

    u_data = get_user_data(user.id)
    city_slug, city_time = u_data["city"], u_data["time"]
    city_name_ru = next((k for k, v in CITIES_MAPPING.items() if v == city_slug), "Минск")

    # 1. ГЛАВНОЕ МЕНЮ
    if text == "💰 Конвертация валюты":
        context.user_data['state'] = 'direction_selection'
        await update.message.reply_text("Выберите направление:", reply_markup=DIRECTION_KEYBOARD)
        return

    elif text == "🏙️ Выбор города":
        context.user_data['state'] = 'city_selection'
        await update.message.reply_text(f"📍 Твой текущий город: **{city_name_ru}**\nВыбери новый:",
                                        reply_markup=CITY_KEYBOARD)
        return

    elif text == "⏰ Время рассылки":
        context.user_data['state'] = 'time_selection'
        status = f"**{city_time}**" if city_time != "off" else "**Отключена**"
        await update.message.reply_text(f"⏰ Текущее время рассылки: {status}\nВыбери новое:",
                                        reply_markup=TIME_KEYBOARD, parse_mode="Markdown")
        return

    # === БЛОК ТВОЕЙ МЕЧТЫ: ПРОГНОЗ ===
    elif text == "🔮 Прогноз курса":
        await update.message.reply_text("🔄 Анализирую исторические данные за 30 дней и считаю тренд...")
        predictions = predict_future_rates()

        if not predictions:
            await update.message.reply_text("❌ Ошибка соединения с сервером исторических данных.",
                                            reply_markup=MAIN_KEYBOARD)
            return

        msg = "🔮 **Аналитический прогноз курсов валют:**\n_Основано на математическом расчете динамики НБРБ за последние 30 дней_\n\n"
        for cur, data in predictions.items():
            unit = "100 " if cur == "RUB" else "10 " if cur == "CNY" else "1 "
            sign = "+" if data['change'] > 0 else ""
            msg += f"{data['icon']} **{unit}{cur}** (Сейчас: `{data['current']:.4f}`)\n"
            msg += f"   • Через неделю: `{data['week']:.4f}` BYN ({sign}{data['change']:.4f})\n"
            msg += f"   • Через месяц: `{data['month']:.4f}` BYN\n\n"

        msg += "⚠️ _Внимание: Рынок непредсказуем. Этот прогноз отражает математический тренд, а не финансовую рекомендацию._"
        await update.message.reply_text(msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")
        return

    # === БЛОК ЧЕСТНЫХ КУРСОВ ===
    elif text == "📊 Лучшие курсы банков":
        await update.message.reply_text(f"🔄 Запрашиваю честные данные обменников для г. {city_name_ru}...")
        data = get_best_rates_summary(city_slug)

        if not data:
            await update.message.reply_text("❌ Сервер агрегатора недоступен. Попробуй позже.",
                                            reply_markup=MAIN_KEYBOARD)
            return

        msg = f"🏆 **ЛУЧШИЕ КУРСЫ В ОБМЕННИКАХ ({city_name_ru}):**\n"
        for cur, info in data["best"].items():
            unit = "100 " if cur == "RUB" else "10 " if cur == "CNY" else "1 "
            msg += (
                f"\n💵 **{unit}{cur}**\n"
                f"🟢 Сдать дороже: `{info['best_buy']:.4f}` BYN ({info['best_buy_bank']})\n"
                f"🔴 Купить дешевле: `{info['best_sell']:.4f}` BYN ({info['best_sell_bank']})\n"
            )
        await update.message.reply_text(msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")
        return

    elif text == "❓ Помощь":
        await update.message.reply_text(
            "Бот берет абсолютно реальные данные с рынка. Раздел «Прогноз» математически вычисляет будущую стоимость на основе истории НБРБ.",
            reply_markup=MAIN_KEYBOARD)
        return

    elif text == "🔙 Назад":
        context.user_data['state'] = 'main_menu'
        await update.message.reply_text("Главное меню:", reply_markup=MAIN_KEYBOARD)
        return

    # 2. НАСТРОЙКИ ГОРОДА И ВРЕМЕНИ
    if current_state == 'city_selection':
        if text in CITIES_MAPPING:
            save_user_setting(user.id, city_slug=CITIES_MAPPING[text])
            context.user_data['state'] = 'main_menu'
            await update.message.reply_text(f"✅ Город изменен на: **{text}**", reply_markup=MAIN_KEYBOARD,
                                            parse_mode="Markdown")
        return

    if current_state == 'time_selection':
        if text in ["07:00", "08:00", "09:00", "10:00", "11:00"]:
            save_user_setting(user.id, time_pref=text)
            context.user_data['state'] = 'main_menu'
            await update.message.reply_text(f"✅ Время рассылки: **{text}**", reply_markup=MAIN_KEYBOARD,
                                            parse_mode="Markdown")
        elif text == "❌ Отключить рассылку":
            save_user_setting(user.id, time_pref="off")
            context.user_data['state'] = 'main_menu'
            await update.message.reply_text("❌ Рассылка отключена.", reply_markup=MAIN_KEYBOARD)
        return

    # 3. ЛОГИКА КОНВЕРТАЦИИ
    if current_state == 'direction_selection':
        if text == "🇧🇾 BYN → 💱 Иностранная":
            context.user_data['direction'], context.user_data['state'] = 'byn_to_foreign', 'currency_selection'
            await update.message.reply_text("Выбери целевую валюту:", reply_markup=CURRENCY_KEYBOARD)
        elif text == "💱 Иностранная → 🇧🇾 BYN":
            context.user_data['direction'], context.user_data['state'] = 'foreign_to_byn', 'currency_selection'
            await update.message.reply_text("Выбери продаваемую валюту:", reply_markup=CURRENCY_KEYBOARD)
        return

    if current_state == 'currency_selection':
        if text in CURRENCY_MAPPING:
            context.user_data['selected_currency'] = CURRENCY_MAPPING[text]
            context.user_data['state'] = 'awaiting_amount'
            unit_str = "BYN" if context.user_data['direction'] == 'byn_to_foreign' else CURRENCY_MAPPING[text]
            await update.message.reply_text(f"Введите сумму в {unit_str}:", reply_markup=BACK_KEYBOARD)
        return

    if current_state == 'awaiting_amount':
        try:
            amount = float(text.replace(",", "."))
            selected_currency = context.user_data['selected_currency']
            direction = context.user_data['direction']

            data = get_best_rates_summary(city_slug)

            if not data:
                await update.message.reply_text("❌ Сервер обмена недоступен.", reply_markup=MAIN_KEYBOARD)
                context.user_data['state'] = 'main_menu'
                return

            best_info = data["best"][selected_currency]
            scale = 100.0 if selected_currency == "RUB" else 10.0 if selected_currency == "CNY" else 1.0

            if direction == 'byn_to_foreign':
                rate = best_info["best_sell"]
                bank_name = best_info["best_sell_bank"]
                if rate > 0:
                    result = (amount / rate) * scale
                    res_text = (f"✅ {amount:.2f} BYN ≈ **{result:.2f} {selected_currency}**\n"
                                f"🏆 По лучшему реальному курсу в г. {city_name_ru}\n"
                                f"🏦 Банк: *{bank_name}* (Продажа: `{rate:.4f}` за {int(scale)} ед.)")
                    log_conversion(user_name, user_last_name, amount, result, "BYN", selected_currency)
                    log_to_console(user, user_name, user_last_name, amount, result, "BYN", selected_currency)
                else:
                    res_text = "❌ Нет доступных курсов."
            else:
                rate = best_info["best_buy"]
                bank_name = best_info["best_buy_bank"]
                if rate > 0:
                    result = (amount / scale) * rate
                    res_text = (f"✅ {amount:.2f} {selected_currency} ≈ **{result:.2f} BYN**\n"
                                f"🏆 По лучшему реальному курсу в г. {city_name_ru}\n"
                                f"🏦 Банк: *{bank_name}* (Покупка: `{rate:.4f}` за {int(scale)} ед.)")
                    log_conversion(user_name, user_last_name, amount, result, selected_currency, "BYN")
                    log_to_console(user, user_name, user_last_name, amount, result, selected_currency, "BYN")
                else:
                    res_text = "❌ Нет доступных курсов."

            await update.message.reply_text(res_text, reply_markup=CURRENCY_KEYBOARD, parse_mode="Markdown")
            context.user_data['state'] = 'currency_selection'
        except ValueError:
            await update.message.reply_text("❌ Введите корректное число!", reply_markup=BACK_KEYBOARD)
        return

    await update.message.reply_text("Используй кнопки меню:", reply_markup=MAIN_KEYBOARD)