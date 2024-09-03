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
    'ConcurrentSystemConfig',
    'ConcurrentSystem',
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

from art import text2art
from colorama import init, Fore, Style

if TYPE_CHECKING:
    pass

sys.set_int_max_str_digits(100000)
init(autoreset=True)
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
    def format(self, record):
        log_colors = {
            logging.DEBUG: Fore.CYAN + Style.BRIGHT,
            logging.INFO: Fore.GREEN + Style.BRIGHT,
            logging.WARNING: Fore.YELLOW + Style.BRIGHT,
            logging.ERROR: Fore.RED + Style.BRIGHT,
            logging.CRITICAL: Fore.RED + Style.BRIGHT + Style.BRIGHT
        }
        color = log_colors.get(record.levelno, Fore.WHITE)
        record.msg = color + str(record.msg) + Style.RESET_ALL
        record.levelname = color + record.levelname + Style.RESET_ALL
        formatted_message = super().format(record)
        return color + formatted_message + Style.RESET_ALL


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
    banner = text2art("TheSeedCore", font="slant", chr_ignore=True)
    print(Fore.MAGENTA + Style.BRIGHT + banner)
    print(Fore.MAGENTA + Style.BRIGHT + f"TheSeedCore version: {__version__} - PID - [{os.getpid()}]")
    print(Fore.MAGENTA + Style.BRIGHT + f"Latest repositories address {__repository__}\n")


def _showSupportInfo(QtSupport):
    if not QtSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[QtSupport] Qt or QApplication is not available, Deny QtMode. If you want to support QtMode, please install [PySide6] or [PyQt6] or [PyQt5]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[QtSupport] Qt is available, Allow Qt Mode")
    if not PyTorchSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[PyTorchSupport] PyTorch or CUDA is not available, Deny GPU Boost.")
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[PyTorchSupport] If you want to support GPU Boost, please use [pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121] command to install PyTorch")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[PyTorchSupport] PyTorch and CUDA is available, Allow GPU Boost")
    if not MySQLSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[MySQLSupport] MySQL is not available, Deny MySQL Support. If you want to support MySQL, please install [mysql-connector-python]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[MySQLSupport] MySQL is available, Allow MySQL Support")
    if not RedisSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[RedisSupport] Redis is not available, Deny Redis Support. If you want to support Redis, please install [redis]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[RedisSupport] Redis is available, Allow Redis Support")
    if not EncryptSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[EncryptSupport] Encryptor is not available, Deny Encrypt Support. If you want to support Encryptor, please install [keyring, pycryptodome]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[EncryptSupport] Encryptor is available, Allow Encrypt Support")
    if not KafkaSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[KafkaSupport] Kafka is not available, Deny Kafka Support. If you want to support Kafka, please install [kafka-python]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[KafkaSupport] Kafka is available, Allow Kafka Support")
    if not NetWorkServiceSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "\n[NetWorkServiceSupport] Network Service is not available, Deny Network Service Support. If you want to support Network Service, please install [aiohttp, certifi, websockets]\n")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n[NetWorkServiceSupport] Network Service is available, Allow Network Service Support\n")


def ConnectNERvGear(concurrent_config: ConcurrentSystemConfig = None, check_env_support=True, debug_mode: bool = False):
    if check_env_support:
        if _AllowQtMode and QApplication.instance():
            _showSupportInfo(True)
        else:
            _showSupportInfo(False)
    _showBanner()
    ConnectConcurrentSystem(concurrent_config, debug_mode)
    print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nNERvGear connection completed. Waiting for link start...")


def LinkStart():
    global MainEventLoop, _QtMode
    try:
        if _AllowQtMode and QApplication.instance():
            # noinspection PyUnresolvedReferences
            import qasync
            MainEventLoop = qasync.QEventLoop(QApplication.instance())
            asyncio.set_event_loop(MainEventLoop)
            QApplication.instance().aboutToQuit.connect(LinkStop)
            _QtMode = True
            print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nTheSeedCore connection completed. System standing by...\n")
            MainEventLoop.run_forever()
        else:
            print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nTheSeedCore connection completed. System standing by...\n")
            MainEventLoop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


def LinkStop():
    global MainEventLoop, _QtMode
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
