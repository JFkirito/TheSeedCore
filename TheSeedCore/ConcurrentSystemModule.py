# -*- coding: utf-8 -*-
"""
TheSeedCore ConcurrentSystem

######################################################################################################################################
# This module provides a concurrent system implementation that includes
# configuration management, synchronization management, and task execution
# within processes and threads. It supports GPU acceleration, task retries,
# and callbacks through the use of Python's multiprocessing, threading, and
# asyncio libraries.

# Main functionalities:
# 1. Configuration management for process and thread handling.
# 2. Task synchronization and execution management.
# 3. Support for GPU-accelerated tasks.
# 4. Handling of tasks with different priority levels.
# 5. Integration with PyQt and PySide for GUI applications.

# Main components:
# 1. ConcurrentSystemConfig - Manages configuration settings.
# 2. _SynchronizationManager - Manages process and thread states.
# 3. _TaskObject - Encapsulates tasks with support for retries and GPU acceleration.
# 4. _ProcessObject - Handles task execution in separate processes.
# 5. _QtCallbackExecutor & _CoreCallbackExecutor - Manage task callbacks in Qt and core event loops.

# Design thoughts:
# 1. Modular approach:
#    a. The system is designed with distinct components like configuration management,
#       synchronization management, and task execution, ensuring modularity and separation of concerns.
#    b. Each component, such as _TaskObject or _ProcessObject, is designed to encapsulate specific
#       functionalities, allowing for easy maintenance and extension.
#
# 2. Asynchronous and parallel task execution:
#    a. The system leverages Python's asyncio for handling asynchronous tasks, improving performance
#       in I/O-bound scenarios.
#    b. For CPU-bound tasks, the system uses multiprocessing to spawn separate processes, ensuring
#       that Python's Global Interpreter Lock (GIL) does not hinder performance.
#    c. Threads are managed separately to handle tasks that may require concurrent access to shared
#       resources without significant CPU load.
#
# 3. GPU acceleration support:
#    a. The system detects available CUDA devices and supports GPU-accelerated task execution
#       when PyTorch is available.
#    b. Tasks that require GPU resources can be easily configured to utilize specific CUDA devices,
#       allowing for optimized performance in compute-intensive operations.
#
# 4. Task prioritization and management:
#    a. Tasks can be assigned different priority levels (high, medium, low), ensuring that critical
#       tasks are executed before less important ones.
#    b. The system maintains separate queues for each priority level, and tasks are processed accordingly.
#
# 5. Integration with GUI frameworks:
#    a. The module is compatible with PyQt5, PyQt6, and PySide6, providing support for callback management
#       within Qt event loops, making it suitable for GUI applications.
#    b. _QtCallbackExecutor and _CoreCallbackExecutor handle the execution of callbacks within these event loops,
#       ensuring that tasks can be integrated seamlessly into GUI applications.
#
# 6. Robust error handling and retries:
#    a. The system includes mechanisms for handling errors during task execution, including retries
#       with exponential backoff, ensuring that transient issues do not cause task failures.
#    b. Exception handling is designed to provide detailed tracebacks, aiding in debugging and resolving issues.
#
# 7. Resource management and cleanup:
#    a. The system includes features for cleaning up resources, such as GPU memory, after tasks are completed,
#       preventing resource leaks.
#    b. Processes and threads are monitored and managed to ensure that they do not remain active longer than necessary,
#       conserving system resources.

# Required dependencies:
# 1. Python libraries: asyncio, multiprocessing, threading, psutil, torch (optional for GPU support), PyQt5/PyQt6/PySide6 (optional for GUI support).
######################################################################################################################################
"""

from __future__ import annotations

__all__ = [
    "ConcurrentSystemConfig",
    "ConcurrentSystem",
    "ConnectConcurrentSystem",
    "PyTorchSupport",
    "AvailableCUDADevicesID",
    "PySide6Support",
    "PyQt6Support",
    "PyQt5Support",
    "QApplication"
]

import asyncio
import ctypes
import logging
import multiprocessing
import os
import pickle
import queue
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Union, Any, Dict, Tuple

import psutil

from . import _ColoredFormatter

if TYPE_CHECKING:
    pass

PyTorchSupport: bool = False
AvailableCUDADevicesID: list = []
PySide6Support: bool = False
PyQt6Support: bool = False
PyQt5Support: bool = False


def _checkDependencies():
    """
    检查当前环境中的依赖库是否可用，并根据结果设置全局变量的状态。

    参数：
        无

    返回：
        无

    执行过程：
        1. 检查是否支持PyTorch库及CUDA设备
            a. 尝试导入torch库并检测CUDA设备的可用性，设置相应的全局变量
            b. 如果导入失败或CUDA不可用，则设置PyTorchSupport为False，并将AvailableCUDADevicesID设为空列表
        2. 检查是否支持PySide6库
            a. 尝试导入qasync和PySide6的QApplication类，如果成功则设置PySide6Support为True
            b. 如果导入失败，则设置PySide6Support为False
        3. 检查是否支持PyQt6库
            a. 尝试导入qasync和PyQt6的QApplication类，如果成功则设置PyQt6Support为True
            b. 如果导入失败，则设置PyQt6Support为False
        4. 检查是否支持PyQt5库
            a. 尝试导入qasync和PyQt5的QApplication类，如果成功则设置PyQt5Support为True
            b. 如果导入失败，则设置PyQt5Support为False

    异常：
        1. ImportError：当尝试导入某个库失败时触发，但在代码中已经处理，不会抛出异常
    """

    global PyTorchSupport, AvailableCUDADevicesID, PySide6Support, PyQt6Support, PyQt5Support
    try:
        # noinspection PyUnresolvedReferences
        import torch

        if torch.cuda.is_available():
            AvailableCUDADevicesID = [cuda_device_id for cuda_device_id in range(torch.cuda.device_count())]
            PyTorchSupport = True
        else:
            AvailableCUDADevicesID = []
            PyTorchSupport = False
    except ImportError as _:
        AvailableCUDADevicesID = []
        PyTorchSupport = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication

        PySide6Support = True
    except ImportError as _:
        PySide6Support = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        PyQt6Support = True
    except ImportError as _:
        PyQt6Support = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        PyQt5Support = True
    except ImportError as _:
        PyQt5Support = False


_checkDependencies()

if PyTorchSupport:
    # noinspection PyUnresolvedReferences
    import torch
if PySide6Support:
    # noinspection PyUnresolvedReferences
    from PySide6.QtCore import QObject, Signal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PySide6.QtWidgets import QApplication
elif PyQt6Support:
    # noinspection PyUnresolvedReferences
    from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PyQt6.QtWidgets import QApplication
elif PyQt5Support:
    # noinspection PyUnresolvedReferences
    from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PyQt5.QtWidgets import QApplication
else:
    QThread = None
    QApplication = None


