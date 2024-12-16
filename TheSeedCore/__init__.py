# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import multiprocessing
import os
import sys
from importlib.metadata import version, PackageNotFoundError
from typing import TYPE_CHECKING, Optional, TypedDict, Literal, Unpack, Callable

from ._Common import _checkPackage, TextColor, PerformanceMonitor

if TYPE_CHECKING:
    pass

__all__ = [
    "DEVELOPMENT_ENV",
    "MainEventLoop",
    "ConnectTheSeedCore",
    "LinkStart",
    "LinkStop",
    "AsyncTask",
    "ProcessTask",
    "ThreadTask",

    # Concurrent
    "submitAsyncTask",
    "submitProcessTask",
    "submitThreadTask",
    "submitSystemProcessTask",
    "submitSystemThreadTask",
    "ProcessPriority",
    "ExpandPolicy",
    "ShrinkagePolicy",
    "TaskFuture",

    # Database
    "SQLiteDatabase",
    "MySQLDatabase",

    # Logger
    "consoleLogger",
    "TheSeedCoreLogger",

    # NetWork
    "WebSocketServer",
    "WebSocketClient",
    "HTTPServer",
    "AsyncFlask",
    "AsyncFastAPI",

    # Security
    "AESEncryptor",
    "RSAEncryptor"
]
__version__: str = "0.1.6"
__author__: str = "疾风Kirito"
__website__: str = "https://ns-cloud-backend-site"
__repository__: str = "https://github.com/JFkirito/TheSeedCore"

sys.set_int_max_str_digits(100000)
DEVELOPMENT_ENV: bool = not hasattr(sys, "frozen") and not globals().get("__compiled__", False)

_MAIN_EVENT_LOOP: Optional[asyncio.AbstractEventLoop] = None
_QT_MODE: bool = False
_CONNECTED: bool = False
_PYSIDE6_SUPPORT: bool = _checkPackage("PySide6")
_PYQT6_SUPPORT: bool = _checkPackage("PyQt6")
_PYQT5_SUPPORT: bool = _checkPackage("PyQt5")

from .Concurrent import _connectConcurrentSystem, _closeConcurrentSystem  # noqa
from .Network import _closeNetworkService  # noqa
from .Concurrent import *
from .Database import *
from .Logger import *
from .Network import *
from .Security import *


class _TheSeedCoreConfig(TypedDict, total=False):
    CheckEnv: bool
    QuitQApp: bool
    HandleSigint: bool
    MainProcessPriority: Literal[
        ProcessPriority.IDLE,
        ProcessPriority.BELOW_NORMAL,
        ProcessPriority.NORMAL,
        ProcessPriority.ABOVE_NORMAL,
        ProcessPriority.HIGH,
        ProcessPriority.REALTIME,
    ]
    CoreProcessCount: Optional[int]
    CoreThreadCount: Optional[int]
    MaximumProcessCount: Optional[int]
    MaximumThreadCount: Optional[int]
    IdleCleanupThreshold: Optional[int]
    TaskThreshold: Optional[int]
    GlobalTaskThreshold: Optional[int]
    SubProcessPriority: Literal[
        ProcessPriority.IDLE,
        ProcessPriority.BELOW_NORMAL,
        ProcessPriority.NORMAL,
        ProcessPriority.ABOVE_NORMAL,
        ProcessPriority.HIGH,
        ProcessPriority.REALTIME,
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
    global _PYSIDE6_SUPPORT, _PYQT6_SUPPORT, _PYQT5_SUPPORT
    if _PYSIDE6_SUPPORT:
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    if _PYQT6_SUPPORT:
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    if _PYQT5_SUPPORT:
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        if QApplication.instance():
            return True
        return False
    raise ImportError("Qt is not available.")


def _checkPackageVersion(package_name: str) -> Optional[str]:
    try:
        package_version = version(package_name)
        return package_version
    except PackageNotFoundError:
        return None


def _compareVersions(current_version: str, target_version: str, comparison: Literal["==", "!=", "<", "<=", ">", ">="]) -> bool:
    v1_parts = [int(part) for part in current_version.split('.')]
    v2_parts = [int(part) for part in target_version.split('.')]
    length = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (length - len(v1_parts)))
    v2_parts.extend([0] * (length - len(v2_parts)))
    if comparison == "==":
        return v1_parts == v2_parts
    elif comparison == "!=":
        return v1_parts != v2_parts
    elif comparison == "<":
        return v1_parts < v2_parts
    elif comparison == "<=":
        return v1_parts <= v2_parts
    elif comparison == ">":
        return v1_parts > v2_parts
    elif comparison == ">=":
        return v1_parts >= v2_parts
    else:
        raise ValueError(f"Invalid comparison operator: {comparison}")


