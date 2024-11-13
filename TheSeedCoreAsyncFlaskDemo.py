# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

import TheSeedCore as TSC

if TYPE_CHECKING:
    pass


class CustomAsyncFlask(TSC.AsyncFlask):

    def addRoute(self):
        @self.Application.route("/")
        def index():
            return "Hello! this is TheSeedCore AsyncFlask Demo."


if __name__ == "__main__":
    TSC.ConnectTheSeedCore()
    caf = CustomAsyncFlask("CustomAsyncFlask", "localhost", 5000)
    caf.start()
    TSC.LinkStart()
