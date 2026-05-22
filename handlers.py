# handlers.py
from telegram import Update
from telegram.ext import ContextTypes

from api_client import get_real_bank_rates, get_best_rates_summary
from predictor import predict_all
from logger import log_conversion, log_to_console
from db_manager import save_user_setting, get_user_data
from rate_cache import get_cache

from bot_config import CURRENCY_MAPPING, CITIES_MAPPING
from keyboards import (
    MAIN_KEYBOARD, DIRECTION_KEYBOARD, CURRENCY_KEYBOARD,
    BACK_KEYBOARD, CITY_KEYBOARD, TIME_KEYBOARD,
)


# ─────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────

def _cache_status(city_slug: str) -> str:
    """Возвращает строку с временем последнего обновления кэша."""
    from rate_cache import get_cache_age_minutes, get_cache
    cached = get_cache(city_slug)
    if cached:
        return f"🕐 Данные от: {cached['updated_at']}"
    return "🕐 Данные: живой запрос"


def _format_forecast_block(cur: str, pred: dict) -> str:
    """Красиво форматирует блок прогноза для одной валюты."""
    scale = pred["scale"]
    unit  = f"{scale} " if scale > 1 else "1 "
    curr_nbrb = pred["current_nbrb"]
    fc    = pred["forecasts"]
    icon  = pred["trend_icon"]
    tl    = pred["trend_label"]
    vol   = pred["volatility_daily"]
    rec   = pred.get("recommendation", {})

    lines = [f"{icon} **{unit}{cur}/BYN** — {tl}"]
    lines.append(f"   Официальный НБРБ: `{curr_nbrb:.4f}`")
    lines.append(
        f"   📅 Через неделю:  `{fc['week']:.4f}`"
        f"  ({'+' if fc['week'] >= curr_nbrb else ''}{fc['week'] - curr_nbrb:.4f})"
    )
    lines.append(
        f"   📅 Через месяц:   `{fc['month']:.4f}`"
        f"  ({'+' if fc['month'] >= curr_nbrb else ''}{fc['month'] - curr_nbrb:.4f})"
    )
    lines.append(
        f"   📅 Через год:     `{fc['year']:.4f}`"
        f"  ({'+' if fc['year'] >= curr_nbrb else ''}{fc['year'] - curr_nbrb:.4f})"
    )
    lines.append(
        f"   📅 Через 5 лет:   `{fc['years5']:.4f}`"
        f"  ({'+' if fc['years5'] >= curr_nbrb else ''}{fc['years5'] - curr_nbrb:.4f})"
    )
    lines.append(f"   ⚡ Дневная волатильность: `±{vol:.5f}` BYN")

    if rec:
        buy_label,  buy_desc  = rec.get("buy",  ("—", "—"))
        sell_label, sell_desc = rec.get("sell", ("—", "—"))
        lines.append(f"   🟢 Купить: **{buy_label}** — _{buy_desc}_")
        lines.append(f"   🔴 Продать: **{sell_label}** — _{sell_desc}_")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# ХЭНДЛЕРЫ
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user_setting(user.id, city_slug="minsk", time_pref="09:00")
    context.user_data["state"] = "main_menu"

    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я агрегатор реальных курсов обменников Беларуси 💰\n\n"
        f"🏙️ Твой город: **Минск**\n"
        f"⏰ Время рассылки: **09:00**\n\n"
        f"📦 Курсы банков кэшируются и обновляются автоматически в:\n"
        f"`06:05 · 09:05 · 12:05 · 15:05 · 18:05 · 21:05 · 00:05 · 03:05`\n\n"
        f"🔮 Прогноз считается по 365 дням истории НБРБ\n"
        f"   методами линейной регрессии и EWM-сглаживания.\n\n"
        f"Используй меню ниже:"
    )
    await update.message.reply_text(
        welcome_text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
    )


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text
    user  = update.message.from_user
    user_name      = user.first_name
    user_last_name = user.last_name or ""
    current_state  = context.user_data.get("state", "main_menu")

    u_data      = get_user_data(user.id)
    city_slug   = u_data["city"]
    city_time   = u_data["time"]
    city_name_ru = next(
        (k for k, v in CITIES_MAPPING.items() if v == city_slug), "Минск"
    )

    # ────── ГЛАВНОЕ МЕНЮ ──────
    if text == "💰 Конвертация валюты":
        context.user_data["state"] = "direction_selection"
        await update.message.reply_text(
            "Выберите направление:", reply_markup=DIRECTION_KEYBOARD
        )
        return

    elif text == "🏙️ Выбор города":
        context.user_data["state"] = "city_selection"
        await update.message.reply_text(
            f"📍 Текущий город: **{city_name_ru}**\nВыбери новый:",
            reply_markup=CITY_KEYBOARD, parse_mode="Markdown"
        )
        return

    elif text == "⏰ Время рассылки":
        context.user_data["state"] = "time_selection"
        status = f"**{city_time}**" if city_time != "off" else "**Отключена**"
        await update.message.reply_text(
            f"⏰ Текущее время рассылки: {status}\nВыбери новое:",
            reply_markup=TIME_KEYBOARD, parse_mode="Markdown"
        )
        return

    # ────── ЛУЧШИЕ КУРСЫ ──────
    elif text == "📊 Лучшие курсы банков":
        cache_info = _cache_status(city_slug)
        await update.message.reply_text(
            f"🔄 Загружаю курсы обменников г. {city_name_ru}…\n{cache_info}"
        )
        data = get_best_rates_summary(city_slug)

        if not data:
            await update.message.reply_text(
                "❌ Сервер агрегатора недоступен. Попробуй позже.",
                reply_markup=MAIN_KEYBOARD
            )
            return

        msg = f"🏆 **ЛУЧШИЕ КУРСЫ ОБМЕННИКОВ — {city_name_ru}**\n{cache_info}\n"
        for cur, info in data["best"].items():
            unit = "100 " if cur == "RUB" else "10 " if cur == "CNY" else "1 "
            msg += (
                f"\n💵 **{unit}{cur}**\n"
                f"🟢 Сдать выгоднее: `{info['best_buy']:.4f}` BYN"
                f" ({info['best_buy_bank']})\n"
                f"🔴 Купить дешевле: `{info['best_sell']:.4f}` BYN"
                f" ({info['best_sell_bank']})\n"
            )

        # Список всех банков
        all_banks = data.get("all_banks", {})
        if all_banks:
            msg += "\n📋 **Все банки в выборке:**\n"
            msg += ", ".join(f"_{b}_" for b in all_banks.keys())

        await update.message.reply_text(
            msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
        )
        return

    # ────── ПРОГНОЗ ──────
    elif text == "🔮 Прогноз курса":
        await update.message.reply_text(
            "⏳ Загружаю 365 дней истории НБРБ и считаю прогноз…\n"
            "_Это занимает 5–10 секунд_",
            parse_mode="Markdown"
        )

        # Получаем банковские курсы для рекомендаций (из кэша — быстро)
        bank_data = get_best_rates_summary(city_slug)
        bank_best = bank_data["best"] if bank_data else None

        predictions = predict_all(bank_rates=bank_best)

        if not predictions:
            await update.message.reply_text(
                "❌ Не удалось получить исторические данные НБРБ.",
                reply_markup=MAIN_KEYBOARD
            )
            return

        msg = (
            "🔮 **АНАЛИТИЧЕСКИЙ ПРОГНОЗ КУРСОВ ВАЛЮТ**\n"
            "_Методы: линейная регрессия + EWM-сглаживание_\n"
            "_База: 365 дней официальной статистики НБРБ_\n\n"
        )

        for cur, pred in predictions.items():
            msg += _format_forecast_block(cur, pred) + "\n\n"

        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ _Прогноз — математический тренд, не финансовая рекомендация._\n"
            "_Рынок может отклоняться от модели под влиянием внешних факторов._"
        )

        # Telegram ограничивает сообщения 4096 символами
        if len(msg) > 4000:
            msg = msg[:3990] + "\n…_(обрезано)_"

        await update.message.reply_text(
            msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
        )
        return

    elif text == "❓ Помощь":
        help_text = (
            "ℹ️ **Как работает бот**\n\n"
            "📊 *Курсы банков* — агрегирует данные Беларусбанка, Приорбанка, "
            "Альфа Банка, Сбер Банка, Белагропромбанка, Белинвестбанка, МТБанка.\n\n"
            "♻️ *Кэш* — курсы обновляются автоматически 8 раз в сутки. "
            "Ты всегда видишь актуальные данные без лишних задержек.\n\n"
            "🔮 *Прогноз* — берёт 365 дней истории НБРБ, применяет линейную "
            "регрессию и экспоненциальное сглаживание (EWM), строит горизонты "
            "на неделю / месяц / год / 5 лет.\n\n"
            "💡 *Рекомендации* сравнивают текущий банковский курс "
            "с прогнозным и подсказывают: купить сейчас или подождать."
        )
        await update.message.reply_text(
            help_text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
        )
        return

    elif text == "🔙 Назад":
        context.user_data["state"] = "main_menu"
        await update.message.reply_text("Главное меню:", reply_markup=MAIN_KEYBOARD)
        return

    # ────── ВЫБОР ГОРОДА ──────
    if current_state == "city_selection":
        if text in CITIES_MAPPING:
            save_user_setting(user.id, city_slug=CITIES_MAPPING[text])
            context.user_data["state"] = "main_menu"
            await update.message.reply_text(
                f"✅ Город изменён на: **{text}**",
                reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
            )
        return

    # ────── ВЫБОР ВРЕМЕНИ ──────
    if current_state == "time_selection":
        if text in ["07:00", "08:00", "09:00", "10:00", "11:00"]:
            save_user_setting(user.id, time_pref=text)
            context.user_data["state"] = "main_menu"
            await update.message.reply_text(
                f"✅ Время рассылки: **{text}**",
                reply_markup=MAIN_KEYBOARD, parse_mode="Markdown"
            )
        elif text == "❌ Отключить рассылку":
            save_user_setting(user.id, time_pref="off")
            context.user_data["state"] = "main_menu"
            await update.message.reply_text(
                "❌ Рассылка отключена.", reply_markup=MAIN_KEYBOARD
            )
        return

    # ────── КОНВЕРТАЦИЯ ──────
    if current_state == "direction_selection":
        if text == "🇧🇾 BYN → 💱 Иностранная":
            context.user_data["direction"] = "byn_to_foreign"
            context.user_data["state"]     = "currency_selection"
            await update.message.reply_text(
                "Выбери целевую валюту:", reply_markup=CURRENCY_KEYBOARD
            )
        elif text == "💱 Иностранная → 🇧🇾 BYN":
            context.user_data["direction"] = "foreign_to_byn"
            context.user_data["state"]     = "currency_selection"
            await update.message.reply_text(
                "Выбери продаваемую валюту:", reply_markup=CURRENCY_KEYBOARD
            )
        return

    if current_state == "currency_selection":
        if text in CURRENCY_MAPPING:
            context.user_data["selected_currency"] = CURRENCY_MAPPING[text]
            context.user_data["state"] = "awaiting_amount"
            unit_str = (
                "BYN" if context.user_data["direction"] == "byn_to_foreign"
                else CURRENCY_MAPPING[text]
            )
            await update.message.reply_text(
                f"Введите сумму в {unit_str}:", reply_markup=BACK_KEYBOARD
            )
        return

    if current_state == "awaiting_amount":
        try:
            amount            = float(text.replace(",", "."))
            selected_currency = context.user_data["selected_currency"]
            direction         = context.user_data["direction"]

            data = get_best_rates_summary(city_slug)
            if not data:
                await update.message.reply_text(
                    "❌ Сервер обмена недоступен.", reply_markup=MAIN_KEYBOARD
                )
                context.user_data["state"] = "main_menu"
                return

            best_info = data["best"][selected_currency]
            scale = 100.0 if selected_currency == "RUB" else 10.0 if selected_currency == "CNY" else 1.0

            if direction == "byn_to_foreign":
                rate      = best_info["best_sell"]
                bank_name = best_info["best_sell_bank"]
                if rate > 0:
                    result   = (amount / rate) * scale
                    res_text = (
                        f"✅ {amount:.2f} BYN ≈ **{result:.2f} {selected_currency}**\n"
                        f"🏆 Лучший курс в г. {city_name_ru}\n"
                        f"🏦 *{bank_name}* (продажа: `{rate:.4f}` за {int(scale)} ед.)\n"
                        f"{_cache_status(city_slug)}"
                    )
                    log_conversion(user_name, user_last_name, amount, result, "BYN", selected_currency)
                    log_to_console(user, user_name, user_last_name, amount, result, "BYN", selected_currency)
                else:
                    res_text = "❌ Нет доступных курсов."
            else:
                rate      = best_info["best_buy"]
                bank_name = best_info["best_buy_bank"]
                if rate > 0:
                    result   = (amount / scale) * rate
                    res_text = (
                        f"✅ {amount:.2f} {selected_currency} ≈ **{result:.2f} BYN**\n"
                        f"🏆 Лучший курс в г. {city_name_ru}\n"
                        f"🏦 *{bank_name}* (покупка: `{rate:.4f}` за {int(scale)} ед.)\n"
                        f"{_cache_status(city_slug)}"
                    )
                    log_conversion(user_name, user_last_name, amount, result, selected_currency, "BYN")
                    log_to_console(user, user_name, user_last_name, amount, result, selected_currency, "BYN")
                else:
                    res_text = "❌ Нет доступных курсов."

            await update.message.reply_text(
                res_text, reply_markup=CURRENCY_KEYBOARD, parse_mode="Markdown"
            )
            context.user_data["state"] = "currency_selection"

        except ValueError:
            await update.message.reply_text(
                "❌ Введите корректное число!", reply_markup=BACK_KEYBOARD
            )
        return

    await update.message.reply_text(
        "Используй кнопки меню:", reply_markup=MAIN_KEYBOARD
    )
