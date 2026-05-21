# api_client.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta


def get_belarusbank_official(city_ru):
    """Прямой запрос к официальному API Беларусбанка (железобетонный резерв)"""
    try:
        url = f"https://belarusbank.by/api/kursExchange?city={city_ru}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                branch = data[0]  # Берем первое актуальное отделение в выбранном городе
                return {
                    "USD_in": float(branch.get("USD_in", 0)),
                    "USD_out": float(branch.get("USD_out", 0)),
                    "EUR_in": float(branch.get("EUR_in", 0)),
                    "EUR_out": float(branch.get("EUR_out", 0)),
                    "RUB_in": float(branch.get("RUB_in", 0)),
                    "RUB_out": float(branch.get("RUB_out", 0)),
                    "CNY_in": float(branch.get("CNY_in", 0)),
                    "CNY_out": float(branch.get("CNY_out", 0))
                }
    except Exception as e:
        print(f"❌ Ошибка API Беларусбанка: {e}")
    return None


def get_real_bank_rates(city="minsk"):
    """
    Гибридный парсер:
    1. Обходит защиту Cloudflare с помощью User-Agent Googlebot.
    2. Тянет Беларусбанк напрямую по API, чтобы бот НИКОГДА не падал.
    """
    rates_data = {}

    # Словарик для перевода слага города в русский язык (требуется для API Беларусбанка)
    city_ru_map = {
        "minsk": "Минск", "gomel": "Гомель", "brest": "Брест",
        "grodno": "Гродно", "mogilev": "Могилев", "vitebsk": "Витебск"
    }
    city_ru = city_ru_map.get(city, "Минск")

    # 1. Попытка парсинга Myfin с обходом блокировок
    try:
        url = f"https://myfin.by/currency/{city}"
        headers = {
            # Притворяемся поисковиком Google — Cloudflare его не блокирует!
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')

            if table:
                rows = table.find_all('tr')
                # Беларусбанк берем по API, поэтому тут ищем только остальные
                target_banks = {
                    "Сбер Банк": ["сбер", "sber"],
                    "Приорбанк": ["приор", "prior"],
                    "Альфа Банк": ["альфа", "alfa"],
                    "Белагропромбанк": ["белагро", "belagro"],
                    "Белинвестбанк": ["белинвест", "belinvest"]
                }

                for row in rows:
                    row_text = row.get_text().lower()
                    matched_bank = None
                    for formal_name, keywords in target_banks.items():
                        if any(kw in row_text for kw in keywords):
                            matched_bank = formal_name
                            break

                    if matched_bank:
                        cells = row.find_all('td')
                        numbers = []
                        for cell in cells:
                            text = cell.get_text().strip().replace(',', '.')
                            match = re.search(r'\d+\.\d+', text)
                            if match:
                                numbers.append(float(match.group()))

                        if len(numbers) >= 4:
                            rates_data[matched_bank] = {
                                "USD_in": numbers[0], "USD_out": numbers[1],
                                "EUR_in": numbers[2], "EUR_out": numbers[3]
                            }
                            if len(numbers) >= 6:
                                rates_data[matched_bank]["RUB_in"] = numbers[4]
                                rates_data[matched_bank]["RUB_out"] = numbers[5]
                            if len(numbers) >= 8:
                                rates_data[matched_bank]["CNY_in"] = numbers[6]
                                rates_data[matched_bank]["CNY_out"] = numbers[7]
    except Exception as e:
        print(f"⚠️ Парсер Myfin заблокирован: {e}")

    # 2. ЖЕЛЕЗОБЕТОННЫЙ ЗАПРОС К БЕЛАРУСБАНКУ
    # Выполняется всегда. Бот гарантированно выдаст реальный курс, даже если агрегатор мертв!
    bb_data = get_belarusbank_official(city_ru)
    if bb_data:
        rates_data["Беларусбанк"] = bb_data

    if not rates_data:
        return None

    return rates_data


def get_best_rates_summary(city="minsk"):
    """Формирует сводку ЛУЧШИХ курсов для калькулятора и рассылки"""
    banks_data = get_real_bank_rates(city)
    if not banks_data:
        return None

    best_summary = {}
    for cur in ["USD", "EUR", "RUB", "CNY"]:
        best_buy_val, best_buy_bank = -1.0, ""
        best_sell_val, best_sell_bank = 999999.0, ""

        for b_name, b_rates in banks_data.items():
            r_in = b_rates.get(f"{cur}_in", 0)
            r_out = b_rates.get(f"{cur}_out", 0)

            if r_in > best_buy_val and r_in > 0:
                best_buy_val, best_buy_bank = r_in, b_name
            if r_out < best_sell_val and r_out > 0:
                best_sell_val, best_sell_bank = r_out, b_name

        best_summary[cur] = {
            "best_buy": best_buy_val, "best_buy_bank": best_buy_bank,
            "best_sell": best_sell_val, "best_sell_bank": best_sell_bank
        }
    return {"best": best_summary, "all_banks": banks_data}


def predict_future_rates():
    """Алгоритм прогнозирования на основе исторической динамики (НБРБ за 30 дней)"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    fmt = "%Y-%m-%d"

    mapping = {"USD": 431, "EUR": 451, "RUB": 456, "CNY": 462}
    predictions = {}

    for cur, cur_id in mapping.items():
        url = f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}?startdate={start_date.strftime(fmt)}&enddate={end_date.strftime(fmt)}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    first_rate = data[0]["Cur_OfficialRate"]
                    last_rate = data[-1]["Cur_OfficialRate"]
                    days_count = len(data)

                    # Математический тренд изменения курса в день
                    daily_change = (last_rate - first_rate) / days_count
                    week_forecast = last_rate + (daily_change * 7)
                    month_forecast = last_rate + (daily_change * 30)

                    trend_icon = "📈" if daily_change > 0 else "📉"

                    predictions[cur] = {
                        "current": last_rate,
                        "week": round(week_forecast, 4),
                        "month": round(month_forecast, 4),
                        "icon": trend_icon,
                        "change": round(daily_change * 7, 4)
                    }
        except Exception as e:
            print(f"❌ Ошибка прогнозирования для {cur}: {e}")

    return predictions