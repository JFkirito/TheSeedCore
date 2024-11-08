# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    # __init__
    "SystemType",
    "DevelopmentEnv",
    "RootDirectoryPath",
    "ExternalLibraryDirectoryPath",
    "ExternalServiceDirectoryPath",
    "DataDirectoryPath",
    "DatabaseDirectoryPath",
    "LogsDirectoryPath",
    "ConnectTheSeedCore",
    "MainEventLoop",
    "LinkStart",
    "LinkStop",
    # Common
    "TextColor",
    "PerformanceMonitor",
    # Concurrent
    "Priority",
    "ExpandPolicy",
    "ShrinkagePolicy",
    "TaskFuture",
    "serviceProcessID",
    "submitProcessTask",
    "submitThreadTask",
    "submitSystemProcessTask",
    "submitSystemThreadTask",
    "closeConcurrentSystem",
    # Database
    "SQLiteDatabase",
    "MySQLDatabase",
    # InstanceManager
    "DatabaseInstanceManager",
    "NetworkInstanceManager",
    # Logger
    "TheSeedCoreLogger",
    "consoleLogger",
    "LoggerManager",
    # Network
    "WebSocketServer",
    "WebSocketClient",
    "HTTPServer",
    # Security
    "AESEncryptor",
    "RSAEncryptor"
]

import asyncio
import os
import platform
import sys
from typing import TYPE_CHECKING, Optional, TypedDict, Literal, Unpack

if TYPE_CHECKING:
    pass

__version__: str = "0.1.1"
__author__: str = "B站疾风Kirito"
__website__: str = "https://space.bilibili.com/6440741"
__repository__: str = "https://github.com/JFkirito/TheSeedCore"

sys.set_int_max_str_digits(100000)
SystemType = platform.system()
DevelopmentEnv: bool = not hasattr(sys, "frozen") and not globals().get("__compiled__", False)
RootDirectoryPath: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if DevelopmentEnv else os.path.dirname(sys.executable)
ExternalLibraryDirectoryPath: str = os.path.join(RootDirectoryPath, "TheSeedCoreExternalLibrary")
ExternalServiceDirectoryPath: str = os.path.join(RootDirectoryPath, "TheSeedCoreExternalService")
DataDirectoryPath: str = os.path.join(RootDirectoryPath, "TheSeedCoreData")
DatabaseDirectoryPath: str = os.path.join(DataDirectoryPath, "Database")
LogsDirectoryPath: str = os.path.join(DataDirectoryPath, "Logs")

_MainEventLoop: Optional[asyncio.AbstractEventLoop] = None
_QtMode: bool = False

from ._Common import _checkPath, _checkPackageVersion, _checkPackage, _createPath, _addSystemPath  # noqa
from ._Common import *
from .Concurrent import _PySide6Support, _PyQt6Support, _PyQt5Support, _PyTorchSupport, _ConnectConcurrentSystem  # noqa
from .Concurrent import *
from .Database import *
from .InstanceManager import *
from .Logger import *
from .Network import *
from .Security import *

_checkPath(ExternalLibraryDirectoryPath, ExternalServiceDirectoryPath, DataDirectoryPath, DatabaseDirectoryPath, LogsDirectoryPath)


class _TheSeedCoreConfig(TypedDict, total=False):
    check_env: bool
    quit_qapp: bool
    handle_sigint: bool
    MainPriority: Literal[
        Priority.IDLE,
        Priority.BELOW_NORMAL,
        Priority.NORMAL,
        Priority.ABOVE_NORMAL,
        Priority.HIGH,
        Priority.REALTIME,
    ]
    CoreProcessCount: Optional[int]
    CoreThreadCount: Optional[int]
    MaximumProcessCount: Optional[int]
    MaximumThreadCount: Optional[int]
    IdleCleanupThreshold: Optional[int]
    TaskThreshold: Optional[int]
    GlobalTaskThreshold: Optional[int]
    ProcessPriority: Literal[
        Priority.IDLE,
        Priority.BELOW_NORMAL,
        Priority.NORMAL,
        Priority.ABOVE_NORMAL,
        Priority.HIGH,
        Priority.REALTIME,
    ]
    ExpandPolicy: Literal[
        ExpandPolicy.NoExpand,
        ExpandPolicy.AutoExpand,
        ExpandPolicy.BeforehandExpand,
    ]
    ShrinkagePolicy: Literal[
        ShrinkagePolicy.NoShrink,
        ShrinkagePolicy.AutoShrink,
        ShrinkagePolicy.TimeoutShrink,
    ]
    ShrinkagePolicyTimeout: Optional[int]
    PerformanceReport: bool


