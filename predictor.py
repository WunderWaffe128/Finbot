# predictor.py
import requests
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

NBRB_IDS = {"USD": 431, "EUR": 451, "RUB": 456, "CNY": 462}
SCALE = {"USD": 1, "EUR": 1, "RUB": 100, "CNY": 10}
CACHE_FILE = "forecast_base_cache.json"

TREND_LABELS = {
    "UP": "Уверенный рост 📈",
    "DOWN": "Снижение 📉",
    "STABLE": "Стабилен ➡️"
}


def _fetch_all_currencies_history(years: int = 3) -> dict | None:
    """
    Загружает историю котировок НБРБ порциями по 365 дней.
    Ограничено 3 годами, так как CNY (юань) появился в корзине только в 2022 году.
    """
    data_all_raw = {cur: {} for cur in NBRB_IDS}
    end_date = datetime.now()

    for i in range(years):
        chunk_end = end_date - timedelta(days=i * 365)
        chunk_start = chunk_end - timedelta(days=364)

        date_str = f"?startdate={chunk_start.strftime('%Y-%m-%d')}&enddate={chunk_end.strftime('%Y-%m-%d')}"

        for cur_name, cur_id in NBRB_IDS.items():
            url = f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}{date_str}"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    json_data = resp.json()
                    if json_data:
                        scale = float(SCALE[cur_name])
                        for item in json_data:
                            d = item["Date"][:10]
                            data_all_raw[cur_name][d] = float(item['Cur_OfficialRate']) / scale
                elif i == 0:
                    # Если упал самый первый (текущий) год — это реальная проблема с API
                    return None
            except Exception:
                if i == 0:
                    return None
        time.sleep(0.05)

    data_final = {}
    for cur_name in NBRB_IDS:
        sorted_dates = sorted(data_all_raw[cur_name].keys())
        if not sorted_dates:
            return None
        data_final[cur_name] = [data_all_raw[cur_name][d] for d in sorted_dates]

    if len(data_final) < len(NBRB_IDS):
        return None

    # Синхронизируем массивы по минимальной длине
    min_len = min(len(v) for v in data_final.values())
    if min_len < 30:
        return None

    for k in data_final:
        data_final[k] = data_final[k][-min_len:]

    return data_final


def _hurwitz_decision_engine(bank_rate: float, pred_week: float, pred_month: float, vol: float, is_buy: bool) -> tuple[
    str, str]:
    """Матричный движок Гурвица для принятия решений в условиях риска"""
    expected_future = (pred_week * 0.6) + (pred_month * 0.4)
    risk_premium = vol * 1.96
    market_states = [expected_future - risk_premium, expected_future, expected_future + risk_premium]
    gamma = 0.35

    if is_buy:
        utility_act = [state - bank_rate for state in market_states]
        utility_wait = [0.0, 0.0, 0.0]
        h_act = gamma * min(utility_act) + (1.0 - gamma) * max(utility_act)
        h_wait = gamma * min(utility_wait) + (1.0 - gamma) * max(utility_wait)

        if h_act > 0.005:
            return "🔥 РЕКОМЕНДУЕТСЯ", f"Критерий Гурвица ({h_act:.4f} > {h_wait:.4f}). Риск оправдан, покупка целесообразна."
        elif h_act < -0.005:
            return "⏳ ПОДОЖДАТЬ", f"Матрица рисков указывает на высокую неопределенность. Лучше отложить покупку."
        else:
            return "⚖️ НЕЙТРАЛЬНО", "Математическое ожидание исходов находится в точке равновесия рынка."

    else:
        utility_act = [bank_rate - state for state in market_states]
        utility_wait = [0.0, 0.0, 0.0]
        h_act = gamma * min(utility_act) + (1.0 - gamma) * max(utility_act)
        h_wait = gamma * min(utility_wait) + (1.0 - gamma) * max(utility_wait)

        if h_act > 0.005:
            return "💰 ВЫГОДНО", f"Критерий Гурвица ({h_act:.4f} > {h_wait:.4f}). Выгодно зафиксировать прибыль сейчас."
        elif h_act < -0.005:
            return "⏳ ПОДОЖДАТЬ", f"Потенциал долгосрочного роста перевешивает риски. Разумнее придержать валюту."
        else:
            return "⚖️ НЕЙТРАЛЬНО", "Решение находится в зоне рыночной эффективности, явных аномалий не обнаружено."


