from enum import Enum
from typing import Optional


class CurrencyEnum(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    CNY = "CNY"
    BYN = "BYN"

    def getCode(self) -> str:
        return self.value

    @staticmethod
    def fromString(code: str) -> Optional['CurrencyEnum']:
        for currencyCode in CurrencyEnum:
            if currencyCode.value == code:
                return currencyCode
        return None

    def toString(self) -> str:
        return self.value

    def isBelarusian(self) -> bool:
        return self == CurrencyEnum.BYN