def _checkQtApplicationInstance():
    """
    Checks if a Qt application instance is currently running.

    This function verifies whether a Qt application instance exists for the supported
    Qt libraries (PySide6, PyQt6, or PyQt5). If an instance is found, it returns
    True; otherwise, it returns False. If none of the Qt libraries are available,
    it raises an ImportError.

    :raises ImportError: If no supported Qt libraries are found.

    :return: True if a Qt application instance exists, False otherwise.
    setup:
        1. Check if PySide6 is supported.
            1.1 If so, attempt to import QApplication from PySide6 and check for an instance.
        2. Check if PyQt6 is supported.
            2.1 If so, attempt to import QApplication from PyQt6 and check for an instance.
        3. Check if PyQt5 is supported.
            3.1 If so, attempt to import QApplication from PyQt5 and check for an instance.
        4. If no supported Qt library is available, raise ImportError.
    """

    if _PySide6Support:
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    if _PyQt6Support:
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    if _PyQt5Support:
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    raise ImportError("Qt is not available.")


# noinspection PyUnresolvedReferences
def _connectLinkStop():
    """
    Sets up a connection to the application's quit event to trigger cleanup operations.

    This function connects the application's quit event to the LinkStop function,
    ensuring that the necessary cleanup procedures are performed when the application
    is about to exit. It checks for the presence of supported Qt libraries (PySide6,
    PyQt6, or PyQt5) and connects the quit event accordingly.

    setup:
        1. Check if PySide6 is supported and the application is running in Qt mode.
            1.1 If so, import QApplication from PySide6 and connect the quit event.
        2. Check if PyQt6 is supported and the application is running in Qt mode.
            2.1 If so, import QApplication from PyQt6 and connect the quit event.
        3. Check if PyQt5 is supported and the application is running in Qt mode.
            3.1 If so, import QApplication from PyQt5 and connect the quit event.
    """

    global _QtMode
    if _PySide6Support and _QtMode:
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)
    elif _PyQt6Support and _QtMode:
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)
    elif _PyQt5Support and _QtMode:
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)


def _compareVersions(version1: str, version2: str):
    """
    Compares two version strings.

    This function compares two version strings in the format 'major.minor.patch'
    and returns:
        -1 if version1 is less than version2,
         0 if version1 is equal to version2,
         1 if version1 is greater than version2.

    :param version1: The first version string to compare.
    :param version2: The second version string to compare.
    :return: An integer indicating the comparison result.
        - Returns -1 if version1 < version2
        - Returns 0 if version1 == version2
        - Returns 1 if version1 > version2
    setup:
        1. Split both version strings into their respective parts.
        2. Normalize the lengths of the version parts by extending with zeros.
        3. Compare the parts in order until a difference is found or all parts are equal.
    """

    v1_parts = [int(part) for part in version1.split('.')]
    v2_parts = [int(part) for part in version2.split('.')]
    length = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (length - len(v1_parts)))
    v2_parts.extend([0] * (length - len(v2_parts)))

    for v1, v2 in zip(v1_parts, v2_parts):
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
    return 0


