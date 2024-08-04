# -*- coding: utf-8 -*-
"""
TheSeedCore Logger Module

Module Description:
This module provides a comprehensive logging system for TheSeedCore, featuring color-formatted console output and non-colored file logging.
It includes functionality for setting up and managing loggers with configurable parameters such as log levels, file paths, and debug modes.
The module supports rotation of log files based on time intervals.

Main Components:
1. Logger Configuration: Defines a data class for configuring loggers, including name, path, backup count, log level, and debug mode.
2. TheSeedCoreLogger Class: Implements the core logging functionalities, providing color-formatted console output and file logging.
3. Utility Functions: Provides functions to set the debug mode for individual loggers or all loggers.

Module Functionality Overview:
- Configurable logging with support for colored console output and non-colored file logging.
- Supports log file rotation based on time intervals.
- Allows setting and updating log levels and debug modes dynamically.
- Manages multiple loggers with unique configurations.
- Ensures proper directory creation for log file storage.

Key Classes and Methods:
- LoggerConfig: Data class for logger configuration parameters.
- TheSeedCoreLogger: Core logger class with color-formatted console output and file logging.
  - _ColorFormatter: Formatter for colored console output.
  - _FileFormatter: Formatter for non-colored file logging.
  - DebugMode: Property to get or set the debug mode of the logger.
- setDebugMode(): Sets the debug mode for a specific logger.
- setAllDebugMode(): Sets the debug mode for all loggers.

Notes:
- Ensure the required directories for log file storage are created before initializing loggers.
- Configure logger parameters appropriately in the LoggerConfig data class.
- Utilize the utility functions to manage debug modes for loggers as needed.
- Refer to the logging output for detailed information on log operations and errors.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING

from colorama import Fore, Style

if TYPE_CHECKING:
    pass

_LOGGERS = {}


@dataclass
class LoggerConfig:
    Name: str
    Path: str
    BackupCount: int
    Level: int
    Debug: bool

    def __post_init__(self):
        if not isinstance(self.Name, str):
            raise ValueError("The logger name must be a string.")
        if not isinstance(self.Path, str):
            raise ValueError("The logger path must be a string.")
        if not isinstance(self.BackupCount, int):
            raise ValueError("The logger backup count must be an integer.")
        if not isinstance(self.Level, int):
            raise ValueError("The logger level must be an integer.")
        if not isinstance(self.Debug, bool):
            raise ValueError("The logger debug mode must be a boolean.")


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
