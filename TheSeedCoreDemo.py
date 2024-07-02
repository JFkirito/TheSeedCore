# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

from TheSeedCore import *

if TYPE_CHECKING:
    pass


class Test(TheSeed):
    def __init__(self):
        ...


if __name__ == "__main__":
    linkStart(Test, debug_mode=True)
