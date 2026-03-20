import requests


def get_currency_rate(currency="USD"):
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
            elif currency == "EUR":
                rate = float(bank["EUR_out"])
            elif currency == "CNY":
                rate = float(bank["CNY_out"])
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
    return get_currency_rate("USD")

def get_rub_rate():
    return get_currency_rate("RUB")

def get_euro_rate():
    return get_currency_rate("EUR")

def get_cny_rate():
    return get_currency_rate("CNY")



