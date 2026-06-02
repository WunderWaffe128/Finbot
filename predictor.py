# predictor.py
# Умный предсказатель курса валют для Беларуси.
# Использует официальный API НБРБ (365 дней истории).
# Методы: линейная регрессия + экспоненциальное сглаживание (EWM).
# Горизонт: неделя / месяц / год / 5 лет.
# Рекомендации к покупке и продаже строятся честно — по соотношению
# текущего банковского курса к спрогнозированному.

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


# ID валют в системе НБРБ
NBRB_IDS = {
    "USD": 431,
    "EUR": 451,
    "RUB": 456,
    "CNY": 462,
}

# Сколько единиц иностранной валюты соответствует одной котировке НБРБ
SCALE = {"USD": 1, "EUR": 1, "RUB": 100, "CNY": 10}


def _fetch_nbrb_history(cur_id: int, days: int = 365) -> list[float] | None:
    """Загружает исторические курсы НБРБ за `days` дней. Возвращает список float или None."""
    end = datetime.now()
    start = end - timedelta(days=days)
    url = (
        f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}"
        f"?startdate={start.strftime('%Y-%m-%d')}&enddate={end.strftime('%Y-%m-%d')}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) >= 30:
                return [item["Cur_OfficialRate"] for item in data]
    except Exception as e:
        print(f"❌ НБРБ история: {e}")
    return None


def _linear_regression_forecast(rates: list[float], horizon_days: int) -> float:
    """Линейная регрессия по всему ряду → прогноз на `horizon_days` вперёд."""
    x = np.arange(len(rates), dtype=float)
    y = np.array(rates, dtype=float)
    # МНК вручную (быстрее sklearn для коротких рядов)
    x_mean, y_mean = x.mean(), y.mean()
    b = np.dot(x - x_mean, y - y_mean) / np.dot(x - x_mean, x - x_mean)
    a = y_mean - b * x_mean
    return float(a + b * (len(rates) - 1 + horizon_days))


def _ewm_forecast(rates: list[float], horizon_days: int, alpha: float = 0.15) -> float:
    """
    Экспоненциальное взвешенное среднее (EWM).
    Чем меньше alpha — тем больше вес далёкой истории (сглаживание тренда).
    Подходит для долгосрочных прогнозов.
    """
    ewm = rates[0]
    for r in rates[1:]:
        ewm = alpha * r + (1 - alpha) * ewm
    # Проецируем последний тренд вперёд
    last_trend = rates[-1] - rates[-2] if len(rates) > 1 else 0
    return float(ewm + last_trend * horizon_days * alpha)


def _volatility(rates: list[float]) -> float:
    """Стандартное отклонение дневных изменений (мера риска)."""
    changes = [rates[i] - rates[i - 1] for i in range(1, len(rates))]
    return float(np.std(changes))


def _trend_strength(rates: list[float]) -> str:
    """
    Оценивает силу тренда за последние 30 дней.
    Возвращает: STRONG_UP / WEAK_UP / FLAT / WEAK_DOWN / STRONG_DOWN
    """
    recent = rates[-30:]
    total_change = recent[-1] - recent[0]
    vol = _volatility(recent) or 0.001
    ratio = total_change / vol  # отношение сигнала к шуму

    if ratio > 2.0:
        return "STRONG_UP"
    elif ratio > 0.5:
        return "WEAK_UP"
    elif ratio < -2.0:
        return "STRONG_DOWN"
    elif ratio < -0.5:
        return "WEAK_DOWN"
    else:
        return "FLAT"


