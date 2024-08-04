# -*- coding: utf-8 -*-
"""
TheSeedCore Framework

Module Description:
This module serves as the entry point for TheSeedCore framework.
It initializes various system paths, configures the main event loop, and sets up logging.
It also manages the initialization and shutdown of different modules, including concurrent systems, databases, encryption, external services, Kafka, and network services.

Main Components:
1. Initialization: Sets up system paths, main event loop, and logging.
2. Dependency Import: Imports necessary dependencies and checks support for various modules.
3. Banner Display: Provides functions to display library banners and support information.
4. Module Management: Manages the initialization and shutdown of different modules.

Module Functionality Overview:
- Initializes system paths and ensures necessary directories exist.
- Sets up and manages the main event loop for asynchronous operations.
- Configures logging with color-formatted console output.
- Imports and checks support for various modules such as PyTorch, MySQL, Redis, Encryptor, Kafka, and Network services.
- Displays library banners and support information.
- Manages the start and stop processes for different modules.

Key Classes and Methods:
- _ColoredFormatter: A custom logging formatter that adds color to log messages based on log level.
- linkStart(): Initializes and starts the main event loop and modules.
- linkStop(): Shuts down all running modules and stops the main event loop.
- _showBanner(): Displays the library banner.
- _showSupportInfo(): Displays support information for various modules.

Notes:
- Ensure all necessary dependencies are installed before using this module.
- Configure system paths and logging settings as needed.
- Utilize the provided functions to manage the lifecycle of the library.
- Refer to the logging output for detailed information on module operations and errors.
- This module is designed as the central initialization point for TheSeedCore framework.
"""

from __future__ import annotations

__version__ = "0.0.8"
__author__ = "B站疾风Kirito"
__website__ = "https://space.bilibili.com/6440741"
__repository__ = "https://github.com/JFkirito/TheSeed"

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


from .ConcurrentSystemModule import _PyTorchSupport, _PySide6Support, _PyQt6Support, _PyQt5Support, QApplication, TaskSerializationProcessor, ConcurrentSystemConfig, TheSeedCoreConcurrentSystem
from .DatabaseModule import _MySQLSupport, _RedisSupport, SQLiteDatabaseConfig, BasicSQLiteDatabase, ExpandSQLiteDatabase, SQLiteDatabaseManager
from .EncryptionModule import _EncryptSupport
from .ExternalServicesModule import NodeService
from .KafkaServiceModule import _KafkaSupport
from .LoggerModule import LoggerConfig, TheSeedCoreLogger
from .NetworkModule import _NetWorkServiceSupport

__all__ = [
    'linkStart',
    'linkStop',
    'MainEventLoop',
    'EXTERNAL_LIBRARY_PATH',
    'DATA_PATH',
    'DATABASE_PATH',
    'LOGS_PATH',
    'TaskSerializationProcessor',
    'ConcurrentSystemConfig',
    'TheSeedCoreConcurrentSystem',
    'SQLiteDatabaseConfig',
    'BasicSQLiteDatabase',
    'ExpandSQLiteDatabase',
    'SQLiteDatabaseManager',
    'NodeService',
    'LoggerConfig',
    'TheSeedCoreLogger',
]

if _MySQLSupport:
    from .DatabaseModule import MySQLDatabaseConfig, BasicMySQLDatabase, MySQLDatabaseManager

    __all__.extend(['MySQLDatabaseConfig', 'BasicMySQLDatabase', 'MySQLDatabaseManager'])
if _RedisSupport:
    from .DatabaseModule import RedisDatabaseConfig, BasicRedisDatabase, RedisDatabaseManager

    __all__.extend(['RedisDatabaseConfig', 'BasicRedisDatabase', 'RedisDatabaseManager'])
if _EncryptSupport:
    from .EncryptionModule import EncryptorConfig, TheSeedCoreEncryptor, EncryptorManager

    __all__.extend(['EncryptorConfig', 'TheSeedCoreEncryptor', 'EncryptorManager'])
if _KafkaSupport:
    from .KafkaServiceModule import KafkaService

    __all__.append('KafkaService')
