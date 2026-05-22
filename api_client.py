# api_client.py
# Все публичные функции сначала читают кэш.
# Реальный HTTP-запрос делается только при обновлении по расписанию
# (scheduler вызывает refresh_all_cities_cache()) или при первом старте.

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from rate_cache import get_cache, save_cache, get_cache_age_minutes

# ──────────────────────────────────────────────
# ВНУТРЕННИЕ ФУНКЦИИ — чистый парсинг/запрос
# ──────────────────────────────────────────────

def _get_belarusbank_official(city_ru: str) -> dict | None:
    """Прямой запрос к официальному API Беларусбанка."""
    try:
        url = f"https://belarusbank.by/api/kursExchange?city={city_ru}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                branch = data[0]
                return {
                    "USD_in":  float(branch.get("USD_in", 0)),
                    "USD_out": float(branch.get("USD_out", 0)),
                    "EUR_in":  float(branch.get("EUR_in", 0)),
                    "EUR_out": float(branch.get("EUR_out", 0)),
                    "RUB_in":  float(branch.get("RUB_in", 0)),
                    "RUB_out": float(branch.get("RUB_out", 0)),
                    "CNY_in":  float(branch.get("CNY_in", 0)),
                    "CNY_out": float(branch.get("CNY_out", 0)),
                }
    except Exception as e:
        print(f"❌ Беларусбанк API: {e}")
    return None


CITY_RU_MAP = {
    "minsk":   "Минск",
    "gomel":   "Гомель",
    "brest":   "Брест",
    "grodno":  "Гродно",
    "mogilev": "Могилев",
    "vitebsk": "Витебск",
}


def _fetch_live_bank_rates(city: str = "minsk") -> dict | None:
    """
    Реальный HTTP-запрос к источникам данных.
    Возвращает словарь {bank_name: {USD_in, USD_out, EUR_in, ...}}.
    """
    rates_data = {}
    city_ru = CITY_RU_MAP.get(city, "Минск")

    # 1. Парсим Myfin (агрегатор)
    try:
        url = f"https://myfin.by/currency/{city}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if table:
                target_banks = {
                    "Сбер Банк":        ["сбер", "sber"],
                    "Приорбанк":        ["приор", "prior"],
                    "Альфа Банк":       ["альфа", "alfa"],
                    "Белагропромбанк":  ["белагро", "belagro"],
                    "Белинвестбанк":    ["белинвест", "belinvest"],
                    "БНБ-Банк":         ["бнб", "bnb"],
                    "МТБанк":           ["мтб", "mtb", "мт банк"],
                }
                for row in table.find_all("tr"):
                    row_text = row.get_text().lower()
                    matched = None
                    for name, kws in target_banks.items():
                        if any(kw in row_text for kw in kws):
                            matched = name
                            break
                    if not matched:
                        continue
                    numbers = []
                    for cell in row.find_all("td"):
                        t = cell.get_text().strip().replace(",", ".")
                        m = re.search(r"\d+\.\d+", t)
                        if m:
                            numbers.append(float(m.group()))
                    if len(numbers) >= 4:
                        rates_data[matched] = {
                            "USD_in": numbers[0], "USD_out": numbers[1],
                            "EUR_in": numbers[2], "EUR_out": numbers[3],
                        }
                        if len(numbers) >= 6:
                            rates_data[matched]["RUB_in"]  = numbers[4]
                            rates_data[matched]["RUB_out"] = numbers[5]
                        if len(numbers) >= 8:
                            rates_data[matched]["CNY_in"]  = numbers[6]
                            rates_data[matched]["CNY_out"] = numbers[7]
    except Exception as e:
        print(f"⚠️ Myfin парсер: {e}")

    # 2. Беларусбанк — всегда напрямую по API (надёжнее любого парсера)
    bb = _get_belarusbank_official(city_ru)
    if bb:
        rates_data["Беларусбанк"] = bb

    return rates_data if rates_data else None


# ──────────────────────────────────────────────
# ПУБЛИЧНЫЕ ФУНКЦИИ (читают кэш, не HTTP!)
# ──────────────────────────────────────────────

def get_real_bank_rates(city: str = "minsk") -> dict | None:
    """
    Возвращает курсы банков для города.
    Данные берутся из кэша (обновляется планировщиком 8 раз в сутки).
    При первом запросе, если кэша нет — делает живой запрос и сохраняет.
    """
    cached = get_cache(city)
    if cached:
        return cached["data"].get("all_banks")

    # Кэша нет — первый старт, грузим вживую
    live = _fetch_live_bank_rates(city)
    if live:
        summary = _build_summary(live)
        save_cache(city, summary)
        return live
    return None


def get_best_rates_summary(city: str = "minsk") -> dict | None:
    """
    Возвращает {best: {...}, all_banks: {...}} для города из кэша.
    При отсутствии кэша — живой запрос.
    """
    cached = get_cache(city)
    if cached:
        return cached["data"]

    live = _fetch_live_bank_rates(city)
    if live:
        summary = _build_summary(live)
        save_cache(city, summary)
        return summary
    return None


def _build_summary(banks_data: dict) -> dict:
    """Строит словарь лучших курсов из полных данных банков."""
    best = {}
    for cur in ["USD", "EUR", "RUB", "CNY"]:
        best_buy_val, best_buy_bank = -1.0, ""
        best_sell_val, best_sell_bank = 999999.0, ""
        for b_name, b_rates in banks_data.items():
            r_in  = b_rates.get(f"{cur}_in",  0)
            r_out = b_rates.get(f"{cur}_out", 0)
            if r_in  > best_buy_val  and r_in  > 0:
                best_buy_val,  best_buy_bank  = r_in,  b_name
            if r_out < best_sell_val and r_out > 0:
                best_sell_val, best_sell_bank = r_out, b_name
        best[cur] = {
            "best_buy":       best_buy_val,
            "best_buy_bank":  best_buy_bank,
            "best_sell":      best_sell_val,
            "best_sell_bank": best_sell_bank,
        }
    return {"best": best, "all_banks": banks_data}


# ──────────────────────────────────────────────
# ФУНКЦИЯ ДЛЯ ПЛАНИРОВЩИКА
# ──────────────────────────────────────────────

ALL_CITIES = ["minsk", "gomel", "brest", "grodno", "mogilev", "vitebsk"]


def refresh_all_cities_cache():
    """
    Делает живые запросы для всех городов и обновляет кэш.
    Вызывается планировщиком 8 раз в сутки.
    """
    updated = []
    failed  = []
    for city in ALL_CITIES:
        try:
            live = _fetch_live_bank_rates(city)
            if live:
                summary = _build_summary(live)
                save_cache(city, summary)
                updated.append(city)
            else:
                failed.append(city)
        except Exception as e:
            print(f"❌ Обновление кэша [{city}]: {e}")
            failed.append(city)

    now = datetime.now().strftime("%H:%M:%S")
    print(f"✅ [{now}] Кэш обновлён: {updated}  |  Ошибки: {failed}")
    return updated, failed


# ──────────────────────────────────────────────
# ПРОГНОЗ (оставлен для совместимости с handlers.py)
# Реальное предсказание теперь в predictor.py
# ──────────────────────────────────────────────

def predict_future_rates():
    """
    Устаревший метод. Сохранён для совместимости.
    Используй predictor.predict_all() для полноценного прогноза.
    """
    from predictor import predict_all
    return predict_all()