def _createMainEventLoop(**config: Unpack[_TheSeedCoreConfig]) -> asyncio.AbstractEventLoop:
    global _PYSIDE6_SUPPORT, _PYQT6_SUPPORT, _PYQT5_SUPPORT, _QT_MODE
    if _PYSIDE6_SUPPORT and _checkQtApplicationInstance():
        if _compareVersions(_checkPackageVersion("PySide6"), "6.7.0", ">="):
            # noinspection PyUnresolvedReferences
            from PySide6.QtAsyncio import QAsyncioEventLoopPolicy
            default_event_loop_policy = asyncio.get_event_loop_policy()
            asyncio.set_event_loop_policy(QAsyncioEventLoopPolicy(quit_qapp=config.get("QuitQApp", True), handle_sigint=config.get("HandleSigint", True)))
            main_event_loop = asyncio.get_event_loop()
            asyncio.set_event_loop_policy(default_event_loop_policy)
            _QT_MODE = True
        elif _checkPackage("qasync"):
            # noinspection PyUnresolvedReferences
            import qasync
            # noinspection PyUnresolvedReferences
            from PySide6.QtWidgets import QApplication
            main_event_loop = qasync.QEventLoop(QApplication.instance())
            asyncio.set_event_loop(main_event_loop)
            _QT_MODE = True
        else:
            main_event_loop = asyncio.get_event_loop()
    elif _PYQT6_SUPPORT and _checkQtApplicationInstance() and _checkPackage("qasync"):
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        main_event_loop = qasync.QEventLoop(QApplication.instance())
        asyncio.set_event_loop(main_event_loop)
        _QT_MODE = True
    elif _PYQT5_SUPPORT and _checkQtApplicationInstance() and _checkPackage("qasync"):
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        main_event_loop = qasync.QEventLoop(QApplication.instance())
        asyncio.set_event_loop(main_event_loop)
        _QT_MODE = True
    else:
        main_event_loop = asyncio.get_event_loop()

    return main_event_loop


def _showSupportInfo():
    if not _QT_MODE:
        print(TextColor.YELLOW_BOLD.value + "[QtSupport] Qt mode is not available. If you want to use QtMode, please install [PySide6] or [PyQt6] or [PyQt5] packages" + TextColor.RESET.value)
    else:
        print(TextColor.GREEN_BOLD.value + "[QtSupport] Qt mode is available." + TextColor.RESET.value)
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
    print(TextColor.PURPLE_BOLD.value + "  ______    __           _____                   __   ______                     ")
    print(TextColor.PURPLE_BOLD.value + " /_  __/   / /_   ___   / ___/  ___   ___   ____/ /  / ____/  ____    _____  ___ ")
    print(TextColor.PURPLE_BOLD.value + "  / /     / __ \\ / _ \\  \\__ \\  / _ \\ / _ \\ / __  /  / /      / __ \\  / ___/ / _ \\")
    print(TextColor.PURPLE_BOLD.value + " / /     / / / //  __/ ___/ / /  __//  __// /_/ /  / /___   / /_/ / / /    /  __/")
    print(TextColor.PURPLE_BOLD.value + "/_/     /_/ /_/ \\___/ /____/  \\___/ \\___/ \\__,_/   \\____/   \\____/ /_/     \\___/ ")
    print(TextColor.PURPLE_BOLD.value + "                                                                                 " + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"\nTheSeedCore version: {__version__}" + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"MainProcess ID - [{os.getpid()}]" + TextColor.RESET.value)
    if service_process_id != 0:
        print(TextColor.PURPLE_BOLD.value + f"ServiceProcess ID - [{service_process_id}]" + TextColor.RESET.value)
    print(TextColor.PURPLE_BOLD.value + f"Latest repositories address {__repository__}\n" + TextColor.RESET.value)


