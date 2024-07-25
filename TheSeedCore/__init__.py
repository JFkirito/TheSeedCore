# -*- coding: utf-8 -*-
"""
TheSeedCore Framework

This module serves as the main entry point for the TheSeedCore framework, providing initialization, configuration,
and control for various system components such as concurrency systems, database management, encryption, logging, and networking services.

Classes:
    - TheSeed:
        A core class that represents the main interface to the TheSeedCore framework.
        It provides methods for submitting tasks and accessing various subsystems like HTTP servers, WebSocket servers, database managers, and more.

    - _TheSeedCore:
        A singleton class responsible for initializing and managing the core components of TheSeedCore.
        It includes methods for starting and stopping the system, setting up paths, databases, and network services.

Functions:
    - linkStart:
        Starts the TheSeedCore framework by setting up the necessary configurations and launching the main application class.

    - linkStop:
        Stops the TheSeedCore framework gracefully, ensuring all services and resources are properly closed.

Features:
    - PyTorch and CUDA Support:
        Detects the availability of PyTorch and CUDA for potential GPU acceleration.

    - Concurrency System:
        Provides task management for both process and thread-based concurrency.

    - Database Management:
        Manages SQLite and Redis databases, with support for encryption and logging.

    - Networking Services:
        Includes HTTP and WebSocket servers for handling network communications.

    - Logging:
        Configures and manages logging for various system components, supporting both file and console outputs.

Common Parameters:
    - Host: The server's host address.
    - Port: The server's port number.
    - Logger: A logger instance for recording activities and errors.

This module ensures that all core components are initialized in a proper sequence, providing a seamless and efficient setup for TheSeedCore applications.
"""

from __future__ import annotations

try:
    # noinspection PyUnresolvedReferences
    import torch

    if torch.cuda.is_available():
        _AvailableCUDADevicesID = [cuda_device_id for cuda_device_id in range(torch.cuda.device_count())]
        _PyTorchSupport = True
    else:
        _AvailableCUDADevicesID = []
        _PyTorchSupport = False
except ImportError as PyTorchImportError:
    _AvailableCUDADevicesID = []
    _PyTorchSupport = False
import random
import socket
import sys

import pyfiglet

from colorama import init, Fore, Style
from .ConcurrencySystemModule import *
from .ConfigModule import *
from .DatabaseModule import *
from .EncryptionModule import *
from .ExternalServicesModule import *
from .LoggerModule import *
from .KafkaServiceModule import KafkaService
from .NetworkModule import *

if TYPE_CHECKING:
    pass

__Version__ = "0.0.7"


class TheSeed:
    Version: str
    SystemBasicPath: str
    ExternalLibraryPath: str
    BasicDataPath: str
    BasicDatabasePath: str
    LogsPath: str
    ExternalServicePath: str
    Application: type
    BasicHost: str
    BasicHttpPort: str
    BasicWsPort: str
    BasicLogger: TheSeedCoreLogger
    BasicEncryptorLogger: TheSeedCoreLogger
    BasicSQLiteDatabaseLogger: TheSeedCoreLogger
    BasicRedisDatabaseLogger: TheSeedCoreLogger
    BasicNetworkServicesLogger: TheSeedCoreLogger
    BasicExternalServicesLogger: TheSeedCoreLogger
    BasicEncryptor: TheSeedCoreEncryptor
    BasicDatabaseManager: TheSeedCoreSQLiteDatabase
    ConcurrencySystem: TheSeedCoreConcurrencySystem
    EncryptorManager: EncryptorManager
    SQLiteDatabaseManager: SQLiteDatabaseManager
    MySQLDatabaseManager: MySQLDatabaseManager
    RedisDatabaseManager: RedisDatabaseManager
    HttpServer: HTTPServer
    WebSocketServer: WebSocketServer
    KafkaService: KafkaService
    NodeService: NodeService
    linkStart: classmethod
    linkStop: classmethod

    @classmethod
    def submitProcessTask(cls, task: callable, priority: int = 0, *args, **kwargs):
        cls.ConcurrencySystem.submitProcessTask(task, priority, *args, **kwargs)

    @classmethod
    def submitThreadTask(cls, task: callable, priority: int = 0, *args, **kwargs):
        cls.ConcurrencySystem.submitThreadTask(task, priority, *args, **kwargs)


