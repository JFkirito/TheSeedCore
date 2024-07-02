# -*- coding: utf-8 -*-
"""
TheSeedCore

# Introduction
# ----------------------
# TheSeedCore framework is a highly modular and scalable system designed to provide strong support for easily building complex applications.
# It focuses on flexibility, high concurrency, and security, offering comprehensive tools and components to meet various development needs.

# Key Features

## Modular Architecture
# ----------------------
# TheSeedCore is designed as a highly modular framework, allowing easy integration into various software architectures.
# It supports independent or collaborative functioning of modules.
# - Independent Modules: Each module operates independently, usable alone or in combination with others.
# - Module Interaction: Interfaces between modules facilitate the implementation of complex business logic.
# - Module Extension: Supports module extension and customization to meet specific needs.

## Command Line Interaction
# ----------------------
# Supports command line operations and customization of commands, providing flexibility in command expansion and operations.

## Database Management
# ----------------------
# Supports SQLite and Redis databases, along with transaction management, offering flexible and secure data management solutions.
# - Diversity: Supports various databases to meet different data storage needs.
# - Encryption: Features built-in data encryption to ensure the security of data storage and transmission.
# - Logging: Detailed operation logs help in tracking and auditing.
# - Data Integrity: Supports transaction management to ensure data integrity and consistency.

## Encryption Management
# ----------------------
# Provides advanced data encryption and decryption capabilities to ensure data security.
# - AES and RSA: Supports AES and RSA encryption algorithms.
# - Key Management: Key management features allow generation, import, and export of keys for easy management and usage.
# - Logging: Comprehensive logging of all encryption and decryption processes.

## External Services Management
# ----------------------
# Manages and operates packages and services related to Node.js, supporting seamless integration with the Node.js environment.
# - Node.js Management: Installation and management of Node.js packages and applications.
# - Service Control: Seamless start and stop of Node.js services.
# - Logging: Automatically logs all operations for monitoring and debugging.

## Network Services Management
# ----------------------
# Implements HTTP and WebSocket servers and clients, supporting real-time data exchange and network communications.
# - HTTP Server: Based on aiohttp, supports route management and dynamic content response.
# - WebSocket Server and Client: Implements real-time communication using the WebSocket protocol.
# - Extensibility: Easily add new routes and handlers to expand functionality.

## Thread Pool Management
# ----------------------
# Provides a highly configurable system for managing synchronous and asynchronous tasks, optimizing resource use and performance.
# - Task Management: Efficient execution of synchronous and asynchronous tasks.
# - Dynamic Adjustment: Automatically adjusts thread numbers based on current load.
# - Load Balancing: Evenly distributes tasks across threads for optimal performance.
# - Performance Monitoring: Monitors system performance to optimize resource utilization.

## Task Scheduling
# ----------------------
# Integrates synchronous and asynchronous task management, optimizing task execution efficiency and supporting high concurrency.
# - Specified Threads: Through thread pool management, supports thread control of tasks for enhanced processing efficiency.
# - Synchronous and Asynchronous Task Execution: Supports synchronous tasks and asyncio-based asynchronous tasks for efficient task handling.
# - Thread Safety: Ensures thread safety of tasks, avoiding resource competition and deadlocks.
# - Data Sharing Safety: Provides secure mechanisms for data sharing and passing, preventing data leaks and damage.

## Logging
# ----------------------
# Offers extensive logging features, supporting color coding, file saving, and debug mode toggling.
# - Color Coding: Different log levels are displayed in different colors to enhance readability.
# - File Rotation: Automatically rotates log files daily, keeping a configurable number of backups.
# - Debug Mode: Easily toggles debug mode on or off, facilitating detailed log viewing during development.

"""
from __future__ import annotations

__all__ = [
    "TheSeed",
    "linkStart",
    "linkStop",
    "TheSeedDatabaseManager",
    "SQLiteDatabaseManager",
    "RedisDatabaseManager",
    "TheSeedEncryptor",
    "EncryptorManager",
    "TheSeedThreadPool",
    "HTTPServer",
    "WebSocketServer",
    "WebSocketClient",
    "NodeService",
    "TheSeedCoreLogger",
    "setDebugMode",
    "setAllDebugMode",
]

