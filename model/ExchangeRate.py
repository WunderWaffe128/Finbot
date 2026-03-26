import decimal
from datetime import datetime
from Currency import Currency


class ExchangeRate:
    __foreignCurrency: Currency
    __belarusianCurrency: Currency
    __rate: decimal  # сколько белорусских рублей за единицу иностранной валюты
    __timestamp: datetime

    def __init__(self, foreignCurrency: Currency, belarusianCurrency: Currency, rate: float, timestamp: datetime):
        self.__foreignCurrency = foreignCurrency
        self.__belarusianCurrency = belarusianCurrency
        self.__rate = rate
        self.__timestamp = timestamp

    def getForeignCurrency(self) -> Currency:
        return self.__foreignCurrency

    def getForeignCurrencyCode(self) -> str:
        return self.__foreignCurrency.getCodeString()

    def getBelarusianCurrency(self) -> Currency:
        return self.__belarusianCurrency

    def getBelarusianCurrencyCode(self) -> str:
        return self.__belarusianCurrency.getCodeString()

    def getRate(self) -> float:
        return self.__rate

    def getTimestamp(self) -> datetime:
        return self.__timestamp

    def toString(self) -> str:
        return (f"ExchangeRate{{foreign={self.__foreignCurrency.getCodeString()}, "
                f"byn={self.__rate}, time={self.__timestamp}}}")