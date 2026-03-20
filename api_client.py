# api_client.py
import requests


def get_currency_rate(currency="USD"):
    """
    Получение курса валюты от Беларусбанка
    currency: USD или RUB
    """
    try:
        url = "https://belarusbank.by/api/kursExchange"
        response = requests.get(url)
        print(f"✅ Статус ответа: {response.status_code}")

        if response.status_code == 200:
            print("✅ Сайт доступен!")
            data = response.json()
            bank = data[0]

            if currency == "USD":
                rate = float(bank["USD_out"])
            elif currency == "RUB":
                rate = float(bank["RUB_out"])
            else:
                raise ValueError(f"Неподдерживаемая валюта: {currency}")

            return rate
        else:
            print("❌ Сайт не доступен")
            return None

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def get_usd_rate():
    """Получение курса USD"""
    return get_currency_rate("USD")


def get_rub_rate():
    """Получение курса RUB"""
    return get_currency_rate("RUB")