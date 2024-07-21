# -*- coding: utf-8 -*-
"""
TheSeedCore Logging Module

# This module provides advanced logging functionalities tailored for applications, supporting features like color coding of logs,
# file saving, and toggling of debug modes. It is designed to enhance diagnostic and tracking capabilities efficiently, making it
# crucial for both development and production environments.
#
# Key Components:
# 1. TheSeedCoreLogger: Central logger class derived from logging.Logger, featuring color-coded log displays and automated log file rotation.
# 2. setDebugMode: Function to enable or disable debug mode for a specific logger, aiding in focused troubleshooting.
# 3. setAllDebugMode: Function to globally toggle debug mode across all logger instances, streamlining log management.
#
# Module Functions:
# - Enables color differentiation of log levels in console outputs to improve readability.
# - Supports automatic daily rotation of log files, maintaining a history of logs as per configuration.
# - Provides mechanisms to dynamically switch debug modes, accommodating various stages of application development and deployment.
# - Ensures a consistent log format that includes essential details such as timestamps, logger names, log levels, and messages.
#
# Usage Scenarios:
# - Essential for systems requiring detailed logging, such as operational logs with varying severity levels from debug to critical errors.
# - Beneficial during the development phase for capturing detailed debug information.
# - Adaptable for different operational environments by adjusting logging detail levels and storage configurations.
#
# Dependencies:
# - logging: Standard Python library for core logging functionalities.
# - colorama: Enhances console output with color coding, improving log visibility and differentiation.
# - os: Manages file and directory operations, crucial for log file management.

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