def _recommendation(
    current_bank_buy: float,   # банк покупает у вас (вы продаёте)
    current_bank_sell: float,  # банк продаёт вам (вы покупаете)
    forecast_week: float,
    forecast_month: float,
    trend: str,
) -> dict:
    """
    Генерирует торговую рекомендацию.
    - Если курс прогнозируется ВЫШЕ текущего → выгоднее подождать с продажей.
    - Если курс прогнозируется НИЖЕ → выгоднее продать сейчас.
    """
    rec = {}

    # ПОКУПКА валюты (тратим BYN)
    if forecast_week > current_bank_sell * 1.005:
        rec["buy"] = ("⚡ ПОКУПАЙ СЕЙЧАС", "Прогноз роста. Сегодня дешевле, чем через неделю.")
    elif forecast_week < current_bank_sell * 0.995:
        rec["buy"] = ("⏳ ПОДОЖДИ", "Прогноз снижения. Через неделю может быть дешевле.")
    else:
        rec["buy"] = ("😐 НЕЙТРАЛЬНО", "Изменение незначительное. Покупай по необходимости.")

    # ПРОДАЖА валюты (получаем BYN)
    if forecast_week > current_bank_buy * 1.005:
        rec["sell"] = ("⏳ ПОДОЖДИ", "Прогноз роста. Через неделю сдашь дороже.")
    elif forecast_week < current_bank_buy * 0.995:
        rec["sell"] = ("⚡ ПРОДАВАЙ СЕЙЧАС", "Прогноз снижения. Сегодня сдашь выгоднее.")
    else:
        rec["sell"] = ("😐 НЕЙТРАЛЬНО", "Изменение незначительное. Продавай по необходимости.")

    return rec


TREND_LABELS = {
    "STRONG_UP": "📈 Сильный рост",
    "WEAK_UP": "↗️ Слабый рост",
    "FLAT": "➡️ Боковик",
    "WEAK_DOWN": "↘️ Слабое снижение",
    "STRONG_DOWN": "📉 Сильное снижение",
}


def predict_all(bank_rates: dict | None = None) -> dict:
    """
    Главная функция. Возвращает прогноз для всех 4 валют.

    bank_rates — словарь из get_best_rates_summary()["best"]:
        {"USD": {"best_buy": ..., "best_sell": ..., ...}, ...}
    """
    results = {}

    for cur, cur_id in NBRB_IDS.items():
        scale = SCALE[cur]

        rates = _fetch_nbrb_history(cur_id, days=365)
        if not rates or len(rates) < 30:
            continue

        current = rates[-1]
        vol = _volatility(rates)
        trend = _trend_strength(rates)

        # Прогнозы (линейная регрессия + EWM → усредняем)
        horizons = {
            "week": 7,
            "month": 30,
            "year": 365,
            "years5": 365 * 5,
        }
        forecasts = {}
        for label, h in horizons.items():
            lr = _linear_regression_forecast(rates, h)
            ewm = _ewm_forecast(rates, h)
            # Чем дальше горизонт — тем больше вес EWM (он устойчивее к выбросам)
            weight_ewm = min(0.3 + h / 1000, 0.7)
            blended = lr * (1 - weight_ewm) + ewm * weight_ewm
            forecasts[label] = round(blended, 4)

        # Направление тренда иконкой
        icon = "📈" if "UP" in trend else ("📉" if "DOWN" in trend else "➡️")

        # Рекомендация — строится по банковским курсам (если переданы)
        rec = {}
        if bank_rates and cur in bank_rates:
            b = bank_rates[cur]
            buy_rate = b.get("best_buy", 0) / scale  # в единицах НБРБ
            sell_rate = b.get("best_sell", 0) / scale
            if buy_rate > 0 and sell_rate > 0:
                rec = _recommendation(
                    buy_rate, sell_rate,
                    forecasts["week"], forecasts["month"],
                    trend
                )

        results[cur] = {
            "current_nbrb": round(current, 4),      # официальный курс НБРБ сегодня
            "scale": scale,                          # единиц иностранной за 1 котировку
            "forecasts": forecasts,                  # {"week": ..., "month": ..., ...}
            "volatility_daily": round(vol, 5),       # ср. дневное колебание BYN
            "trend": trend,
            "trend_label": TREND_LABELS[trend],
            "trend_icon": icon,
            "recommendation": rec,                   # {"buy": (label, desc), "sell": (label, desc)}
            "history_days": len(rates),
        }

    return results