import asyncio
import logging
import os
import random
import socket
import sys
import threading
import time
from typing import TYPE_CHECKING, Literal, Optional, List, Any, Callable, Coroutine

import pyfiglet
from colorama import init, Fore, Style

from .DatabaseModule import *
from .EncryptionModule import *
from .ExternalServicesModule import *
from .LoggerModule import *
from .NetworkModule import *
from .ThreadPoolModule import *

if TYPE_CHECKING:
    pass

__Version__ = "0.0.2"
_SYSTEM_BASIC_PATH = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXTERNAL_LIBRARY_PATH = os.path.join(_SYSTEM_BASIC_PATH, "ExternalLibrary")


class TheSeed:
    CommandList: list = ["start http server", "stop http server", "exit"]
    Version: _TheSeedCore.THESEED_CORE_INSTANCE.Version = None
    SystemBasicPath: _TheSeedCore.THESEED_CORE_INSTANCE.SystemBasicPath = None
    ExternalLibraryPath: _TheSeedCore.THESEED_CORE_INSTANCE.ExternalLibraryPath = None
    BasicDataPath: _TheSeedCore.THESEED_CORE_INSTANCE.BasicDataPath = None
    DatabasePath: _TheSeedCore.THESEED_CORE_INSTANCE.DatabasePath = None
    LogsPath: _TheSeedCore.THESEED_CORE_INSTANCE.LogsPath = None
    ExternalServicePath: _TheSeedCore.THESEED_CORE_INSTANCE.ExternalServicePath = None

    Application: _TheSeedCore.THESEED_CORE_INSTANCE.Application = None
    BasicHost: _TheSeedCore.THESEED_CORE_INSTANCE.BasicHost = None
    BasicHttpPort: _TheSeedCore.THESEED_CORE_INSTANCE.BasicHttpPort = None
    BasicWsPort: _TheSeedCore.THESEED_CORE_INSTANCE.BasicWsPort = None

    BasicLogger: TheSeedCoreLogger = None
    BasicEncryptorLogger: TheSeedCoreLogger = None
    BasicSQLiteDatabaseLogger: TheSeedCoreLogger = None
    BasicRedisDatabaseLogger: TheSeedCoreLogger = None
    BasicThreadPoolLogger: TheSeedCoreLogger = None
    BasicNetworkServicesLogger: TheSeedCoreLogger = None
    BasicExternalServicesLogger: TheSeedCoreLogger = None

    BasicEncryptor: TheSeedEncryptor = None
    BasicDatabaseManager: TheSeedDatabaseManager = None
    BasicThreadPool: TheSeedThreadPool = None

    EncryptorManager: EncryptorManager = None
    SQLiteDatabaseManager: SQLiteDatabaseManager = None
    RedisDatabaseManager: RedisDatabaseManager = None
    HttpServer: HTTPServer = None
    WebSocketServer: WebSocketServer = None
    NodeService: NodeService = None

    linkStart: _TheSeedCore.linkStart = None
    linkStop: _TheSeedCore.linkStop = None

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("TheSeed is a static class cannot be instantiated.")

    @staticmethod
    def commandProcessor(command):
        if command == "start http server":
            TheSeed.startHttpServer()
            return
        if command == "stop http server":
            TheSeed.stopHttpServer()
            return
        if command == "exit":
            TheSeed.linkStop()
            return
        print(command)

    @staticmethod
    def setTaskThreshold(task_threshold: int):
        """设置任务阈值。"""
        TheSeed.BasicThreadPool._TaskThreshold = task_threshold
        TheSeed.BasicDatabaseManager.upsertItem("TaskThreshold", str(task_threshold))

    @staticmethod
    def setPerformanceMode(performance_mode: Literal["HighestPerformance", "Balance", "LowPerformance"]):
        """设置性能模式。"""
        TheSeed.BasicThreadPool._PerformanceMode = performance_mode
        TheSeed.BasicDatabaseManager.upsertItem("PerformanceMode", performance_mode)

    @staticmethod
    def addSyncTask(task: Callable[..., Any], callback: Optional[Callable[[Any], Any]] = None, thread_label: str = None, lock: bool = False, *args, **kwargs):
        """添加同步任务。"""
        TheSeed.BasicThreadPool.addSyncTask(task, callback, thread_label, lock, *args, **kwargs)

    @staticmethod
    def addAsyncTask(task: Callable[..., Coroutine[Any, Any, Any]], callback: Optional[Callable[[Any], Any]] = None, thread_label: str = None, lock: bool = False, *args, **kwargs):
        """添加异步任务。"""
        TheSeed.BasicThreadPool.addAsyncTask(task, callback, thread_label, lock, *args, **kwargs)

    @staticmethod
    def createSyncThread(thread_label: str):
        TheSeed.BasicThreadPool.createSyncThread(thread_label)

    @staticmethod
    def createAsyncThread(thread_label: str):
        TheSeed.BasicThreadPool.createAsyncThread(thread_label)

    @staticmethod
    def startHttpServer():
        """启动HTTP服务器。"""
        TheSeed.BasicThreadPool.addAsyncTask(task=TheSeed.HttpServer.startHTTPServer, thread_label="TheSeed-Async")

    @staticmethod
    def stopHttpServer():
        """停止HTTP服务器。"""
        TheSeed.BasicThreadPool.addAsyncTask(task=TheSeed.HttpServer.stopHTTPServer, thread_label="TheSeed-Async")

    @staticmethod
    def getHttpServerAddress() -> str:
        """获取HTTP服务器地址。"""
        return TheSeed.HttpServer.getServerAddress()

    @staticmethod
    def startWebSocketServer():
        """启动WebSocket服务器。"""
        TheSeed.BasicThreadPool.addAsyncTask(task=TheSeed.WebSocketServer.startWebSocketServer, thread_label="TheSeed-Async")

    @staticmethod
    def stopWebSocketServer():
        """停止WebSocket服务器。"""
        TheSeed.BasicThreadPool.addAsyncTask(task=TheSeed.WebSocketServer.stopWebSocketServer, thread_label="TheSeed-Async")

    @staticmethod
    def getWebSocketServerAddress() -> str:
        """获取WebSocket服务器地址。"""
        return TheSeed.WebSocketServer.getServerAddress()


