# -*- coding: utf-8 -*-
"""
TheSeed Logging Module

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

__all__ = ["TheSeedCoreLogger", "setDebugMode", "setAllDebugMode"]

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING, Union

from colorama import Fore, Style

if TYPE_CHECKING:
    pass

_LOGGERS = {}


def setDebugMode(LoggerName: str, Debug: bool):
    """
    设置日志记录器的调试模式。

    参数：
        :param LoggerName : 日志记录器的名称。
        :param Debug : 是否启用调试模式。
    """
    if LoggerName in _LOGGERS:
        _LOGGERS[LoggerName].DebugMode = Debug


def setAllDebugMode(Debug: bool):
    """
    设置所有日志记录器的调试模式。

    参数：
        :param Debug : 是否启用调试模式。
    """
    for logger in _LOGGERS.values():
        logger.DebugMode = Debug


class TheSeedCoreLogger(logging.Logger):
    """
    TheSeedCore日志记录器。

    参数：
        :param LoggerName : 日志记录器的名称。
        :param LoggerPath : 日志文件存储的路径。
        :param BackupCount : 日志文件的备份数量，默认为30。
        :param Level : 日志的级别，默认为DEBUG。
        :param Debug : 是否启用调试模式，默认为False。
    """

    class _ColoredSyncFormatter(logging.Formatter):
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

    def __new__(cls, LoggerName: str, LoggerPath: str, BackupCount: int = 30, Level: Union[logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET] = logging.DEBUG, Debug: bool = False):
        if LoggerName in _LOGGERS:
            return _LOGGERS[LoggerName]
        else:
            instance = super(TheSeedCoreLogger, cls).__new__(cls)
            _LOGGERS[LoggerName] = instance
            return instance

    def __init__(self, LoggerName: str, LoggerPath: str, BackupCount: int = 30, Level: Union[logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET] = logging.DEBUG, Debug: bool = False):
        if not hasattr(self, '_initialized'):
            super().__init__(LoggerName, Level)
            self._LoggerPath = LoggerPath
            self._Debug = Debug
            self._StreamProcessor = None
            self._StreamFormatter = None

            try:
                if not os.path.exists(self._LoggerPath):
                    os.makedirs(self._LoggerPath)
            except Exception as e:
                raise RuntimeError(f"Error creating sync log path: {e}")

            self._LogFile = os.path.join(self._LoggerPath, f"{LoggerName}.log")
            self._FileProcessor = TimedRotatingFileHandler(self._LogFile, when="midnight", interval=1, backupCount=BackupCount, encoding="utf-8")
            self._FileProcessor.suffix = "%Y-%m-%d"
            self._FileProcessor.setLevel(Level)
            self._Formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            self._FileProcessor.setFormatter(self._Formatter)
            self.addHandler(self._FileProcessor)

            self._updateConsoleHandler()
            self._initialized = True

    @property
    def DebugMode(self):
        return self._Debug

    @DebugMode.setter
    def DebugMode(self, value):
        if self._Debug != value:
            self._Debug = value
            self._updateConsoleHandler()

    def _updateConsoleHandler(self):
        if self._Debug:
            if not self._StreamProcessor:
                self._StreamProcessor = logging.StreamHandler()
                self._StreamFormatter = self._ColoredSyncFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                self._StreamProcessor.setLevel(self.level)
                self._StreamProcessor.setFormatter(self._StreamFormatter)
                self.addHandler(self._StreamProcessor)
        else:
            if self._StreamProcessor and self._StreamProcessor in self.handlers:
                self.removeHandler(self._StreamProcessor)
                self._StreamProcessor = None
                self._StreamFormatter = None
