from CurrencyEnum import CurrencyEnum


class Currency:
    __code: CurrencyEnum
    __name: str
    __symbol: str

    def __init__(self, code: CurrencyEnum, name: str, symbol: str):
        self.__code = code
        self.__name = name
        self.__symbol = symbol

    def getCode(self) -> CurrencyEnum:
        return self.__code

    def getCodeString(self) -> str:
        return self.__code.getCode()

    def getName(self) -> str:
        return self.__name

    def getSymbol(self) -> str:
        return self.__symbol

    def toString(self) -> str:
        return f"Currency{{code={self.__code.getCode()}, name={self.__name}, symbol={self.__symbol}}}"