# -*- coding: utf-8 -*-
"""
TheSeedCore Framework

######################################################################################################################################
# TheSeedCore is a highly modular Python framework designed for building complex, scalable, and efficient systems.
# It integrates a variety of functional modules, providing a comprehensive solution for everything from concurrency management
# to network service support, making it suitable for high-performance and reliable application development.

# Key Features:
# 1. Concurrent System Module:
#    - Supports the configuration and management of concurrent tasks, efficiently handling multi-threading and multi-processing tasks,
#      ensuring optimal resource utilization and system performance.
#
# 2. Database Module:
#    - Supports multiple databases, including SQLite, MySQL, and Redis. This module offers convenient database configuration,
#      management, and connection pooling, ensuring efficiency and security in data storage and access.
#
# 3. Encryption Module:
#    - Provides powerful data encryption and decryption functionalities with support for various encryption algorithms,
#      ensuring data security in applications handling sensitive information.
#
# 4. External Services Module:
#    - Facilitates integration with external services, offering features to install and manage Node.js services.
#      This enables applications to interact with external APIs and services, extending their functionality and service range.
#
# 5. Kafka Service Module:
#    - Integrates Kafka messaging service, supporting distributed messaging and stream processing, suitable for real-time
#      data processing and large-scale data stream management scenarios.
#
# 6. Logger Module:
#    - Provides a flexible and powerful logging system with support for console output and time-based rotating log files.
#      It also supports centralized debug mode control, allowing developers to monitor and debug in different environments.
#
# 7. Network Module:
#    - Implements HTTP server and WebSocket server/client, supporting asynchronous communication and real-time data exchange,
#      making it ideal for building real-time applications and high-concurrency network services.
#
# 8. Extensibility and Configurability:
#    - TheSeedCore is designed to be highly extensible and configurable, allowing developers to customize and extend the framework
#      to suit specific application needs across various scenarios.

# Suitable Use Cases:
# TheSeedCore is especially well-suited for complex applications that require concurrent task management, real-time communication,
# real-time data processing, and external service integration. Whether building enterprise-level applications, distributed systems,
# or personal projects, this framework provides robust support for rapid and efficient development.

# Design Philosophy:
# TheSeedCore emphasizes modularity, extensibility, and development efficiency. By modularizing common functionalities,
# developers can freely combine and extend these modules to build systems tailored to specific needs. The framework also focuses
# on security and performance optimization, ensuring that applications remain stable and secure under high loads.

# Overall, TheSeedCore is a powerful and flexible framework, suitable for various types of Python project development.
######################################################################################################################################
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "B站疾风Kirito"
__website__ = "https://space.bilibili.com/6440741"
__repository__ = "https://github.com/JFkirito/TheSeedCore"
__all__ = [
    # Initialization Module
    'ConnectNERvGear',
    'LinkStart',
    'LinkStop',
    'MainEventLoop',
    'EXTERNAL_LIBRARY_PATH',
    'DATA_PATH',
    'DATABASE_PATH',
    'LOGS_PATH',
    # ConcurrentSystem Module
    'ConcurrentSystem',
    'TaskFuture',
    # Database Module
    'SQLiteDatabaseConfig',
    'BasicSQLiteDatabase',
    'SQLiteDatabaseManager',
    'MySQLDatabaseConfig',
    'BasicMySQLDatabase',
    'MySQLDatabaseManager',
    'RedisDatabaseConfig',
    'BasicRedisDatabase',
    'RedisDatabaseManager',
    # Encryption Module
    'EncryptorConfig',
    'Encryptor',
    'EncryptorManager',
    # ExternalServices Module
    'NodeService',
    # KafkaService Module
    'KafkaService',
    # Logger Module
    'LoggerConfig',
    'TheSeedCoreLogger',
    'setDebugMode',
    'setAllDebugMode',
    # Network Module
    "HTTPServer",
    "WebSocketServer",
    "WebSocketClient",
    "NetWorkServiceSupport"
]

import asyncio
import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

sys.set_int_max_str_digits(100000)
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
PURPLE = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

RED_BOLD = "\033[1m\033[31m"
GREEN_BOLD = "\033[1m\033[32m"
YELLOW_BOLD = "\033[1m\033[33m"
BLUE_BOLD = "\033[1m\033[34m"
PURPLE_BOLD = "\033[1m\033[35m"
CYAN_BOLD = "\033[1m\033[36m"
WHITE_BOLD = "\033[1m\033[37m"

RESET = "\033[0m"
MainEventLoop = asyncio.get_event_loop()
SYSTEM_PATH = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTERNAL_LIBRARY_PATH = os.path.join(SYSTEM_PATH, "ExternalLibrary")
DATA_PATH = os.path.join(SYSTEM_PATH, "TheSeedCoreData")
DATABASE_PATH = os.path.join(DATA_PATH, "Database")
LOGS_PATH = os.path.join(DATA_PATH, "Logs")
EXTERNAL_SERVICE_PATH = os.path.join(DATA_PATH, "ExternalServices")
_AllowQtMode = False
_QtMode = False
_BasicPath = {
    "ExternalLibrary": EXTERNAL_LIBRARY_PATH,
    "Data": DATA_PATH,
    "Database": DATABASE_PATH,
    "Logs": LOGS_PATH,
    "ExternalServices": EXTERNAL_SERVICE_PATH
}
for path in _BasicPath.values():
    if not os.path.exists(path):
        os.makedirs(path)
        sys.path.append(path)


class _ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that adds color to log messages based on their severity level.

    This class extends `logging.Formatter` to enhance the readability of log outputs by using ANSI escape sequences for colored text.

    Attributes:
        COLORS: A dictionary mapping log levels to their corresponding ANSI color codes.
        RESET: ANSI code to reset text formatting.

    Methods:
        format: Overrides the default format method to apply color to log messages based on their severity level.

    Notes:
        - The formatter improves log visibility in terminal outputs, making it easier to distinguish between different log levels.
        - The colors used correspond to standard practices for log severity, with blue for DEBUG, green for INFO, yellow for WARNING, and red for ERROR.
    """

    COLORS = {
        logging.DEBUG: "\033[1;34m",
        logging.INFO: "\033[1;32m",
        logging.WARNING: "\033[1;33m",
        logging.ERROR: "\033[0;31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        """
        Formats log messages with color based on their severity level.

        :param record: The log record containing information about the log message.

        :return: A formatted string representing the log message, with color applied based on the log level.

        steps:
            1. Call the superclass's format method to get the base message from the log record.
            2. Retrieve the appropriate color for the log level from the COLORS dictionary:
                - If the log level is not found in COLORS, use the default reset color.
            3. Return the formatted message wrapped in the corresponding color codes, followed by a reset code.

        Notes:
            - This method enhances log visibility by adding color coding to different levels of log messages (e.g., DEBUG, WARNING, ERROR).
            - It improves readability and helps quickly identify the severity of log messages in the console output.
        """

        message = super().format(record)
        color = self.COLORS.get(record.levelno, self.RESET)
        return f"{color}{message}{self.RESET}"


from .ConcurrentSystemModule import *
from .DatabaseModule import *
from .EncryptionModule import *
from .ExternalServicesModule import *
from .KafkaServiceModule import *
from .LoggerModule import *
from .NetworkModule import *

if PySide6Support or PyQt5Support or PyQt6Support:
    _AllowQtMode = True


def _showBanner():
    print(PURPLE_BOLD + "  ______    __           _____                   __   ______                     ")
    print(PURPLE_BOLD + " /_  __/   / /_   ___   / ___/  ___   ___   ____/ /  / ____/  ____    _____  ___ ")
    print(PURPLE_BOLD + "  / /     / __ \\ / _ \\  \\__ \\  / _ \\ / _ \\ / __  /  / /      / __ \\  / ___/ / _ \\")
    print(PURPLE_BOLD + " / /     / / / //  __/ ___/ / /  __//  __// /_/ /  / /___   / /_/ / / /    /  __/")
    print(PURPLE_BOLD + "/_/     /_/ /_/ \\___/ /____/  \\___/ \\___/ \\__,_/   \\____/   \\____/ /_/     \\___/ ")
    print(PURPLE_BOLD + "                                                                                 " + RESET)
    print(PURPLE_BOLD + f"\nTheSeedCore version: {__version__}" + RESET)
    print(PURPLE_BOLD + f"MainProcess PID - [{os.getpid()}]" + RESET)
    print(PURPLE_BOLD + f"ServiceProcess PID - [{ConcurrentSystem.serviceProcessPID()}]" + RESET)
    print(PURPLE_BOLD + f"Latest repositories address {__repository__}" + RESET)


def _showSupportInfo(QtSupport):
    if not QtSupport:
        print(YELLOW_BOLD + "[QtSupport] Qt or QApplication is not available, Deny QtMode. If you want to support QtMode, please install [PySide6] or [PyQt6] or [PyQt5]" + RESET)
    else:
        print(GREEN_BOLD + "[QtSupport] Qt is available, Allow Qt Mode" + RESET)
    if not bool(PyTorchSupport.value):
        print(YELLOW_BOLD + "[PyTorchSupport] PyTorch or CUDA is not available, Deny GPU Boost." + RESET)
        print(YELLOW_BOLD + "[PyTorchSupport] If you want to support GPU Boost, please use [pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121] command to install PyTorch" + RESET)
    else:
        print(GREEN_BOLD + "[PyTorchSupport] PyTorch and CUDA is available, Allow GPU Boost" + RESET)
    if not MySQLSupport:
        print(YELLOW_BOLD + "[MySQLSupport] MySQL is not available, Deny MySQL Support. If you want to support MySQL, please install [mysql-connector-python]" + RESET)
    else:
        print(GREEN_BOLD + "[MySQLSupport] MySQL is available, Allow MySQL Support" + RESET)
    if not RedisSupport:
        print(YELLOW_BOLD + "[RedisSupport] Redis is not available, Deny Redis Support. If you want to support Redis, please install [redis]" + RESET)
    else:
        print(GREEN_BOLD + "[RedisSupport] Redis is available, Allow Redis Support" + RESET)
    if not EncryptSupport:
        print(YELLOW_BOLD + "[EncryptSupport] Encryptor is not available, Deny Encrypt Support. If you want to support Encryptor, please install [keyring, pycryptodome]" + RESET)
    else:
        print(GREEN_BOLD + "[EncryptSupport] Encryptor is available, Allow Encrypt Support" + RESET)
    if not KafkaSupport:
        print(YELLOW_BOLD + "[KafkaSupport] Kafka is not available, Deny Kafka Support. If you want to support Kafka, please install [kafka-python]" + RESET)
    else:
        print(GREEN_BOLD + "[KafkaSupport] Kafka is available, Allow Kafka Support" + RESET)
    if not NetWorkServiceSupport:
        print(YELLOW_BOLD + "[NetWorkServiceSupport] Network Service is not available, Deny Network Service Support. If you want to support Network Service, please install [aiohttp, certifi, websockets]\n" + RESET)
    else:
        print(GREEN_BOLD + "[NetWorkServiceSupport] Network Service is available, Allow Network Service Support\n" + RESET)


def ConnectNERvGear(check_env_support=True, **kwargs):
    if check_env_support:
        if _AllowQtMode and QApplication.instance():
            _showSupportInfo(True)
        else:
            _showSupportInfo(False)
    ConnectConcurrentSystem(**kwargs)
    _showBanner()
    print(GREEN_BOLD + f"NERvGear connection completed. Waiting for link start..." + RESET)


def LinkStart():
    global MainEventLoop, _QtMode
    try:
        if _AllowQtMode and QApplication.instance():
            # noinspection PyUnresolvedReferences
            import qasync
            MainEventLoop = qasync.QEventLoop(QApplication.instance())
            QApplication.instance().aboutToQuit.connect(LinkStop)
            _QtMode = True
        print(GREEN_BOLD + f"TheSeedCore connection completed. System standing by..." + RESET)
        MainEventLoop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


def LinkStop():
    global _QtMode
    if SQLiteDatabaseManager.INSTANCE is not None:
        SQLiteDatabaseManager.INSTANCE.closeAllDatabase()
    if MySQLDatabaseManager.INSTANCE is not None:
        MySQLDatabaseManager.INSTANCE.closeAllDatabase()
    if RedisDatabaseManager.INSTANCE is not None:
        RedisDatabaseManager.INSTANCE.closeAllDatabase()
    if KafkaService.INSTANCE is not None:
        KafkaService.INSTANCE.closeAllClusters()
    ConcurrentSystem.closeSystem()
    if not _QtMode:
        MainEventLoop.stop()