if _NetWorkServiceSupport:
    from .NetworkModule import HTTPServer, WebSocketServer, WebSocketClient

    __all__.extend(['HTTPServer', 'WebSocketServer', 'WebSocketClient'])
if QApplication:
    __all__.append('QApplication')
    _AllowQtMode = True


def _showBanner():
    banner = text2art("TheSeedCore", font="slant", chr_ignore=True)
    print(Fore.MAGENTA + Style.BRIGHT + banner)
    print(Fore.MAGENTA + Style.BRIGHT + f"TheSeedCore version: {__version__} - PID - [{os.getpid()}]")
    print(Fore.MAGENTA + Style.BRIGHT + f"Latest repositories address {__repository__}\n")


def _showSupportInfo(QtSupport):
    if not QtSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[QtSupport] Qt or QApplication is not available, Deny QtMode. If you want to support QtMode, please install [PySide6] or [PyQt6] or [PyQt5]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[QtSupport] Qt is available, Allow Qt Mode")
    if not _PyTorchSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[PyTorchSupport] PyTorch or CUDA is not available, Deny GPU Boost.")
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[PyTorchSupport] If you want to support GPU Boost, please use [pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121] command to install PyTorch")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[PyTorchSupport] PyTorch and CUDA is available, Allow GPU Boost")
    if not _MySQLSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[MySQLSupport] MySQL is not available, Deny MySQL Support. If you want to support MySQL, please install [mysql-connector-python]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[MySQLSupport] MySQL is available, Allow MySQL Support")
    if not _RedisSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[RedisSupport] Redis is not available, Deny Redis Support. If you want to support Redis, please install [redis]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[RedisSupport] Redis is available, Allow Redis Support")
    if not _EncryptSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[EncryptSupport] Encryptor is not available, Deny Encrypt Support. If you want to support Encryptor, please install [keyring, pycryptodome]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[EncryptSupport] Encryptor is available, Allow Encrypt Support")
    if not _KafkaSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[KafkaSupport] Kafka is not available, Deny Kafka Support. If you want to support Kafka, please install [kafka-python]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[KafkaSupport] Kafka is available, Allow Kafka Support")
    if not _NetWorkServiceSupport:
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT + "[NetWorkServiceSupport] Network Service is not available, Deny Network Service Support. If you want to support Network Service, please install [aiohttp, certifi, websockets]")
    else:
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "[NetWorkServiceSupport] Network Service is available, Allow Network Service Support")


def linkStop():
    global MainEventLoop, _QtMode
    if SQLiteDatabaseManager.INSTANCE is not None:
        SQLiteDatabaseManager.INSTANCE.closeAllDatabase()
    if _MySQLSupport:
        if MySQLDatabaseManager.INSTANCE is not None:
            MySQLDatabaseManager.INSTANCE.closeAllDatabase()
    if _RedisSupport:
        if RedisDatabaseManager.INSTANCE is not None:
            RedisDatabaseManager.INSTANCE.closeAllDatabase()
    if _KafkaSupport:
        if KafkaService.INSTANCE is not None:
            KafkaService.INSTANCE.closeAllClusters()
    if TheSeedCoreConcurrentSystem.INSTANCE is not None:
        TheSeedCoreConcurrentSystem.INSTANCE.closeSystem()
    if not _QtMode:
        MainEventLoop.stop()


def linkStart(check_support=True):
    global MainEventLoop, _QtMode
    _showBanner()
    try:
        if _AllowQtMode:
            if QApplication.instance():
                import qasync
                MainEventLoop = qasync.QEventLoop(QApplication.instance())
                asyncio.set_event_loop(MainEventLoop)
                QApplication.instance().aboutToQuit.connect(linkStop)
                _QtMode = True
                if check_support:
                    _showSupportInfo(True)
                print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nTheSeedCore connection completed. System standing by...\n")
                MainEventLoop.run_forever()
            else:
                if check_support:
                    _showSupportInfo(False)
                print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nTheSeedCore connection completed. System standing by...\n")
                MainEventLoop.run_forever()
        else:
            if check_support:
                _showSupportInfo(False)
            print(Fore.LIGHTGREEN_EX + Style.BRIGHT + f"\nTheSeedCore connection completed. System standing by...\n")
            MainEventLoop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
