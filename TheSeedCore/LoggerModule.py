# -*- coding: utf-8 -*-
"""
TheSeedCore Logging Module

This module provides a comprehensive logging system for TheSeedCore ecosystem, including color-coded console output and non-colored file logging.

Classes:
    - TheSeedCoreLogger:
        A custom logger that supports color-coded console logging and file logging with timed rotation. It allows setting log levels and debug modes dynamically.

    - _ColorFormatter:
        A nested class within TheSeedCoreLogger that handles color formatting for console logs based on log level.

    - _FileFormatter:
        A nested class within TheSeedCoreLogger for formatting log messages written to files, without color codes.

Functions:
    - setDebugMode(name: str, debug: bool):
        Enables or disables debug mode for a specific logger by name.

    - setAllDebugMode(debug: bool):
        Sets the debug mode for all registered loggers.

Features:
    - Color-Coded Console Logging: Provides visual differentiation of log levels using colors for console output.
    - Timed Rotating File Logging: Log messages are written to files with daily rotation and configurable backup counts.
    - Dynamic Debug Mode: Allows toggling debug mode for individual loggers or all loggers at runtime.
    - Centralized Logger Management: All loggers are stored in a centralized dictionary for easy management.

This module is designed to offer robust logging capabilities with ease of use and customization, aiding in monitoring and debugging TheSeedCore applications.
"""


from __future__ import annotations

__all__ = [
    "TheSeedCoreLogger",
    "setDebugMode",
    "setAllDebugMode"
]

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    from .ConfigModule import LoggerConfig

_LOGGERS = {}


class TheSeedCoreLogger(logging.Logger):
    """
    TheSeedCore日志记录器。

    提供具有颜色格式化功能的控制台输出和不带颜色格式化的文件记录功能。
    """

    class _ColorFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: Fore.BLUE,
            logging.INFO: Fore.GREEN,
            logging.WARNING: Fore.YELLOW,
            logging.ERROR: Fore.RED,
            logging.CRITICAL: Fore.MAGENTA
        }

        def format(self, record):
            color = self.COLORS.get(record.levelno, Fore.RESET)
            message = super().format(record)
            return f"{color}{Style.BRIGHT}{message}{Style.RESET_ALL}"

    class _FileFormatter(logging.Formatter):
        """
        文件日志格式器，不包含颜色代码。
        """

        def format(self, record):
            message = super().format(record)
            return message

    def __new__(cls, Config: LoggerConfig):
        if Config.Name in _LOGGERS:
            return _LOGGERS[Config.Name]
        else:
            instance = super(TheSeedCoreLogger, cls).__new__(cls)
            _LOGGERS[Config.Name] = instance
            return instance

    def __init__(self, Config: LoggerConfig):
        super().__init__(Config.Name, Config.Level)
        self._LoggerPath = Config.Path
        self._Debug = Config.Debug

        if not os.path.exists(self._LoggerPath):
            os.makedirs(self._LoggerPath)

        self._LogFile = os.path.join(self._LoggerPath, f"{Config.Name}.log")
        self._FileProcessor = TimedRotatingFileHandler(self._LogFile, when="midnight", interval=1, backupCount=Config.BackupCount, encoding="utf-8")
        self._FileProcessor.suffix = "%Y-%m-%d"
        self._FileProcessor.setLevel(Config.Level if Config.Debug else max(Config.Level, logging.WARNING))
        self._FileFormatter = self._FileFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self._FileProcessor.setFormatter(self._FileFormatter)
        self.addHandler(self._FileProcessor)

        self._StreamProcessor = logging.StreamHandler()
        self._ConsoleFormatter = self._ColorFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self._StreamProcessor.setLevel(logging.DEBUG if Config.Debug else max(Config.Level, logging.WARNING))
        self._StreamProcessor.setFormatter(self._ConsoleFormatter)
        self.addHandler(self._StreamProcessor)

    @property
    def DebugMode(self):
        return self._Debug

    @DebugMode.setter
    def DebugMode(self, value):
        if self._Debug != value:
            self._Debug = value
            new_level = logging.DEBUG if self._Debug else max(self.level, logging.WARNING)
            self._FileProcessor.setLevel(new_level)
            self._StreamProcessor.setLevel(new_level)


def setDebugMode(name: str, debug: bool):
    """
    设置日志记录器的调试模式。

    参数：
        :param name : 日志记录器的名称。
        :param debug : 是否启用调试模式。
    """
    if name in _LOGGERS:
        _LOGGERS[name].DebugMode = debug


def setAllDebugMode(debug: bool):
    """
    设置所有日志记录器的调试模式。

    参数：
        :param debug : 是否启用调试模式。
    """
    for logger in _LOGGERS.values():
        logger.DebugMode = debug