def predict_all(bank_rates: Optional[dict] = None) -> dict:
    """
    Главная точка расчета. Поддерживает суточное кэширование базовой ML-модели.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_results = None

    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                if cache_data.get("date") == today_str:
                    base_results = cache_data.get("results")
        except Exception:
            base_results = None

    if not base_results:
        base_results = {}
        history = _fetch_all_currencies_history(3)  # Запрашиваем стабильные 3 года чанками

        if not history:
            print("⚠️ [ML Engine] API НБРБ недоступно. Пытаемся поднять прошлый кэш...")
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        base_results = json.load(f).get("results", {})
                except Exception:
                    pass
            if not base_results:
                return {}
        else:
            LAG_DAYS = 5
            ALPHA_RIDGE = 0.25
            horizons = {"week": 7, "month": 30, "year": 365, "years5": 1825}
            max_steps = max(horizons.values())

            for cur in NBRB_IDS.keys():
                scale = SCALE[cur]
                seq = history[cur]
                current_in_units = seq[-1]
                hist_mean = float(np.mean(seq))
                vol_daily_unit = float(np.std(np.diff(seq)))

                X, Y = [], []
                for t in range(LAG_DAYS, len(seq) - 1):
                    row = [seq[t - i] for i in range(LAG_DAYS)]
                    row.append(1.0)
                    X.append(row)
                    Y.append(seq[t + 1])

                X = np.array(X)
                Y = np.array(Y)

                I = np.eye(X.shape[1])
                W = np.linalg.inv(X.T @ X + ALPHA_RIDGE * I) @ X.T @ Y

                current_lags = list(seq[-LAG_DAYS:])
                predictions_steps = []

                for step in range(1, max_steps + 1):
                    feat_row = current_lags[::-1] + [1.0]
                    pred_raw = float(np.dot(feat_row, W))
                    decay = 0.996 ** step
                    pred_final = pred_raw * decay + hist_mean * (1.0 - decay)

                    predictions_steps.append(pred_final)
                    current_lags.pop(0)
                    current_lags.append(pred_final)

                forecasts = {
                    "week": round(predictions_steps[horizons["week"] - 1] * scale, 4),
                    "month": round(predictions_steps[horizons["month"] - 1] * scale, 4),
                    "year": round(predictions_steps[horizons["year"] - 1] * scale, 4),
                    "years5": round(predictions_steps[horizons["years5"] - 1] * scale, 4)
                }

                if forecasts["week"] / scale > current_in_units + 0.001:
                    trend = "UP"
                elif forecasts["week"] / scale < current_in_units - 0.001:
                    trend = "DOWN"
                else:
                    trend = "STABLE"

                icon = "📈" if trend == "UP" else ("📉" if trend == "DOWN" else "➡️")

                base_results[cur] = {
                    "current_nbrb": round(current_in_units * scale, 4),
                    "scale": scale,
                    "forecasts": forecasts,
                    "volatility_daily": round(vol_daily_unit * scale, 5),
                    "trend": trend,
                    "trend_label": TREND_LABELS[trend],
                    "trend_icon": icon,
                    "recent_vol_unit": float(np.std(np.diff(seq[-30:])))
                }

            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"date": today_str, "results": base_results}, f, ensure_ascii=False, indent=2)
                print(f"💾 [ML Engine] Актуальный ИИ-прогноз успешно закэширован на дату {today_str}")
            except Exception as e:
                print(f"⚠️ Ошибка сохранения кэша прогнозов: {e}")

    final_results = {}
    for cur, data in base_results.items():
        final_results[cur] = dict(data)
        rec = {}

        if bank_rates and cur in bank_rates:
            b = bank_rates[cur]
            scale = data["scale"]
            buy_rate = b.get("best_buy", 0) / scale
            sell_rate = b.get("best_sell", 0) / scale

            if buy_rate > 0 and sell_rate > 0:
                recent_vol = data.get("recent_vol_unit", data["volatility_daily"] / scale)
                forecasts = data["forecasts"]

                buy_signal = _hurwitz_decision_engine(sell_rate, forecasts["week"] / scale, forecasts["month"] / scale,
                                                      recent_vol, is_buy=True)
                sell_signal = _hurwitz_decision_engine(buy_rate, forecasts["week"] / scale, forecasts["month"] / scale,
                                                       recent_vol, is_buy=False)

                rec = {"buy": buy_signal, "sell": sell_signal}

        final_results[cur]["recommendation"] = rec
        if "recent_vol_unit" in final_results[cur]:
            del final_results[cur]["recent_vol_unit"]

    return final_results