"""Gebündelte Statusmeldungen im Terminal: gleiche Meldungen werden gezählt statt wiederholt."""
from __future__ import annotations

import os
from time import time as now
from typing import Literal, Optional

_REFRESH_SECONDS = 0.5


class Console:
    def __init__(self) -> None:
        self.messages: dict[str, tuple[str, int, float]] = {}
        self.__lastDisplayed: float = 0

    def log(self, _case: Literal[0, 1, 2], symbol: str, problem: str, reason: str = "", detailsSymbol: str = "",
            details: str = "", obj: Optional[object] = None) -> None:
        """Merkt sich eine Meldung. _case wählt die Form: 0 mit Details, 1 mit Grund, 2 nur Problem."""
        key = f"{problem}{reason}"
        if _case == 0:
            text = f"{symbol} |{problem} <- {reason} -  | {detailsSymbol}|{details}"
        elif _case == 1:
            text = f"{symbol} |{problem} <- {reason}"
        else:
            text = f"{symbol} |{problem}"
        count = self.messages.get(key, ("", 0, 0.0))[1] + 1
        self.messages[key] = (text, count, now())
        self.display()

    def display(self) -> None:
        """Zeichnet die Meldungen neu, höchstens alle 0,5 Sekunden."""
        if now() - self.__lastDisplayed < _REFRESH_SECONDS:
            return
        self.__lastDisplayed = now()
        os.system("cls" if os.name == "nt" else "clear")
        for text, count, _ in sorted(self.messages.values(), key=lambda entry: entry[2]):
            print(f"{text} (x{count})" if count > 1 else text)
