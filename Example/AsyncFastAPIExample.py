# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

import TheSeedCore as TSC

if TYPE_CHECKING:
    pass

if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreProcessCount=0, CoreThreadCount=0)
    afa = TSC.AsyncFastAPI("TestAsyncFastAPI", "localhost", 5000)
    afa.start()
    TSC.LinkStart()