@dataclass
class ConcurrentSystemConfig:
    """
    并发系统配置类，配置并发系统的各项参数，包括进程和线程的数量、优先级、任务阈值以及扩展和收缩策略等。

    参数：
        :param - CoreProcessCount：核心进程的数量
        :param - CoreThreadCount：核心线程的数量
        :param - MaximumProcessCount：最大进程数量
        :param - MaximumThreadCount：最大线程数量
        :param - IdleCleanupThreshold：空闲清理阈值
        :param - ProcessPriority：进程的优先级
        :param - TaskThreshold：任务阈值
        :param - GlobalTaskThreshold：全局任务阈值
        :param - ExpandPolicy：扩展策略
        :param - ShrinkagePolicy：收缩策略
        :param - ShrinkagePolicyTimeout：收缩策略超时时间

    属性：
        - CoreProcessCount：核心进程的数量，默认为8
        - CoreThreadCount：核心线程的数量，默认为None
        - MaximumProcessCount：最大进程数量，默认为None
        - MaximumThreadCount：最大线程数量，默认为None
        - IdleCleanupThreshold：空闲清理阈值，默认为None
        - ProcessPriority：进程的优先级，默认为" NORMAL"
        - TaskThreshold：任务阈值，默认为None
        - GlobalTaskThreshold：全局任务阈值，默认为None
        - ExpandPolicy：扩展策略，默认为None
        - ShrinkagePolicy：收缩策略，默认为None
        - ShrinkagePolicyTimeout：收缩策略超时时间，默认为None

    设计思路：
        1. 配置系统的基本参数
            a. 设置核心进程和线程的数量
            b. 设置最大进程和线程的数量
            c. 设置空闲清理阈值和任务阈值
        2. 配置系统的优先级和策略
            a. 设定进程优先级
            b. 设定扩展和收缩策略及其相关参数
    """

    CoreProcessCount: Union[None, int] = None
    CoreThreadCount: Union[None, int] = None
    MaximumProcessCount: Union[None, int] = None
    MaximumThreadCount: Union[None, int] = None
    IdleCleanupThreshold: Union[None, int] = None
    ProcessPriority: Literal[None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = "NORMAL"
    TaskThreshold: Union[None, int] = None
    GlobalTaskThreshold: Union[None, int] = None
    ExpandPolicy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand"] = None
    ShrinkagePolicy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink"] = None
    ShrinkagePolicyTimeout: Union[None, int] = None


class _SynchronizationManager:
    """
    同步管理器，管理和协调进程和线程的状态，提供对进程和线程状态的存储和访问，并支持结果存储和任务锁定功能。

    参数：
        :param - SharedObjectManager: 多处理管理器，用于创建共享对象和同步原语

    属性：
        - SharedObjectManagerID：共享对象管理器的进程ID
        - CoreProcessStatusPool：核心进程状态池，存储每个核心进程的状态信息
        - ExpandProcessStatusPool：扩展进程状态池，存储每个扩展进程的状态信息
        - CoreThreadStatusPool：核心线程状态池，存储每个核心线程的状态信息
        - ExpandThreadStatusPool：扩展线程状态池，存储每个扩展线程的状态信息
        - ResultStorageQueue：结果存储队列，用于存储进程和线程的处理结果
        - TaskLock：任务锁，用于同步对任务的访问

    设计思路：
        1. 初始化共享对象管理器
            a. 获取共享对象管理器的进程ID
            b. 使用共享对象管理器创建字典和队列用于状态存储和结果存储
        2. 配置状态池
            a. 初始化核心进程和线程的状态池
            b. 初始化扩展进程和线程的状态池
        3. 配置同步原语
            a. 创建结果存储队列
            b. 创建任务锁，用于确保对任务的互斥访问
    """

    def __init__(self, SharedObjectManager: multiprocessing.Manager):
        # noinspection PyProtectedMember
        self.SharedObjectManagerID = SharedObjectManager._process.pid
        self.CoreProcessStatusPool: Dict[str, Tuple[int, int, int]] = SharedObjectManager.dict()
        self.ExpandProcessStatusPool: Dict[str, Tuple[int, int, int]] = SharedObjectManager.dict()
        self.CoreThreadStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ExpandThreadStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ResultStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.TaskLock: multiprocessing.Lock = multiprocessing.Lock()


class _ConfigManager:
    """
    配置管理器，确保配置值的有效性，并提供默认值和日志记录功能。

    参数：
        :param - SharedObjectManager: 用于创建共享对象的多处理管理器
        :param - Config: 传入的并发系统配置
        :param - DebugMode: 调试模式开关，默认为False

    属性：
        - PhysicalCores：物理CPU核心数
        - Logger：日志记录器
        - DebugMode：调试模式开关
        - CoreProcessCount：核心进程数量（共享对象）
        - CoreThreadCount：核心线程数量（共享对象）
        - MaximumProcessCount：最大进程数量（共享对象）
        - MaximumThreadCount：最大线程数量（共享对象）
        - IdleCleanupThreshold：空闲清理阈值（共享对象）
        - TaskThreshold：任务阈值（共享对象）
        - GlobalTaskThreshold：全局任务阈值（共享对象）
        - ProcessPriority：进程优先级（共享对象）
        - ExpandPolicy：扩展策略（共享对象）
        - ShrinkagePolicy：收缩策略（共享对象）
        - ShrinkagePolicyTimeout：收缩策略超时（共享对象）

    设计思路：
        1. 初始化配置
            a. 从传入的Config对象中读取并验证配置参数
            b. 使用共享对象管理器创建共享对象来存储配置参数
        2. 设置日志记录器
            a. 创建日志记录器并根据DebugMode设置适当的日志级别
            b. 配置日志格式和处理器
        3. 验证配置值
            a. 为每个配置参数提供验证逻辑，确保其值在合理范围内
            b. 在配置值无效时提供默认值，并记录相关日志
    """

    def __init__(self, SharedObjectManager: multiprocessing.Manager, Config: ConcurrentSystemConfig, DebugMode: bool = False):
        self.PhysicalCores = psutil.cpu_count(logical=False)
        self.Logger = None
        self.DebugMode = DebugMode
        self._setLogger()
        self.CoreProcessCount = SharedObjectManager.Value("i", self._validateCoreProcessCount(Config.CoreProcessCount))
        self.CoreThreadCount = SharedObjectManager.Value("i", self._validateCoreThreadCount(Config.CoreThreadCount))
        self.MaximumProcessCount = SharedObjectManager.Value("i", self._validateMaximumProcessCount(Config.MaximumProcessCount))
        self.MaximumThreadCount = SharedObjectManager.Value("i", self._validateMaximumThreadCount(Config.MaximumThreadCount))
        self.IdleCleanupThreshold = SharedObjectManager.Value("i", self._validateIdleCleanupThreshold(Config.IdleCleanupThreshold))
        self.TaskThreshold = SharedObjectManager.Value("i", self._validateTaskThreshold(Config.TaskThreshold))
        self.GlobalTaskThreshold = SharedObjectManager.Value("i", self._validateGlobalTaskThreshold(Config.GlobalTaskThreshold))
        self.ProcessPriority = SharedObjectManager.Value("c", self._validateProcessPriority(Config.ProcessPriority))
        self.ExpandPolicy = SharedObjectManager.Value("c", self._validateExpandPolicy(Config.ExpandPolicy))
        self.ShrinkagePolicy = SharedObjectManager.Value("c", self._validateShrinkagePolicy(Config.ShrinkagePolicy))
        self.ShrinkagePolicyTimeout = SharedObjectManager.Value("i", self._validateShrinkagePolicyTimeout(Config.ShrinkagePolicyTimeout))

    def _setLogger(self):
        """
        初始化并配置日志记录器，设置日志的输出级别和格式。

        参数：
            无

        返回：
            无

        执行过程：
            1. 创建日志记录器
                a. 使用指定的名称'ConcurrentSystem - ConfigManager'创建一个日志记录器
                b. 设置日志记录器的级别为DEBUG
            2. 配置控制台输出处理器
                a. 创建一个控制台输出处理器（StreamHandler）
                b. 根据DebugMode的状态设置控制台处理器的日志级别
                    - 如果DebugMode为True，设置为DEBUG级别
                    - 如果DebugMode为False，设置为DEBUG和WARNING中的较高级别
            3. 设置日志格式
                a. 使用_ColoredFormatter设置日志的输出格式，格式包括时间、名称、日志级别和消息内容
            4. 将处理器添加到日志记录器
                a. 将配置好的控制台处理器添加到日志记录器
            5. 将配置好的日志记录器保存到实例变量self.Logger中

        异常：
            无
        """

        logger = logging.getLogger('TheSeedCore - ConcurrentSystem - ConfigManager')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if self.DebugMode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        self.Logger = logger

    def _validateCoreProcessCount(self, core_process_count: int) -> int:
        """
        验证核心进程数量的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - core_process_count: 传入的核心进程数量

        返回：
            :return - int : 有效的核心进程数量

        执行过程：
            1. 设置默认值
                a. 将默认值设置为物理核心数的一半
            2. 检查是否传入核心进程数量
                a. 如果core_process_count为None，记录警告日志并返回默认值
            3. 验证核心进程数量的类型
                a. 如果core_process_count的类型不是整数，记录警告日志并返回默认值
            4. 验证核心进程数量的范围
                a. 如果core_process_count不在有效范围内（默认值到物理核心数之间），记录警告日志并返回默认值
            5. 返回有效的核心进程数量
                a. 如果core_process_count通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = self.PhysicalCores // 2
        if core_process_count is None:
            self.Logger.warning(f"Core process count not set, using default value {default_value}.")
            return default_value

        if not isinstance(core_process_count, int):
            self.Logger.warning(f"Invalid type for core process count '{core_process_count}'. Must be an integer; using default value {default_value}.")
            return default_value

        if not (default_value <= core_process_count <= self.PhysicalCores):
            self.Logger.warning(f"Core process count {core_process_count} is out of valid range ({default_value} to {self.PhysicalCores}); using default value {default_value}.")
            return default_value

        return core_process_count

    def _validateCoreThreadCount(self, core_thread_count: int) -> int:
        """
        验证核心线程数量的有效性，并在无效或未设置时提供默认值或进行调整。

        参数：
            :param - core_thread_count: 传入的核心线程数量

        返回：
            :return - int : 有效的核心线程数量

        执行过程：
            1. 设置默认值
                a. 默认值设置为核心进程数的两倍
            2. 检查是否传入核心线程数量
                a. 如果core_thread_count为None，记录警告日志并返回默认值
            3. 验证核心线程数量的类型
                a. 如果core_thread_count的类型不是整数，记录警告日志并返回默认值
            4. 验证核心线程数量是否小于最小值
                a. 如果core_thread_count小于默认值，记录警告日志并返回默认值
            5. 验证核心线程数量是否大于最大值
                a. 如果core_thread_count大于物理核心数的两倍，记录警告日志并返回默认值
            6. 验证核心线程数量是否为偶数
                a. 如果core_thread_count不是偶数，记录警告日志并将其调整为最接近的偶数
            7. 返回有效的核心线程数量
                a. 如果core_thread_count通过了所有验证，则返回调整后的核心线程数量

        异常：
            无
        """

        default_value = int(self.CoreProcessCount.value * 2)
        if core_thread_count is None:
            self.Logger.warning(f"Core thread count not set, using default value {default_value}.")
            return default_value

        if not isinstance(core_thread_count, int):
            self.Logger.warning(f"Invalid type for core thread count '{core_thread_count}'. Must be an integer; using default value {default_value}.")
            return default_value

        if core_thread_count < default_value:
            self.Logger.warning(f"Core thread count {core_thread_count} is less than the minimum allowed {default_value}. Using default value {default_value}.")
            adjusted_count = default_value
        elif core_thread_count > int(self.PhysicalCores * 2):
            self.Logger.warning(f"Core thread count {core_thread_count} exceeds the maximum allowed {int(self.PhysicalCores * 2)}. Using default value {default_value}.")
            adjusted_count = default_value
        elif core_thread_count % 2 != 0:
            self.Logger.warning(f"Core thread count {core_thread_count} is not an even number. Adjusting to {core_thread_count - 1}.")
            adjusted_count = core_thread_count - 1
        else:
            adjusted_count = core_thread_count
        return adjusted_count

    def _validateMaximumProcessCount(self, maximum_process_count: int) -> int:
        """
        验证最大进程数量的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - maximum_process_count: 传入的最大进程数量

        返回：
            :return - int : 有效的最大进程数量

        执行过程：
            1. 设置默认值
                a. 默认值设置为物理核心数
            2. 检查是否传入最大进程数量
                a. 如果maximum_process_count为None，记录警告日志并返回默认值
            3. 验证最大进程数量的类型
                a. 如果maximum_process_count的类型不是整数，记录警告日志并返回默认值
            4. 验证最大进程数量是否超过物理核心数
                a. 如果maximum_process_count超过物理核心数，记录警告日志并返回默认值
            5. 验证最大进程数量是否小于核心进程数量
                a. 如果maximum_process_count小于核心进程数量，记录警告日志并返回默认值
            6. 返回有效的最大进程数量
                a. 如果maximum_process_count通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = self.PhysicalCores
        if maximum_process_count is None:
            self.Logger.warning(f"Maximum process count not set, using default value: {default_value}.")
            return default_value

        if not isinstance(maximum_process_count, int):
            self.Logger.warning(f"Invalid type for maximum process count '{maximum_process_count}'. Must be an integer; using default value: {default_value}.")
            return default_value

        if maximum_process_count > self.PhysicalCores:
            self.Logger.warning(f"Maximum process count {maximum_process_count} exceeds the number of physical CPU cores ({self.PhysicalCores}). Using default value: {default_value}.")
            return default_value

        if maximum_process_count < self.CoreProcessCount.value:
            self.Logger.warning(f"Maximum process count {maximum_process_count} is less than the core process count ({self.CoreProcessCount}). Using default value: {default_value}.")
            return default_value

        return maximum_process_count

    def _validateMaximumThreadCount(self, maximum_thread_count: int) -> int:
        """
        验证最大线程数量的有效性，并在无效或未设置时提供默认值或进行调整。

        参数：
            :param - maximum_thread_count: 传入的最大线程数量

        返回：
            :return - int : 有效的最大线程数量

        执行过程：
            1. 设置默认值
                a. 默认值设置为物理核心数的两倍
            2. 检查是否传入最大线程数量
                a. 如果maximum_thread_count为None，记录警告日志并返回默认值
            3. 验证最大线程数量的类型
                a. 如果maximum_thread_count的类型不是整数，记录警告日志并返回默认值
            4. 验证最大线程数量是否小于最小值
                a. 如果maximum_thread_count小于核心线程数量，记录警告日志并返回默认值
            5. 验证最大线程数量是否超过最大值
                a. 如果maximum_thread_count超过默认值，记录警告日志并返回默认值
            6. 验证最大线程数量是否为偶数
                a. 如果maximum_thread_count不是偶数，将其调整为最接近的偶数，并记录警告日志
            7. 返回有效的最大线程数量
                a. 如果maximum_thread_count通过了所有验证，则返回调整后的最大线程数量

        异常：
            无
        """

        default_value = int(self.PhysicalCores * 2)
        if maximum_thread_count is None:
            self.Logger.warning(f"Maximum thread count not set, using default value: {default_value}.")
            return default_value

        if not isinstance(maximum_thread_count, int):
            self.Logger.warning(f"Invalid type for maximum thread count '{maximum_thread_count}'. Must be an integer; using default value: {default_value}.")
            return default_value

        if maximum_thread_count < self.CoreThreadCount.value:
            self.Logger.warning(f"Maximum thread count {maximum_thread_count} is less than the minimum default value: {default_value}. Using default value.")
            adjusted_count = default_value
        elif maximum_thread_count > default_value:
            self.Logger.warning(f"Maximum thread count {maximum_thread_count} exceeds the maximum default value: {default_value}. Using default value.")
            adjusted_count = default_value
        elif maximum_thread_count % 2 != 0:
            adjusted_count = maximum_thread_count - 1
            self.Logger.warning(f"Adjusted maximum thread count to even number: {adjusted_count}.")
        else:
            adjusted_count = maximum_thread_count

        return adjusted_count

    def _validateIdleCleanupThreshold(self, idle_cleanup_threshold: int) -> int:
        """
        验证空闲清理阈值的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - idle_cleanup_threshold: 传入的空闲清理阈值

        返回：
            :return - int : 有效的空闲清理阈值

        执行过程：
            1. 设置默认值
                a. 默认值设置为60
            2. 检查是否传入空闲清理阈值
                a. 如果idle_cleanup_threshold为None，记录警告日志并返回默认值
            3. 验证空闲清理阈值的类型
                a. 如果idle_cleanup_threshold的类型不是整数，记录警告日志并返回默认值
            4. 返回有效的空闲清理阈值
                a. 如果idle_cleanup_threshold通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = 60
        if idle_cleanup_threshold is None:
            self.Logger.warning(f"Idle cleanup threshold not set, using default value: {default_value}.")
            return default_value

        if not isinstance(idle_cleanup_threshold, int):
            self.Logger.warning(f"Invalid type for idle cleanup threshold '{idle_cleanup_threshold}'. Must be an integer; using default value: {default_value}.")
            return default_value

        return idle_cleanup_threshold

    def _validateTaskThreshold(self, task_threshold: int) -> int:
        """
        验证任务阈值的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - task_threshold: 传入的任务阈值

        返回：
            :return - int : 有效的任务阈值

        执行过程：
            1. 计算默认值
                a. 调用calculateTaskThreshold方法计算默认值
            2. 检查是否传入任务阈值
                a. 如果task_threshold为None，记录警告日志并返回默认值
            3. 验证任务阈值的类型
                a. 如果task_threshold的类型不是整数，记录警告日志并返回默认值
            4. 返回有效的任务阈值
                a. 如果task_threshold通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = self.calculateTaskThreshold()
        if task_threshold is None:
            self.Logger.warning(f"Task threshold not set, using default value: {default_value}.")
            return default_value

        if not isinstance(task_threshold, int):
            self.Logger.warning(f"Invalid type for task threshold '{task_threshold}'. Must be an integer; using default value: {default_value}.")
            return default_value

        return task_threshold

    def _validateGlobalTaskThreshold(self, global_task_threshold: int) -> int:
        """
        验证全局任务阈值的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - global_task_threshold: 传入的全局任务阈值

        返回：
            :return - int : 有效的全局任务阈值

        执行过程：
            1. 计算默认值
                a. 根据核心进程数、核心线程数和任务阈值计算默认全局任务阈值
            2. 检查是否传入全局任务阈值
                a. 如果global_task_threshold为None，记录警告日志并返回默认值
            3. 验证全局任务阈值的类型
                a. 如果global_task_threshold的类型不是整数，记录警告日志并返回默认值
            4. 返回有效的全局任务阈值
                a. 如果global_task_threshold通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = int((self.CoreProcessCount.value + self.CoreThreadCount.value) * self.TaskThreshold.value)
        if global_task_threshold is None:
            self.Logger.warning(f"Global task threshold not set, using default value: {default_value}.")
            return default_value

        if not isinstance(global_task_threshold, int):
            self.Logger.warning(f"Invalid type for global task threshold '{global_task_threshold}'. Must be an integer; using default value: {default_value}.")
            return default_value

        return global_task_threshold

    def _validateProcessPriority(self, process_priority: Literal[None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]) -> str:
        """
        验证进程优先级的有效性，并在无效或未设置时提供默认值或进行调整。

        参数：
            :param - process_priority: 传入的进程优先级

        返回：
            :return - str : 有效的进程优先级

        执行过程：
            1. 验证进程优先级
                a. 如果process_priority不在允许的范围内（包括None），记录警告日志并返回默认值"NORMAL"
            2. 检查是否传入进程优先级
                a. 如果process_priority为None，记录警告日志并返回默认值"NORMAL"
            3. 检查进程优先级是否适合所有物理核心
                a. 如果CoreProcessCount等于物理核心数且process_priority为"HIGH"或"REALTIME"，记录警告日志并返回调整后的值"ABOVE_NORMAL"
            4. 返回有效的进程优先级
                a. 如果process_priority通过了所有验证，则返回该值

        异常：
            无
        """

        if process_priority not in [None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            self.Logger.warning(f"Invalid process priority '{process_priority}'. Using default value: NORMAL.")
            return "NORMAL"

        if process_priority is None:
            self.Logger.warning("Process priority not set, using default value: NORMAL.")
            return "NORMAL"

        if self.CoreProcessCount.value == self.PhysicalCores and process_priority in ["HIGH", "REALTIME"]:
            self.Logger.warning(f"Process priority {process_priority} is not recommended for all physical cores; using default value: ABOVE_NORMAL.")
            return "ABOVE_NORMAL"
        return process_priority

    def _validateExpandPolicy(self, expand_policy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand"]) -> str:
        """
        验证扩展策略的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - expand_policy: 传入的扩展策略

        返回：
            :return - str : 有效的扩展策略

        执行过程：
            1. 验证扩展策略
                a. 如果expand_policy不在允许的范围内（包括None），记录警告日志并返回默认值"NoExpand"
            2. 检查是否传入扩展策略
                a. 如果expand_policy为None，记录警告日志并返回默认值"NoExpand"
            3. 返回有效的扩展策略
                a. 如果expand_policy通过了所有验证，则返回该值

        异常：
            无
        """

        if expand_policy not in [None, "NoExpand", "AutoExpand", "BeforehandExpand"]:
            self.Logger.warning(f"Invalid expand policy '{expand_policy}'. Using default value: NoExpand.")
            return "NoExpand"

        if expand_policy is None:
            self.Logger.warning("Expand policy not set, using default value: NoExpand.")
            return "NoExpand"

        return expand_policy

    def _validateShrinkagePolicy(self, shrinkage_policy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink"]) -> str:
        """
        验证收缩策略的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - shrinkage_policy: 传入的收缩策略

        返回：
            :return - str : 有效的收缩策略

        执行过程：
            1. 验证收缩策略
                a. 如果shrinkage_policy不在允许的范围内（包括None），记录警告日志并返回默认值"NoShrink"
            2. 检查是否传入收缩策略
                a. 如果shrinkage_policy为None，记录警告日志并返回默认值"NoShrink"
            3. 返回有效的收缩策略
                a. 如果shrinkage_policy通过了所有验证，则返回该值

        异常：
            无
        """

        if shrinkage_policy not in [None, "NoShrink", "AutoShrink", "TimeoutShrink"]:
            self.Logger.warning(f"Invalid shrinkage policy '{shrinkage_policy}'. Using default value: NoShrink.")
            return "NoShrink"

        if shrinkage_policy is None:
            self.Logger.warning("Shrinkage policy not set, using default value: NoShrink.")
            return "NoShrink"

        return shrinkage_policy

    def _validateShrinkagePolicyTimeout(self, shrinkage_policy_timeout: int) -> int:
        """
        验证收缩策略超时的有效性，并在无效或未设置时提供默认值。

        参数：
            :param - shrinkage_policy_timeout: 传入的收缩策略超时

        返回：
            :return - int : 有效的收缩策略超时

        执行过程：
            1. 设置默认值
                a. 默认值设置为15
            2. 检查是否传入收缩策略超时
                a. 如果shrinkage_policy_timeout为None，记录警告日志并返回默认值
            3. 验证收缩策略超时的类型
                a. 如果shrinkage_policy_timeout的类型不是整数，记录警告日志并返回默认值
            4. 返回有效的收缩策略超时
                a. 如果shrinkage_policy_timeout通过了所有验证，则返回该值

        异常：
            无
        """

        default_value = 15
        if shrinkage_policy_timeout is None:
            self.Logger.warning(f"Shrinkage policy timeout not set, using default value: {default_value}.")
            return default_value

        if not isinstance(shrinkage_policy_timeout, int):
            self.Logger.warning(f"Invalid type for shrinkage policy timeout '{shrinkage_policy_timeout}'. Must be an integer; using default value: {default_value}.")
            return default_value

        return shrinkage_policy_timeout

    @staticmethod
    def calculateTaskThreshold():
        """
        计算任务阈值，根据物理核心数和总内存大小来确定适当的任务阈值。

        参数：
            无

        返回：
            :return - int : 计算出的任务阈值

        执行过程：
            1. 获取物理核心数
                a. 使用psutil库获取物理CPU核心数
            2. 获取总内存
                a. 使用psutil库获取系统总内存，并将其转换为GB
            3. 计算平衡评分
                a. 根据物理核心数和总内存计算平衡评分
            4. 根据平衡评分确定任务阈值
                a. 使用平衡评分和预定义的评分阈值来确定对应的任务阈值
            5. 返回计算出的任务阈值
                a. 如果平衡评分超过所有评分阈值，则返回任务阈值列表中的最大值

        异常：
            无
        """

        physical_cores = psutil.cpu_count(logical=False)
        total_memory = psutil.virtual_memory().total / (1024 ** 3)
        balanced_score = ((physical_cores / 128) + (total_memory / 3072)) / 2

        balanced_score_thresholds = [0.2, 0.4, 0.6, 0.8]
        task_thresholds = [40, 80, 120, 160, 200]
        for score_threshold, threshold in zip(balanced_score_thresholds, task_thresholds):
            if balanced_score <= score_threshold:
                return threshold
        return task_thresholds[-1]


if multiprocessing.current_process().name == 'MainProcess':
    _CallbackObject: Dict[str, callable] = {}
    _CoreProcessPool = {}
    _ExpandProcessPool = {}
    _ExpandProcessSurvivalTime = {}
    _CoreThreadPool = {}
    _ExpandThreadPool = {}
    _ExpandThreadSurvivalTime = {}

if QThread is not None and QApplication is not None:
    # noinspection PyUnresolvedReferences
    import qasync


    class _QtCallbackExecutor(QThread):
        """
        QT回调执行器，处理任务结果并通过Qt信号触发回调函数。

        参数：
            :param - SM: _SynchronizationManager 实例，用于管理和存储任务结果
            :param - parent: 可选的父对象，用于Qt对象的父子关系

        属性：
            - SynchronizationManager: 同步管理器实例，用于获取任务结果
            - CloseEvent: 用于触发关闭事件的线程事件
            - ExecuteSignal: Qt信号，用于触发回调函数

        设计思路：
            1. 启动和关闭执行器
                a. 使用self.start()方法启动线程
                b. 通过设置self.CloseEvent来触发执行器的关闭，并使用self.wait()等待线程停止
            2. 运行任务并处理回调
                a. 在run()方法中持续运行，直到关闭事件被触发
                b. 从self.SynchronizationManager.ResultStorageQueue中非阻塞地获取回调数据
                c. 发出ExecuteSignal信号，传递回调对象和任务结果
                d. 处理队列为空的情况，通过短暂休眠继续循环
            3. 执行回调函数
                a. 在callbackExecutor()方法中，根据回调对象是否为协程函数，异步或同步执行回调
        """

        if PySide6Support:
            ExecuteSignal = Signal(tuple)
        elif PyQt6Support or PyQt5Support:
            ExecuteSignal = pyqtSignal(tuple)

        def __init__(self, SM: _SynchronizationManager, parent=None):
            super().__init__(parent)
            self.SynchronizationManager = SM
            self.CloseEvent = threading.Event()
            self.ExecuteSignal.connect(self.callbackExecutor)

        def startExecutor(self):
            """
            启动执行器，调用基础类的启动方法。

            参数：
                无

            返回：
                无

            执行过程：
                1. 调用基础类的启动方法
                    a. 使用self.start()方法启动执行器

            异常：
                无
            """

            self.start()

        def closeExecutor(self):
            """
            关闭执行器，设置关闭事件并等待执行器停止。

            参数：
                无

            返回：
                无

            执行过程：
                1. 设置关闭事件
                    a. 设置self.CloseEvent为已触发状态
                2. 等待执行器停止
                    a. 调用self.wait()方法，阻塞直到执行器完全停止

            异常：
                无
            """

            self.CloseEvent.set()
            self.wait()

        def run(self):
            """
            运行执行器，处理任务结果并触发相应的回调。

            参数：
                无

            返回：
                无

            执行过程：
                1. 持续运行直到关闭事件被触发
                    a. 使用while循环检查self.CloseEvent是否被设置
                2. 处理任务结果
                    a. 尝试从self.SynchronizationManager.ResultStorageQueue中非阻塞地获取回调数据
                    b. 从回调数据中提取任务结果和任务ID
                    c. 获取与任务ID关联的回调对象
                    d. 发出执行信号，传递回调对象和任务结果
                    e. 从_CallbackObject中删除已处理的任务ID
                3. 处理队列为空的情况
                    a. 如果队列为空，暂停0.001秒后继续循环

            异常：
                1. queue.Empty: 队列为空时，进行短暂的休眠并继续循环
            """

            global _CallbackObject
            while not self.CloseEvent.is_set():
                try:
                    callback_data = self.SynchronizationManager.ResultStorageQueue.get_nowait()
                    task_result, task_id = callback_data
                    callback_object = _CallbackObject[task_id]
                    # noinspection PyUnresolvedReferences
                    self.ExecuteSignal.emit((callback_object, task_result))
                    del _CallbackObject[task_id]
                except queue.Empty:
                    time.sleep(0.001)
                    continue

        @qasync.asyncSlot(tuple)
        async def callbackExecutor(self, callback_data: tuple):
            """
            异步执行回调函数，将任务结果传递给回调对象。

            参数：
                :param - callback_data: 一个包含回调对象和任务结果的元组

            返回：
                无

            执行过程：
                1. 解包回调数据
                    a. 从callback_data中提取回调对象和任务结果
                2. 判断回调对象是否为协程函数
                    a. 如果回调对象是协程函数，则使用await关键字异步执行它，并传递任务结果
                    b. 如果回调对象不是协程函数，则直接调用它，并传递任务结果

            异常：
                无
            """

            callback_object, task_result = callback_data
            if asyncio.iscoroutinefunction(callback_object):
                await callback_object(task_result)
                return
            callback_object(task_result)


class _CoreCallbackExecutor:
    """
    核心回调执行器，将任务结果从同步管理器传递到回调对象，并在主事件循环中运行任务。

    参数：
        :param - SM: _SynchronizationManager 实例，用于管理和存储任务结果

    属性：
        - SynchronizationManager: 同步管理器实例，用于获取任务结果
        - CloseEvent: 用于触发关闭事件的线程事件
        - MainEventLoop: 主事件循环对象，用于调度异步任务

    设计思路：
        1. 启动和关闭执行器
            a. 使用self.MainEventLoop.create_task将任务调度到事件循环中
            b. 通过设置self.CloseEvent来触发执行器的关闭
        2. 运行任务并处理回调
            a. 在异步方法self.run()中持续运行，直到关闭事件被触发
            b. 从self.SynchronizationManager.ResultStorageQueue中非阻塞地获取回调数据
            c. 执行回调函数，将任务结果传递给回调对象
            d. 处理队列为空的情况，通过异步休眠进行短暂等待
    """

    def __init__(self, SM: _SynchronizationManager):
        self.SynchronizationManager = SM
        self.CloseEvent = threading.Event()
        self.MainEventLoop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    def startExecutor(self):
        """
        启动执行器，将运行任务调度到主事件循环中。

        参数：
            无

        返回：
            无

        执行过程：
            1. 将运行任务添加到主事件循环
                a. 使用self.MainEventLoop.create_task将self.run()方法调度到事件循环中

        异常：
            无
        """

        self.MainEventLoop.create_task(self.run())

    def closeExecutor(self):
        """
        关闭执行器，触发关闭事件。

        参数：
            无

        返回：
            无

        执行过程：
            1. 触发关闭事件
                a. 设置self.CloseEvent为已触发状态

        异常：
            无
        """

        self.CloseEvent.set()

    async def run(self):
        """
        异步运行执行器，处理任务结果并触发回调。

        参数：
            无

        返回：
            无

        执行过程：
            1. 持续运行直到关闭事件被触发
                a. 使用while循环检查self.CloseEvent是否被设置
            2. 处理任务结果
                a. 尝试从self.SynchronizationManager.ResultStorageQueue中非阻塞地获取回调数据
                b. 从回调数据中提取任务结果和任务ID
                c. 获取与任务ID关联的回调对象
                d. 将回调执行任务调度到主事件循环中
                e. 从_CallbackObject中删除已处理的任务ID
            3. 处理队列为空的情况
                a. 如果队列为空，异步休眠0.001秒后继续循环

        异常：
            1. queue.Empty: 队列为空时，进行异步休眠并继续循环
        """

        global _CallbackObject
        while not self.CloseEvent.is_set():
            try:
                callback_data = self.SynchronizationManager.ResultStorageQueue.get_nowait()
                task_result, task_id = callback_data
                callback_object = _CallbackObject[task_id]
                # noinspection PyAsyncCall
                self.MainEventLoop.create_task(self.callbackExecutor((callback_object, task_result)))
                del _CallbackObject[task_id]
            except queue.Empty:
                await asyncio.sleep(0.001)
                continue

    @staticmethod
    async def callbackExecutor(callback_data: tuple):
        """
        异步执行回调函数，将任务结果传递给回调对象。

        参数：
            :param - callback_data: 包含回调对象和任务结果的元组

        返回：
            无

        执行过程：
            1. 解包回调数据
                a. 从callback_data中提取回调对象和任务结果
            2. 判断回调对象是否为协程函数
                a. 如果回调对象是协程函数，使用await关键字异步执行它，并传递任务结果
                b. 如果回调对象不是协程函数，直接调用它，并传递任务结果

        异常：
            无
        """

        callback_object, task_result = callback_data
        if asyncio.iscoroutinefunction(callback_object):
            await callback_object(task_result)
            return
        callback_object(task_result)


class _TaskObject:
    """
    任务对象，用于管理和执行异步或同步任务，支持参数序列化、GPU加速、任务重试和异常处理等功能。

    参数：
        :param - Task: 任务函数或可调用对象
        :param - TaskID: 任务的唯一标识符
        :param - Callback: 是否需要回调，默认为False
        :param - Lock: 是否需要锁定，默认为False
        :param - LockTimeout: 锁定超时时间，默认为3秒
        :param - TimeOut: 任务超时时间，默认为None（不超时）
        :param - GpuBoost: 是否启用GPU加速，默认为False
        :param - GpuID: GPU设备ID，默认为0
        :param - Retry: 是否启用重试机制，默认为False
        :param - MaxRetries: 最大重试次数，默认为3
        :param - *args: 任务的其他位置参数
        :param - **kwargs: 任务的其他关键字参数

    属性：
        - Task: 任务函数或可调用对象
        - TaskID: 任务的唯一标识符
        - TaskType: 任务类型（同步或异步）
        - IsCallback: 是否需要回调
        - Lock: 是否需要锁定
        - LockTimeout: 锁定超时时间
        - TimeOut: 任务超时时间
        - IsGpuBoost: 是否启用GPU加速
        - GpuID: GPU设备ID
        - IsRetry: 是否启用重试机制
        - MaxRetries: 最大重试次数
        - RetriesCount: 当前重试次数
        - UnserializableInfo: 不可序列化对象的信息
        - Args: 序列化后的任务位置参数
        - Kwargs: 序列化后的任务关键字参数
        - RecoveredArgs: 反序列化后的任务位置参数
        - RecoveredKwargs: 反序列化后的任务关键字参数

    设计思路：
        1. 初始化任务对象
            a. 确定任务的基本属性，如任务类型、锁定、超时、GPU加速等
            b. 处理任务参数，进行序列化以便于存储和传递
        2. 执行任务
            a. 通过reinitializeParams()方法恢复参数
            b. 根据任务类型（同步或异步）执行任务
            c. 处理任务执行中的异常，支持重试机制
            d. 在任务执行后清理GPU资源（如果启用了GPU加速）
    """

    def __init__(self, Task: callable, TaskID: str, Callback: bool = False, Lock: bool = False, LockTimeout: int = 3, TimeOut: int = None, GpuBoost: bool = False, GpuID: int = 0, Retry: bool = False, MaxRetries: int = 3, *args, **kwargs):
        self.Task = Task
        self.TaskID = TaskID
        self.TaskType: Literal["Sync", "Async"] = "Async" if asyncio.iscoroutinefunction(self.Task) else "Sync"
        self.IsCallback = Callback
        self.Lock = Lock
        self.LockTimeout = LockTimeout
        self.TimeOut = TimeOut
        self.IsGpuBoost = GpuBoost
        self.GpuID = GpuID
        self.IsRetry = Retry
        self.MaxRetries = MaxRetries
        self.RetriesCount = 0
        self.UnserializableInfo = {}
        self.Args = self.serialize(args)
        self.Kwargs = self.serialize(kwargs)
        self.RecoveredArgs = None
        self.RecoveredKwargs = None

    def reinitializeParams(self):
        """
        重新初始化参数，恢复序列化的参数，并设置GPU参数（如果启用GPU加速）。

        参数：
            无

        返回：
            无

        执行过程：
            1. 反序列化参数
                a. 使用self.deserialize方法恢复self.Args和self.Kwargs的值
            2. 检查是否启用GPU加速
                a. 如果self.IsGpuBoost为True且PyTorch支持可用，调用self.setupGpuParams()设置GPU参数

        异常：
            无
        """

        self.RecoveredArgs = self.deserialize(self.Args)
        self.RecoveredKwargs = self.deserialize(self.Kwargs)
        if self.IsGpuBoost and PyTorchSupport:
            self.setupGpuParams()

    def setupGpuParams(self):
        """
        设置GPU参数，检查GPU ID的有效性并调整参数以使用指定的GPU设备。

        参数：
            无

        返回：
            无

        执行过程：
            1. 检查GPU ID的有效性
                a. 如果self.GpuID不在AvailableCUDADevicesID中，将self.GpuID设置为0
            2. 获取指定的GPU设备
                a. 使用torch.device创建指定GPU设备
            3. 调整参数以使用指定的GPU设备
                a. 将self.RecoveredArgs中的每个参数转移到指定的GPU设备
                b. 将self.RecoveredKwargs中的每个值转移到指定的GPU设备

        异常：
            无
        """

        if self.GpuID not in AvailableCUDADevicesID:
            self.GpuID = 0
        device = torch.device(f"cuda:{self.GpuID}")
        self.RecoveredArgs = [self.paramsTransfer(arg, device) for arg in self.RecoveredArgs]
        self.RecoveredKwargs = {key: self.paramsTransfer(value, device) for key, value in self.RecoveredKwargs.items()}

    def paramsTransfer(self, obj, device):
        """
        将参数对象转移到指定的设备（如GPU），支持各种数据类型的递归转移。

        参数：
            :param - obj: 需要转移的对象
            :param - device: 目标设备（如GPU）

        返回：
            :return - 转移到指定设备的对象

        执行过程：
            1. 检查对象类型
                a. 如果obj是torch.Tensor或torch.nn.Module，使用.to(device)方法将其转移到指定设备
                b. 如果obj是列表或元组，对其每个元素进行递归转移并返回新的列表或元组
                c. 如果obj是字典，对其每个值进行递归转移并返回新的字典
            2. 如果obj不是上述类型，直接返回原对象

        异常：
            无
        """

        if isinstance(obj, (torch.Tensor, torch.nn.Module)):
            return obj.to(device)
        if isinstance(obj, (list, tuple)):
            return type(obj)(self.paramsTransfer(x, device) for x in obj)
        if isinstance(obj, dict):
            return {k: self.paramsTransfer(v, device) for k, v in obj.items()}
        return obj

    @staticmethod
    def cleanupGpuResources():
        """
        清理GPU资源，确保GPU缓存被清空并同步。

        参数：
            无

        返回：
            无

        执行过程：
            1. 同步GPU
                a. 调用torch.cuda.synchronize()确保所有GPU操作完成
            2. 清空GPU缓存
                a. 调用torch.cuda.empty_cache()释放未使用的GPU内存

        异常：
            无
        """

        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    def serialize(self, obj):
        """
        序列化对象，将对象及其嵌套内容转换为可序列化的格式。

        参数：
            :param - obj: 需要序列化的对象

        返回：
            :return - 序列化后的对象

        执行过程：
            1. 处理对象类型
                a. 如果obj是元组，对其每个元素递归调用序列化方法
                b. 如果obj是字典，对其每个键值对递归调用序列化方法
                c. 如果obj不可序列化，记录其信息并返回一个包含对象类型和ID的字典
                d. 如果obj是可序列化的，直接返回对象本身

        异常：
            无
        """

        if isinstance(obj, tuple):
            return tuple(self.serialize(item) for item in obj)
        elif isinstance(obj, dict):
            return {key: self.serialize(value) for key, value in obj.items()}
        elif not self.isSerializable(obj):
            obj_id = id(obj)
            self.UnserializableInfo[obj_id] = obj
            return {"__unserializable__": True, "id": obj_id, "type": type(obj).__name__}
        else:
            return obj

    def deserialize(self, obj):
        """
        反序列化对象，将序列化的格式恢复为原始对象。

        参数：
            :param - obj: 需要反序列化的对象

        返回：
            :return - 反序列化后的对象

        执行过程：
            1. 处理对象类型
                a. 如果obj是元组，对其每个元素递归调用反序列化方法
                b. 如果obj是字典
                    i. 如果字典中包含"__unserializable__"键，从UnserializableInfo中获取原始对象
                    ii. 否则，对字典中的每个键值对递归调用反序列化方法
                c. 如果obj是其他类型，直接返回对象本身

        异常：
            无
        """

        if isinstance(obj, tuple):
            return tuple(self.deserialize(item) for item in obj)
        elif isinstance(obj, dict):
            if "__unserializable__" in obj:
                return self.UnserializableInfo[obj["id"]]
            return {key: self.deserialize(value) for key, value in obj.items()}
        else:
            return obj

    @staticmethod
    def isSerializable(obj):
        """
        检查对象是否可序列化，即是否可以通过pickle模块进行序列化。

        参数：
            :param - obj: 需要检查的对象

        返回：
            :return - bool: 如果对象可序列化，则返回True；否则返回False

        执行过程：
            1. 尝试序列化对象
                a. 使用pickle.dumps方法尝试序列化对象
            2. 捕获序列化错误
                a. 如果发生pickle.PicklingError、AttributeError或TypeError，返回False
                b. 否则，返回True

        异常：
            无
        """

        try:
            pickle.dumps(obj)
            return True
        except (pickle.PicklingError, AttributeError, TypeError):
            return False

    async def execute(self):
        """
        异步执行任务，处理参数初始化、超时、异常处理和GPU资源清理。

        参数：
            无

        返回：
            :return - 执行结果：任务的结果或在异常情况下的处理结果

        执行过程：
            1. 重新初始化参数
                a. 调用self.reinitializeParams()方法恢复参数
            2. 执行任务
                a. 如果设置了超时时间，使用asyncio.wait_for执行self.run()，并设置超时
                b. 如果未设置超时时间，直接执行self.run()
            3. 异常处理
                a. 捕获asyncio.TimeoutError异常时，直接返回
                b. 捕获asyncio.CancelledError异常时，直接返回
                c. 捕获其他异常时，如果设置了重试，则调用self.retry()进行重试；否则，抛出新的异常
            4. 最终处理
                a. 如果启用了GPU加速，调用self.cleanupGpuResources()清理GPU资源

        异常：
            1. asyncio.TimeoutError: 任务超时，直接返回
            2. asyncio.CancelledError: 任务被取消，直接返回
            3. Exception: 其他异常，如果设置了重试则进行重试，否则抛出详细异常
        """

        self.reinitializeParams()
        try:
            if self.TimeOut is not None:
                result = await asyncio.wait_for(self.run(), timeout=self.TimeOut)
            else:
                result = await self.run()

        except asyncio.TimeoutError:
            return
        except asyncio.CancelledError:
            return
        except Exception as e:
            if self.IsRetry:
                result = await self.retry()
            else:
                raise Exception(f"Failed to execute task {self.Task.__name__} due to {str(e)}\n\n{traceback.format_exc()}.")
        finally:
            if self.IsGpuBoost:
                self.cleanupGpuResources()
        return result

    async def run(self):
        """
        异步执行任务，并处理任务结果。

        参数：
            无

        返回：
            :return - 任务结果：通过self.result()处理后的任务结果

        执行过程：
            1. 执行任务
                a. 如果self.TaskType为"Async"，异步执行任务，并传递恢复后的参数
                b. 如果self.TaskType不是"Async"，同步执行任务，并传递恢复后的参数
            2. 处理任务结果
                a. 使用await关键字等待self.result()处理任务结果

        异常：
            无
        """

        if self.TaskType == "Async":
            task_result = await self.Task(*self.RecoveredArgs, **self.RecoveredKwargs)
        else:
            task_result = self.Task(*self.RecoveredArgs, **self.RecoveredKwargs)
        return await self.result(task_result)

    async def retry(self):
        """
        执行任务的重试机制，处理任务执行失败时的重试逻辑。

        参数：
            无

        返回：
            :return - 任务结果：重试成功时的任务结果

        执行过程：
            1. 设置初始退避时间
                a. 将backoff_time初始化为0.1秒
            2. 重试任务
                a. 当重试次数少于最大重试次数时
                    i. 尝试执行任务
                        - 如果执行成功，返回任务结果
                    ii. 如果执行失败
                        - 增加重试计数
                        - 等待退避时间
                        - 增加退避时间（每次退避时间翻倍）

        异常：
            无
        """

        backoff_time = 0.1
        while self.RetriesCount < self.MaxRetries:
            try:
                return await self.run()
            except Exception:  # noqa
                self.RetriesCount += 1
                await asyncio.sleep(backoff_time)
                backoff_time *= 2

    async def result(self, task_result):
        """
        处理任务结果，如果任务结果是GPU张量，则将其转移到CPU并清理GPU资源。

        参数：
            :param - task_result: 任务的结果

        返回：
            :return - 处理后的任务结果：如果结果是GPU张量，则返回CPU张量；否则返回原结果

        执行过程：
            1. 检查是否启用GPU加速以及任务结果是否为GPU张量
                a. 如果启用GPU加速且任务结果是torch.Tensor或torch.nn.Module
                    i. 将任务结果克隆并转移到CPU
                    ii. 删除原任务结果并清理GPU资源
                    iii. 返回转移到CPU的结果
            2. 如果结果不是GPU张量，直接返回任务结果

        异常：
            无
        """

        if self.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result = task_result.clone().detach().cpu()
            del task_result
            self.cleanupGpuResources()
            return cpu_result
        return task_result


class _ProcessObject(multiprocessing.Process):
    """
    进程对象，用于处理任务队列中的任务，支持任务的优先级调度、日志记录、进程内存清理、进程状态更新等功能。

    参数：
        :param - ProcessName: 进程名称
        :param - ProcessType: 进程类型（'Core' 或 'Expand'）
        :param - SM: 同步管理器
        :param - CM: 配置管理器
        :param - DebugMode: 调试模式标志

    属性：
        - ProcessName: 进程名称
        - ProcessType: 进程类型
        - SynchronizationManager: 同步管理器
        - ConfigManager: 配置管理器
        - DebugMode: 调试模式标志
        - Logger: 日志记录器
        - PendingTasks: 待处理任务字典
        - HighPriorityQueue: 高优先级任务队列
        - MediumPriorityQueue: 中优先级任务队列
        - LowPriorityQueue: 低优先级任务队列
        - WorkingEvent: 工作事件
        - CloseEvent: 关闭事件
        - StatusUpdateThread: 状态更新线程
        - EventLoop: 异步事件循环
        - PsutilObject: psutil进程对象

    设计思路：
        1. 初始化
            a. 设置日志记录器
            b. 设置进程优先级
            c. 清理进程内存
            d. 创建事件循环
            e. 创建psutil进程对象
            f. 设置状态更新线程
        2. 任务处理
            a. 根据优先级从队列中获取任务并执行
            b. 在空闲时进行内存清理
        3. 进程终止
            a. 停止进程
            b. 清理所有剩余任务
    """

    def __init__(self, ProcessName: str, ProcessType: Literal['Core', 'Expand'], SM: _SynchronizationManager, CM: _ConfigManager, DebugMode: bool):
        super().__init__(name=ProcessName, daemon=True)
        self.ProcessName = ProcessName
        self.ProcessType = ProcessType
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.DebugMode = DebugMode
        self.Logger = None
        self.PendingTasks = {}
        self.HighPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.MediumPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.LowPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.StatusUpdateThread: Union[threading.Thread, None] = None
        self.EventLoop: Union[asyncio.AbstractEventLoop, None] = None
        self.PsutilObject: Union[psutil.Process, None] = None

    def run(self):
        """
        初始化和运行事件循环，设置日志、进程优先级，清理进程内存，处理任务并关闭事件循环。

        参数：
            无

        返回：
            无

        执行过程：
            1. 初始化
                a. 调用self._setLogger()设置日志记录器
                b. 调用self._setProcessPriority()设置进程优先级
                c. 调用self._cleanupProcessMemory()清理进程内存
                d. 创建新的事件循环并赋值给self.EventLoop
                e. 创建psutil.Process对象以管理进程资源
                f. 调用self._setStatusUpdateThread()设置状态更新线程
                g. 将新的事件循环设置为当前事件循环
            2. 运行任务处理器
                a. 使用self.EventLoop.run_until_complete()运行任务处理器
            3. 清理
                a. 关闭事件循环
                b. 记录进程关闭的调试信息

        异常：
            无
        """

        self._setLogger()
        self._setProcessPriority()
        self._cleanupProcessMemory()
        self.EventLoop = asyncio.new_event_loop()
        self.PsutilObject = psutil.Process(self.pid)
        self._setStatusUpdateThread()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        finally:
            self.EventLoop.close()
            self.Logger.debug(f"[{self.ProcessName} - {self.pid}] has been closed.")

    def stop(self):
        """
        停止并清理进程，确保进程终止并释放资源。

        参数：
            无

        返回：
            无

        执行过程：
            1. 停止进程
                a. 设置关闭事件self.CloseEvent
                b. 等待进程结束最多2秒
                c. 如果进程仍在运行，调用terminate()强制终止进程
            2. 清理
                a. 删除进程对象

        异常：
            无
        """

        self.CloseEvent.set()
        self.join(2)
        if self.is_alive():
            self.terminate()
        del self

    def addProcessTask(self, priority: int, task_object: _TaskObject):
        """
        根据优先级将任务添加到相应的任务队列中，并设置工作事件标志。

        参数：
            :param - priority: 任务优先级（整数，范围为0到10）
            :param - task_object: 任务对象，包含任务ID和其他信息

        返回：
            无

        执行过程：
            1. 根据优先级将任务添加到相应的队列
                a. 如果优先级在0到3之间，将任务添加到高优先级队列
                b. 如果优先级在4到7之间，将任务添加到中优先级队列
                c. 如果优先级在8到10之间，将任务添加到低优先级队列
                d. 如果优先级无效，记录错误信息并返回
            2. 设置工作事件标志
                a. 如果工作事件未被设置，则将其设置

        异常：
            无
        """

        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object))
        elif 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object))
        elif 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object))
        else:
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} has been rejected due to invalid priority {priority}.")
            return
        if not self.WorkingEvent.is_set():
            self.WorkingEvent.set()

    def _setLogger(self):
        """
        设置日志记录器，配置日志级别和输出格式。

        参数：
            无

        返回：
            无

        执行过程：
            1. 配置日志记录器
                a. 创建一个名为'TheSeedCore - ConcurrentSystem'的日志记录器
                b. 设置日志记录器的日志级别为DEBUG
            2. 配置控制台输出处理器
                a. 创建一个StreamHandler对象用于输出到控制台
                b. 根据DebugMode设置控制台输出的日志级别（DEBUG或WARNING）
                c. 创建一个格式化器并设置日志消息的格式
                d. 将格式化器添加到控制台处理器
            3. 将控制台处理器添加到日志记录器
            4. 将配置好的日志记录器赋值给self.Logger

        异常：
            无
        """

        logger = logging.getLogger(f'TheSeedCore - ConcurrentSystem')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if self.DebugMode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        self.Logger = logger

    def _setProcessPriority(self, priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = None):
        """
        设置进程的优先级。

        参数：
            :param - priority: 进程优先级（字符串，值为"IDLE"、"BELOW_NORMAL"、"NORMAL"、"ABOVE_NORMAL"、"HIGH"、"REALTIME"之一；默认为None）

        返回：
            无

        执行过程：
            1. 配置优先级映射
                a. 定义一个字典，将优先级字符串映射到Windows API中的优先级常量
            2. 获取进程句柄
                a. 使用ctypes库的OpenProcess函数获取指定进程ID的进程句柄
                b. 如果句柄无效，抛出ValueError异常
            3. 设置进程优先级
                a. 使用ctypes库的SetPriorityClass函数设置进程优先级
                b. 如果设置失败，获取错误代码并抛出异常
            4. 关闭句柄
                a. 使用ctypes库的CloseHandle函数关闭进程句柄

        异常：
            1. 如果获取句柄失败，记录错误信息
            2. 如果设置优先级失败，记录错误信息
        """

        priority_mapping = {
            "IDLE": 0x00000040,
            "BELOW_NORMAL": 0x00004000,
            "NORMAL": 0x00000020,
            "ABOVE_NORMAL": 0x00008000,
            "HIGH": 0x00000080,
            "REALTIME": 0x00000100
        }
        handle = None
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.pid)
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
            result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping.get(self.ConfigManager.ProcessPriority if priority is None else priority, priority_mapping["NORMAL"]))
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"Set priority failed with error code {error_code}.")
        except Exception as e:
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _setStatusUpdateThread(self):
        """
        创建并启动状态更新线程，用于定期更新进程状态。

        参数：
            无

        返回：
            无

        执行过程：
            1. 创建线程
                a. 使用线程模块创建一个新线程，目标函数为self._updateProcessStatus
            2. 启动线程
                a. 启动新创建的线程

        异常：
            无
        """

        self.StatusUpdateThread = threading.Thread(target=self._updateProcessStatus)
        self.StatusUpdateThread.start()

    def _cleanupProcessMemory(self):
        """
        清理进程的内存使用。

        参数：
            无

        返回：
            无

        执行过程：
            1. 获取进程句柄
                a. 使用ctypes库的OpenProcess函数获取指定进程ID的进程句柄
                b. 如果句柄无效，抛出ValueError异常
            2. 清理进程内存
                a. 使用ctypes库的EmptyWorkingSet函数清理进程的内存
                b. 如果清理失败，获取错误代码并记录错误信息
            3. 关闭句柄
                a. 使用ctypes库的CloseHandle函数关闭进程句柄

        异常：
            1. 如果获取句柄失败，记录错误信息
            2. 如果内存清理失败，记录错误信息
        """

        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.pid)
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
        except Exception as e:
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        if not handle:
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] failed to obtain a valid process handle.")
            return
        result = ctypes.windll.psapi.EmptyWorkingSet(handle)
        if result == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed with error code {error_code}.")
        ctypes.windll.kernel32.CloseHandle(handle)

    def _updateProcessStatus(self):
        """
        定期更新进程的状态信息，包括CPU使用率、内存使用率和任务数量，并将这些信息存储到状态池中。

        参数：
            无

        返回：
            无

        执行过程：
            1. 判断是否需要结束
                a. 循环执行，直到CloseEvent被设置
            2. 选择状态池
                a. 根据进程类型选择CoreProcessStatusPool或ExpandProcessStatusPool
            3. 计算任务数量
                a. 统计高、中、低优先级队列中的任务数量及待处理任务的数量
            4. 获取资源使用信息
                a. 使用psutil库获取进程的CPU和内存使用情况
                b. 计算CPU负载和内存负载
                c. 计算加权负载
            5. 更新状态池
                a. 将进程ID、任务数量和加权负载存储到状态池中
            6. 处理异常
                a. 如果psutil抛出NoSuchProcess异常，设置状态池中的负载为0

        异常：
            1. psutil.NoSuchProcess: 如果进程不存在，设置状态池中的负载为0
        """

        while not self.CloseEvent.is_set():
            status_pool = self.SynchronizationManager.CoreProcessStatusPool if self.ProcessType == "Core" else self.SynchronizationManager.ExpandProcessStatusPool
            task_count = self.HighPriorityQueue.qsize() + self.MediumPriorityQueue.qsize() + self.LowPriorityQueue.qsize() + len(self.PendingTasks)
            try:
                process_cpu_usage = self.PsutilObject.cpu_percent(0.5)
                total_cpu_usage = psutil.cpu_percent(0.5)
                process_memory_usage = self.PsutilObject.memory_info().rss
                total_memory_usage = psutil.virtual_memory().total
                if process_cpu_usage == 0 and total_cpu_usage == 0:
                    cpu_load = 0
                else:
                    try:
                        cpu_load = process_cpu_usage / total_cpu_usage
                    except ZeroDivisionError:
                        cpu_load = 0
                memory_load = process_memory_usage / total_memory_usage
                weighted_load = (cpu_load * 5) + (memory_load * 5)
                status_pool[self.ProcessName] = (self.pid, task_count, min(max(weighted_load, 0), 100))
            except psutil.NoSuchProcess:
                status_pool[self.ProcessName] = (self.pid, task_count, 0)

    async def _taskProcessor(self):
        """
        任务处理器，处理任务队列中的任务，根据任务的优先级执行任务，并在空闲时进行内存清理。

        参数：
            无

        返回：
            无

        执行过程：
            1. 判断是否需要结束
                a. 循环执行，直到CloseEvent被设置
            2. 获取任务数据
                a. 依次从高、中、低优先级队列中获取任务
                b. 如果队列为空，检查空闲时间，决定是否进行内存清理
            3. 处理任务
                a. 如果任务需要锁定，尝试获取锁并执行任务
                b. 如果锁定失败，将任务重新加入队列
                c. 执行任务并处理异常
            4. 处理异常
                a. 捕获异常并记录日志
            5. 清理工作
                a. 任务处理完成后调用_cleanup方法进行清理

        异常：
            1. queue.Empty: 如果队列为空，等待一段时间后重新尝试
            2. Exception: 处理任务过程中发生的任何异常
        """

        idle_times = 0
        while not self.CloseEvent.is_set():
            try:
                if not self.HighPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.HighPriorityQueue.get_nowait()
                elif not self.MediumPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.MediumPriorityQueue.get_nowait()
                elif not self.LowPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.LowPriorityQueue.get_nowait()
                else:
                    await asyncio.sleep(0.001)
                    if idle_times < self.ConfigManager.IdleCleanupThreshold.value:
                        idle_times += 0.005
                        continue
                    if self.WorkingEvent.is_set():
                        self.WorkingEvent.clear()
                        continue
                    self._cleanupProcessMemory()
                    idle_times = 0
                    continue
            except queue.Empty:
                await asyncio.sleep(0.001)
                if idle_times < self.ConfigManager.IdleCleanupThreshold.value:
                    idle_times += 0.005
                    continue
                if self.WorkingEvent.is_set():
                    self.WorkingEvent.clear()
                    continue
                self._cleanupProcessMemory()
                idle_times = 0
                continue
            task_priority, task_object = task_data
            try:
                if task_object.Lock:
                    acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
                    if not acquired:
                        await self._requeueTask(task_priority, task_object)
                        continue
                    try:
                        coroutine_task = self.EventLoop.create_task(self._taskExecutor(task_object))
                        self.PendingTasks[task_object.TaskID] = coroutine_task
                        await coroutine_task
                    finally:
                        self.SynchronizationManager.TaskLock.release()
                else:
                    coroutine_task = self.EventLoop.create_task(self._taskExecutor(task_object))
                    self.PendingTasks[task_object.TaskID] = coroutine_task
            except Exception as e:
                self.Logger.error(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} failed due to {str(e)}\n\n{traceback.format_exc()}.")
        await self._cleanup()

    async def _taskExecutor(self, task_object: _TaskObject):
        """
        任务执行器，执行任务对象的方法，并处理任务结果。

        参数：
            task_object (_TaskObject): 任务对象，包含任务的执行方法和相关参数

        返回：
            无

        执行过程：
            1. 执行任务
                a. 调用任务对象的execute方法
            2. 处理任务结果
                a. 调用_taskResultProcessor方法处理任务结果
            3. 处理异常
                a. 捕获并记录任务被取消的警告信息

        异常：
            1. asyncio.CancelledError: 如果任务被取消，记录警告信息
        """

        try:
            task_result = await task_object.execute()
            await self._taskResultProcessor(task_result, task_object)
        except asyncio.CancelledError:
            self.Logger.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} has been cancelled.")

    async def _taskResultProcessor(self, task_result: Any, task_object: _TaskObject):
        """
        任务结果处理器，处理任务执行后的结果，并更新任务状态。

        参数：
            task_result (Any): 任务的执行结果
            task_object (_TaskObject): 任务对象，包含任务的相关信息

        返回：
            无

        执行过程：
            1. 存储任务结果
                a. 如果任务对象的IsCallback属性为True，将结果和任务ID放入结果存储队列
            2. 更新任务状态
                a. 从PendingTasks字典中删除任务ID，表示任务已完成

        异常：
            1. KeyError: 如果任务ID不在PendingTasks字典中，忽略该异常
        """

        if task_object.IsCallback:
            self.SynchronizationManager.ResultStorageQueue.put_nowait((task_result, task_object.TaskID))
        try:
            del self.PendingTasks[task_object.TaskID]
        except KeyError:
            pass

    async def _requeueTask(self, task_priority: str, task_object: _TaskObject):
        """
        将失败的任务重新排入队列以重新尝试执行。

        参数：
            task_priority (str): 任务的优先级，可以是"HighPriority", "MediumPriority" 或 "LowPriority"
            task_object (_TaskObject): 需要重新排队的任务对象

        返回：
            无

        执行过程：
            1. 等待一段时间后重新排队任务
                a. 等待时间为最小值0.1秒乘以2的任务对象最大重试次数的幂，最大为10秒
            2. 根据任务优先级将任务放回相应的队列
                a. 如果优先级为"HighPriority"，将任务放入高优先级队列
                b. 如果优先级为"MediumPriority"，将任务放入中优先级队列
                c. 如果优先级为"LowPriority"，将任务放入低优先级队列
        """

        await asyncio.sleep(min(0.1 * (2 ** task_object.MaxRetries), 10))
        if task_priority == "HighPriority":
            self.HighPriorityQueue.put_nowait((task_priority, task_object))
            return
        if task_priority == "MediumPriority":
            self.MediumPriorityQueue.put_nowait((task_priority, task_object))
            return
        if task_priority == "LowPriority":
            self.LowPriorityQueue.put_nowait((task_priority, task_object))
            return

    async def _cleanup(self):
        """
        清理所有队列中的剩余任务并取消所有挂起的任务。

        参数：
            无

        返回：
            无

        执行过程：
            1. 统计高、中、低优先级队列中的剩余任务
                a. 从高优先级队列中获取任务直到队列为空
                b. 从中优先级队列中获取任务直到队列为空
                c. 从低优先级队列中获取任务直到队列为空
            2. 取消所有挂起的任务
                a. 遍历所有挂起的任务并取消它们
            3. 清除挂起的任务列表
            4. 记录丢弃的任务数量
        """

        remaining_tasks = 0
        while not self.HighPriorityQueue.empty():
            try:
                _, task_object = self.HighPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.MediumPriorityQueue.empty():
            try:
                _, task_object = self.MediumPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.LowPriorityQueue.empty():
            try:
                _, task_object = self.LowPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        for i, coroutine_task in self.PendingTasks.items():
            coroutine_task.cancel()
        self.Logger.debug(f"[{self.ProcessName} - {self.pid}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()


class _ThreadObject(threading.Thread):
    """
    线程对象，用于处理任务队列中的任务，支持不同优先级的任务处理以及任务结果处理。

    参数：
        :param ThreadName: 线程名称
        :param ThreadType: 线程类型，可能的值包括 'Core' 和 'Expand'
        :param SM: 同步管理器
        :param CM: 配置管理器
        :param Logger: 日志记录器

    属性：
        - ThreadName: 线程名称
        - ThreadType: 线程类型
        - SynchronizationManager: 同步管理器
        - ConfigManager: 配置管理器
        - Logger: 日志记录器
        - PendingTasks: 待处理任务字典
        - HighPriorityQueue: 高优先级任务队列
        - MediumPriorityQueue: 中优先级任务队列
        - LowPriorityQueue: 低优先级任务队列
        - WorkingEvent: 工作事件
        - CloseEvent: 关闭事件
        - EventLoop: 事件循环

    设计思路：
        1. 初始化线程，设置任务队列及事件
        2. 创建事件循环并执行任务处理器
        3. 提供任务添加、处理和清理功能
   """

    def __init__(self, ThreadName: str, ThreadType: Literal['Core', 'Expand'], SM: _SynchronizationManager, CM: _ConfigManager, Logger: logging.Logger):
        super().__init__(name=ThreadName, daemon=True)
        self.ThreadName = ThreadName
        self.ThreadType = ThreadType
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.Logger = Logger
        self.PendingTasks = {}
        self.HighPriorityQueue: queue.Queue = queue.Queue()
        self.MediumPriorityQueue: queue.Queue = queue.Queue()
        self.LowPriorityQueue: queue.Queue = queue.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.EventLoop: Union[asyncio.AbstractEventLoop, None] = None

    def run(self):
        """
        创建并运行一个新的事件循环，执行任务处理器。

        参数：
            无

        返回：
            无

        执行过程：
            1. 创建新的事件循环
            2. 将事件循环设置为当前事件循环
            3. 执行任务处理器，直到处理完所有任务
            4. 关闭事件循环
            5. 记录线程停止的日志
        """

        self.EventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        finally:
            self.EventLoop.close()
            self.Logger.debug(f"[{self.ThreadName} - {self.ident}] has been stopped.")

    def stop(self):
        """
        停止线程并清理相关资源。

        参数：
            无

        返回：
            无

        执行过程：
            1. 设置关闭事件，通知线程停止运行
            2. 等待线程结束，最多等待2秒
            3. 删除线程对象，释放资源

        异常：
            1. 无显式异常处理，但可能会因线程未能及时停止而产生潜在问题
        """

        self.CloseEvent.set()
        self.join(2)
        del self

    def addThreadTask(self, priority: int, task_object: _TaskObject):
        """
        根据任务优先级将任务对象添加到相应的任务队列中。

        参数：
            :param priority: 任务的优先级，范围从0到10
            :param task_object: 需要添加的任务对象

        返回：
            无

        执行过程：
            1. 根据优先级将任务对象添加到相应的任务队列（高、中、低优先级队列）
            2. 如果工作事件未设置，则将其设置为已触发，表示有任务在处理

        异常：
            1. 如果优先级不在0到10的范围内，则记录错误日志，任务被拒绝
        """

        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object))
        elif 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object))
        elif 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object))
        else:
            self.Logger.error(f"[{self.ThreadName}] task {task_object.TaskID} has been rejected due to invalid priority {priority}.")
            return
        if not self.WorkingEvent.is_set():
            self.WorkingEvent.set()

    async def _taskProcessor(self):
        """
        任务处理器，处理任务队列中的任务，根据任务优先级执行，并处理锁定任务和异常情况。

        参数：
            无

        返回：
            无

        执行过程：
            1. 检查各个优先级队列（高、中、低）是否有任务：
                a. 如果高优先级队列有任务，则获取并处理该任务
                b. 如果没有高优先级任务，则检查中优先级队列
                c. 如果没有中优先级任务，则检查低优先级队列
                d. 如果所有队列都为空，则等待0.001秒后继续检查
            2. 如果队列为空，捕获`queue.Empty`异常，等待0.001秒后继续检查
            3. 对于每个任务：
                a. 如果任务需要锁定，则尝试获取锁定
                    i. 如果无法获取锁定，则重新排队任务
                    ii. 如果获取成功，执行任务，并在完成后释放锁定
                b. 如果任务不需要锁定，则直接创建任务协程并执行
            4. 捕获并记录任务执行过程中的异常
            5. 完成任务处理后，执行清理操作

        异常：
            1. 处理任务执行中的异常，并记录错误日志
        """

        while not self.CloseEvent.is_set():
            try:
                if not self.HighPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.HighPriorityQueue.get_nowait()
                elif not self.MediumPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.MediumPriorityQueue.get_nowait()
                elif not self.LowPriorityQueue.empty():
                    task_data: Tuple[str, _TaskObject] = self.LowPriorityQueue.get_nowait()
                else:
                    await asyncio.sleep(0.001)
                    continue
            except queue.Empty:
                await asyncio.sleep(0.001)
                continue
            task_priority, task_object = task_data
            try:
                if task_object.Lock:
                    acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
                    if not acquired:
                        await self._requeueTask(task_priority, task_object)
                        continue
                    try:
                        coroutine_task = self.EventLoop.create_task(self._taskExecutor(task_object))
                        self.PendingTasks[task_object.TaskID] = coroutine_task
                        await coroutine_task
                    finally:
                        self.SynchronizationManager.TaskLock.release()
                else:
                    coroutine_task = self.EventLoop.create_task(self._taskExecutor(task_object))
                    self.PendingTasks[task_object.TaskID] = coroutine_task
            except Exception as e:
                self.Logger.error(f"[{self.ThreadName} - {self.ident}] task {task_object.TaskID} failed due to {str(e)}\n\n{traceback.format_exc()}.")
        await self._cleanup()

    async def _taskExecutor(self, task_object: Any):
        """
        任务执行器，执行单个任务对象，并处理任务结果。处理任务取消情况，并更新工作状态事件。

        参数：
            :param task_object: 任务对象，包含要执行的任务和相关信息

        返回：
            无

        执行过程：
            1. 尝试执行任务：
                a. 调用任务对象的`execute`方法并等待结果
                b. 调用`_taskResultProcessor`处理任务结果
                c. 如果`WorkingEvent`事件已设置，则清除事件
            2. 捕获`asyncio.CancelledError`异常：
                a. 记录任务被取消的错误日志
                b. 如果`WorkingEvent`事件已设置，则清除事件

        异常：
            1. `asyncio.CancelledError`: 任务被取消时记录错误
        """

        try:
            task_result = await task_object.execute()
            await self._taskResultProcessor(task_result, task_object)
            if self.WorkingEvent.is_set():
                self.WorkingEvent.clear()
        except asyncio.CancelledError:
            self.Logger.error(f"[{self.ThreadName} - {self.ident}] task {task_object.TaskID} has been cancelled.")
            if self.WorkingEvent.is_set():
                self.WorkingEvent.clear()

    async def _taskResultProcessor(self, task_result: Any, task_object: Any):
        """
        任务结果处理器，处理任务执行后的结果，将结果存储到结果队列，并从待处理任务列表中删除任务。

        参数：
            :param task_result: 任务执行结果
            :param task_object: 任务对象，包含任务ID和回调标志

        返回：
            无

        执行过程：
            1. 如果任务对象的`IsCallback`标志为真：
                a. 将任务结果和任务ID放入`ResultStorageQueue`中
            2. 尝试从`PendingTasks`字典中删除任务对象：
                a. 捕获`KeyError`异常，如果任务ID不存在则忽略

        异常：
            1. `KeyError`: 从`PendingTasks`中删除任务对象时任务ID不存在
        """

        if task_object.IsCallback:
            self.SynchronizationManager.ResultStorageQueue.put_nowait((task_result, task_object.TaskID))
        try:
            del self.PendingTasks[task_object.TaskID]
        except KeyError:
            pass

    async def _requeueTask(self, task_priority: str, task_object: _TaskObject):
        """
        将任务重新放入相应的优先级队列中，以便重新处理。

        参数：
            :param task_priority: 任务优先级，可能的值包括 "HighPriority", "MediumPriority", "LowPriority"
            :param task_object: 任务对象，包含任务ID和相关任务数据

        返回：
            无

        执行过程：
            1. 计算重新入队的延迟时间：
                a. 计算为 `0.1 * (2 ** task_object.MaxRetries)`，最大值为 10 秒
                b. 使用 `await asyncio.sleep` 进行异步等待
            2. 根据任务优先级将任务重新放入相应的优先级队列中：
                a. 如果任务优先级是 "HighPriority"，将任务放入 `HighPriorityQueue` 中
                b. 如果任务优先级是 "MediumPriority"，将任务放入 `MediumPriorityQueue` 中
                c. 如果任务优先级是 "LowPriority"，将任务放入 `LowPriorityQueue` 中
        """

        await asyncio.sleep(min(0.1 * (2 ** task_object.MaxRetries), 10))
        if task_priority == "HighPriority":
            self.HighPriorityQueue.put_nowait((task_priority, task_object))
            return
        if task_priority == "MediumPriority":
            self.MediumPriorityQueue.put_nowait((task_priority, task_object))
            return
        if task_priority == "LowPriority":
            self.LowPriorityQueue.put_nowait((task_priority, task_object))
            return

    async def _cleanup(self):
        """
        清理处理中的任务，并取消未完成的协程任务。

        参数：
            无

        返回：
            无

        执行过程：
            1. 计算并丢弃在各优先级队列中的剩余任务：
                a. 从 `HighPriorityQueue` 中移除所有任务，并计算剩余任务数量
                b. 从 `MediumPriorityQueue` 中移除所有任务，并计算剩余任务数量
                c. 从 `LowPriorityQueue` 中移除所有任务，并计算剩余任务数量
            2. 取消所有在 `PendingTasks` 中的协程任务
            3. 打印日志，记录丢弃的任务数量
            4. 清空 `PendingTasks` 列表
        """

        remaining_tasks = 0
        while not self.HighPriorityQueue.empty():
            try:
                _, task_object = self.HighPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.MediumPriorityQueue.empty():
            try:
                _, task_object = self.MediumPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.LowPriorityQueue.empty():
            try:
                _, task_object = self.LowPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        for i, coroutine_task in self.PendingTasks.items():
            coroutine_task.cancel()
        self.Logger.debug(f"[{self.ThreadName} - {self.ident}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()


class _LoadBalancer(threading.Thread):
    """
    负载均衡器，用于动态调整进程和线程池的大小，确保系统负载均衡。

    参数：
        :param SM - _SynchronizationManager：同步管理器实例
        :param CM - _ConfigManager：配置管理器实例
        :param Logger - logging.Logger：日志记录器实例
        :param DebugMode - bool：调试模式标志

    属性：
        - SynchronizationManager：同步管理器
        - ConfigManager：配置管理器
        - Logger：日志记录器
        - DebugMode：调试模式标志
        - CloseEvent：停止事件

    设计思路：
        1. 初始化线程，设置同步管理器、配置管理器、日志记录器和调试模式
        2. 在 `run` 方法中实现负载均衡逻辑
        3. 根据配置的策略，执行进程和线程的扩展或收缩操作

    """

    def __init__(self, SM: _SynchronizationManager, CM: _ConfigManager, Logger: logging.Logger, DebugMode: bool):
        super().__init__(name='LoadBalancer', daemon=True)
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.Logger = Logger
        self.DebugMode = DebugMode
        self.CloseEvent = multiprocessing.Event()

    def run(self):
        """
        负载均衡器线程运行逻辑，包括定期清理内存、更新线程状态、执行扩展和收缩策略。

        参数：
            无

        返回：
            无

        执行过程：
            1. 初始化休息时间计数器为 0
            2. 清理主进程内存
            3. 清理服务进程内存
            4. 在主线程运行循环中：
                a. 更新线程状态
                b. 执行扩展策略
                c. 执行收缩策略
                d. 暂停 1 秒
                e. 递增休息时间计数器
                f. 每 60 次循环清理主进程和服务进程内存，并重置计数器

        异常：
            无
        """

        rest_times = 0
        self._cleanupMainProcessMemory()
        self._cleanupServiceProcessMemory()
        while not self.CloseEvent.is_set():
            self._updateThreadStatus()
            self._expandPolicyExecutor()
            self._shrinkagePolicyExecutor()
            time.sleep(1)
            rest_times += 1
            if rest_times >= 60:
                self._cleanupMainProcessMemory()
                self._cleanupServiceProcessMemory()
                rest_times = 0

    def stop(self):
        """
        停止负载均衡线程的运行并清理资源。

        参数：
            无

        返回：
            无

        执行过程：
            1. 设置 `CloseEvent` 以通知线程停止运行
            2. 等待线程结束，最多等待 2 秒
            3. 删除线程实例

        异常：
            无
        """

        self.CloseEvent.set()
        self.join(2)
        del self

    def _cleanupMainProcessMemory(self):
        """
        清理主进程的内存。

        参数：
            无

        返回：
            无

        执行过程：
            1. 尝试打开当前进程的句柄以进行内存清理
            2. 如果无法获取句柄，则记录错误日志并退出
            3. 使用 `EmptyWorkingSet` 函数清理进程的内存
            4. 检查是否成功清理内存，如果失败，记录错误代码
            5. 关闭句柄

        异常：
            1. 失败获取进程句柄
            2. 内存清理失败
        """

        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, os.getpid())
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
        except Exception as e:
            self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        if not handle:
            self.Logger.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
            return
        result = ctypes.windll.psapi.EmptyWorkingSet(handle)
        if result == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
        ctypes.windll.kernel32.CloseHandle(handle)

    def _cleanupServiceProcessMemory(self):
        """
        清理服务进程的内存。

        参数：
            无

        返回：
            无

        执行过程：
            1. 尝试使用 `OpenProcess` 函数打开服务进程的句柄以进行内存清理
            2. 如果无法获取句柄，则记录错误日志并退出
            3. 使用 `EmptyWorkingSet` 函数清理服务进程的内存
            4. 检查是否成功清理内存，如果失败，记录错误代码
            5. 关闭句柄

        异常：
            1. 失败获取进程句柄
            2. 内存清理失败
        """

        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.SynchronizationManager.SharedObjectManagerID)
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
        except Exception as e:
            self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        if not handle:
            self.Logger.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
            return
        result = ctypes.windll.psapi.EmptyWorkingSet(handle)
        if result == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
        ctypes.windll.kernel32.CloseHandle(handle)

    def _updateThreadStatus(self):
        """
        更新核心线程池和扩展线程池的状态信息。

        参数：
            无

        返回：
            无

        执行过程：
            1. 遍历 `_CoreThreadPool` 中的每个线程对象
                a. 更新 `CoreThreadStatusPool`，包含线程的标识符和待处理任务的数量
            2. 如果 `_ExpandThreadPool` 存在
                a. 遍历 `_ExpandThreadPool` 中的每个线程对象
                    i. 更新 `ExpandThreadStatusPool`，包含线程的标识符和待处理任务的数量

        异常：
            无
        """

        global _CoreThreadPool, _ExpandThreadPool
        for thread_name, thread_obj in _CoreThreadPool.items():
            self.SynchronizationManager.CoreThreadStatusPool[thread_name] = (thread_obj.ident, len(thread_obj.PendingTasks))
        if _ExpandThreadPool:
            for thread_name, thread_obj in _ExpandThreadPool.items():
                self.SynchronizationManager.ExpandThreadStatusPool[thread_name] = (thread_obj.ident, len(thread_obj.PendingTasks))

    def _expandPolicyExecutor(self):
        """
        根据配置的扩展策略执行相应的扩展方法。

        参数：
            无

        返回：
            无

        执行过程：
            1. 根据 `ConfigManager.ExpandPolicy` 的值选择扩展策略方法
                a. "NoExpand": 调用 `_noExpand` 方法
                b. "AutoExpand": 调用 `_autoExpand` 方法
                c. "BeforehandExpand": 调用 `_beforehandExpand` 方法
            2. 执行选定的扩展策略方法

        异常：
            无
        """

        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self.ConfigManager.ExpandPolicy.value]
        expand_method()

    def _noExpand(self):
        """
        不扩展的占位方法，当前不执行任何扩展操作。

        参数：
            无

        返回：
            无

        执行过程：
            1. 不执行任何操作

        异常：
            无
        """

        pass

    def _autoExpand(self):
        """
        根据当前负载自动扩展进程或线程，依据配置和负载情况进行扩展操作。

        参数：
            无

        返回：
            无

        执行过程：
            1. 计算当前核心进程的总负载和核心线程的总负载。
            2. 计算当前核心进程和核心线程的平均负载。
            3. 根据进程和线程的理想负载值，判断是否需要扩展。
            4. 如果进程的平均负载超过理想负载且允许扩展，则调用扩展进程的方法。
            5. 如果线程的平均负载超过理想负载且允许扩展，则调用扩展线程的方法。

        异常：
            无
        """

        current_core_process_total_load = sum([load for _, _, load in self.SynchronizationManager.CoreProcessStatusPool.values()])
        current_core_thread_total_load = sum([load for _, load in self.SynchronizationManager.CoreThreadStatusPool.values()])

        average_process_load = current_core_process_total_load / len(self.SynchronizationManager.CoreProcessStatusPool) if len(self.SynchronizationManager.CoreProcessStatusPool) > 0 else 0
        average_thread_load = current_core_thread_total_load / len(self.SynchronizationManager.CoreThreadStatusPool) if len(self.SynchronizationManager.CoreThreadStatusPool) > 0 else 0

        ideal_load_per_process = 100 * 0.8 / (len(self.SynchronizationManager.CoreProcessStatusPool) + len(self.SynchronizationManager.ExpandProcessStatusPool))
        ideal_load_per_thread = 100 * 0.8

        if average_process_load > ideal_load_per_process:
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self.Logger.debug(f"Load reaches {int(ideal_load_per_process)}%, but unable to expand more process")

        if average_thread_load > ideal_load_per_thread:
            if self._isExpansionAllowed("Thread"):
                self._expandThread()
            else:
                self.Logger.debug(f"Load reaches {int(ideal_load_per_thread)}%, but unable to expand more thread")

    def _beforehandExpand(self):
        """
        根据待处理任务的总数提前扩展进程或线程，以应对即将到来的任务负载。

        参数：
            无

        返回：
            无

        执行过程：
            1. 计算当前核心进程的待处理任务总数和核心线程的待处理任务总数。
            2. 如果待处理任务总数超过全局任务阈值的80%，则进行扩展操作。
            3. 检查是否允许扩展进程，如果允许，则调用扩展进程的方法。
            4. 检查是否允许扩展线程，如果允许，则调用扩展线程的方法。

        异常：
            无
        """

        core_process_pending_task_count = sum([task_count for _, task_count, _ in self.SynchronizationManager.CoreProcessStatusPool.values()])
        core_thread_pending_task_count = sum([task_count for _, task_count in self.SynchronizationManager.CoreThreadStatusPool.values()])
        if (core_process_pending_task_count + core_thread_pending_task_count) >= self.ConfigManager.GlobalTaskThreshold.value * 0.8:
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self.Logger.debug(f"Pending task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more process")
            if self._isExpansionAllowed("Thread"):
                self._expandThread()
            else:
                self.Logger.debug(f"Pending task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more thread")

    def _isExpansionAllowed(self, expand_type: Literal["Process", "Thread"]) -> bool:
        """
        检查是否允许扩展进程或线程，根据当前的数量和最大数量进行判断。

        参数：
            :param expand_type: 扩展的类型，取值为 "Process" 或 "Thread"。

        返回：
            :return - bool : 是否允许扩展。如果当前数量未达到最大限制，则返回 True；否则返回 False。

        执行过程：
            1. 根据传入的扩展类型判断是进程还是线程。
            2. 如果扩展类型是 "Process"，则检查当前核心进程数量与扩展进程数量的总和是否达到最大进程数量限制。
            3. 如果扩展类型是 "Thread"，则检查当前核心线程数量与扩展线程数量的总和是否达到最大线程数量限制。
            4. 如果当前数量未达到最大限制，则返回 True，表示允许扩展；否则返回 False，表示不允许扩展。

        异常：
            无
        """

        match expand_type:
            case "Process":
                if (len(self.SynchronizationManager.CoreProcessStatusPool) + len(self.SynchronizationManager.ExpandProcessStatusPool)) >= self.ConfigManager.MaximumProcessCount.value:
                    return False
                return True
            case "Thread":
                if (len(self.SynchronizationManager.CoreThreadStatusPool) + len(self.SynchronizationManager.ExpandThreadStatusPool)) >= self.ConfigManager.MaximumThreadCount.value:
                    return False
                return True

    def _expandProcess(self):
        """
        扩展核心进程池，创建一个新的进程对象并启动。

        参数：
            无

        返回：
            无

        执行过程：
            1. 获取当前时间用于记录扩展时间。
            2. 生成一个新的进程 ID。
            3. 创建一个新的进程名称。
            4. 初始化一个新的进程对象，并启动该进程。
            5. 将新创建的进程对象添加到扩展进程池中。
            6. 更新扩展进程状态池，记录新进程的 PID 和初始状态。
            7. 记录新进程的扩展时间。

        异常：
            无
        """

        global _ExpandProcessPool, _ExpandProcessSurvivalTime
        current_time = time.time()
        process_id = self._generateExpandID("Process")
        process_name = f"Process-{process_id}"
        process_object = _ProcessObject(process_name, "Expand", self.SynchronizationManager, self.ConfigManager, self.DebugMode)
        process_object.start()
        _ExpandProcessPool[process_id] = process_object
        self.SynchronizationManager.ExpandProcessStatusPool[process_name] = (process_object.pid, 0, 0)
        _ExpandProcessSurvivalTime[process_name] = current_time

    def _expandThread(self):
        """
        扩展核心线程池，创建一个新的线程对象并启动。

        参数：
            无

        返回：
            无

        执行过程：
            1. 获取当前时间用于记录扩展时间。
            2. 生成一个新的线程 ID。
            3. 创建一个新的线程名称。
            4. 初始化一个新的线程对象，并启动该线程。
            5. 将新创建的线程对象添加到扩展线程池中。
            6. 更新扩展线程状态池，记录新线程的 ID 和初始状态。
            7. 记录新线程的扩展时间。

        异常：
            无
        """

        global _ExpandThreadPool, _ExpandThreadSurvivalTime
        current_time = time.time()
        thread_id = self._generateExpandID("Thread")
        thread_name = f"Thread-{thread_id}"
        thread_object = _ThreadObject(thread_name, "Expand", self.SynchronizationManager, self.ConfigManager, self.Logger)
        thread_object.start()
        _ExpandThreadPool[thread_id] = thread_object
        self.SynchronizationManager.ExpandThreadStatusPool[thread_name] = (thread_object.ident, 0)
        _ExpandThreadSurvivalTime[thread_name] = current_time

    @staticmethod
    def _generateExpandID(expand_type: Literal["Process", "Thread"]):
        """
        生成唯一的扩展 ID，根据扩展类型（进程或线程）递增编号。

        参数：
            :param expand_type - 扩展类型，"Process" 或 "Thread"。决定生成哪个类型的 ID。

        返回：
            :return - 生成的唯一 ID 字符串。

        执行过程：
            1. 根据扩展类型选择相应的扩展池（进程池或线程池）。
            2. 初始化基本 ID 为 `{expand_type}-0`。
            3. 使用循环检查该 ID 是否已存在于扩展池中。
            4. 如果 ID 不存在，则返回该 ID。
            5. 如果 ID 已存在，则递增编号并继续检查。

        异常：
            无
        """

        global _ExpandProcessPool, _ExpandThreadPool
        expand_type_mapping = {
            "Process": _ExpandProcessPool,
            "Thread": _ExpandThreadPool,
        }
        basic_id = f"{expand_type}-{0}"
        while True:
            if basic_id not in expand_type_mapping[expand_type]:
                return basic_id
            basic_id = f"{expand_type}-{int(basic_id.split('-')[-1]) + 1}"

    def _shrinkagePolicyExecutor(self):
        """
        执行收缩策略，根据配置的收缩策略类型来决定如何缩减进程或线程。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 根据配置的收缩策略选择对应的收缩方法（`NoShrink`、`AutoShrink` 或 `TimeoutShrink`）。
            2. 调用选择的收缩方法以执行相应的收缩操作。

        异常：
            无
        """

        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self.ConfigManager.ShrinkagePolicy.value]
        shrink_method()

    def _noShrink(self):
        """
        不执行任何收缩操作。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 方法体为空，不进行任何操作。

        异常：
            无
        """

        pass

    def _autoShrink(self):
        """
        根据设定的收缩策略，自动关闭空闲的进程和线程。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 获取当前所有的扩展进程和线程对象。
            2. 识别出所有空闲的进程和线程对象（其任务计数为零）。
            3. 根据设定的超时时间，筛选出可以关闭的空闲进程和线程。
            4. 对于符合关闭条件的进程，调用其 `stop` 方法停止其运行，并从相关全局字典和状态池中移除该进程。
            5. 对于符合关闭条件的线程，调用其 `stop` 方法停止其运行，并从相关全局字典和状态池中移除该线程。

        异常：
            无
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime
        expand_process_obj = [obj for i, obj in _ExpandProcessPool.items()]
        expand_thread_obj = [obj for i, obj in _ExpandThreadPool.items()]

        idle_process = [obj for obj in expand_process_obj if self.SynchronizationManager.ExpandProcessStatusPool[obj.ProcessName][1] == 0]
        idle_thread = [obj for obj in expand_thread_obj if self.SynchronizationManager.ExpandThreadStatusPool[obj.ThreadName][1] == 0]

        allow_close_process = [obj for obj in idle_process if (time.time() - _ExpandProcessSurvivalTime[obj.ProcessName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
        allow_close_thread = [obj for obj in idle_thread if (time.time() - _ExpandThreadSurvivalTime[obj.ThreadName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value]

        if idle_process:
            for obj in idle_process:
                if obj in allow_close_process:
                    obj.stop()
                    del _ExpandProcessPool[obj.ProcessName]
                    del self.SynchronizationManager.ExpandProcessStatusPool[obj.ProcessName]
                    del _ExpandProcessSurvivalTime[obj.ProcessName]
                    self.Logger.debug(f"Process {obj.ProcessName} has been closed due to idle status.")

        if idle_thread:
            for obj in idle_thread:
                if obj in allow_close_thread:
                    obj.stop()
                    del _ExpandThreadPool[obj.ThreadName]
                    del self.SynchronizationManager.ExpandThreadStatusPool[obj.ThreadName]
                    del _ExpandThreadSurvivalTime[obj.ThreadName]
                    self.Logger.debug(f"Thread {obj.ThreadName} has been closed due to idle status.")

    def _timeoutShrink(self):
        """
        根据设定的超时时间，关闭超时的空闲进程和线程。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 筛选出超时的扩展进程对象（当前时间减去创建时间超过设定的超时时间）。
            2. 筛选出超时的扩展线程对象（当前时间减去创建时间超过设定的超时时间）。
            3. 对于超时的扩展进程，调用其 `stop` 方法停止其运行，并从相关全局字典和状态池中移除该进程。
            4. 对于超时的扩展线程，调用其 `stop` 方法停止其运行，并从相关全局字典和状态池中移除该线程。

        异常：
            无
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime
        expand_process_obj = [obj for obj, survival_time in _ExpandProcessSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
        expand_thread_obj = [obj for obj, survival_time in _ExpandThreadSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]

        if expand_process_obj:
            for obj in expand_process_obj:
                _ExpandProcessPool[obj].stop()
                del _ExpandProcessPool[obj]
                del self.SynchronizationManager.ExpandProcessStatusPool[obj]
                del _ExpandProcessSurvivalTime[obj]
                self.Logger.debug(f"Process {obj} has been closed due to timeout.")

        if expand_thread_obj:
            for obj in expand_thread_obj:
                _ExpandThreadPool[obj].stop()
                del _ExpandThreadPool[obj]
                del self.SynchronizationManager.ExpandThreadStatusPool[obj]
                del _ExpandThreadSurvivalTime[obj]
                self.Logger.debug(f"Thread {obj} has been closed due to timeout.")


class _ProcessTaskScheduler(threading.Thread):
    """
    进程任务调度器，基于进程的状态和负载情况，将任务分配给适当的进程。

    参数：
        :param SM: `_SynchronizationManager` 实例，用于管理进程同步
        :param CM: `_ConfigManager` 实例，用于配置管理
        :param ProcessTaskStorageQueue: 存储进程任务的队列
        :param Logger: 日志记录器实例，用于记录调度过程中的信息

    属性：
        - SynchronizationManager: `_SynchronizationManager` 实例
        - ConfigManager: `_ConfigManager` 实例
        - ProcessTaskStorageQueue: 存储进程任务的队列
        - Logger: 日志记录器实例
        - LastSelectedProcess: 上次选择的进程对象
        - CloseEvent: 用于控制线程停止的事件

    设计思路：
        1. 从队列中获取任务数据，并根据任务优先级和进程状态决定任务的调度。
        2. 优先分配任务给未工作的核心进程，若核心进程都忙碌，则考虑扩展进程。
        3. 若核心进程和扩展进程都不可用，将任务放回队列等待重新调度。
        4. 提供停止方法安全地停止调度线程的执行并释放资源。

    """

    def __init__(self, SM: _SynchronizationManager, CM: _ConfigManager, ProcessTaskStorageQueue: multiprocessing.Queue, Logger: logging.Logger):
        super().__init__(name='ProcessTaskScheduler', daemon=True)
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.ProcessTaskStorageQueue = ProcessTaskStorageQueue
        self.Logger = Logger
        self.LastSelectedProcess = None
        self.CloseEvent = multiprocessing.Event()

    def run(self):
        """
        在关闭事件未触发时，不断从任务存储队列中获取任务并进行调度，直到所有任务被调度完毕。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 初始化调度计数器 `scheduled_count` 为0。
            2. 在关闭事件 `CloseEvent` 未触发的情况下：
                a. 如果已调度的任务数量等于核心进程池和扩展进程池中的进程数量总和，则等待1秒钟后重置调度计数器，并继续循环。
                b. 尝试从任务存储队列 `ProcessTaskStorageQueue` 中获取任务数据。如果队列为空，则等待0.001秒后继续循环。
                c. 如果成功获取到任务数据，调用 `_scheduler` 方法对任务进行调度，并增加调度计数器 `scheduled_count` 的值。

        异常：
            无
        """

        scheduled_count = 0
        while not self.CloseEvent.is_set():
            if scheduled_count == (len(self.SynchronizationManager.CoreProcessStatusPool) + len(self.SynchronizationManager.ExpandProcessStatusPool)):
                time.sleep(1)
                scheduled_count = 0
                continue
            try:
                task_data = self.ProcessTaskStorageQueue.get_nowait()
            except queue.Empty:
                time.sleep(0.001)
                continue
            priority, task_object = task_data
            self._scheduler(priority, task_object)
            scheduled_count += 1

    def stop(self):
        """
        触发关闭事件并等待线程停止，然后删除线程实例。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 触发关闭事件 `CloseEvent`。
            2. 等待线程终止 `join` 最多等待2秒。
            3. 删除线程实例 `self`。

        异常：
            无
        """

        self.CloseEvent.set()
        self.join(2)
        del self

    def _scheduler(self, priority: int, task_object: _TaskObject):
        """
        根据任务优先级和进程负载情况将任务分配到合适的进程中。如果没有适合的进程，则将任务放入任务存储队列中。

        参数：
            :param - priority: 任务的优先级。
            :param - task_object: 任务对象，包含任务的详细信息和操作。

        返回：
            :return - 无

        执行过程：
            1. 检查并获取未工作的核心进程列表。
            2. 如果有未工作的核心进程，将任务分配给负载最小的核心进程，并设置其工作事件。
            3. 如果没有未工作的核心进程，检查核心进程是否已满。
                a. 如果有核心进程未满，选择负载最小的核心进程，分配任务，并设置其工作事件（如果尚未设置）。
            4. 如果核心进程池已满，检查并获取未工作的扩展进程列表。
                a. 如果有未工作的扩展进程，将任务分配给负载最小的扩展进程，并设置其工作事件。
                b. 如果没有未工作的扩展进程，检查扩展进程是否已满。
                    i. 如果有扩展进程未满，选择负载最小的扩展进程，分配任务，并设置其工作事件（如果尚未设置）。
            5. 如果没有合适的进程可用，将任务放入任务存储队列中。

        异常：
            无
        """

        global _ExpandProcessPool
        not_working_core_processes = self._checkNotWorkingProcess("Core")
        not_full_core_processes = self._checkNotFullProcess("Core")

        if not_working_core_processes:
            minimum_load_core_process = self._checkMinimumLoadProcess(not_working_core_processes, "Core")
            minimum_load_core_process.addProcessTask(priority, task_object)
            minimum_load_core_process.WorkingEvent.set()
            return
        if not_full_core_processes:
            minimum_load_core_process = self._checkMinimumLoadProcess(not_full_core_processes, "Core")
            minimum_load_core_process.addProcessTask(priority, task_object)
            if not minimum_load_core_process.WorkingEvent.is_set():
                minimum_load_core_process.WorkingEvent.set()
            return
        if _ExpandProcessPool:
            not_working_expand_processes = self._checkNotWorkingProcess("Expand")
            not_full_expand_processes = self._checkNotFullProcess("Expand")

            if not_working_expand_processes:
                minimum_load_expand_process = self._checkMinimumLoadProcess(not_working_expand_processes, "Expand")
                minimum_load_expand_process.addProcessTask(priority, task_object)
                minimum_load_expand_process.WorkingEvent.set()
                return
            if not_full_expand_processes:
                minimum_load_expand_process = self._checkMinimumLoadProcess(not_full_expand_processes, "Expand")
                minimum_load_expand_process.addProcessTask(priority, task_object)
                if not minimum_load_expand_process.WorkingEvent.is_set():
                    minimum_load_expand_process.WorkingEvent.set()
                return
            self.ProcessTaskStorageQueue.put_nowait((priority, task_object))
            return
        self.ProcessTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNotFullProcess(self, process_type: Literal["Core", "Expand"]) -> list:
        """
        检查并返回未满的进程列表，这些进程的任务负载低于设定的阈值。

        参数：
            :param - process_type: 进程类型，"Core" 表示核心进程，"Expand" 表示扩展进程。

        返回：
            :return - not_full_processes: 未满的进程对象列表。

        执行过程：
            1. 根据 `process_type` 参数选择对应的进程池和状态池。
                a. 如果 `process_type` 为 "Core"，选择核心进程池和核心进程状态池。
                b. 如果 `process_type` 为 "Expand"，选择扩展进程池和扩展进程状态池。
            2. 遍历选择的进程池，检查每个进程的任务负载。
                a. 如果进程的任务负载低于配置的任务阈值，则将其添加到未满进程列表中。
            3. 返回未满进程列表。

        异常：
            无
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        status_pool = self.SynchronizationManager.CoreProcessStatusPool if process_type == "Core" else self.SynchronizationManager.ExpandProcessStatusPool
        not_full_processes = [obj for index, obj in obj_pool.items() if status_pool[obj.ProcessName][1] < self.ConfigManager.TaskThreshold.value]
        return not_full_processes

    @staticmethod
    def _checkNotWorkingProcess(process_type: Literal["Core", "Expand"]) -> list:
        """
        检查并返回未工作的进程列表，这些进程的工作事件未设置。

        参数：
            :param - process_type: 进程类型，"Core" 表示核心进程，"Expand" 表示扩展进程。

        返回：
            :return - not_working_processes: 未工作的进程对象列表。

        执行过程：
            1. 根据 `process_type` 参数选择对应的进程池。
                a. 如果 `process_type` 为 "Core"，选择核心进程池。
                b. 如果 `process_type` 为 "Expand"，选择扩展进程池。
            2. 遍历选择的进程池，检查每个进程的工作事件。
                a. 如果进程的工作事件未设置，则将其添加到未工作进程列表中。
            3. 返回未工作进程列表。

        异常：
            无
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        not_working_processes = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_processes

    def _checkMinimumLoadProcess(self, processes: list, process_type: Literal["Core", "Expand"]) -> _ProcessObject:
        """
        在给定的进程列表中选择负载最小的进程，并返回该进程对象。

        参数：
            :param - processes: 进程对象列表，从中选择负载最小的进程。
            :param - process_type: 进程类型，"Core" 表示核心进程，"Expand" 表示扩展进程。

        返回：
            :return - selected_process: 负载最小的进程对象。

        执行过程：
            1. 根据 `process_type` 参数选择对应的进程状态池。
                a. 如果 `process_type` 为 "Core"，选择核心进程状态池。
                b. 如果 `process_type` 为 "Expand"，选择扩展进程状态池。
            2. 从 `processes` 列表中过滤掉最后选择的进程（如果存在），以避免选择相同的进程。
            3. 如果过滤后的进程列表为空，则选择原始进程列表中的第一个进程。
            4. 否则，选择负载最小的进程。
                a. 使用状态池中的负载信息作为排序依据。
            5. 更新 `LastSelectedProcess` 为当前选择的进程。

        异常：
            无
        """

        status_pool = self.SynchronizationManager.CoreProcessStatusPool if process_type == "Core" else self.SynchronizationManager.ExpandProcessStatusPool
        available_processes = [p for p in processes if p != self.LastSelectedProcess] if self.LastSelectedProcess is not None else processes
        if not available_processes:
            selected_process = processes[0]
        else:
            selected_process = min(available_processes, key=lambda x: status_pool[x.ProcessName][2])
        self.LastSelectedProcess = selected_process
        return selected_process


class _ThreadTaskScheduler(threading.Thread):
    """
    线程任务调度器，基于线程的状态和负载情况，将任务分配给适当的线程。

    参数：
        :param SM: `_SynchronizationManager` 实例，用于管理线程同步
        :param CM: `_ConfigManager` 实例，用于配置管理
        :param ThreadTaskStorageQueue: 存储线程任务的队列
        :param Logger: 日志记录器实例，用于记录调度过程中的信息

    属性：
        - SynchronizationManager: `_SynchronizationManager` 实例
        - ConfigManager: `_ConfigManager` 实例
        - ThreadTaskStorageQueue: 存储线程任务的队列
        - Logger: 日志记录器实例
        - LastSelectedThread: 上次选择的线程对象
        - CloseEvent: 用于控制线程停止的事件

    设计思路：
        1. 从队列中获取任务数据，并根据任务优先级和线程状态决定任务的调度。
        2. 优先分配任务给未工作的核心线程，若核心线程都忙碌，则考虑扩展线程。
        3. 若核心线程和扩展线程都不可用，将任务放回队列等待重新调度。
        4. 提供停止方法安全地停止调度线程的执行并释放资源。

    """

    def __init__(self, SM: _SynchronizationManager, CM: _ConfigManager, ThreadTaskStorageQueue: queue.Queue, Logger: logging.Logger):
        super().__init__(name='ThreadTaskScheduler', daemon=True)
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.ThreadTaskStorageQueue = ThreadTaskStorageQueue
        self.Logger = Logger
        self.LastSelectedThread = None
        self.CloseEvent = multiprocessing.Event()

    def run(self):
        """
        管理线程任务的调度，通过检查线程池的状态来决定是否调度任务，并根据任务优先级将任务分配给适当的线程。

        参数：
            无

        返回：
            无

        执行过程：
            1. 初始化调度计数器 `scheduled_count` 为 0。
            2. 进入主循环，直到 `CloseEvent` 被设置为停止信号。
                a. 如果 `scheduled_count` 等于核心线程池和扩展线程池中线程数量的总和，则表示所有线程都已调度，暂停 1 秒后重置 `scheduled_count` 为 0。
                b. 尝试从 `ThreadTaskStorageQueue` 中获取任务数据。
                    i. 如果队列为空，则暂停 0.001 秒后继续循环。
                c. 处理获取到的任务数据，包括优先级和任务对象。
                    i. 调用 `_scheduler` 方法将任务分配给合适的线程。
                    ii. 增加 `scheduled_count`。

        异常：
            无
        """

        scheduled_count = 0
        while not self.CloseEvent.is_set():
            if scheduled_count == (len(self.SynchronizationManager.CoreThreadStatusPool) + len(self.SynchronizationManager.ExpandThreadStatusPool)):
                time.sleep(1)
                scheduled_count = 0
                continue
            try:
                task_data = self.ThreadTaskStorageQueue.get_nowait()
            except queue.Empty:
                time.sleep(0.001)
                continue
            priority, task_object = task_data
            self._scheduler(priority, task_object)
            scheduled_count += 1

    def stop(self):
        """
        停止线程的执行，等待线程安全地终止，并释放线程的资源。

        参数：
            无

        返回：
            无

        执行过程：
            1. 设置 `CloseEvent` 为停止信号，通知线程停止工作。
            2. 等待线程终止，最多等待 2 秒。
            3. 删除线程对象，释放资源。

        异常：
            无
        """

        self.CloseEvent.set()
        self.join(2)
        del self

    def _scheduler(self, priority: int, task_object: _TaskObject):
        """
        调度任务到合适的线程中，根据线程的工作状态和负载情况决定任务的分配。

        参数：
            :param priority: 任务的优先级
            :param task_object: 任务对象，包含执行任务所需的信息

        返回：
            无

        执行过程：
            1. 检查核心线程中未工作的线程。
            2. 如果存在未工作的核心线程，选择负载最小的线程，将任务分配给它，并设置工作事件。
            3. 如果所有核心线程都有工作，但有负载未满的核心线程，选择负载最小的线程，将任务分配给它。
            4. 如果核心线程不可用，检查扩展线程中未工作的线程。
            5. 如果存在未工作的扩展线程，选择负载最小的线程，将任务分配给它，并设置工作事件。
            6. 如果所有扩展线程都有工作，但有负载未满的扩展线程，选择负载最小的线程，将任务分配给它。
            7. 如果以上条件都不满足，将任务放入任务存储队列，等待调度。

        异常：
            无
        """

        global _ExpandThreadPool
        not_working_core_threads = self._checkNonWorkingThread("Core")
        not_full_core_threads = self._checkNonFullThread("Core")

        if not_working_core_threads:
            minimum_load_core_thread = self._checkMinimumLoadThread(not_working_core_threads, "Core")
            minimum_load_core_thread.addThreadTask(priority, task_object)
            minimum_load_core_thread.WorkingEvent.set()
            return
        if not_full_core_threads:
            minimum_load_core_thread = self._checkMinimumLoadThread(not_full_core_threads, "Core")
            minimum_load_core_thread.addThreadTask(priority, task_object)
            if not minimum_load_core_thread.WorkingEvent.is_set():
                minimum_load_core_thread.WorkingEvent.set()
            return
        if _ExpandThreadPool:
            not_working_expand_threads = self._checkNonWorkingThread("Expand")
            not_full_expand_threads = self._checkNonFullThread("Expand")

            if not_working_expand_threads:
                minimum_load_expand_thread = self._checkMinimumLoadThread(not_working_expand_threads, "Expand")
                minimum_load_expand_thread.addThreadTask(priority, task_object)
                minimum_load_expand_thread.WorkingEvent.set()
                return
            if not_full_expand_threads:
                minimum_load_expand_thread = self._checkMinimumLoadThread(not_full_expand_threads, "Expand")
                minimum_load_expand_thread.addThreadTask(priority, task_object)
                if not minimum_load_expand_thread.WorkingEvent.is_set():
                    minimum_load_expand_thread.WorkingEvent.set()
                return
            self.ThreadTaskStorageQueue.put_nowait((priority, task_object))
            return
        self.ThreadTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNonFullThread(self, thread_type: Literal["Core", "Expand"]) -> list:
        """
        检查并返回负载未满的线程对象列表。

        参数：
            :param thread_type: 线程类型，可为 "Core" 或 "Expand"，用于指定检查核心线程还是扩展线程

        返回：
            :return - not_full_threads: 负载未满的线程对象列表

        执行过程：
            1. 根据 `thread_type` 确定使用的线程池（核心线程池或扩展线程池）。
            2. 根据 `thread_type` 确定使用的线程状态池（核心线程状态池或扩展线程状态池）。
            3. 从线程池中筛选出负载小于 `ConfigManager.TaskThreshold.value` 的线程对象。

        异常：
            无
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        status_pool = self.SynchronizationManager.CoreThreadStatusPool if thread_type == "Core" else self.SynchronizationManager.ExpandThreadStatusPool
        not_full_threads = [obj for index, obj in obj_pool.items() if status_pool[obj.ThreadName][1] < self.ConfigManager.TaskThreshold.value]
        return not_full_threads

    @staticmethod
    def _checkNonWorkingThread(thread_type: Literal["Core", "Expand"]) -> list:
        """
        检查并返回未工作的线程对象列表。

        参数：
            :param thread_type: 线程类型，可为 "Core" 或 "Expand"，用于指定检查核心线程还是扩展线程

        返回：
            :return - not_working_threads: 未工作的线程对象列表

        执行过程：
            1. 根据 `thread_type` 确定使用的线程池（核心线程池或扩展线程池）。
            2. 从线程池中筛选出 `WorkingEvent` 未设置的线程对象。

        异常：
            无
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        not_working_threads = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_threads

    def _checkMinimumLoadThread(self, threads: list, thread_type: Literal["Core", "Expand"]) -> _ThreadObject:
        """
        从给定的线程列表中选择负载最小的线程对象。

        参数：
            :param threads: 线程对象列表，用于选择负载最小的线程
            :param thread_type: 线程类型，可为 "Core" 或 "Expand"，用于确定使用的线程状态池

        返回：
            :return - selected_thread: 负载最小的线程对象

        执行过程：
            1. 根据 `thread_type` 确定使用的线程状态池（核心线程状态池或扩展线程状态池）。
            2. 排除上次选择的线程（如果有）。
            3. 从剩余的线程中选择负载最小的线程作为结果。
            4. 更新 `LastSelectedThread` 为选择的线程。

        异常：
            无
        """

        status_pool = self.SynchronizationManager.CoreThreadStatusPool if thread_type == "Core" else self.SynchronizationManager.ExpandThreadStatusPool
        available_threads = [p for p in threads if p != self.LastSelectedThread] if self.LastSelectedThread is not None else threads
        if not available_threads:
            selected_thread = threads[0]
        else:
            selected_thread = min(available_threads, key=lambda x: status_pool[x.ThreadName][1])
        self.LastSelectedThread = selected_thread
        return selected_thread


class ConcurrentSystem:
    """
    TheSeedCore并发系统核心，用于管理核心进程、核心线程、负载均衡、任务调度和回调执行。

    参数：
        :param SM: `_SynchronizationManager` 实例，用于进程和线程同步
        :param CM: `_ConfigManager` 实例，用于配置管理
        :param DebugMode: 是否启用调试模式，默认为 False

    属性：
        - _INSTANCE：单例模式的唯一实例
        - _INITIALIZED：标记系统是否已初始化
        - _ProcessTaskStorageQueue：用于存储进程任务的队列
        - _ThreadTaskStorageQueue：用于存储线程任务的队列
        - _Logger：日志记录器实例
        - _LoadBalancer：负载均衡器实例
        - _ProcessTaskScheduler：进程任务调度器实例
        - _ThreadTaskScheduler：线程任务调度器实例
        - _CallbackExecutor：回调执行器实例
        - _SystemThreadPoolExecutor：系统线程池执行器实例

    设计思路：
        1. 使用单例模式确保 `ConcurrentSystem` 只有一个实例。
        2. 初始化系统组件，包括任务队列、日志记录器、负载均衡器、任务调度器和回调执行器。
        3. 根据配置启动核心进程和核心线程。
        4. 提供方法提交进程任务和线程任务，并处理任务优先级、回调、锁定和 GPU 加速等。
        5. 提供方法关闭系统并停止所有相关组件。

    异常：
        1. RuntimeError: 如果在非主进程中提交任务或系统尚未初始化。
        2. pickle.PicklingError, AttributeError, TypeError: 任务函数序列化失败。
    """

    _INSTANCE: ConcurrentSystem = None
    _INITIALIZED: bool = False

    def __new__(cls, SM: '_SynchronizationManager' = None, CM: '_ConfigManager' = None, DebugMode: bool = False):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(ConcurrentSystem, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, SM: '_SynchronizationManager' = None, CM: '_ConfigManager' = None, DebugMode: bool = False):
        if self._INITIALIZED:
            return
        self._SynchronizationManager = SM
        self._ConfigManager = CM
        self._DebugMode = DebugMode
        self._ProcessTaskStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self._ThreadTaskStorageQueue: queue.Queue = queue.Queue()
        self._Logger = self._setLogger()
        self._LoadBalancer = _LoadBalancer(self._SynchronizationManager, self._ConfigManager, self._Logger, self._DebugMode)
        self._ProcessTaskScheduler = _ProcessTaskScheduler(self._SynchronizationManager, self._ConfigManager, self._ProcessTaskStorageQueue, self._Logger)
        self._ThreadTaskScheduler = _ThreadTaskScheduler(self._SynchronizationManager, self._ConfigManager, self._ThreadTaskStorageQueue, self._Logger)
        self._CallbackExecutor: Union[_QtCallbackExecutor, _CoreCallbackExecutor] = self._setCallbackExecutor()
        self._SystemThreadPoolExecutor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self._ConfigManager.CoreProcessCount.value + self._ConfigManager.CoreThreadCount.value)
        self._INITIALIZED = True
        self._initSystem()

    @classmethod
    def submitProcessTask(cls, task: callable, priority: int = 0, callback: callable = None, lock: bool = False, lock_timeout: int = 3, timeout: int = None, gpu_boost: bool = False, gpu_id: int = 0, retry: bool = True, max_retries: int = 3, *args, **kwargs):
        """
        提交一个进程任务

        参数：
            :param task: 需要提交的任务函数（可调用对象）
            :param priority: 任务的优先级，默认为 0，最大值为 10
            :param callback: 任务完成后的回调函数，默认为 None
            :param lock: 是否对任务加锁，默认为 False
            :param lock_timeout: 锁超时时间，单位秒，默认为 3
            :param timeout: 任务超时时间，单位秒，默认为 3
            :param gpu_boost: 是否启用 GPU 加速，默认为 False
            :param gpu_id: 使用的 GPU ID，默认为 0
            :param retry: 是否启用任务重试机制，默认为 True
            :param max_retries: 最大重试次数，默认为 3
            :param args: 传递给任务函数的其他位置参数
            :param kwargs: 传递给任务函数的其他关键字参数

        返回：
            无

        执行过程：
            1. 检查当前进程是否为主进程，否则抛出异常。
            2. 检查 `TheSeedCore ConcurrentSystem` 是否已初始化，否则抛出异常。
            3. 生成一个唯一的任务 ID。
            4. 尝试序列化任务函数以确保其可序列化。
                a. 如果序列化失败，记录错误并退出。
            5. 创建一个任务对象 `_TaskObject`。
            6. 将任务对象放入 `ProcessTaskStorageQueue` 中，并根据优先级调整。
            7. 如果提供了回调函数，将回调函数添加到 `_CallbackObject` 中，以便在任务完成时调用。

        异常：
            1. RuntimeError: 如果当前进程不是主进程，或 `TheSeedCore ConcurrentSystem` 尚未初始化。
            2. pickle.PicklingError, AttributeError, TypeError: 任务函数的序列化失败。
        """

        global _CallbackObject, _CoreProcessPool, _ExpandProcessPool
        if multiprocessing.current_process().name != 'MainProcess':
            raise RuntimeError("Process task submission must be done in the main process.")
        if cls._INSTANCE is None:
            raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
        task_id = f"{uuid.uuid4()}"
        try:
            pickle.dumps(task)
        except (pickle.PicklingError, AttributeError, TypeError) as e:
            cls._INSTANCE._Logger.error(f"Task [{task.__name__} - {task_id}] serialization failed. Task submission has been rejected.\n{e}")
            return
        task_object = _TaskObject(task, task_id, False if callback is None else True, lock, lock_timeout, timeout, gpu_boost, gpu_id, retry, max_retries, *args, **kwargs)
        cls._INSTANCE._ProcessTaskStorageQueue.put_nowait((priority if not priority > 10 else 10, task_object))
        if callback is not None:
            _CallbackObject[task_id] = callback

    @classmethod
    def submitThreadTask(cls, task: callable, priority: int = 0, callback: callable = None, lock: bool = False, lock_timeout: int = 3, timeout: int = None, gpu_boost: bool = False, gpu_id: int = 0, retry: bool = True, max_retries: int = 3, *args, **kwargs):
        """
        提交一个线程任务

        参数：
            :param task: 需要提交的任务函数（可调用对象）
            :param priority: 任务的优先级，默认为 0，最大值为 10
            :param callback: 任务完成后的回调函数，默认为 None
            :param lock: 是否对任务加锁，默认为 False
            :param lock_timeout: 锁超时时间，单位秒，默认为 3
            :param timeout: 任务超时时间，单位秒，默认为 3
            :param gpu_boost: 是否启用 GPU 加速，默认为 False
            :param gpu_id: 使用的 GPU ID，默认为 0
            :param retry: 是否启用任务重试机制，默认为 True
            :param max_retries: 最大重试次数，默认为 3
            :param args: 传递给任务函数的其他位置参数
            :param kwargs: 传递给任务函数的其他关键字参数

        返回：
            无

        执行过程：
            1. 检查当前进程是否为主进程，否则抛出异常。
            2. 检查 `TheSeedCore ConcurrentSystem` 是否已初始化，否则抛出异常。
            3. 生成一个唯一的任务 ID。
            4. 创建一个任务对象 `_TaskObject`。
            5. 将任务对象放入 `ThreadTaskStorageQueue` 中，并根据优先级调整。
            6. 如果提供了回调函数，将回调函数添加到 `_CallbackObject` 中，以便在任务完成时调用。

        异常：
            1. RuntimeError: 如果当前进程不是主进程，或 `TheSeedCore ConcurrentSystem` 尚未初始化。
        """

        global _CallbackObject
        if multiprocessing.current_process().name != 'MainProcess':
            raise RuntimeError("Thread task submission must be done in the main process.")
        if cls._INSTANCE is None:
            raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
        task_id = f"{uuid.uuid4()}"
        task_object = _TaskObject(task, task_id, False if callback is None else True, lock, lock_timeout, timeout, gpu_boost, gpu_id, retry, max_retries, *args, **kwargs)
        cls._INSTANCE._ThreadTaskStorageQueue.put_nowait((priority if not priority > 10 else 10, task_object))
        if callback is not None:
            _CallbackObject[task_id] = callback

    @classmethod
    def closeSystem(cls):
        """
        关闭并发系统，包括所有的核心和扩展进程、线程，并停止相关的调度器和执行器。

        参数：
            无

        返回：
            无

        执行过程：
            1. 检查当前进程是否为主进程，否则抛出异常。
            2. 检查 `TheSeedCore ConcurrentSystem` 是否已初始化，否则抛出异常。
            3. 遍历 `_CoreProcessPool` 中的每个核心进程，提交停止任务到 `_SystemThreadPoolExecutor`。
            4. 遍历 `_CoreThreadPool` 中的每个核心线程，提交停止任务到 `_SystemThreadPoolExecutor`。
            5. 遍历 `_ExpandProcessPool` 中的每个扩展进程，提交停止任务到 `_SystemThreadPoolExecutor`。
            6. 遍历 `_ExpandThreadPool` 中的每个扩展线程，提交停止任务到 `_SystemThreadPoolExecutor`。
            7. 等待所有停止任务完成。
            8. 停止负载均衡器 `_LoadBalancer`。
            9. 停止进程任务调度器 `_ProcessTaskScheduler`。
            10. 停止线程任务调度器 `_ThreadTaskScheduler`。
            11. 关闭回调执行器 `_CallbackExecutor`。
            12. 关闭系统线程池执行器 `_SystemThreadPoolExecutor`，等待所有任务完成并取消未完成的任务。

        异常：
            1. RuntimeError: 如果当前进程不是主进程，或 `TheSeedCore ConcurrentSystem` 尚未初始化。
        """

        global _CoreProcessPool, _CoreThreadPool, _ExpandProcessPool, _ExpandThreadPool
        if multiprocessing.current_process().name != 'MainProcess':
            raise RuntimeError("System closing must be done in the main process.")
        if cls._INSTANCE is None:
            raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
        futures = []
        for process_name, process_obj in _CoreProcessPool.items():
            future = cls._INSTANCE._SystemThreadPoolExecutor.submit(process_obj.stop)
            futures.append(future)
        for thread_name, thread_obj in _CoreThreadPool.items():
            future = cls._INSTANCE._SystemThreadPoolExecutor.submit(thread_obj.stop)
            futures.append(future)
        for process_name, process_obj in _ExpandProcessPool.items():
            future = cls._INSTANCE._SystemThreadPoolExecutor.submit(process_obj.stop)
            futures.append(future)
        for thread_name, thread_obj in _ExpandThreadPool.items():
            future = cls._INSTANCE._SystemThreadPoolExecutor.submit(thread_obj.stop)
            futures.append(future)
        for future in futures:
            future.result()
        cls._INSTANCE._LoadBalancer.stop()
        cls._INSTANCE._ProcessTaskScheduler.stop()
        cls._INSTANCE._ThreadTaskScheduler.stop()
        cls._INSTANCE._CallbackExecutor.closeExecutor()
        cls._INSTANCE._SystemThreadPoolExecutor.shutdown(wait=True, cancel_futures=True)

    def _setLogger(self) -> logging.Logger:
        """
        设置并返回用于 `TheSeedCore - ConcurrentSystem` 的日志记录器。

        参数：
            无

        返回：
            :return - logger : 配置好的日志记录器

        执行过程：
            1. 创建一个名为 'TheSeedCore - ConcurrentSystem' 的日志记录器实例。
            2. 设置日志记录器的日志级别为 DEBUG。
            3. 创建一个流处理器，用于将日志输出到控制台。
            4. 根据调试模式设置流处理器的日志级别，如果是调试模式则为 DEBUG，否则为 DEBUG 和 WARNING 中的较高级别。
            5. 创建一个带有彩色格式化的格式器，并设置流处理器的格式器。
            6. 将流处理器添加到日志记录器中。
            7. 返回配置好的日志记录器。

        异常：
            无
        """

        logger = logging.getLogger('TheSeedCore - ConcurrentSystem')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if self._DebugMode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        return logger

    def _setCallbackExecutor(self):
        """
        设置并返回适当的回调执行器，根据是否存在 QApplication 实例来选择。

        参数：
            无

        返回：
            :return - 回调执行器实例 : 根据是否存在 QApplication 实例返回对应的回调执行器

        执行过程：
            1. 检查是否存在 QApplication 类及其实例。
            2. 如果 QApplication 实例存在，则返回一个 `_QtCallbackExecutor` 实例。
            3. 如果 QApplication 实例不存在，则返回一个 `_CoreCallbackExecutor` 实例。

        异常：
            无
        """

        # noinspection PyUnresolvedReferences
        if QApplication and QApplication.instance():
            return _QtCallbackExecutor(self._SynchronizationManager)
        return _CoreCallbackExecutor(self._SynchronizationManager)

    def _initSystem(self):
        """
        初始化核心进程和核心线程，并启动负载均衡器、任务调度器和回调执行器。

        参数：
            无

        返回：
            无

        执行过程：
            1. 初始化核心进程。
                a. 根据配置的核心进程数量循环创建进程名称。
                b. 使用线程池执行 `_startCoreProcess` 方法来启动每个核心进程。
            2. 初始化核心线程。
                a. 根据配置的核心线程数量循环创建线程名称。
                b. 使用线程池执行 `_startCoreThread` 方法来启动每个核心线程。
            3. 等待所有核心进程和核心线程的初始化完成。
            4. 启动负载均衡器、进程任务调度器和线程任务调度器。
            5. 启动回调执行器。

        异常：
            无
        """

        global _CoreProcessPool, _CoreThreadPool
        futures = []
        for i in range(self._ConfigManager.CoreProcessCount.value):
            process_name = f"Process-{i}"
            future = self._SystemThreadPoolExecutor.submit(self._startCoreProcess, process_name)
            futures.append(future)

        for i in range(self._ConfigManager.CoreThreadCount.value):
            thread_name = f"Thread-{i}"
            future = self._SystemThreadPoolExecutor.submit(self._startCoreThread, thread_name)
            futures.append(future)
        for future in futures:
            future.result()
        self._LoadBalancer.start()
        self._ProcessTaskScheduler.start()
        self._ThreadTaskScheduler.start()
        self._CallbackExecutor.startExecutor()

    def _startCoreProcess(self, process_name):
        """
        启动一个核心进程，并将其添加到核心进程池中。

        参数：
            :param process_name: 进程名称

        返回：
            :return - process_object: 启动的核心进程对象

        执行过程：
            1. 创建一个 `_ProcessObject` 实例，指定其名称为 `process_name`，类型为 "Core"。
            2. 启动核心进程对象。
            3. 将核心进程对象添加到 `_CoreProcessPool` 中，使用 `process_name` 作为键。
            4. 返回核心进程对象。

        异常：
            无
        """

        global _CoreProcessPool
        process_object = _ProcessObject(process_name, "Core", self._SynchronizationManager, self._ConfigManager, self._DebugMode)
        process_object.start()
        _CoreProcessPool[process_name] = process_object
        return process_object

    def _startCoreThread(self, thread_name):
        """
        启动一个核心线程，并将其添加到核心线程池中。

        参数：
            :param thread_name: 线程名称

        返回：
            :return - thread_object: 启动的核心线程对象

        执行过程：
            1. 创建一个 `_ThreadObject` 实例，指定其名称为 `thread_name`，类型为 "Core"。
            2. 启动核心线程对象。
            3. 将核心线程对象添加到 `_CoreThreadPool` 中，使用 `thread_name` 作为键。
            4. 返回核心线程对象。

        异常：
            无
        """

        global _CoreThreadPool
        thread_object = _ThreadObject(thread_name, "Core", self._SynchronizationManager, self._ConfigManager, self._Logger)
        thread_object.start()
        _CoreThreadPool[thread_name] = thread_object
        return thread_object


# ConnectConcurrentSystem 必须置于 `if __name__ == "__main__"` 中执行
def ConnectConcurrentSystem(config: ConcurrentSystemConfig = None, debug_mode: bool = False):
    """
    初始化并启动并发系统。

    参数：
        :param config: `ConcurrentSystemConfig` 对象，包含系统的配置参数。如果未提供，则使用默认配置。
        :param debug_mode: 布尔值，指示是否启用调试模式。默认为 `False`。

    返回：
        无

    执行过程：
        1. 如果未提供 `config` 参数，则创建一个默认的 `ConcurrentSystemConfig` 对象。
        2. 使用 `multiprocessing.Manager()` 创建一个共享对象管理器。
        3. 创建一个 `_SynchronizationManager` 实例，使用共享对象管理器进行初始化。
        4. 创建一个 `_ConfigManager` 实例，使用共享对象管理器和配置对象进行初始化。
        5. 创建一个 `ConcurrentSystem` 实例，传入同步管理器、配置管理器和调试模式参数。
        6. 进入循环，直到核心进程池中的进程数量达到配置中指定的核心进程数量。

    异常：
        无
    """

    _config = config if config is not None else ConcurrentSystemConfig()
    _shared_object_manager = multiprocessing.Manager()
    _synchronization_manager = _SynchronizationManager(_shared_object_manager)
    _config_manager = _ConfigManager(_shared_object_manager, _config)
    _concurrent_system = ConcurrentSystem(_synchronization_manager, _config_manager, debug_mode)
    while True:
        if len(_synchronization_manager.CoreProcessStatusPool) >= _config_manager.CoreProcessCount.value:
            break
