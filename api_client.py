# api_client.py
import requests


def get_currency_rate(currency_code="USD"):
    """
    Получение курса валюты от Беларусбанка
    currency_code: USD, EUR, RUB, CNY
    Возвращает: сколько BYN за 1 единицу иностранной валюты
    """
    try:
        url = "https://belarusbank.by/api/kursExchange"
        response = requests.get(url, timeout=10)
        print(f"✅ Статус ответа для {currency_code}: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            bank = data[0]

            currency_fields = {
                "USD": "USD_out",
                "EUR": "EUR_out",
                "RUB": "RUB_out",
                "CNY": "CNY_out"
            }

            if currency_code in currency_fields:
                field_name = currency_fields[currency_code]
                rate = float(bank[field_name])
                return rate
            else:
                print(f"❌ Неподдерживаемая валюта: {currency_code}")
                return None
        else:
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def get_all_rates():
    """Получение всех курсов валют"""
    try:
        url = "https://belarusbank.by/api/kursExchange"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            bank = data[0]

            rates = {
                "USD": float(bank["USD_out"]),
                "EUR": float(bank["EUR_out"]),
                "RUB": float(bank["RUB_out"]),
                "CNY": float(bank["CNY_out"])
            }
            return rates
        else:
            return None
    except Exception as e:
        print(f"❌ Ошибка получения всех курсов: {e}")
        return None