# noinspection PyUnresolvedReferences
def _connectLinkStop():
    global _PYSIDE6_SUPPORT, _PYQT6_SUPPORT, _PYQT5_SUPPORT, _QT_MODE
    if _PYSIDE6_SUPPORT and _QT_MODE:
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)
        return
    if _PYQT6_SUPPORT and _QT_MODE:
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)
        return
    if _PYQT5_SUPPORT and _QT_MODE:
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(LinkStop)
        return


def MainEventLoop() -> asyncio.AbstractEventLoop:
    global _MAIN_EVENT_LOOP, _CONNECTED
    if not _CONNECTED:
        raise RuntimeError("TheSeedCore is not connected.")
    return _MAIN_EVENT_LOOP


def AsyncTask(func: Optional[Callable] = None) -> Callable:
    def decorator(actual_func: Callable) -> Callable:
        if not asyncio.iscoroutinefunction(actual_func):
            raise TypeError(f"The function <{actual_func.__name__}> must be a coroutine.")

        def wrapper(*args, **kwargs):
            func_future = MainEventLoop().create_task(actual_func(*args, **kwargs))
            return func_future

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def ProcessTask(priority=0, callback=None, future=None) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> TaskFuture:
            return submitProcessTask(func, priority, callback, future, *args, **kwargs)

        return wrapper

    return decorator


def ThreadTask(priority=0, callback=None, future=None) -> Callable:
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> TaskFuture:
            return submitThreadTask(func, priority, callback, future, *args, **kwargs)

        return wrapper

    return decorator


def ConnectTheSeedCore(**config: Unpack[_TheSeedCoreConfig]):
    global _MAIN_EVENT_LOOP, DEVELOPMENT_ENV, _CONNECTED

    _MAIN_EVENT_LOOP = _createMainEventLoop(**config)
    check_env = config.get("CheckEnv", True)
    config_core_process_count = config.get("CoreProcessCount", None)
    config_core_thread_count = config.get("CoreThreadCount", None)
    shared_manager = None
    shared_manager_pid = 0
    if config_core_process_count is not None and config_core_process_count > 0:
        shared_manager = multiprocessing.Manager()
        shared_manager_pid = shared_manager._process.pid  # noqa
    _showBanner(shared_manager_pid)
    if check_env and DEVELOPMENT_ENV:
        _showSupportInfo()
    if config_core_process_count is not None or config_core_thread_count is not None:
        _connectConcurrentSystem(shared_manager, _MAIN_EVENT_LOOP, **config)
    _connectLinkStop()
    _CONNECTED = True
    print(TextColor.GREEN_BOLD.value + f"\nTheSeedCore connection completed. System standing by...\n" + TextColor.RESET.value)


def LinkStart():
    global _MAIN_EVENT_LOOP
    try:
        _MAIN_EVENT_LOOP.run_forever()
    except (BrokenPipeError, EOFError, KeyboardInterrupt, Exception) as e:
        print(TextColor.RED_BOLD.value + f"Error: {e}" + TextColor.RESET.value)


def LinkStop():
    global _MAIN_EVENT_LOOP, _QT_MODE
    _closeNetworkService()
    _closeConcurrentSystem()
    if not _QT_MODE:
        _MAIN_EVENT_LOOP.stop()
