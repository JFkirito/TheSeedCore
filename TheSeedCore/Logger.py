# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "TheSeedCoreLogger",
    "consoleLogger",
    "LoggerManager"
]

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING, Optional

from . import LogsDirectoryPath, DevelopmentEnv
from ._Common import TextColor, _checkPath  # noqa

if TYPE_CHECKING:
    pass

_LoggerInstance = {}


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
    """
    Custom logger class for managing logging to files and console output with different levels of detail.

    Class: TheSeedCoreLogger
    Inherits from: logging.Logger

    Methods:
        __new__: Ensures a single instance of the logger is created per name.
        __init__: Initializes the logger with file and stream handlers.
        DebugMode: Property for getting and setting the debug mode for the logger.

    Attributes:
        _DirectoryPath: Path where log files are stored.
        _LogFilePath: Full path for the log file.
        _FileProcessor: Handler for writing logs to file with rotation.
        _FileFormatter: Formatter for the file logs.
        _StreamProcessor: Handler for outputting logs to console.
        _StreamFormatter: Formatter for console logs.

    Global Attributes:
        _LoggerInstance: Dictionary holding all registered logger instances.
    """

    def __new__(cls, name: str, path: str = LogsDirectoryPath, backup_count: int = 7, level: int = logging.DEBUG, debug: bool = DevelopmentEnv):
        global _LoggerInstance
        if name not in _LoggerInstance:
            instance: TheSeedCoreLogger = super().__new__(cls)
            _LoggerInstance[name] = instance
        return _LoggerInstance[name]

    def __init__(self, name: str, path: str = LogsDirectoryPath, backup_days: int = 7, level: int = logging.DEBUG, debug: bool = DevelopmentEnv):
        super().__init__(name, level)
        self._Debug = debug
        self._DirectoryPath: str = path
        _checkPath(self._DirectoryPath)
        self._LogFilePath: str = os.path.join(self._DirectoryPath, f"{name}.log")
        self._FileProcessor: TimedRotatingFileHandler = TimedRotatingFileHandler(self._LogFilePath, when="midnight", interval=1, backupCount=backup_days, encoding="utf-8")
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


class LoggerManager:
    """
    Manages logger instances, providing methods to retrieve, delete, and configure logger settings.

    Class Methods:
        getLogger: Retrieves a logger instance by its name.
        deleteLogger: Deletes a logger instance by its name.
        setDebugMode: Sets the debug mode for a specific logger instance.
        setAllDebugMode: Sets the debug mode for all logger instances.

    Global Attributes:
        _LoggerInstance: A dictionary holding all registered logger instances.
    """

    @classmethod
    def getLogger(cls, name: str) -> TheSeedCoreLogger:
        """
        Retrieves a logger instance by its name from the _LoggerInstance dictionary.

        :param name: A string representing the name of the logger to be retrieved.
        :return: The logger instance associated with the specified name.
        :raises KeyError: If the specified logger name does not exist in the _LoggerInstance dictionary.
        setup:
            1. Check if the logger with the specified name exists in the _LoggerInstance dictionary:
                1.1. If it exists, return the logger instance.
                1.2. If it does not exist, raise a KeyError indicating that the logger was not found.
        """

        global _LoggerInstance
        if name in _LoggerInstance:
            return _LoggerInstance[name]
        raise KeyError(f"Logger '{name}' not found")

    @classmethod
    def deleteLogger(cls, name: str) -> None:
        """
        Deletes a logger instance identified by its name from the _LoggerInstance dictionary.

        :param name: A string representing the name of the logger to be deleted.
        :raises KeyError: If the specified logger name does not exist in the _LoggerInstance dictionary.
        setup:
            1. Check if the logger with the specified name exists in the _LoggerInstance dictionary:
                1.1. If it exists, delete the logger from the _LoggerInstance.
                1.2. If it does not exist, raise a KeyError indicating that the logger was not found.
        """

        global _LoggerInstance
        if name in _LoggerInstance:
            del _LoggerInstance[name]
            return
        raise KeyError(f"Logger '{name}' not found")

    @classmethod
    def setDebugMode(cls, name: str, debug: bool) -> None:
        """
        Sets the debug mode for a specific logger instance identified by its name.

        :param name: A string representing the name of the logger whose debug mode is to be set.
        :param debug: A boolean indicating whether to enable or disable debug mode for the specified logger.
        :raises KeyError: If the specified logger name does not exist in the _LoggerInstance dictionary.
        setup:
            1. Check if the logger with the specified name exists in the _LoggerInstance dictionary:
                1.1. If it exists, set its DebugMode attribute to the provided value.
                1.2. If it does not exist, raise a KeyError indicating that the logger was not found.
        """

        global _LoggerInstance
        if name in _LoggerInstance:
            _LoggerInstance[name].DebugMode = debug
            return
        raise KeyError(f"Logger '{name}' not found")

    @classmethod
    def setAllDebugMode(cls, debug: bool) -> None:
        """
        Sets the debug mode for all logger instances to the specified value.

        :param debug: A boolean indicating whether to enable or disable debug mode.
        setup:
            1. Iterate through all logger instances stored in the _LoggerInstance dictionary:
                1.1. For each logger, set its DebugMode attribute to the provided value.
        """

        global _LoggerInstance
        for logger in _LoggerInstance.values():
            logger.DebugMode = debug


def consoleLogger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Creates and configures a console logger with the specified name and logging level.

    :param name: A string representing the name of the logger.
    :param level: An integer representing the logging level (default is logging.DEBUG).
    :return: A configured logging.Logger instance.

    setup:
        1. Retrieve or create a logger instance with the specified name.
        2. Set the logger's level to the specified level.
        3. Create a StreamHandler to output log messages to the console.
        4. Configure the handler's level based on the development environment:
            4.1. If in development mode, set the handler's level to the specified level.
            4.2. Otherwise, set it to the maximum of logging.DEBUG and logging.WARNING.
        5. Create a formatter with a specified format string and assign it to the handler.
        6. Add the handler to the logger.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    if DevelopmentEnv:
        handler.setLevel(level)
    else:
        handler.setLevel(max(logging.DEBUG, logging.WARNING))
    formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