class _TheSeedCore:
    LINK_START: bool = False
    THESEED_CORE_INSTANCE: _TheSeedCore = None
    APPLICATION: type = None
    TOTAL_THREAD_COUNT: int = None
    SYNC_THREAD_LABEL_DEFAULT: Optional[List[str]] = ["TheSeed-Sync"]
    ASYNC_THREAD_LABEL_DEFAULT: Optional[List[str]] = ["TheSeed-Async"]
    TASK_THRESHOLD: int = 10
    LOAD_BALANCING: bool = True
    LOGGER_BACKUP_COUNT: int = 30
    BANNER_COLOR_MODE: Literal["Solid", "Gradient"] = "Solid"
    DEBUG: bool = False
    ARGS: Any = None
    KWARGS: Any = None
    IS_CLOSING: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls.LINK_START:
            raise RuntimeError("TheSeedCore must first be started using the 'link start' method.")
        if not cls.THESEED_CORE_INSTANCE:
            cls.THESEED_CORE_INSTANCE = super(_TheSeedCore, cls).__new__(cls, *args, **kwargs)
        return cls.THESEED_CORE_INSTANCE

    def __init__(self):
        if not _TheSeedCore.LINK_START:
            raise RuntimeError("TheSeedCore must first be started using the 'link start' method.")
        init(autoreset=True)
        self.Version = __Version__
        self.SystemBasicPath = _SYSTEM_BASIC_PATH
        self.ExternalLibraryPath = _EXTERNAL_LIBRARY_PATH
        self.BasicDataPath = os.path.join(_SYSTEM_BASIC_PATH, "TheSeedData")
        self.DatabasePath = os.path.join(self.BasicDataPath, "Database")
        self.LogsPath = os.path.join(self.BasicDataPath, "Logs")
        self.ExternalServicePath = os.path.join(self.BasicDataPath, "ExternalService")
        self._setupPath()

        self.Application = None
        self._MainEventLoop = None
        self._PerformanceMode: Literal["HighestPerformance", "Balance", "LowPerformance"] = "Balance"
        self._TaskThreshold: int = _TheSeedCore.TASK_THRESHOLD
        self._LoadBalancing: bool = _TheSeedCore.LOAD_BALANCING
        self._SyncCloseEvent = threading.Event()
        self._AsyncCloseEvent = asyncio.Event()

        self.BasicHost: str = ""
        self.BasicHttpPort: str = ""
        self.BasicWsPort: str = ""

        self.BasicLogger = TheSeedCoreLogger("TheSeedLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicEncryptorLogger = TheSeedCoreLogger("TheSeedEncryptorLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicSQLiteDatabaseLogger = TheSeedCoreLogger("TheSeedSQLiteDatabaseLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicRedisDatabaseLogger = TheSeedCoreLogger("TheSeedRedisDatabaseLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicThreadPoolLogger = TheSeedCoreLogger("TheSeedThreadPoolLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicNetworkServicesLogger = TheSeedCoreLogger("TheSeedNetworkServicesLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)
        self.BasicExternalServicesLogger = TheSeedCoreLogger("TheSeedExternalServicesLog", self.LogsPath, _TheSeedCore.LOGGER_BACKUP_COUNT, logging.DEBUG, _TheSeedCore.DEBUG)

        self.BasicEncryptor = TheSeedEncryptor("TheSeed", self.BasicEncryptorLogger)
        self.BasicDatabaseManager = TheSeedDatabaseManager(os.path.join(self.DatabasePath, "TheSeedCore.db"), self.BasicSQLiteDatabaseLogger, self.BasicEncryptor, True)
        self._setupDatabase()
        self._setupThreadPool()
        self._setupNetworkServiceAddress()
        self.BasicThreadPool = TheSeedThreadPool(self.BasicThreadPoolLogger, self._PerformanceMode, self._TaskThreshold, self._LoadBalancing, _TheSeedCore.TOTAL_THREAD_COUNT, _TheSeedCore.SYNC_THREAD_LABEL_DEFAULT, _TheSeedCore.ASYNC_THREAD_LABEL_DEFAULT)
        self.EncryptorManager = EncryptorManager(self.BasicEncryptorLogger)
        self.SQLiteDatabaseManager = SQLiteDatabaseManager(self.DatabasePath, self.BasicSQLiteDatabaseLogger, self.BasicEncryptor)
        self.RedisDatabaseManager = RedisDatabaseManager(self.BasicRedisDatabaseLogger, self.BasicEncryptor)
        self.HttpServer = HTTPServer(self.BasicHost, self.BasicHttpPort, self.BasicNetworkServicesLogger)
        self.WebSocketServer = WebSocketServer(self.BasicHost, self.BasicWsPort, self.BasicNetworkServicesLogger)
        self.NodeService = NodeService(self.ExternalServicePath, self.BasicExternalServicesLogger)

    @classmethod
    def linkStart(cls, application: type, total_thread_count: int = None, sync_thread_labels: Optional[List[str]] = None, async_thread_labels: Optional[List[str]] = None, task_threshold: int = 10, load_balancing: bool = True, logger_backup_count: int = 30,
                  banner_color_mode: Literal["Solid", "Gradient"] = "Solid", debug_mode: bool = False, *args, **kwargs):
        cls._validateLinkStartParameters(application, total_thread_count, sync_thread_labels, async_thread_labels, task_threshold, load_balancing, logger_backup_count, banner_color_mode, debug_mode)
        cls.APPLICATION = application
        cls.TOTAL_THREAD_COUNT = total_thread_count
        cls.SYNC_THREAD_LABEL_DEFAULT = (sync_thread_labels or []) + cls.SYNC_THREAD_LABEL_DEFAULT
        cls.ASYNC_THREAD_LABEL_DEFAULT = (async_thread_labels or []) + cls.ASYNC_THREAD_LABEL_DEFAULT
        cls.TASK_THRESHOLD = task_threshold
        cls.LOAD_BALANCING = load_balancing
        cls.LOGGER_BACKUP_COUNT = logger_backup_count
        cls.BANNER_COLOR_MODE = banner_color_mode
        cls.DEBUG = debug_mode
        cls.ARGS = args
        cls.KWARGS = kwargs
        cls.LINK_START = True
        cls._startTheSeed()

    @classmethod
    def linkStop(cls):
        async def _closeTheSeedCore():
            cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.set()

        cls.THESEED_CORE_INSTANCE._SyncCloseEvent.set()
        asyncio.run_coroutine_threadsafe(_closeTheSeedCore(), cls.THESEED_CORE_INSTANCE._MainEventLoop)

    @classmethod
    def _validateLinkStartParameters(cls, application, total_thread_count, sync_thread_labels, async_thread_labels, TaskThreshold, load_balancing, logger_backup_count, banner_color_mode, debug_mode):
        if not isinstance(application, type):
            raise TypeError("The application parameter must be a class and cannot be an instance")
        if not isinstance(total_thread_count, (int, type(None))):
            raise TypeError("The total_thread_count parameter must be an integer or None")
        if not isinstance(sync_thread_labels, (list, type(None))):
            raise TypeError("The sync_thread_labels parameter must be a list or None")
        if not isinstance(async_thread_labels, (list, type(None))):
            raise TypeError("The async_thread_labels parameter must be a list or None")
        if not isinstance(TaskThreshold, int):
            raise TypeError("The TaskThreshold parameter must be an integer")
        if not isinstance(load_balancing, bool):
            raise TypeError("The load_balancing parameter must be a boolean")
        if not isinstance(logger_backup_count, int):
            raise TypeError("The logger_backup_count parameter must be an integer")
        if not isinstance(banner_color_mode, str):
            raise TypeError("The banner_color_mode parameter must be a string")
        if banner_color_mode not in ["Solid", "Gradient"]:
            raise ValueError("The banner_color_mode parameter must be 'Solid' or 'Gradient'")
        if not isinstance(debug_mode, bool):
            raise TypeError("The debug_mode parameter must be a boolean")

    @classmethod
    def _startTheSeed(cls):
        try:
            cls._showBanner()
            cls.THESEED_CORE_INSTANCE = _TheSeedCore()
            cls.THESEED_CORE_INSTANCE.BasicDatabaseManager.upsertItem("StartTime", str(time.time()))
            cls._setupTheSeedCoreInterface()
            cls.THESEED_CORE_INSTANCE._MainEventLoop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.THESEED_CORE_INSTANCE._MainEventLoop)
            cls.THESEED_CORE_INSTANCE.Application = cls.APPLICATION(*cls.ARGS, **cls.KWARGS)
            cls.THESEED_CORE_INSTANCE.BasicThreadPool.startConsoleThread(TheSeed.commandProcessor, TheSeed.CommandList)
            if cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.is_set():
                cls._closeTheSeed()
                return
            cls.THESEED_CORE_INSTANCE._MainEventLoop.run_until_complete(cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.wait())
            cls._closeTheSeed()
        except KeyboardInterrupt:
            cls.linkStop()
            cls._closeTheSeed()
        except Exception as e:
            cls.linkStop()
            cls._closeTheSeed()
            raise RuntimeError(f"TheSeed start failed : {str(e)}")

    @classmethod
    def _closeTheSeed(cls):
        if _TheSeedCore.IS_CLOSING:
            return
        cls.THESEED_CORE_INSTANCE._cleanup()
        _TheSeedCore.IS_CLOSING = True
        if cls.THESEED_CORE_INSTANCE._MainEventLoop.is_running():
            cls.THESEED_CORE_INSTANCE._MainEventLoop.stop()
        cls.THESEED_CORE_INSTANCE._MainEventLoop.close()

    @classmethod
    def _cleanup(cls):
        cls.THESEED_CORE_INSTANCE.BasicThreadPool.addAsyncTask(task=cls.THESEED_CORE_INSTANCE.HttpServer.stopHTTPServer, thread_label="TheSeed-Async")
        cls.THESEED_CORE_INSTANCE.BasicThreadPool.addAsyncTask(task=cls.THESEED_CORE_INSTANCE.WebSocketServer.stopWebSocketServer, thread_label="TheSeed-Async")
        cls.THESEED_CORE_INSTANCE.SQLiteDatabaseManager.closeAllDatabase()
        cls.THESEED_CORE_INSTANCE.RedisDatabaseManager.closeAllDatabase()
        cls.THESEED_CORE_INSTANCE.NodeService.stopAllNodeService()
        while True:
            if all([
                cls.THESEED_CORE_INSTANCE.HttpServer.IsClosed,
                cls.THESEED_CORE_INSTANCE.WebSocketServer.IsClosed,
                cls.THESEED_CORE_INSTANCE.SQLiteDatabaseManager.IsClosed,
                cls.THESEED_CORE_INSTANCE.RedisDatabaseManager.IsClosed,
                cls.THESEED_CORE_INSTANCE.NodeService.IsClosed
            ]):
                cls.THESEED_CORE_INSTANCE.BasicDatabaseManager.upsertItem("CloseTime", str(time.time()))
                cls.THESEED_CORE_INSTANCE.BasicDatabaseManager.closeDatabase()
                cls.THESEED_CORE_INSTANCE.BasicThreadPool.closeThreadPool()
                break

    @classmethod
    def _setupTheSeedCoreInterface(cls):
        attributes = [
            'Version', 'SystemBasicPath', 'ExternalLibraryPath', 'BasicDataPath', 'DatabasePath',
            'LogsPath', 'ExternalServicePath', 'Application', 'BasicHost', 'BasicHttpPort', 'BasicWsPort',
            'BasicLogger', 'BasicEncryptorLogger', 'BasicSQLiteDatabaseLogger', 'BasicRedisDatabaseLogger',
            'BasicThreadPoolLogger', 'BasicNetworkServicesLogger', 'BasicExternalServicesLogger',
            'BasicEncryptor', 'BasicDatabaseManager', 'BasicThreadPool', 'EncryptorManager',
            'SQLiteDatabaseManager', 'RedisDatabaseManager', 'HttpServer', 'WebSocketServer', 'NodeService'
        ]

        for attr in attributes:
            setattr(TheSeed, attr, getattr(cls.THESEED_CORE_INSTANCE, attr))

        TheSeed.linkStart = cls.linkStart
        TheSeed.linkStop = cls.linkStop

    @classmethod
    def _showBanner(cls):
        ft = pyfiglet.Figlet(font="slant", width=200)
        banner = "T h e S e e d"
        rendered_banner = ft.renderText(banner)
        if cls.BANNER_COLOR_MODE == "Gradient":
            colors = [Fore.BLUE, Fore.MAGENTA, Fore.GREEN, Fore.CYAN, Fore.YELLOW, Fore.RED]
            colored_text = ""
            for line in rendered_banner.splitlines():
                colored_line = ""
                for i, char in enumerate(line):
                    if char != ' ':
                        colored_line += colors[i % len(colors)] + char
                    else:
                        colored_line += char
                colored_text += colored_line + '\n'
            print(Style.BRIGHT + colored_text)
        else:
            print(Fore.MAGENTA + Style.BRIGHT + rendered_banner)
        print(Fore.MAGENTA + Style.BRIGHT + f"TheSeedCore version: {__Version__}")
        print(Fore.MAGENTA + Style.BRIGHT + f"Supported by B站疾风Kirito")

    @staticmethod
    def _checkFreePorts(num_ports=2, low_range=1024, high_range=65535):
        """
        检查并返回指定数量的可用端口号。

        参数:
            :param num_ports : 需要的可用端口数量。
            :param low_range : 端口号检查的下限。
            :param high_range : 端口号检查的上限。

        返回:
            :return : 可用端口号列表。
        """
        free_ports = []
        trials = 0
        while len(free_ports) < num_ports and trials < 1000:
            port = random.randint(low_range, high_range)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    s.listen(1)
                    free_ports.append(port)
                except socket.error:
                    pass
            trials += 1
        return free_ports

    def _setupPath(self):
        try:
            path_list = [
                self.SystemBasicPath,
                self.ExternalLibraryPath,
                self.BasicDataPath,
                self.DatabasePath,
                self.LogsPath,
                self.ExternalServicePath
            ]
            for path in path_list:
                if not os.path.exists(path):
                    os.makedirs(path)
            sys.path.insert(0, self.ExternalLibraryPath)
            os.environ["PYTHONPATH"] = self.ExternalLibraryPath + os.pathsep + os.environ.get("PYTHONPATH", "")
            sys.path.append(self.ExternalLibraryPath)
        except IOError as e:
            raise RuntimeError(f"TheSeed error creating basic path: {e}")

    def _setupDatabase(self):
        """初始化TheSeed核心数据库。如果是首次运行，则进行数据库初始化配置。"""
        first_run = self.BasicDatabaseManager.searchItem("FirstRun")
        if not first_run:
            self.BasicDatabaseManager.initTheSeedDatabase()

    def _setupThreadPool(self):
        """初始化TheSeed核心线程池。"""
        self._PerformanceMode = self.BasicDatabaseManager.searchItem("PerformanceMode")[1]
        current_task_threshold = int(self.BasicDatabaseManager.searchItem("TaskThreshold")[1])
        if current_task_threshold != self._TaskThreshold:
            self.BasicDatabaseManager.upsertItem("TaskThreshold", str(self._TaskThreshold))
        else:
            self._TaskThreshold = current_task_threshold

    def _setupNetworkServiceAddress(self):
        current_host = self.BasicDatabaseManager.searchItem("TheSeedHost")[1]
        current_http_port = self.BasicDatabaseManager.searchItem("TheSeedHttpPort")[1]
        current_ws_port = self.BasicDatabaseManager.searchItem("TheSeedWsPort")[1]
        free_ports = self._checkFreePorts()
        if current_host == "":
            self.BasicDatabaseManager.upsertItem("TheSeedHost", "localhost")
            self.BasicHost = "localhost"
        else:
            self.BasicHost = current_host
        if current_http_port == "":
            self.BasicDatabaseManager.upsertItem("TheSeedHttpPort", str(free_ports[1]))
            self.BasicHttpPort = str(free_ports[1])
        else:
            self.BasicHttpPort = current_http_port
        if current_ws_port == "":
            self.BasicDatabaseManager.upsertItem("TheSeedWsPort", str(free_ports[0]))
            self.BasicWsPort = str(free_ports[0])
        else:
            self.BasicWsPort = current_ws_port


def linkStart(application: type, total_thread_count: int = None, sync_thread_labels: Optional[List[str]] = None, async_thread_labels: Optional[List[str]] = None, task_threshold: int = 10, load_balancing: bool = True, logger_backup_count: int = 30,
              banner_color_mode: Literal["Solid", "Gradient"] = "Solid", debug_mode: bool = False, *args, **kwargs):
    _TheSeedCore.linkStart(application, total_thread_count, sync_thread_labels, async_thread_labels, task_threshold, load_balancing, logger_backup_count, banner_color_mode, debug_mode, *args, **kwargs)


def linkStop():
    _TheSeedCore.linkStop()
