# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import multiprocessing
import os
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING, Optional

from . import DEVELOPMENT_ENV
from ._Common import TextColor

if TYPE_CHECKING:
    pass

__all__ = [
    "consoleLogger",
    "TheSeedCoreLogger"
]

_LOGGER_INSTANCE = {}


def consoleLogger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    if DEVELOPMENT_ENV:
        handler.setLevel(level)
    else:
        handler.setLevel(max(logging.DEBUG, logging.WARNING))
    formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class _FileFormatter(logging.Formatter):
    def format(self, record) -> str:
        message = super().format(record)
        return message


class _ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: TextColor.BLUE_BOLD.value,
        logging.INFO: TextColor.GREEN_BOLD.value,
        logging.WARNING: TextColor.YELLOW_BOLD.value,
        logging.ERROR: TextColor.RED_BOLD.value,
    }

    def format(self, record) -> str:
        message = super().format(record)
        color = self.COLORS.get(record.levelno, TextColor.RESET.value)
        return f"{color}{message}{TextColor.RESET.value}"


class TheSeedCoreLogger(logging.Logger):
    def __new__(cls, name: str, path: str, backup_count: int = 7, level: int = logging.DEBUG, debug: bool = DEVELOPMENT_ENV):
        global _LOGGER_INSTANCE
        if multiprocessing.current_process() != "MainProcess":
            return consoleLogger(name, level)
        if name not in _LOGGER_INSTANCE:
            instance: TheSeedCoreLogger = super().__new__(cls)
            _LOGGER_INSTANCE[name] = instance
        return _LOGGER_INSTANCE[name]

    def __init__(self, name: str, path: str, backup_days: int = 7, level: int = logging.DEBUG, debug: bool = DEVELOPMENT_ENV):
        super().__init__(name, level)
        self._Debug = debug
        self._FoldersPath: str = path
        self._FilePath: str = os.path.join(self._FoldersPath, f"{name}.log")
        self._FileProcessor: TimedRotatingFileHandler = TimedRotatingFileHandler(self._FilePath, when="midnight", interval=1, backupCount=backup_days, encoding="utf-8")
        self._FileFormatter: _FileFormatter = _FileFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self._FileProcessor.suffix = "%Y-%m-%d"
        self._FileProcessor.setLevel(level if debug else max(level, logging.WARNING))
        self._FileProcessor.setFormatter(self._FileFormatter)
        self.addHandler(self._FileProcessor)

        self._StreamProcessor: logging.StreamHandler = logging.StreamHandler()
        self._StreamFormatter: _ColoredFormatter = _ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self._StreamProcessor.setLevel(logging.DEBUG if debug else max(level, logging.WARNING))
        self._StreamProcessor.setFormatter(self._StreamFormatter)
        self.addHandler(self._StreamProcessor)

    @property
    def DebugMode(self) -> bool:
        return self._Debug

    @DebugMode.setter
    def DebugMode(self, debug: Optional[bool]) -> None:
        if self._Debug != debug:
            self._Debug: bool = debug
            new_level: int = logging.DEBUG if self._Debug else max(self.level, logging.WARNING)
            self._FileProcessor.setLevel(new_level)
            self._StreamProcessor.setLevel(new_level)