class _TheSeedCore:
    LINK_START: bool = False
    THESEED_CORE_INSTANCE: Union[None, _TheSeedCore] = None
    APPLICATION: type = None
    BASIC_SYSTEM_PATH: str = None
    CONCURRENCY_SYSTEM_CONFIG: ConcurrencySystemConfig = None
    BANNER_MODE: Literal["Solid", "Gradient"] = "Solid"
    DEBUG_MODE: bool = False
    ARGS: Union[None, tuple, list] = None
    KWARGS: Union[None, dict] = None
    IS_CLOSING: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls.LINK_START:
            raise RuntimeError("TheSeedCore must first be started using the 'link start' method.")
        if not cls.THESEED_CORE_INSTANCE:
            cls.THESEED_CORE_INSTANCE = super(_TheSeedCore, cls).__new__(cls, *args, **kwargs)
        return cls.THESEED_CORE_INSTANCE

    def __init__(self):
        sys.set_int_max_str_digits(100000)
        init(autoreset=True)
        self.Version = __Version__
        self.SystemBasicPath = _TheSeedCore.BASIC_SYSTEM_PATH
        self.ExternalLibraryPath = os.path.join(self.SystemBasicPath, "ExternalLibrary")
        self.BasicDataPath = os.path.join(self.SystemBasicPath, "TheSeedData")
        self.BasicDatabasePath = os.path.join(self.BasicDataPath, "Database")
        self.LogsPath = os.path.join(self.BasicDataPath, "Logs")
        self.ExternalServicePath = os.path.join(self.BasicDataPath, "ExternalService")
        self._setupPath()

        self.Application = None
        self._MainEventLoop = asyncio.new_event_loop()
        self._AsyncCloseEvent = asyncio.Event()

        self.BasicHost: str = ""
        self.BasicHttpPort: str = ""
        self.BasicWsPort: str = ""

        self.BasicLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreLog", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicEncryptorLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreEncryptor", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicSQLiteDatabaseLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreSQLiteDatabase", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicMySQLDatabaseLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreMySQLDatabase", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicRedisDatabaseLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreRedisDatabase", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicNetworkServicesLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreNetworkServices", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicKafkaServiceLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreKafkaServices", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))
        self.BasicExternalServicesLogger = TheSeedCoreLogger(LoggerConfig("TheSeedCoreExternalServices", self.LogsPath, 30, logging.DEBUG, _TheSeedCore.DEBUG_MODE))

        self.BasicEncryptor = TheSeedCoreEncryptor(EncryptorConfig("TheSeedCore", self.BasicEncryptorLogger, None))
        self.BasicDatabaseManager = TheSeedCoreSQLiteDatabase(SQLiteDatabaseConfig("TheSeedCore", self.BasicDatabasePath, self.BasicSQLiteDatabaseLogger, self.BasicEncryptor, True))
        self._setupDatabase()
        self._setupNetworkServiceAddress()
        self.ConcurrencySystem = TheSeedCoreConcurrencySystem(_TheSeedCore.CONCURRENCY_SYSTEM_CONFIG)
        self.EncryptorManager = EncryptorManager(self.BasicEncryptorLogger)
        self.SQLiteDatabaseManager = SQLiteDatabaseManager(self.BasicSQLiteDatabaseLogger)
        self.MySQLDatabaseManager = MySQLDatabaseManager(self.BasicMySQLDatabaseLogger)
        self.RedisDatabaseManager = RedisDatabaseManager(self.BasicRedisDatabaseLogger)
        self.HttpServer = HTTPServer(self.BasicHost, self.BasicHttpPort, self.BasicNetworkServicesLogger)
        self.WebSocketServer = WebSocketServer(self.BasicHost, self.BasicWsPort, self.BasicNetworkServicesLogger)
        self.KafkaService = KafkaService(self.BasicKafkaServiceLogger)
        self.NodeService = NodeService(self.ExternalServicePath, self.BasicExternalServicesLogger)

    @classmethod
    def linkStart(cls, config: TheSeedCoreConfig):
        cls.LINK_START = True
        cls.APPLICATION = config.Application
        cls.CONCURRENCY_SYSTEM_CONFIG = config.ConcurrencySystemConfig
        cls.BASIC_SYSTEM_PATH = config.BasicSystemPath
        cls.BANNER_MODE = config.BannerMode
        cls.DEBUG_MODE = config.DebugMode
        cls.ARGS = config.Args
        cls.KWARGS = config.KwArgs
        cls._startTheSeed()

    @classmethod
    def linkStop(cls):
        cls.THESEED_CORE_INSTANCE.ConcurrencySystem.submitProcessTask(task=cls._stopTheSeedSignal, Callback=cls._stopTheSeed)

    @classmethod
    async def _callbackProcessor(cls):
        while not cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.is_set():
            tasks = []
            start_time = time.time()

            while (time.time() - start_time) < 1:
                try:
                    task_type, task_object, task_result = cls.THESEED_CORE_INSTANCE.ConcurrencySystem.CallbackQueue.get_nowait()
                    tasks.append((task_type, task_object, task_result))
                except queue.Empty:
                    continue

            for task_type, task_object, task_result in tasks:
                if task_type == "Callback":
                    if asyncio.iscoroutinefunction(task_object):
                        await task_object(task_result)
                    else:
                        task_object(task_result)
                elif task_type == "Rejected":
                    if asyncio.iscoroutinefunction(task_object.execute):
                        await task_object.execute()
                    else:
                        task_object.execute()
            await asyncio.sleep(0.1)

    @classmethod
    def _startTheSeed(cls):
        try:
            cls._showBanner()
            cls.THESEED_CORE_INSTANCE = _TheSeedCore()
            cls._setupTheSeedCoreInterface()
            asyncio.set_event_loop(cls.THESEED_CORE_INSTANCE._MainEventLoop)
            while cls.THESEED_CORE_INSTANCE is not None:
                break
            global _PyTorchSupport
            if _PyTorchSupport:
                print(Fore.GREEN + Style.BRIGHT + "PyTorch and CUDA is available, Allow GPU Boost")
            else:
                print(Fore.RED + Style.BRIGHT + "PyTorch or CUDA is not available, Deny GPU Boost")
            cls.THESEED_CORE_INSTANCE.BasicDatabaseManager.upsertItem("StartTime", str(time.time()))
            print(Fore.MAGENTA + Style.BRIGHT + "Connection completed system standing by...")
            cls.THESEED_CORE_INSTANCE.Application = cls.APPLICATION(*cls.ARGS, **cls.KWARGS)
            if cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.is_set():
                cls._closeTheSeed()
                return
            cls.THESEED_CORE_INSTANCE._MainEventLoop.run_until_complete(cls._callbackProcessor())
            if cls.THESEED_CORE_INSTANCE._MainEventLoop.is_running():
                cls.THESEED_CORE_INSTANCE._MainEventLoop.stop()
            cls.THESEED_CORE_INSTANCE._MainEventLoop.close()
        except (KeyboardInterrupt, SystemExit):
            cls._exceptionCloseTheSeed()
        except Exception as e:
            cls._exceptionCloseTheSeed()
            raise RuntimeError(f"TheSeed start failed : {str(e)}")

    @classmethod
    def _stopTheSeedSignal(cls):
        return True

    @classmethod
    def _stopTheSeed(cls, result):
        if result:
            cls._closeTheSeed()
            cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.set()

    @classmethod
    def _closeTheSeed(cls):
        if _TheSeedCore.IS_CLOSING:
            return
        cls.THESEED_CORE_INSTANCE._cleanup()
        _TheSeedCore.IS_CLOSING = True

    @classmethod
    def _exceptionCloseTheSeed(cls):
        cls._closeTheSeed()
        cls.THESEED_CORE_INSTANCE._AsyncCloseEvent.set()
        if cls.THESEED_CORE_INSTANCE._MainEventLoop.is_running():
            cls.THESEED_CORE_INSTANCE._MainEventLoop.stop()
        cls.THESEED_CORE_INSTANCE._MainEventLoop.close()

    def _cleanup(self):
        self.ConcurrencySystem.submitThreadTask(task=self.HttpServer.stopHTTPServer)
        self.ConcurrencySystem.submitThreadTask(task=self.WebSocketServer.stopWebSocketServer)
        self.SQLiteDatabaseManager.closeAllDatabase()
        self.RedisDatabaseManager.closeAllDatabase()
        self.NodeService.stopAllNodeService()
        while True:
            if all([
                self.HttpServer.IsClosed,
                self.WebSocketServer.IsClosed,
                self.SQLiteDatabaseManager.IsClosed,
                self.RedisDatabaseManager.IsClosed,
                self.NodeService.IsClosed
            ]):
                self.BasicDatabaseManager.upsertItem("CloseTime", str(time.time()))
                self.BasicDatabaseManager.closeDatabase()
                self.ConcurrencySystem.closeConcurrencySystem()
                break

    @classmethod
    def _setupTheSeedCoreInterface(cls):
        attributes = [
            'Version', 'SystemBasicPath', 'ExternalLibraryPath', 'BasicDataPath', 'BasicDatabasePath',
            'LogsPath', 'ExternalServicePath', 'Application', 'BasicHost', 'BasicHttpPort', 'BasicWsPort',
            'BasicLogger', 'BasicEncryptorLogger', 'BasicSQLiteDatabaseLogger', 'BasicRedisDatabaseLogger',
            'BasicNetworkServicesLogger', 'BasicExternalServicesLogger', 'BasicEncryptor', 'BasicDatabaseManager',
            'ConcurrencySystem', 'EncryptorManager', 'SQLiteDatabaseManager', 'MySQLDatabaseManager', 'RedisDatabaseManager', 'HttpServer',
            'WebSocketServer', 'KafkaService', 'NodeService'
        ]

        for attr in attributes:
            setattr(TheSeed, attr, getattr(cls.THESEED_CORE_INSTANCE, attr))

        TheSeed.linkStart = cls.linkStart
        TheSeed.linkStop = cls.linkStop

    @classmethod
    def _showBanner(cls):
        ft = pyfiglet.Figlet(font="slant", width=200)
        banner = "T h e S e e d C o r e"
        rendered_banner = ft.renderText(banner)
        if cls.BANNER_MODE == "Gradient":
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
        url = "https://space.bilibili.com/6440741"
        text = "B站疾风Kirito"
        print(Fore.MAGENTA + Style.BRIGHT + f"TheSeedCore version: {__Version__}")
        print(Fore.MAGENTA + Style.BRIGHT + f"Supported by {text} {url}")

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
                self.BasicDatabasePath,
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


def linkStart(application: type, basic_system_path: Union[None, str] = BASIC_SYSTEM_PATH, concurrency_system_config: ConcurrencySystemConfig = None, banner_mode: Literal["Solid", "Gradient"] = "Solid", debug_mode: bool = False, *args, **kwargs):
    """
    启动TheSeedCore框架。

    参数:
        :param application : 应用程序的主类。
        :param basic_system_path : 基础系统路径。
        :param concurrency_system_config: 并发系统配置。
        :param banner_mode : 横幅模式。
        :param debug_mode : 调试模式。
        :param args : 位置参数。
        :param kwargs : 关键字参数。
    """
    concurrency_system_config = concurrency_system_config if concurrency_system_config is not None else ConcurrencySystemConfig(debug_mode, None, None, None, None, None, None, None, None, None, None, None)
    config = TheSeedCoreConfig(application, concurrency_system_config, basic_system_path, banner_mode, debug_mode, args, kwargs)
    _TheSeedCore.linkStart(config)


def linkStop():
    _TheSeedCore.linkStop()