def _createMainEventLoop(**config: Unpack[_TheSeedCoreConfig]) -> asyncio.AbstractEventLoop:
    """
    Creates the main asyncio event loop for TheSeedCore.

    This function checks for the availability of Qt support (PySide6, PyQt6, PyQt5) and
    configures the appropriate event loop accordingly. If a Qt application instance exists,
    it sets up the event loop to work seamlessly with Qt's event handling.

    :param config: Configuration options to customize the behavior of the event loop.
        - quit_qapp: A boolean indicating whether to quit the Qt application.
        - handle_sigint: A boolean indicating whether to handle SIGINT signals.
    :return: The configured asyncio event loop instance.
    :raise: Raises an exception if no suitable Qt framework is found or if event loop creation fails.
    setup:
        1. Check for PySide6 support and its application instance.
            1.1. If supported, compare the version and set the event loop policy accordingly.
        2. Check for PyQt6 support and its application instance.
            2.1. Set up the event loop if supported.
        3. Check for PyQt5 support and its application instance.
            3.1. Set up the event loop if supported.
        4. If no Qt support, default to the standard asyncio event loop.
    """

    global _QtMode
    if _PySide6Support and _checkQtApplicationInstance():
        if _compareVersions(_checkPackageVersion("PySide6"), "6.7.0") < 0:
            from PySide6.QtAsyncio import QAsyncioEventLoopPolicy
            default_event_loop_policy = asyncio.get_event_loop_policy()
            asyncio.set_event_loop_policy(QAsyncioEventLoopPolicy(quit_qapp=config.get("quit_qapp", True), handle_sigint=config.get("handle_sigint", False)))
            main_event_loop = asyncio.get_event_loop()
            asyncio.set_event_loop_policy(default_event_loop_policy)
            _QtMode = True
        elif _checkPackage("qasync"):
            import qasync
            from PySide6.QtWidgets import QApplication
            main_event_loop = qasync.QEventLoop(QApplication.instance())
            asyncio.set_event_loop(main_event_loop)
            _QtMode = True
        else:
            main_event_loop = asyncio.get_event_loop()
    elif _PyQt6Support and _checkQtApplicationInstance():
        if _checkPackage("qasync"):
            import qasync
            # noinspection PyUnresolvedReferences
            from PyQt6.QtWidgets import QApplication
            main_event_loop = qasync.QEventLoop(QApplication.instance())
            asyncio.set_event_loop(main_event_loop)
            _QtMode = True
        else:
            main_event_loop = asyncio.get_event_loop()
    elif _PyQt5Support and _checkQtApplicationInstance():
        if _checkPackage("qasync"):
            import qasync
            # noinspection PyUnresolvedReferences
            from PyQt5.QtWidgets import QApplication
            main_event_loop = qasync.QEventLoop(QApplication.instance())
            asyncio.set_event_loop(main_event_loop)
            _QtMode = True
        else:
            main_event_loop = asyncio.get_event_loop()
    else:
        main_event_loop = asyncio.get_event_loop()

    return main_event_loop


