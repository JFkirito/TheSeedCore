# -*- coding: utf-8 -*-
"""
TheSeedCore LoggerModule

######################################################################################################################################
# This module provides a custom logging system for managing loggers with advanced features like
# colorized console output, timed rotating file handlers, and debug mode control. It is designed
# to be flexible and scalable, allowing easy integration into larger applications.

# Main functionalities:
# 1. Creation and configuration of custom loggers with support for timed rotating log files.
# 2. Colorized console logging for better readability during development and debugging.
# 3. Centralized control of debug mode for individual or all loggers.
# 4. Persistent logging to disk with automatic log file management.

# Main components:
# 1. LoggerConfig - A configuration class that holds logger settings such as name, path, log level, and debug mode.
# 2. TheSeedCoreLogger - A custom logger class that manages log file handlers and console handlers.
# 3. _ColorFormatter - A formatter that applies color to log messages based on their severity level.
# 4. setDebugMode - A function to toggle debug mode for a specific logger.
# 5. setAllDebugMode - A function to toggle debug mode for all active loggers.

# Design thoughts:
# 1. Custom and reusable logging system:
#    a. The module is designed to provide a robust logging infrastructure that can be reused across different parts of the application.
#    b. Each logger is configured with its own file handler and console handler, ensuring that logs are both saved and easily visible during development.
#
# 2. Enhanced readability through colorized logs:
#    a. The console output is enhanced with color codes that highlight the severity of log messages, making it easier to identify issues at a glance.
#    b. This is especially useful during development and debugging, where quick identification of errors and warnings is crucial.
#
# 3. Scalable debug mode management:
#    a. The module provides centralized control over the debug mode, allowing for quick toggling of log verbosity across the entire application.
#    b. This feature helps developers focus on relevant logs by adjusting the level of detail without modifying individual logger configurations.
#
# 4. Timed log rotation and backup:
#    a. Log files are managed with a timed rotating handler that creates new log files at regular intervals (e.g., daily), preventing logs from growing too large.
#    b. Old log files are automatically archived based on the backup count specified, ensuring that disk space is managed efficiently.
#
# 5. Error handling and configurability:
#    a. The module includes error checking and validation during logger configuration, ensuring that only valid settings are applied.
#    b. The loggers are highly configurable, allowing for different logging behaviors depending on the application's environment and needs.

# Required dependencies:
# 1. Python libraries: logging, os, dataclasses, typing.
# 2. External libraries: colorama (for colorized console output).
######################################################################################################################################
"""
from __future__ import annotations

__all__ = [
    "LoggerConfig",
    "TheSeedCoreLogger",
    "setDebugMode",
    "setAllDebugMode"
]

import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING

from . import _ColoredFormatter

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


class _FileFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return message


class TheSeedCoreLogger(logging.Logger):

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
        self._FileFormatter = _FileFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self._FileProcessor.setFormatter(self._FileFormatter)
        self.addHandler(self._FileProcessor)

        self._StreamProcessor = logging.StreamHandler()
        self._ConsoleFormatter = _ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
    if name in _LOGGERS:
        _LOGGERS[name].DebugMode = debug


def setAllDebugMode(debug: bool):
    for logger in _LOGGERS.values():
        logger.DebugMode = debug