def _showSupportInfo(qt_support: bool):
    """
    Displays support information regarding various modules and features available in TheSeedCore.

    This function checks for the availability of Qt support, PyTorch support,
    security modules, database support, and network support. It prints messages to
    the console indicating whether each feature is available or not, and provides
    installation instructions for missing packages.

    :param qt_support: A boolean indicating whether Qt support is available.
    :return: None
    :raise: This function does not raise exceptions, but will output messages to the console.
    setup:
        1. Check if Qt mode is supported and print the appropriate message.
        2. Check if GPU boost is available with PyTorch and print the appropriate message.
        3. Check if the security module is available and provide installation guidance if not.
        4. Check if MySQL database support is available and provide installation guidance if not.
        5. Check if websocket support is available and provide installation guidance if not.
        6. Check if HTTP server support is available and provide installation guidance if not.
    """

    if not qt_support:
        print(TextColor.YELLOW_BOLD.value + "[QtSupport] Qt mode is not available. If you want to use QtMode, please install [PySide6] or [PyQt6] or [PyQt5] packages" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[QtSupport] Qt mode is available." + TextColor.RESET.value)
    if not _PyTorchSupport:
        print(TextColor.YELLOW_BOLD.value + "[PyTorchSupport] GPU boost is not available." + TextColor.RESET.value)
        print(TextColor.YELLOW_BOLD.value + "[PyTorchSupport] If you want to use GPU boost, please use [pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121] command to install PyTorch packages" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[PyTorchSupport] GPU boost is available." + TextColor.RESET.value)
    if not _checkPackage("keyring") and not _checkPackage("pycryptodome"):
        print(TextColor.YELLOW_BOLD.value + "[SecuritySupport] Security module is not available. If you want to use security module, please install [keyring, pycryptodome] packages" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[SecuritySupport] Security module is available." + TextColor.RESET.value)
    if not _checkPackage("mysql"):
        print(TextColor.YELLOW_BOLD.value + "[DatabaseSupport] MySQL database is not available. If you want to use MySQL database, please install [mysql-connector-python] package" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[DatabaseSupport] MySQL database is available." + TextColor.RESET.value)
    if not _checkPackage("certifi") or not _checkPackage("websockets"):
        print(TextColor.YELLOW_BOLD.value + "[NetworkSupport] websocket is not available. If you want to use websocket service, please install [certifi, websockets] packages" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[NetworkSupport] websocket is available." + TextColor.RESET.value)
    if not _checkPackage("aiohttp"):
        print(TextColor.YELLOW_BOLD.value + "[NetworkSupport] http server is not available. If you want to use http server, please install [aiohttp] package" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[NetworkSupport] http server is available." + TextColor.RESET.value)


def _showBanner(service_process_id: int):
    """
    Displays a banner with information about the TheSeedCore service.

    This function prints a stylized text banner to the console, showcasing the
    TheSeedCore logo, version number, and process IDs. The banner also includes
    the address of the latest repositories for TheSeedCore.

    :param service_process_id: The process ID of the service process.
    :return: None
    :raise: This function does not raise exceptions, but will output to the console.
    setup:
        1. Print the TheSeedCore logo.
        2. Display the current version of TheSeedCore.
        3. Show the Main Process ID of the application.
        4. Show the Service Process ID passed as a parameter.
        5. Display the latest repositories address.
    """

    print(TextColor.PURPLE_BOLD.value + "  ______    __           _____                   __   ______                     ")
    print(TextColor.PURPLE_BOLD.value + " /_  __/   / /_   ___   / ___/  ___   ___   ____/ /  / ____/  ____    _____  ___ ")
    print(TextColor.PURPLE_BOLD.value + "  / /     / __ \\ / _ \\  \\__ \\  / _ \\ / _ \\ / __  /  / /      / __ \\  / ___/ / _ \\")
    print(TextColor.PURPLE_BOLD.value + " / /     / / / //  __/ ___/ / /  __//  __// /_/ /  / /___   / /_/ / / /    /  __/")
    print(TextColor.PURPLE_BOLD.value + "/_/     /_/ /_/ \\___/ /____/  \\___/ \\___/ \\__,_/   \\____/   \\____/ /_/     \\___/ ")
    print(TextColor.PURPLE_BOLD.value + "                                                                                 " + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"\nTheSeedCore version: {__version__}" + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"MainProcess ID - [{os.getpid()}]" + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"ServiceProcess ID - [{service_process_id}]" + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"Latest repositories address {__repository__}" + TextColor.RESET.value)


def _cleanupDatabase():
    """
    Cleans up the databases by deleting all active SQLite and MySQL database instances.

    This function retrieves all instances of SQLite and MySQL databases managed
    by the DatabaseInstanceManager. It iterates through each instance and calls
    the `deleteDatabase` method to remove them from storage.

    :return: None
    :raise: This function does not raise exceptions, but will log errors
            if any occur during the deletion process of the databases.
    setup:
        1. Retrieve all SQLite database instances.
        2. Retrieve all MySQL database instances.
        3. Call the deleteDatabase method for each SQLite database instance.
        4. Call the deleteDatabase method for each MySQL database instance.
    """

    all_sqlite_database = DatabaseInstanceManager.getAllSQLiteDatabaseInstances()
    all_mysql_database = DatabaseInstanceManager.getAllMySQLDatabaseInstances()
    for sqlite_database_instance in all_sqlite_database.values():
        sqlite_database_instance.deleteDatabase()
    for mysql_database_instance in all_mysql_database.values():
        mysql_database_instance.deleteDatabase()


def _cleanupNetworkService():
    """
    Cleans up the network services by stopping all active HTTP and WebSocket servers.

    This function retrieves all instances of HTTP and WebSocket servers managed
    by the NetworkInstanceManager and initiates their shutdown processes. It
    submits the stop tasks to a thread pool for asynchronous execution. The
    function then waits until all HTTP and WebSocket server instances have
    completed their shutdown procedures before returning.

    :return: None
    :raise: This function does not raise exceptions, but will log errors
            if any occur during the shutdown process of the servers.
    setup:
        1. Retrieve all HTTP server instances.
        2. Retrieve all WebSocket server instances.
        3. Submit stop tasks for each HTTP server instance.
        4. Submit stop tasks for each WebSocket server instance.
        5. Wait for all HTTP server instances to close.
        6. Wait for all WebSocket server instances to close.
    """

    all_http_server = NetworkInstanceManager.getAllHTTPServerInstances()
    all_websocket_server = NetworkInstanceManager.getAllWebSocketServerInstances()
    for http_server_instance in all_http_server.values():
        submitThreadTask(http_server_instance.stopHTTPServer)
    for websocket_server_instance in all_websocket_server.values():
        submitThreadTask(websocket_server_instance.stopWebSocketServer)
    while True:
        if all([http_server_instance.IsClosed for http_server_instance in all_http_server.values()]):
            break
    while True:
        if all([websocket_server_instance.IsClosed for websocket_server_instance in all_websocket_server.values()]):
            break


def MainEventLoop() -> asyncio.AbstractEventLoop:
    """
    Retrieves the current main event loop for TheSeedCore.

    This function accesses the global variable that holds the main event loop
    instance and returns it. The event loop is used for managing asynchronous
    operations within the TheSeedCore framework.

    :return: The main event loop instance of type asyncio.AbstractEventLoop.
    :raise: Raises a NameError if the global main event loop variable is not defined.
    """

    global _MainEventLoop
    return _MainEventLoop


def ConnectTheSeedCore(**config: Unpack[_TheSeedCoreConfig]):
    """
    Establishes a connection to the TheSeedCore system using the provided configuration.

    This function initializes the main event loop and connects the concurrent system.
    If the 'check_env' parameter is set to True in the configuration, it will display
    support information for the current environment. It also displays a banner
    with the service process ID after establishing the connection.

    :param config: Keyword arguments representing configuration options for connecting to TheSeedCore.
    :return: None
    :raise: Raises exceptions related to the event loop creation or connection processes.

    setup:
        1. Create the main event loop with the provided configuration.
        2. Optionally display environment support information based on configuration.
        3. Connect the concurrent system to the main event loop.
        4. Show a banner displaying the service process ID.
    """

    global _MainEventLoop
    _MainEventLoop = _createMainEventLoop(**config)
    if config.get("check_env", False):
        _showSupportInfo(_QtMode)
    _ConnectConcurrentSystem(_MainEventLoop, **config)
    _showBanner(serviceProcessID())
    _connectLinkStop()


def LinkStart():
    """
    Starts the main event loop for the application and indicates that the system
    is ready for operations.

    This function prints a message to the console indicating that the connection
    has been established and the system is now standing by. It then enters an
    infinite loop to keep the event loop running until explicitly stopped.

    :return: None
    :raise: Raises exceptions if the event loop encounters errors during execution.

    setup:
        1. Print a confirmation message indicating the system is ready.
        2. Call `run_forever` on the main event loop to start processing events.
    """

    global _MainEventLoop
    print(TextColor.GREEN_BOLD.value + f"TheSeedCore connection completed. System standing by...\n" + TextColor.RESET.value)
    _MainEventLoop.run_forever()


def LinkStop():
    """
    Safely stops the link services and performs necessary cleanup operations.

    This function orchestrates the shutdown process by calling various cleanup
    methods to ensure that all resources are released properly before stopping the
    link services.

    :return: None
    :raise: Raises exceptions if any cleanup operation fails.

    setup:
        1. Call `_cleanupDatabase` to release database resources.
        2. Call `_cleanupNetworkService` to stop any network services.
        3. Invoke `closeConcurrentSystem` to close any concurrent operations or threads.
    """

    _cleanupDatabase()
    _cleanupNetworkService()
    closeConcurrentSystem()
    if not _QtMode:
        _MainEventLoop.stop()
