# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "Priority",
    "ExpandPolicy",
    "ShrinkagePolicy",
    "TaskFuture",
    "serviceProcessID",
    "submitAsyncTask",
    "submitProcessTask",
    "submitThreadTask",
    "submitSystemProcessTask",
    "submitSystemThreadTask",
    "closeConcurrentSystem"
]

import asyncio
import ctypes
import multiprocessing
import os
import pickle
import platform
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, CancelledError, ProcessPoolExecutor
from enum import Enum
from typing import TYPE_CHECKING, Union, Optional, Dict, Tuple, Any, Literal, List, TypedDict, Unpack, Callable, Coroutine

from .Logger import TheSeedCoreLogger, consoleLogger
from ._Common import _checkPackage, PerformanceMonitor, TextColor  # noqa

if TYPE_CHECKING:
    from concurrent.futures import Future


def _checkPyTorchSupport() -> Tuple[bool, List[int]]:
    """
    Checks for the availability of the PyTorch library and whether CUDA is supported.

    :return: A tuple containing:
        - A boolean indicating whether PyTorch and CUDA are supported (True) or not (False).
        - A list of available CUDA device IDs if CUDA is supported, or an empty list if not.
    setup:
        1. Check if the 'torch' package is installed using the _checkPackage function:
            1.1. If the package is available:
                1.1.1. Import the torch module.
                1.1.2. Check if CUDA is available using torch.cuda.is_available():
                    1.1.2.1. If CUDA is available, return True and a list of available CUDA device IDs.
                    1.1.2.2. If CUDA is not available, return False and an empty list.
        2. If the 'torch' package is not available, return False and an empty list.
    """

    if _checkPackage("torch"):
        # noinspection PyUnresolvedReferences
        import torch
        if torch.cuda.is_available():
            return True, [cuda_device_id for cuda_device_id in range(torch.cuda.device_count())]
        else:
            return False, []
    return False, []


_DefaultLogger = consoleLogger("Concurrent")
_SystemType = platform.system()
_PyTorchSupport, _AvailableCUDADevicesID = _checkPyTorchSupport()
_PySide6Support: bool = _checkPackage("PySide6")
_PyQt6Support: bool = _checkPackage("PyQt6")
_PyQt5Support: bool = _checkPackage("PyQt5")
if _PyTorchSupport:
    # noinspection PyUnresolvedReferences
    import torch
if multiprocessing.current_process().name == "MainProcess":
    _ResourceMonitor = PerformanceMonitor(_SystemType)
    _CoreProcessPool: Dict[str, _ProcessObject] = {}
    _ExpandProcessPool: Dict[str, _ProcessObject] = {}
    _ExpandProcessSurvivalTime: Dict[str, float] = {}
    _CoreThreadPool: Dict[str, _ThreadObject] = {}
    _ExpandThreadPool: Dict[str, _ThreadObject] = {}
    _ExpandThreadSurvivalTime: Dict[str, float] = {}
    _CallbackObject: Dict[str, callable] = {}
    _FutureResult: Dict[str, Any] = {}
    _ProcessTaskSchedulingEvent: threading.Event = threading.Event()
    _ThreadTaskSchedulingEvent: threading.Event = threading.Event()
    _ProcessBalanceEvent: threading.Event = threading.Event()
    _ThreadBalanceEvent: threading.Event = threading.Event()


class Priority(str, Enum):
    IDLE: str = "IDLE"
    BELOW_NORMAL: str = "BELOW_NORMAL"
    NORMAL: str = "NORMAL"
    ABOVE_NORMAL: str = "ABOVE_NORMAL"
    HIGH: str = "HIGH"
    REALTIME: str = "REALTIME"


class ExpandPolicy(str, Enum):
    NoExpand: str = "NoExpand"
    AutoExpand: str = "AutoExpand"
    BeforehandExpand: str = "BeforehandExpand"


class ShrinkagePolicy(str, Enum):
    NoShrink: str = "NoShrink"
    AutoShrink: str = "AutoShrink"
    TimeoutShrink: str = "TimeoutShrink"


class TaskFuture:
    def __init__(self):
        self._TaskID: Optional[str] = None

    @property
    def taskID(self):
        return self._TaskID

    @taskID.setter
    def taskID(self, id: str):
        self._TaskID = id

    def result(self, timeout: Optional[int] = None):
        """
        Waits for the result of a task identified by its TaskID, with an optional timeout.

        :param timeout: An optional integer specifying the maximum time to wait for the result (in seconds).
        :return: The result of the task once it is available.
        :raise TimeoutError: If the specified timeout is reached without the task result being available.
        setup:
            1. Record the start time to track the elapsed time.
            2. Enter an infinite loop to check for the task result:
                2.1. If the task ID is found in the _FutureResult dictionary:
                    2.1.1. Retrieve the task result and remove it from the dictionary.
                    2.1.2. Return the retrieved task result.
                2.2. If no timeout is specified, continue to the next iteration.
                2.3. Sleep briefly to yield control and avoid busy waiting.
                2.4. Check if the elapsed time exceeds the specified timeout:
                    2.4.1. If it does, raise a TimeoutError indicating that the task execution timed out.
        """

        global _FutureResult
        _start_time = time.time()
        while True:
            if self._TaskID in _FutureResult:
                task_result: Any = _FutureResult[self._TaskID]
                del _FutureResult[self._TaskID]
                return task_result
            if timeout is None:
                continue
            time.sleep(0.001)
            if time.time() - _start_time >= timeout:
                raise TimeoutError("Task execution timed out.")

    def execute(self):
        raise NotImplementedError("The execute method must be implemented in a subclass.")

    async def asyncExecute(self):
        raise NotImplementedError("The asyncExecute method must be implemented in a subclass.")


class _StatusManager:
    """
    Manages the status of processes and threads, including task and load information.

    The class is responsible for tracking and managing the status of processes and threads within a system, specifically focusing on task and load information.
    It maintains separate pools for core and expandable resources, enabling efficient monitoring and management of system load, task distribution, and resource usage.

    InstanceAttribute:
        SharedObjectManagerID: The process ID of the shared object manager.
        CoreProcessTaskStatusPool: A dictionary storing the task status of core processes.
        ExpandProcessTaskStatusPool: A dictionary storing the task status of expand processes.
        CoreProcessLoadStatusPool: A dictionary storing the load status of core processes.
        ExpandProcessLoadStatusPool: A dictionary storing the load status of expand processes.
        CoreThreadTaskStatusPool: A dictionary storing the task status of core threads.
        ExpandThreadTaskStatusPool: A dictionary storing the task status of expand threads.
        ResultStorageQueue: A queue for storing results from tasks.
        TaskLock: A lock for synchronizing task updates.
        _ProcessTaskLock: A lock for synchronizing process task updates.
        _ProcessLoadLock: A lock for synchronizing process load updates.
        _ThreadLock: A lock for synchronizing thread updates.
    Method:
        getCoreProcessTaskStatus: Retrieves the task status for a specified core process.
        getExpandProcessTaskStatus: Retrieves the task status for a specified expand process.
        getCoreProcessLoadStatus: Retrieves the load status for a specified core process.
        getExpandProcessLoadStatus: Retrieves the load status for a specified expand process.
        getCoreThreadTaskStatus: Retrieves the task status for a specified core thread.
        getExpandThreadTaskStatus: Retrieves the task status for a specified expand thread.
        updateCoreProcessTaskStatus: Updates the task status for a specified core process.
        updateExpandProcessTaskStatus: Updates the task status for a specified expand process.
        updateCoreProcessLoadStatus: Updates the load status for a specified core process.
        updateExpandProcessLoadStatus: Updates the load status for a specified expand process.
        updateCoreThreadTaskStatus: Updates the task status for a specified core thread.
        updateExpandThreadTaskStatus: Updates the task status for a specified expand thread.
    """

    def __init__(self, SharedObjectManager: multiprocessing.Manager):
        # noinspection PyProtectedMember
        self.SharedObjectManagerID = SharedObjectManager._process.pid
        self.CoreProcessTaskStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ExpandProcessTaskStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.CoreProcessLoadStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ExpandProcessLoadStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.CoreThreadTaskStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ExpandThreadTaskStatusPool: Dict[str, Tuple[int, int]] = SharedObjectManager.dict()
        self.ResultStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.TaskLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ProcessTaskLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ProcessLoadLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ThreadLock: multiprocessing.Lock = multiprocessing.Lock()

    def getCoreProcessTaskStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the task status for a specific core process while ensuring thread safety.

        :param name: A string representing the name of the core process.
        :return: A tuple containing the process ID and current task count for the core process.
        setup:
            1. Acquire the process task lock to ensure safe access to shared resources.
            2. Access the CoreProcessTaskStatusPool dictionary using the process name to get its status.
            3. Release the process task lock after retrieving the status.
            4. Return the retrieved status as a tuple.
        """

        self._ProcessTaskLock.acquire()
        status = self.CoreProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getExpandProcessTaskStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the task status for a specific expand process while ensuring thread safety.

        :param name: A string representing the name of the expand process.
        :return: A tuple containing the process ID and current task count for the expand process.
        setup:
            1. Acquire the process task lock to ensure safe access to shared resources.
            2. Access the ExpandProcessTaskStatusPool dictionary using the process name to get its status.
            3. Release the process task lock after retrieving the status.
            4. Return the retrieved status as a tuple.
        """

        self._ProcessTaskLock.acquire()
        status = self.ExpandProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getCoreProcessLoadStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the load status for a specific core process while ensuring thread safety.

        :param name: A string representing the name of the core process.
        :return: A tuple containing the process ID and current load for the core process.
        setup:
            1. Acquire the process load lock to ensure safe access to shared resources.
            2. Access the CoreProcessLoadStatusPool dictionary using the process name to get its status.
            3. Release the process load lock after retrieving the status.
            4. Return the retrieved status as a tuple.
        """

        self._ProcessLoadLock.acquire()
        status = self.CoreProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getExpandProcessLoadStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the load status for a specific expand process while ensuring thread safety.

        :param name: A string representing the name of the expand process.
        :return: A tuple containing the process ID and current load for the expand process.
        setup:
            1. Acquire the process load lock to ensure safe access to shared resources.
            2. Access the ExpandProcessLoadStatusPool dictionary using the process name to get its status.
            3. Release the process load lock after retrieving the status.
            4. Return the retrieved status as a tuple.
        """

        self._ProcessLoadLock.acquire()
        status = self.ExpandProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getCoreThreadTaskStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the task status for a specific core thread.

        :param name: A string representing the name of the core thread.
        :return: A tuple containing the thread ID and current task count for the core thread.
        setup:
            1. Access the CoreThreadTaskStatusPool dictionary using the thread name to get its status.
            2. Return the retrieved status as a tuple.
        """

        status = self.CoreThreadTaskStatusPool[name]
        return status

    def getExpandThreadTaskStatus(self, name: str) -> Tuple[int, int]:
        """
        Retrieves the task status for a specific expand thread.

        :param name: A string representing the name of the expand thread.
        :return: A tuple containing the thread ID and current task count for the expand thread.
        setup:
            1. Access the ExpandThreadTaskStatusPool dictionary using the thread name to get its status.
            2. Return the retrieved status as a tuple.
        """

        status = self.ExpandThreadTaskStatusPool[name]
        return status

    def updateCoreProcessTaskStatus(self, name: str, pid: int, task_count: int) -> None:
        """
        Updates the task status for a specific core process in the task status pool.

        :param name: A string representing the name of the core process.
        :param pid: An integer representing the process ID associated with the core process.
        :param task_count: An integer representing the current task count for the core process.
        :return: None
        setup:
            1. Update the CoreProcessTaskStatusPool dictionary with the process name as the key,
               associating it with a tuple containing the process ID and task count.
        """

        self.CoreProcessTaskStatusPool[name] = (pid, task_count)

    def updateExpandProcessTaskStatus(self, name: str, pid: int, task_count: int) -> None:
        """
        Updates the task status for a specific expand process in the task status pool.

        :param name: A string representing the name of the expand process.
        :param pid: An integer representing the process ID associated with the expand process.
        :param task_count: An integer representing the current task count for the expand process.
        :return: None
        setup:
            1. Update the ExpandProcessTaskStatusPool dictionary with the process name as the key,
               associating it with a tuple containing the process ID and task count.
        """

        self.ExpandProcessTaskStatusPool[name] = (pid, task_count)

    def updateCoreProcessLoadStatus(self, name: str, pid: int, load: int) -> None:
        """
        Updates the load status for a specific core process in the load status pool.

        :param name: A string representing the name of the core process.
        :param pid: An integer representing the process ID associated with the core process.
        :param load: An integer representing the current load for the core process.
        :return: None
        setup:
            1. Update the CoreProcessLoadStatusPool dictionary with the process name as the key,
               associating it with a tuple containing the process ID and load.
        """

        self.CoreProcessLoadStatusPool[name] = (pid, load)

    def updateExpandProcessLoadStatus(self, name: str, pid: int, load: int) -> None:
        """
        Updates the load status for a specific expand process in the load status pool.

        :param name: A string representing the name of the expand process.
        :param pid: An integer representing the process ID associated with the expand process.
        :param load: An integer representing the current load for the expand process.
        :return: None
        setup:
            1. Update the ExpandProcessLoadStatusPool dictionary with the process name as the key,
               associating it with a tuple containing the process ID and load.
        """

        self.ExpandProcessLoadStatusPool[name] = (pid, load)

    def updateCoreThreadTaskStatus(self, name: str, tid: int, task_count: int) -> None:
        """
        Updates the task status for a specific core thread in the task status pool.

        :param name: A string representing the name of the core thread.
        :param tid: An integer representing the thread ID associated with the core thread.
        :param task_count: An integer representing the current task count for the core thread.
        :return: None
        setup:
            1. Update the CoreThreadTaskStatusPool dictionary with the thread name as the key,
               associating it with a tuple containing the thread ID and task count.
        """

        self.CoreThreadTaskStatusPool[name] = (tid, task_count)

    def updateExpandThreadTaskStatus(self, name: str, tid: int, task_count: int) -> None:
        """
        Updates the task status for a specific expand thread in the task status pool.

        :param name: A string representing the name of the expand thread.
        :param tid: An integer representing the thread ID associated with the expand thread.
        :param task_count: An integer representing the current task count for the expand thread.
        :return: None
        setup:
            1. Update the ExpandThreadTaskStatusPool dictionary with the thread name as the key,
               associating it with a tuple containing the thread ID and task count.
        """

        self.ExpandThreadTaskStatusPool[name] = (tid, task_count)


class _Config(TypedDict, total=False):
    """
    Defines the configuration settings for the system as a TypedDict.

    InstanceAttribute:
        MainPriority: The main priority level for the processes.
        CoreProcessCount: The number of core processes to be used.
        CoreThreadCount: The number of core threads to be used.
        MaximumProcessCount: The maximum number of processes allowed.
        MaximumThreadCount: The maximum number of threads allowed.
        IdleCleanupThreshold: The threshold for cleaning up idle resources.
        TaskThreshold: The threshold for task management.
        GlobalTaskThreshold: The overall task threshold for the system.
        ProcessPriority: The priority setting for processes.
        ExpandPolicy: The policy governing process expansion.
        ShrinkagePolicy: The policy governing process shrinkage.
        ShrinkagePolicyTimeout: The timeout for the shrinkage policy.
        PerformanceReport: Flag indicating whether to generate performance reports.
    """

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


class _TaskConfig(TypedDict, total=False):
    """
    Defines the configuration settings for a task as a TypedDict.

    InstanceAttribute:
        lock: Indicates if the task should be executed with a lock.
        lock_timeout: The timeout duration for acquiring the lock.
        timeout: The maximum time allowed for the task to execute.
        gpu_boost: Indicates if GPU acceleration is enabled for the task.
        gpu_id: The ID of the GPU to be used for acceleration.
        retry: Indicates if the task should be retried on failure.
        max_retries: The maximum number of retries allowed for the task.
    """

    lock: bool
    lock_timeout: int
    timeout: Optional[int]
    gpu_boost: bool
    gpu_id: int
    retry: bool
    max_retries: int


class _ConfigManager:
    """
    Manages the configuration settings for the system, including process and thread management.

    The class manages configuration settings for system resources and task management.
    It is responsible for validating and applying settings for process and thread management, resource thresholds, and performance monitoring.
    By centralizing configuration, the ConfigManager allows other system components to access consistent settings,
    optimizing resource allocation and ensuring reliable task execution.

    InstanceAttribute:
        Logger: Logger instance for recording events and warnings.
        PhysicalCores: The number of physical CPU cores available.
        Priority: The main priority level for the processes.
        CoreProcessCount: The number of core processes to be used.
        CoreThreadCount: The number of core threads to be used.
        MaximumProcessCount: The maximum number of processes allowed.
        MaximumThreadCount: The maximum number of threads allowed.
        IdleCleanupThreshold: The threshold for cleaning up idle resources.
        TaskThreshold: The threshold for task management.
        GlobalTaskThreshold: The overall task threshold for the system.
        ProcessPriority: The priority setting for processes.
        ExpandPolicy: The policy governing process expansion.
        ShrinkagePolicy: The policy governing process shrinkage.
        ShrinkagePolicyTimeout: The timeout for the shrinkage policy.
        PerformanceReport: Flag indicating whether to generate performance reports.
    Method:
        _validatePriority: Validates and returns the main priority level.
        _validateCoreProcessCount: Validates the count of core processes.
        _validateCoreThreadCount: Validates the count of core threads.
        _validateMaximumProcessCount: Validates the maximum process count.
        _validateMaximumThreadCount: Validates the maximum thread count.
        _validateIdleCleanupThreshold: Validates the idle cleanup threshold.
        _validateTaskThreshold: Validates the task threshold.
        _validateGlobalTaskThreshold: Validates the global task threshold.
        _validateProcessPriority: Validates the process priority setting.
        _validateExpandPolicy: Validates the expand policy setting.
        _validateShrinkagePolicy: Validates the shrinkage policy setting.
        _validateShrinkagePolicyTimeout: Validates the shrinkage policy timeout.
        _calculateTaskThreshold: Calculates an appropriate task threshold based on system resources.
    """

    def __init__(self, SharedObjectManager: multiprocessing.Manager, **config: Unpack[_Config]):
        self.Logger = _DefaultLogger
        self.PhysicalCores: int = _ResourceMonitor.physicalCpuCores()
        self.Priority = SharedObjectManager.Value("c", self._validatePriority(config.get("MainPriority", Priority.NORMAL)))
        self.CoreProcessCount = SharedObjectManager.Value("i", self._validateCoreProcessCount(config.get("CoreProcessCount", None)))
        self.CoreThreadCount = SharedObjectManager.Value("i", self._validateCoreThreadCount(config.get("CoreThreadCount", None)))
        self.MaximumProcessCount = SharedObjectManager.Value("i", self._validateMaximumProcessCount(config.get("MaximumProcessCount", None)))
        self.MaximumThreadCount = SharedObjectManager.Value("i", self._validateMaximumThreadCount(config.get("MaximumThreadCount", None)))
        self.IdleCleanupThreshold = SharedObjectManager.Value("i", self._validateIdleCleanupThreshold(config.get("IdleCleanupThreshold", None)))
        self.TaskThreshold = SharedObjectManager.Value("i", self._validateTaskThreshold(config.get("TaskThreshold", None)))
        self.GlobalTaskThreshold = SharedObjectManager.Value("i", self._validateGlobalTaskThreshold(config.get("GlobalTaskThreshold", None)))
        self.ProcessPriority = SharedObjectManager.Value("c", self._validateProcessPriority(config.get("ProcessPriority", Priority.NORMAL)))
        self.ExpandPolicy = SharedObjectManager.Value("c", self._validateExpandPolicy(config.get("ExpandPolicy", ExpandPolicy.NoExpand)))
        self.ShrinkagePolicy = SharedObjectManager.Value("c", self._validateShrinkagePolicy(config.get("ShrinkagePolicy", ShrinkagePolicy.NoShrink)))
        self.ShrinkagePolicyTimeout = SharedObjectManager.Value("i", self._validateShrinkagePolicyTimeout(config.get("ShrinkagePolicyTimeout", None)))
        self.PerformanceReport = SharedObjectManager.Value("b", config.get("PerformanceReport", False))

    def _validatePriority(self, priority: Priority) -> str:
        """
        Validates the priority level, ensuring it is one of the accepted options.

        :param priority: A string representing the desired priority level (e.g., "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME").
        :return: A string representing the validated priority level.
        setup:
            1. Check if the provided priority is valid:
                1.1. If it is not one of the accepted values, log a warning and return the default priority "NORMAL".
            2. If the priority is valid, return it as is.
        """

        if priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            self.Logger.warning(f"Invalid priority level '{priority}'. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        return priority

    def _validateCoreProcessCount(self, core_process_count: Optional[int]) -> int:
        """
        Validates the core process count value, ensuring it is set and within the acceptable range.

        :param core_process_count: An optional integer representing the desired core process count.
        :return: An integer representing the validated core process count.
        setup:
            1. Calculate a default core process count as half the number of physical cores.
            2. If the calculated default value is less than or equal to zero, set it to 1.
            3. Check if the provided process count is None:
                3.1. If it is None, log a warning and return the default value.
            4. Check if the provided process count is an integer:
                4.1. If it is not an integer, log a warning about the invalid type and return the default value.
            5. Check if the process count is within the acceptable range:
                5.1. If the core process count is less than 0 or greater than the number of physical cores, log a warning and return the default value.
            6. If the core process count is set to 0, log a warning that the process pool will be unavailable.
            7. If the process count is valid and within range, return it as is.
        """

        default_value = self.PhysicalCores // 2
        if default_value <= 0:
            default_value = 1
        if core_process_count is None:
            self.Logger.warning(f"Core process count not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(core_process_count, int):
            self.Logger.warning(f"Invalid type for core process count '{core_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        if core_process_count < 0 or core_process_count > self.PhysicalCores:
            self.Logger.warning(f"Core process count exceeds the range of 0 - {self.PhysicalCores}. Default value [{default_value}] has been used.")
            return default_value

        if core_process_count == 0:
            self.Logger.warning(f"Core process count set to 0, process pool will be unavailable")

        return core_process_count

    def _validateCoreThreadCount(self, core_thread_count: Optional[int]) -> int:
        """
        Validates the core thread count value, ensuring it is set and within the acceptable range.

        :param core_thread_count: An optional integer representing the desired core thread count.
        :return: An integer representing the validated core thread count.
        setup:
            1. Calculate a default core thread count as half the number of physical cores.
            2. If the calculated default value is less than or equal to zero, set it to 1.
            3. Check if the provided thread count is None:
                3.1. If it is None, log a warning and return the default value.
            4. Check if the provided thread count is an integer:
                4.1. If it is not an integer, log a warning about the invalid type and return the default value.
            5. Check if the thread count is within the acceptable range:
                5.1. If the core thread count is less than or equal to 0 or greater than four times the number of physical cores, log a warning and return the default value.
            6. If the thread count is valid and within range, return it as is.
        """

        default_value: int = self.PhysicalCores // 2
        if default_value <= 0:
            default_value: int = 1
        if core_thread_count is None:
            self.Logger.warning(f"Core thread count not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(core_thread_count, int):
            self.Logger.warning(f"Invalid type for core thread count '{core_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        if core_thread_count <= 0 or core_thread_count > self.PhysicalCores * 4:
            self.Logger.warning(f"Core thread count exceeds the range of 1 - {self.PhysicalCores * 4}. Default value [{default_value}] has been used.")
            return default_value

        return core_thread_count

    def _validateMaximumProcessCount(self, maximum_process_count: Optional[int]) -> int:
        """
        Validates the maximum process count value, ensuring it is set and within the acceptable range.

        :param maximum_process_count: An optional integer representing the desired maximum process count.
        :return: An integer representing the validated maximum process count.
        setup:
            1. Calculate a default maximum process count based on the number of physical cores.
            2. Check if the core process count is zero:
                2.1. If it is zero, return 0 immediately.
            3. Check if the provided process count is None:
                3.1. If it is None, log a warning and return the default value.
            4. Check if the provided process count is an integer:
                4.1. If it is not an integer, log a warning about the invalid type and return the default value.
            5. Check if the process count is within the acceptable range:
                5.1. If the maximum process count is less than the core process count or greater than the number of physical cores, log a warning and return the default value.
            6. If the process count is valid and within range, return it as is.
        """

        default_value: int = self.PhysicalCores
        if self.CoreProcessCount.value == 0:
            return 0
        if maximum_process_count is None:
            self.Logger.warning(f"Maximum process count not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(maximum_process_count, int):
            self.Logger.warning(f"Invalid type for maximum process count '{maximum_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        if maximum_process_count < self.CoreProcessCount.value or maximum_process_count > self.PhysicalCores:
            self.Logger.warning(f"Maximum process count exceeds the range of {self.CoreProcessCount.value} - {self.PhysicalCores}. Default value [{default_value}] has been used.")
            return default_value

        return maximum_process_count

    def _validateMaximumThreadCount(self, maximum_thread_count: Optional[int]) -> int:
        """
        Validates the maximum thread count value, ensuring it is set and within the acceptable range.

        :param maximum_thread_count: An optional integer representing the desired maximum thread count.
        :return: An integer representing the validated maximum thread count.
        setup:
            1. Calculate a default maximum thread count based on the number of physical cores.
            2. Check if the provided thread count is None:
                2.1. If it is None, log a warning and return the default value.
            3. Check if the provided thread count is an integer:
                3.1. If it is not an integer, log a warning about the invalid type and return the default value.
            4. Check if the thread count is within the acceptable range:
                4.1. If the maximum thread count is less than the core thread count or greater than four times the number of physical cores, log a warning and return the default value.
            5. If the thread count is valid and within range, return it as is.
        """

        default_value: int = self.PhysicalCores * 4
        if maximum_thread_count is None:
            self.Logger.warning(f"Maximum thread count not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(maximum_thread_count, int):
            self.Logger.warning(f"Invalid type for maximum thread count '{maximum_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        if maximum_thread_count < self.CoreThreadCount.value or maximum_thread_count > self.PhysicalCores * 4:
            self.Logger.warning(f"Maximum thread count exceeds the range of {self.CoreThreadCount.value} - {self.PhysicalCores * 4}. Default value [{default_value}] has been used.")
            return default_value

        return maximum_thread_count

    def _validateIdleCleanupThreshold(self, idle_cleanup_threshold: Optional[int]) -> int:
        """
        Validates the idle cleanup threshold value, ensuring it is set and of the correct type.

        :param idle_cleanup_threshold: An optional integer representing the desired idle cleanup threshold.
        :return: An integer representing the validated idle cleanup threshold.
        setup:
            1. Define a default idle cleanup threshold value.
            2. Check if the provided threshold value is None:
                2.1. If it is None, log a warning and return the default value.
            3. Check if the provided threshold value is an integer:
                3.1. If it is not an integer, log a warning about the invalid type and return the default value.
            4. If the threshold value is valid, return it as is.
        """

        default_value: int = 60
        if idle_cleanup_threshold is None:
            self.Logger.warning(f"Idle cleanup threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(idle_cleanup_threshold, int):
            self.Logger.warning(f"Invalid type for idle cleanup threshold '{idle_cleanup_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return idle_cleanup_threshold

    def _validateTaskThreshold(self, task_threshold: Optional[int]) -> int:
        """
        Validates the task threshold value, ensuring it is set and of the correct type.

        :param task_threshold: An optional integer representing the desired task threshold.
        :return: An integer representing the validated task threshold.
        setup:
            1. Calculate a default threshold value using the _calculateTaskThreshold method.
            2. Check if the provided threshold value is None:
                2.1. If it is None, log a warning and return the default value.
            3. Check if the provided threshold value is an integer:
                3.1. If it is not an integer, log a warning about the invalid type and return the default value.
            4. If the threshold value is valid, return it as is.
        """

        default_value: int = self._calculateTaskThreshold()
        if task_threshold is None:
            self.Logger.warning(f"Task threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(task_threshold, int):
            self.Logger.warning(f"Invalid type for task threshold '{task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return task_threshold

    def _validateGlobalTaskThreshold(self, global_task_threshold: Optional[int]) -> int:
        """
        Validates the global task threshold value, ensuring it is set and of the correct type.

        :param global_task_threshold: An optional integer representing the desired global task threshold.
        :return: An integer representing the validated global task threshold.
        setup:
            1. Calculate a default threshold value based on the number of core processes, core threads, and the configured task threshold.
            2. Check if the provided threshold value is None:
                2.1. If it is None, log a warning and return the default value.
            3. Check if the provided threshold value is an integer:
                3.1. If it is not an integer, log a warning about the invalid type and return the default value.
            4. If the threshold value is valid, return it as is.
        """

        default_value: int = (self.CoreProcessCount.value + self.CoreThreadCount.value) * self.TaskThreshold.value
        if global_task_threshold is None:
            self.Logger.warning(f"Global task threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(global_task_threshold, int):
            self.Logger.warning(f"Invalid type for global task threshold '{global_task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return global_task_threshold

    def _validateProcessPriority(self, process_priority: Priority.NORMAL) -> str:
        """
        Validates the process priority value, ensuring it is one of the accepted options.

        :param process_priority: A string representing the desired process priority (e.g., "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME").
        :return: A string representing the validated process priority.
        setup:
            1. Check if the provided process priority is valid:
                1.1. If it is not one of the accepted values (None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"), log a warning and return the default priority "NORMAL".
            2. Check if the provided process priority is None:
                2.1. If it is None, log a warning and return the default priority "NORMAL".
            3. Check if the core process count equals the number of physical cores and if the priority is "HIGH" or "REALTIME":
                3.1. If both conditions are met, log a warning and return the default priority "NORMAL".
            4. If the process priority is valid, return it as is.
        """

        if process_priority not in [None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            self.Logger.warning(f"Invalid process priority '{process_priority}'. Default value ['NORMAL'] has been used.")
            return "NORMAL"

        if process_priority is None:
            self.Logger.warning("Process priority not set. Default value ['NORMAL'] has been used.")
            return "NORMAL"

        if self.CoreProcessCount.value == self.PhysicalCores and process_priority in ["HIGH", "REALTIME"]:
            self.Logger.warning(f"Process priority {process_priority} is not recommended for all physical cores. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        return process_priority

    def _validateExpandPolicy(self, expand_policy: ExpandPolicy) -> str:
        """
        Validates the expand policy value, ensuring it is one of the accepted options.

        :param expand_policy: An ExpandPolicy representing the desired policy.
        :return: A string representing the validated expand policy.
        setup:
            1. Check if the provided expand policy is valid:
                1.1. If it is not one of the accepted values (None, "NoExpand", "AutoExpand", "BeforehandExpand"), log a warning and return the default policy "NoExpand".
            2. Check if the provided expand policy is None:
                2.1. If it is None, log a warning and return the default policy "NoExpand".
            3. If the expand policy is valid, return it as is.
        """

        if expand_policy not in [None, "NoExpand", "AutoExpand", "BeforehandExpand"]:
            self.Logger.warning(f"Invalid expand policy '{expand_policy}'. Default value ['NoExpand'] has been used.")
            return "NoExpand"

        if expand_policy is None:
            self.Logger.warning("Expand policy not set. Default value ['NoExpand'] has been used.")
            return "NoExpand"

        return expand_policy

    def _validateShrinkagePolicy(self, shrinkage_policy: ShrinkagePolicy) -> str:
        """
        Validates the shrinkage policy value, ensuring it is one of the accepted options.

        :param shrinkage_policy: A ShrinkagePolicy representing the desired policy.
        :return: A string representing the validated shrinkage policy.
        setup:
            1. Check if the provided shrinkage policy is valid:
                1.1. If it is not one of the accepted values (None, "NoShrink", "AutoShrink", "TimeoutShrink"), log a warning and return the default policy "NoShrink".
            2. Check if the provided shrinkage policy is None:
                2.1. If it is None, log a warning and return the default policy "NoShrink".
            3. If the shrinkage policy is valid, return it as is.
        """

        if shrinkage_policy not in [None, "NoShrink", "AutoShrink", "TimeoutShrink"]:
            self.Logger.warning(f"Invalid shrinkage policy '{shrinkage_policy}'. Default value ['NoShrink'] has been used.")
            return "NoShrink"

        if shrinkage_policy is None:
            self.Logger.warning("Shrinkage policy not set. Default value ['NoShrink'] has been used.")
            return "NoShrink"

        return shrinkage_policy

    def _validateShrinkagePolicyTimeout(self, shrinkage_policy_timeout: Optional[int]) -> int:
        """
        Validates the shrinkage policy timeout value, ensuring it is set and of the correct type.

        :param shrinkage_policy_timeout: An optional integer representing the desired timeout value.
        :return: An integer representing the validated timeout value.
        setup:
            1. Define a default timeout value.
            2. Check if the provided timeout value is None:
                2.1. If it is None, log a warning and return the default value.
            3. Check if the provided timeout value is an integer:
                3.1. If it is not an integer, log a warning about the invalid type and return the default value.
            4. If the timeout value is valid, return it as is.
        """

        default_value: int = 5
        if shrinkage_policy_timeout is None:
            self.Logger.warning(f"Shrinkage policy timeout not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(shrinkage_policy_timeout, int):
            self.Logger.warning(f"Invalid type for shrinkage policy timeout '{shrinkage_policy_timeout}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return shrinkage_policy_timeout

    def _calculateTaskThreshold(self) -> int:
        """
        Calculates the task threshold based on the number of physical CPU cores and total memory.

        :return: An integer representing the calculated task threshold.
        setup:
            1. Retrieve the number of physical cores and total physical memory (in GB).
            2. Calculate a balanced score based on the ratio of physical cores to a maximum (128) and total memory to a maximum (3072 GB).
            3. Define a list of balanced score thresholds and corresponding task thresholds.
            4. Iterate through the score thresholds and task thresholds:
                4.1. If the balanced score is less than or equal to the current score threshold, return the corresponding task threshold.
            5. If no thresholds are met, return the highest task threshold.
        """

        physical_cores: int = self.PhysicalCores
        total_memory: int = _ResourceMonitor.totalPhysicalMemory() / (1024 ** 3)
        balanced_score: float = ((physical_cores / 128) + (total_memory / 3072)) / 2

        balanced_score_thresholds: List[float] = [0.2, 0.4, 0.6, 0.8]
        task_thresholds: List[int] = [10, 40, 70, 100, 130]
        for score_threshold, threshold in zip(balanced_score_thresholds, task_thresholds):
            if balanced_score <= score_threshold:
                return threshold
        return task_thresholds[-1]


class _CallbackExecutor:
    """
    Manages the execution of callback functions in response to completed tasks.

    The class manages the execution of callback functions triggered upon the completion of tasks.
    It operates within an asynchronous event loop, allowing both synchronous and asynchronous callbacks to be handled efficiently.
    This class ensures that task results are processed and any associated callbacks are executed in response,
    allowing for dynamic, real-time reactions to task completion.

    InstanceAttribute:
        StatusManager: Manages the status and results of tasks.
        CloseEvent: Event to signal the executor to stop running.
        MainEventLoop: The main asyncio event loop for handling asynchronous operations.
    Method:
        startExecutor: Starts the executor by creating a task in the main event loop.
        closeExecutor: Signals the executor to stop processing callbacks.
        run: The main loop that retrieves results from the StatusManager and executes callbacks.
        callbackExecutor: Executes the provided callback with the task result, handling both synchronous and asynchronous callbacks.
    """

    def __init__(self, sm: _StatusManager, main_event_loop: asyncio.AbstractEventLoop):
        self.StatusManager: _StatusManager = sm
        self.CloseEvent: threading.Event = threading.Event()
        self.MainEventLoop: asyncio.AbstractEventLoop = main_event_loop

    def startExecutor(self) -> None:
        """
        Starts the executor by scheduling the run method as a task in the main event loop.

        :return: None
        setup:
            1. Create a new task in the MainEventLoop to execute the run method, which will handle processing results and executing callbacks.
        """

        self.MainEventLoop.create_task(self.run())

    def closeExecutor(self) -> None:
        """
        Signals the executor to close by setting the CloseEvent.

        :return: None
        setup:
            1. Set the CloseEvent to indicate that the executor should stop processing.
        """

        self.CloseEvent.set()

    async def run(self) -> None:
        """
        Processes results from the ResultStorageQueue and executes associated callback functions.

        :return: None
        setup:
            1. Enter a loop that continues until the CloseEvent is triggered:
                1.1. Attempt to retrieve callback data from the ResultStorageQueue:
                    1.1.1. If data is retrieved, unpack it into task_result and task_id.
                    1.1.2. Store the task result in the _FutureResult dictionary using task_id as the key.
                    1.1.3. Check if the task_id exists in the _CallbackObject dictionary:
                        1.1.3.1. If it exists, retrieve the associated callback function.
                        1.1.3.2. Create a new task in the main event loop to execute the callback with the task result.
                        1.1.3.3. Remove the callback from _CallbackObject.
                1.2. If the queue is empty, sleep briefly to yield control and avoid busy waiting.
        """

        global _CallbackObject, _FutureResult
        while not self.CloseEvent.is_set():
            try:
                callback_data: Tuple[Any, str] = self.StatusManager.ResultStorageQueue.get_nowait()
                task_result, task_id = callback_data
                _FutureResult[task_id] = task_result
                if task_id in _CallbackObject:
                    callback_object = _CallbackObject[task_id]
                    self.MainEventLoop.create_task(self.callbackExecutor((callback_object, task_result)))
                    del _CallbackObject[task_id]
            except queue.Empty:
                await asyncio.sleep(0.001)

    @staticmethod
    async def callbackExecutor(callback_data: Tuple[callable, Any]) -> None:
        """
        Executes a callback function with the provided task result, handling both coroutine and regular functions.

        :param callback_data: A tuple containing the callback function and the task result to be passed to it.
        :return: None
        setup:
            1. Extract the callback function and task result from the callback_data tuple.
            2. Check if the callback function is a coroutine:
                2.1. If it is a coroutine function, await its execution with the task result.
                2.2. If it is a regular function, call it directly with the task result.
        """

        callback_object, task_result = callback_data
        if asyncio.iscoroutinefunction(callback_object):
            await callback_object(task_result)
            return
        callback_object(task_result)


class _TaskObject:
    """
    Represents a task with associated parameters and execution settings.

    The class represents an individual task with parameters and execution settings, allowing it to be customized and controlled.
    It includes attributes for handling synchronization, retries, GPU acceleration,
    and serialization, enabling the task to be transferred across processes and run in either synchronous or asynchronous modes.

    InstanceAttribute:
        ConfigDefaultsValue: A dictionary of default configuration values for the task.
        Config: A dictionary of configuration values for the task, populated from kwargs.
        Task: The callable function or method that will be executed.
        TaskID: A unique identifier for the task.
        TaskType: The type of the task, either 'Sync' or 'Async'.
        IsCallback: Indicates if the task is a callback function.
        Lock: Indicates if the task should be executed with a lock.
        LockTimeout: The timeout for acquiring the lock.
        TimeOut: The timeout for executing the task.
        IsGpuBoost: Indicates if GPU acceleration is enabled for the task.
        GpuID: The ID of the GPU to use for acceleration.
        IsRetry: Indicates if the task should be retried on failure.
        MaxRetries: The maximum number of retries allowed for the task.
        RetriesCount: The current count of retries for the task.
        UnserializableInfo: A dictionary to store unserializable objects with their IDs.
        TaskArgs: The serialized arguments for the task.
        TaskKwargs: The serialized keyword arguments for the task.
        RecoveredArgs: The arguments to be used when the task is executed.
        RecoveredKwargs: The keyword arguments to be used when the task is executed.
    Method:
        reinitializedParams: Re-initializes the task parameters for execution.
        setupGpuParams: Sets up the parameters for GPU execution.
        paramsTransfer: Transfers parameters to the specified GPU device.
        cleanupGpuResources: Cleans up GPU resources after task execution.
        serialize: Serializes an object for safe transfer between processes.
        deserialize: Deserializes an object back to its original form.
        isSerializable: Checks if an object can be serialized using pickle.
    """

    def __init__(self, task: callable, task_id: str, callback: bool = False, *args, **kwargs):
        self.ConfigDefaultsValue = {
            "lock": False,
            "lock_timeout": 3,
            "timeout": None,
            "gpu_boost": False,
            "gpu_id": 0,
            "retry": False,
            "max_retries": 3,
        }
        self.Config = {key: kwargs.pop(key, default) for key, default in self.ConfigDefaultsValue.items()}

        self.Task: callable = task
        self.TaskID: str = task_id
        self.TaskType: Literal["Sync", "Async"] = "Async" if asyncio.iscoroutinefunction(self.Task) else "Sync"

        self.IsCallback: bool = callback
        self.Lock: bool = self.Config['lock']
        self.LockTimeout: int = self.Config['lock_timeout']
        self.TimeOut: Optional[int] = self.Config['timeout']
        self.IsGpuBoost: bool = self.Config['gpu_boost']
        self.GpuID: int = self.Config['gpu_id']
        self.IsRetry: bool = self.Config['retry']
        self.MaxRetries: int = self.Config['max_retries']

        self.RetriesCount: int = 0
        self.UnserializableInfo: Dict[int, Any] = {}

        self.TaskArgs = self.serialize(args)
        self.TaskKwargs = self.serialize(kwargs)
        self.RecoveredArgs = None
        self.RecoveredKwargs = None

    def reinitializedParams(self) -> None:
        """
        Reinitializes the parameters for the task by deserializing the arguments and setting up GPU parameters if applicable.

        :return: None
        setup:
            1. Deserialize the TaskArgs attribute to populate the RecoveredArgs attribute.
            2. Deserialize the TaskKwargs attribute to populate the RecoveredKwargs attribute.
            3. If the task is set to use GPU boosting and PyTorch support is available:
                3.1. Call setupGpuParams to transfer the parameters to the specified CUDA device.
        """

        self.RecoveredArgs = self.deserialize(self.TaskArgs)
        self.RecoveredKwargs = self.deserialize(self.TaskKwargs)
        if self.IsGpuBoost and _PyTorchSupport:
            self.setupGpuParams()

    def setupGpuParams(self) -> None:
        """
        Sets up GPU parameters by transferring arguments and keyword arguments to the specified CUDA device.

        :return: None
        setup:
            1. Check if the specified GpuID is available in the list of available CUDA device IDs:
                1.1. If not, reset GpuID to 0.
            2. Create a device object representing the specified GPU (e.g., "cuda:0").
            3. Transfer each argument in RecoveredArgs to the specified device using paramsTransfer.
            4. Transfer each value in RecoveredKwargs to the specified device using paramsTransfer.
        """

        if self.GpuID not in _AvailableCUDADevicesID:
            self.GpuID = 0
        device = torch.device(f"cuda:{self.GpuID}")
        self.RecoveredArgs = [self.paramsTransfer(arg, device) for arg in self.RecoveredArgs]
        self.RecoveredKwargs = {key: self.paramsTransfer(value, device) for key, value in self.RecoveredKwargs.items()}

    def paramsTransfer(self, obj, device) -> Any:
        """
        Transfers parameters to a specified device (CPU or GPU) for tensors, modules, or collections.

        :param obj: The object to be transferred, which may be a tensor, module, list, tuple, dictionary, or a simple data type.
        :param device: The target device to transfer the parameters to (e.g., "cuda" or "cpu").
        :return: The object transferred to the specified device, preserving the original structure.
        setup:
            1. Check if the object is a torch.Tensor or torch.nn.Module:
                1.1. If true, transfer it to the specified device using the .to(device) method.
            2. Check if the object is a list or tuple:
                2.1. If true, return a new list or tuple where each item is recursively transferred to the specified device.
            3. Check if the object is a dictionary:
                3.1. If true, return a new dictionary where each key-value pair is recursively transferred to the specified device.
            4. If the object is none of the above types, return it as is (assumed to be a simple data type).
        """

        if isinstance(obj, (torch.Tensor, torch.nn.Module)):
            return obj.to(device)
        if isinstance(obj, (list, tuple)):
            return type(obj)(self.paramsTransfer(x, device) for x in obj)
        if isinstance(obj, dict):
            return {k: self.paramsTransfer(v, device) for k, v in obj.items()}
        return obj

    @staticmethod
    def cleanupGpuResources() -> None:
        """
        Cleans up GPU resources by synchronizing and clearing the CUDA cache.

        :return: None
        setup:
            1. Call torch.cuda.synchronize() to wait for all kernels to complete.
            2. Call torch.cuda.empty_cache() to release unused memory from the GPU.
        """

        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    def serialize(self, obj) -> Any:
        """
        Recursively serializes an object, handling tuples and dictionaries appropriately.

        :param obj: The object to be serialized, which may be a tuple, dictionary, or a simple data type.
        :return: The serialized object, which may be modified to indicate unserializable objects.
        setup:
            1. Check if the object is a tuple:
                1.1. If true, return a new tuple where each item is serialized recursively.
            2. Check if the object is a dictionary:
                2.1. Return a new dictionary where each key-value pair is serialized recursively.
            3. Check if the object is serializable using the isSerializable method:
                3.1. If the object is not serializable, assign it a unique ID and store it in the UnserializableInfo dictionary.
                3.2. Return a dictionary indicating that the object is unserializable, along with its ID and type.
            4. If the object is serializable, return it as is.
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

    def deserialize(self, obj) -> Any:
        """
        Recursively deserializes an object, handling tuples and dictionaries appropriately.

        :param obj: The object to be deserialized, which may be a tuple, dictionary, or a simple data type.
        :return: The deserialized object.
        setup:
            1. Check if the object is a tuple:
                1.1. If true, return a new tuple where each item is deserialized recursively.
            2. Check if the object is a dictionary:
                2.1. If the dictionary contains a key "__unserializable__", retrieve and return the corresponding unserializable information.
                2.2. Otherwise, return a new dictionary where each key-value pair is deserialized recursively.
            3. If the object is neither a tuple nor a dictionary, return it as is (assumed to be a simple data type).
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
    def isSerializable(obj) -> bool:
        """
        Checks if an object is serializable using the pickle module.

        :param obj: The object to be checked for serializability.
        :return: A boolean indicating whether the object can be serialized (True) or not (False).
        setup:
            1. Attempt to serialize the object using pickle.dumps.
            2. If serialization is successful, return True.
            3. If a PicklingError, AttributeError, or TypeError occurs, return False.
        """

        try:
            pickle.dumps(obj)
            return True
        except (pickle.PicklingError, AttributeError, TypeError):
            return False


class _ProcessObject(multiprocessing.Process):
    """
    Represents a process that handles task execution for either core or expand operations.

    The class represents a multiprocess-based task handler designed for managing core and expandable processes.
    It efficiently executes tasks through an asynchronous event loop and synchronous executor, and it prioritizes, retries, and cleans up tasks.
    The process dynamically adjusts to system configurations, handling both asynchronous and synchronous tasks,
    and manages resources to prevent memory overuse.

    InstanceAttribute:
        ProcessName: The name of the process.
        ProcessType: The type of the process, either 'Core' or 'Expand'.
        StatusManager: Manages the status of tasks and processes.
        ConfigManager: Handles configuration settings for task execution.
        PendingTasks: A dictionary storing pending tasks for execution.
        SystemExecutor: ThreadPoolExecutor for executing synchronous tasks.
        HighPriorityQueue: Queue for high-priority tasks.
        MediumPriorityQueue: Queue for medium-priority tasks.
        LowPriorityQueue: Queue for low-priority tasks.
        WorkingEvent: Event to indicate the process is currently working.
        CloseEvent: Event to signal the process to stop running.
        EventLoop: The asyncio event loop for handling asynchronous tasks.
    Method:
        run: The main loop for processing tasks and managing resources.
        stop: Signals the process to stop and waits for its completion.
        addProcessTask: Adds a new task to the appropriate priority queue.
        _taskProcessor: Processes tasks from the queues and executes them.
        _executeAsyncTask: Executes asynchronous tasks, handling locking if necessary.
        _executeSyncTask: Executes synchronous tasks, handling locking if necessary.
        _executeLockedAsyncTask: Executes a locked asynchronous task with timeout handling.
        _executeUnLockedAsyncTask: Executes an unlocked asynchronous task without timeout.
        _executeTimeoutAsyncTask: Handles asynchronous tasks that have a timeout set.
        _executeNonTimeoutAsyncTask: Handles asynchronous tasks that do not have a timeout set.
        _executeLockedSyncTask: Executes a locked synchronous task with timeout handling.
        _executeUnLockedSyncTask: Executes an unlocked synchronous task without timeout.
        _executeTimeoutSyncTask: Handles synchronous tasks that have a timeout set.
        _executeNonTimeoutSyncTask: Handles synchronous tasks that do not have a timeout set.
        _updateTaskStatus: Updates the status of tasks being processed.
        _taskResultProcessor: Processes the result of a completed task.
        _requeueTask: Requeues a task for execution based on its priority.
        _cleanup: Cleans up remaining tasks and pending tasks.
        _setProcessPriority: Sets the priority of the process based on configuration.
        _setSystemExecutorThreadCount: Determines the number of threads for the executor based on physical cores.
        _cleanupProcessMemory: Cleans up memory used by the process.
        _getTaskData: Retrieves task data from the appropriate priority queue.
    """

    def __init__(self, process_name: str, process_type: Literal['Core', 'Expand'], sm: _StatusManager, cm: _ConfigManager):
        super().__init__(name=process_name, daemon=True)
        self.ProcessName: str = process_name
        self.ProcessType: Literal['Core', 'Expand'] = process_type
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.PendingTasks: Dict[str, asyncio.Task | Future] = {}
        self.SystemExecutor: Optional[ThreadPoolExecutor] = None
        self.HighPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.MediumPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.LowPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.WorkingEvent: multiprocessing.Event = multiprocessing.Event()
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self) -> None:
        """
        Runs the process, setting its priority and initializing the task execution environment.

        :return: None
        setup:
            1. Set the process priority using the _setProcessPriority method.
            2. Initialize the SystemExecutor as a ThreadPoolExecutor with a thread count determined by _setSystemExecutorThreadCount.
            3. Create a new asyncio event loop and set it as the current event loop.
            4. Attempt to run the task processor until completion:
                4.1. If any exception occurs during execution, log the error with the process name and PID.
            5. Ensure that the event loop is closed in the finally block to release resources.
            6. Log an informational message indicating that the process has been closed.
        """

        self._setProcessPriority()
        self.SystemExecutor: ThreadPoolExecutor = ThreadPoolExecutor(self._setSystemExecutorThreadCount())
        self.EventLoop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        except Exception as e:
            _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] has been terminated due to {e}.")
        finally:
            self.EventLoop.close()
            _DefaultLogger.info(f"[{self.ProcessName} - {self.pid}] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def addProcessTask(self, priority: int, task_object: _TaskObject) -> None:
        """
        Adds a task to the appropriate priority queue based on the given priority level.

        :param priority: An integer representing the priority of the task (0 to 10).
        :param task_object: An instance of _TaskObject representing the task to be added.
        :return: None
        setup:
            1. Set the working event to indicate that a task is being processed.
            2. Determine the appropriate queue for the task based on its priority:
                2.1. If the priority is between 0 and 3, add the task to the HighPriorityQueue.
                2.2. If the priority is between 4 and 7, add the task to the MediumPriorityQueue.
                2.3. If the priority is between 8 and 10, add the task to the LowPriorityQueue.
                2.4. If the priority is outside the range of 0 to 10, add the task to the MediumPriorityQueue and log a warning about the default priority being used.
        """

        self.WorkingEvent.set()
        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object, 0))
        elif 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
        elif 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object, 0))
        else:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
            _DefaultLogger.warning(f"[{self.ProcessName} - {self.pid}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self) -> None:
        """
        Processes tasks from the queue, executing them based on their type and handling memory cleanup.

        :return: None
        setup:
            1. Perform initial memory cleanup for the process.
            2. Initialize a timestamp for tracking the last cleanup time.
            3. Enter a loop that continues until the CloseEvent is triggered:
                3.1. Check if it's time to perform idle cleanup based on the configured threshold:
                    3.1.1. If the threshold is reached, call the cleanup method and update the last cleanup time.
                3.2. Attempt to retrieve task data from the task queue:
                    3.2.1. If the queue is empty, check if there are pending tasks:
                        3.2.1.1. If there are no pending tasks, clear the working event.
                        3.2.1.2. Sleep briefly to yield control and avoid busy waiting.
                        3.2.1.3. Continue to the next iteration of the loop.
                3.3. Extract task priority, task object, and retry count from the retrieved task data.
                3.4. Reinitialize parameters for the task object.
                3.5. Execute the task based on its type:
                    3.5.1. If the task is asynchronous, call _executeAsyncTask.
                    3.5.2. If the task is synchronous, call _executeSyncTask.
                3.6. If any exception occurs during execution, log the error with the process name and task ID.
            4. After exiting the loop, call the cleanup method to finalize any necessary operations.
        """

        self._cleanupProcessMemory()
        last_cleanup_time: float = time.time()
        while not self.CloseEvent.is_set():
            await asyncio.sleep(0.001)
            current_time: float = time.time()
            if current_time - last_cleanup_time >= self.ConfigManager.IdleCleanupThreshold.value:
                self._cleanupProcessMemory()
                last_cleanup_time: float = current_time
            try:
                task_data: Tuple[str, _TaskObject, int] = self._getTaskData()
                task_priority, task_object, retried = task_data
                try:
                    task_object.reinitializedParams()
                    await self._executeAsyncTask(task_priority, task_object, retried) if task_object.TaskType == "Async" else await self._executeSyncTask(task_priority, task_object, retried)
                except Exception as e:
                    _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} failed due to {e}.")
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                continue
        self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task, determining whether to acquire a task lock based on the task's properties.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task requires a lock:
                1.1. If the task has a lock, call _executeLockedAsyncTask to handle the task with the lock.
                1.2. If the task does not require a lock, call _executeUnLockedAsyncTask to handle the task without the lock.
        """

        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task, determining whether to acquire a task lock based on the task's properties.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task requires a lock:
                1.1. If the task has a lock, call _executeLockedSyncTask to handle the task with the lock.
                1.2. If the task does not require a lock, call _executeUnLockedSyncTask to handle the task without the lock.
        """

        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task while holding a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Attempt to acquire the task lock with a timeout defined by task_object.LockTimeout:
                1.1. If the lock cannot be acquired, requeue the task and exit the method.
            2. Check if the task has a specified timeout:
                2.1. If a timeout is set, call _executeTimeoutAsyncTask to handle the task with a timeout while the lock is held.
                2.2. If no timeout is set, call _executeNonTimeoutAsyncTask to handle the task without timeout constraints while the lock is held.
        """

        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task without acquiring a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task has a specified timeout:
                1.1. If a timeout is set, call _executeTimeoutAsyncTask to handle the task with a timeout.
                1.2. If no timeout is set, call _executeNonTimeoutAsyncTask to handle the task without timeout constraints.
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes an asynchronous task with a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Create an asyncio Event to signal task completion.
            2. Define an inner asynchronous function _onTaskCancelled to handle task cancellation:
                2.1. Await the cancellation of the future object.
                2.2. Remove the task from PendingTasks.
                2.3. Update the task status.
                2.4. Release the task lock if it was held.
            3. Define an inner function _onTaskCompleted to handle task completion:
                3.1. If the future is cancelled, schedule the cancellation handler.
                3.2. Otherwise, retrieve the result of the completed task and set the wait_for_event to signal that the task has completed.
                3.3. Process the task result using _taskResultProcessor.
                3.4. If an exception occurs during processing:
                    3.4.1. Remove the task from PendingTasks.
                    3.4.2. If the task is marked for retry and the retry count is within limits, requeue the task.
                    3.4.3. If the task cannot be retried, update the task status and log the error.
                    3.4.4. Release the task lock if it was held.
            4. Create an asynchronous task using the event loop to execute the task method with recovered arguments.
            5. Store the future in the PendingTasks dictionary using the task ID as the key.
            6. Add the completion callback to the future to handle the result processing.
            7. Use asyncio.wait_for to wait for the wait_for_event to be set, with a timeout based on task_object.TimeOut:
                7.1. If the timeout is reached, cancel the future and log a warning about the timeout.
        """

        wait_for_event: asyncio.Event = asyncio.Event()

        async def _onTaskCancelled(future_object) -> None:
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()

        def _onTaskCompleted(future_object: asyncio.Task) -> None:
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result: Any = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            _DefaultLogger.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes an asynchronous task without a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Define an inner asynchronous function _onTaskCancelled to handle task cancellation:
                1.1. Await the cancellation of the future object.
                1.2. Remove the task from PendingTasks.
                1.3. Update the task status.
                1.4. Release the task lock if it was held.
                1.5. Log a warning indicating the task was cancelled.
            2. Define an inner function _onTaskCompleted to handle task completion:
                2.1. If the future is cancelled, schedule the cancellation handler.
                2.2. Otherwise, retrieve the result of the completed task and process it using _taskResultProcessor.
                2.3. If an exception occurs during processing:
                    2.3.1. Remove the task from PendingTasks.
                    2.3.2. If the task is marked for retry and the retry count is within limits, requeue the task.
                    2.3.3. If the task cannot be retried, update the task status and log the error.
                    2.3.4. Release the task lock if it was held.
            3. Create an asynchronous task using the event loop to execute the task method with recovered arguments.
            4. Store the future in the PendingTasks dictionary using the task ID as the key.
            5. Add the completion callback to the future to handle the result processing.
        """

        async def _onTaskCancelled(future_object: asyncio.Task) -> None:
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()
            _DefaultLogger.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")

        def _onTaskCompleted(future_object: asyncio.Task) -> None:
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result: Any = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task while holding a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Attempt to acquire the task lock with a timeout defined by task_object.LockTimeout:
                1.1. If the lock cannot be acquired, requeue the task and exit the method.
            2. Check if the task has a specified timeout:
                2.1. If a timeout is set, call _executeTimeoutSyncTask to handle the task with a timeout while the lock is held.
                2.2. If no timeout is set, call _executeNonTimeoutSyncTask to handle the task without timeout constraints while the lock is held.
        """

        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task without acquiring a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task has a specified timeout:
                1.1. If a timeout is set, call _executeTimeoutSyncTask to handle the task with a timeout.
                1.2. If no timeout is set, call _executeNonTimeoutSyncTask to handle the task without timeout constraints.
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes a synchronous task with a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Create an asyncio Event to signal task completion.
            2. Define an inner function _onTaskCompleted to handle the completion of the task:
                2.1. Retrieve the result of the task and set the wait_for_event to signal that the task has completed.
                2.2. Process the task result using _taskResultProcessor.
                2.3. Release the task lock if it was held.
                2.4. Handle CancelledError by updating the task status and removing the task from PendingTasks.
                2.5. Handle exceptions by removing the task from PendingTasks and deciding whether to requeue it or log an error.
            3. Submit the task for execution using the system executor, capturing the future object.
            4. Store the future in the PendingTasks dictionary using the task ID as the key.
            5. Add the completion callback to the future to handle the result processing.
            6. Use asyncio.wait_for to wait for the wait_for_event to be set, with a timeout based on task_object.TimeOut:
                6.1. If the timeout is reached, cancel the future and log a warning about the timeout.
        """

        wait_for_event: asyncio.Event = asyncio.Event()

        def _onTaskCompleted(future_object: Future):
            try:
                task_result: Any = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except CancelledError:
                del self.PendingTasks[task_object.TaskID]
                self._updateTaskStatus()
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            _DefaultLogger.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes a non-timeout synchronous task and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Define a callback function _onTaskCompleted to handle the completion of the task:
                1.1. Retrieve the result of the task and process it using _taskResultProcessor.
                1.2. If the task was cancelled, update the task status and log a warning.
                1.3. If an exception occurs during processing:
                    1.3.1. If the task is marked for retry and the retry count is within limits, requeue the task.
                    1.3.2. If the task cannot be retried, remove it from the PendingTasks and log the error.
                    1.3.3. Release the task lock if it was held.
            2. Submit the task for execution using the system executor, capturing the future object.
            3. Store the future in the PendingTasks dictionary using the task ID as the key.
            4. Add the completion callback to the future to handle the result processing.
        """

        def _onTaskCompleted(future_object: Future):
            try:
                task_result: Any = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except CancelledError:
                self._updateTaskStatus()
                if locked:
                    self.StatusManager.TaskLock.release()
                _DefaultLogger.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self) -> None:
        """
        Updates the task status for the current process based on its type.

        :return: None
        setup:
            1. Retrieve the current task status for the process:
                1.1. If the process type is "Core", get the status from the core process status pool.
                1.2. If the process type is "Expand", get the status from the expand process status pool.
            2. Extract the process ID and current task count from the status.
            3. Calculate the new task count, ensuring it does not drop below zero.
            4. Update the task status in the appropriate status pool based on the process type:
                4.1. For "Core" processes, call the method to update the core process task status.
                4.2. For "Expand" processes, call the method to update the expand process task status.
        """

        current_status: Tuple[int, int] = self.StatusManager.getCoreProcessTaskStatus(self.ProcessName) if self.ProcessType == "Core" else self.StatusManager.getExpandProcessTaskStatus(self.ProcessName)
        pid: int = current_status[0]
        task_count: int = current_status[1]
        new_task_count: int = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ProcessType == "Core":
            self.StatusManager.updateCoreProcessTaskStatus(self.ProcessName, pid, new_task_count)
        else:
            self.StatusManager.updateExpandProcessTaskStatus(self.ProcessName, pid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any) -> None:
        """
        Processes the result of a completed task and updates the task status.

        :param task_object: An instance of _TaskObject representing the completed task.
        :param task_result: The result returned by the completed task, which may be a tensor or module.
        :return: None
        setup:
            1. Check if the task uses GPU resources and if the result is of the expected type:
                1.1. If true, clone and detach the result to move it to the CPU and clean up GPU resources.
                1.2. Otherwise, use the result as is.
            2. Place the processed result along with the task ID into the ResultStorageQueue.
            3. Attempt to remove the task from the PendingTasks dictionary:
                3.1. If the task ID does not exist, handle the KeyError silently.
                3.2. If any other exception occurs, log an error message.
            4. Call the method to update the task status.
        """

        if task_object.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result: Any = task_result.clone().detach().cpu()
            task_object.cleanupGpuResources()
        else:
            cpu_result: Any = task_result
        self.StatusManager.ResultStorageQueue.put_nowait((cpu_result, task_object.TaskID))
        # noinspection PyBroadException
        try:
            del self.PendingTasks[task_object.TaskID]
            del cpu_result
        except KeyError:
            pass
        except Exception:
            _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] failed to remove task {task_object.TaskID} from PendingTasks.")
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Requeues a task into the appropriate priority queue based on its priority level.

        :param task_priority: A string indicating the priority level of the task ("HighPriority", "MediumPriority", or "LowPriority").
        :param task_object: An instance of _TaskObject representing the task to be requeued.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check the task priority:
                1.1. If the priority is "HighPriority", place the task into the HighPriorityQueue.
                1.2. If the priority is "MediumPriority", place the task into the MediumPriorityQueue.
                1.3. If the priority is "LowPriority", place the task into the LowPriorityQueue.
        """

        if task_priority == "HighPriority":
            self.HighPriorityQueue.put_nowait((task_priority, task_object, retried))
            return
        if task_priority == "MediumPriority":
            self.MediumPriorityQueue.put_nowait((task_priority, task_object, retried))
            return
        if task_priority == "LowPriority":
            self.LowPriorityQueue.put_nowait((task_priority, task_object, retried))
            return

    def _cleanup(self) -> None:
        """
        Cleans up remaining tasks, shuts down the system executor, and clears the pending tasks.

        :return: None
        setup:
            1. Initialize a counter for remaining tasks.
            2. Check and discard tasks from the high priority queue until it is empty:
                2.1. Attempt to retrieve tasks without blocking and increment the remaining tasks counter.
            3. Repeat the same process for the medium priority queue.
            4. Repeat the same process for the low priority queue.
            5. Shutdown the system executor, waiting for ongoing tasks to complete and cancelling any futures.
            6. Attempt to cancel any pending tasks in the PendingTasks dictionary:
                6.1. If an exception occurs during cancellation, handle it silently.
            7. Log the number of discarded tasks using a debug message.
            8. Clear the PendingTasks dictionary to remove references to cancelled tasks.
        """

        remaining_tasks: int = 0
        while not self.HighPriorityQueue.empty():
            try:
                _, task_object, _ = self.HighPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.MediumPriorityQueue.empty():
            try:
                _, task_object, _ = self.MediumPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.LowPriorityQueue.empty():
            try:
                _, task_object, _ = self.LowPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        self.SystemExecutor.shutdown(wait=True, cancel_futures=True)
        # noinspection PyBroadException
        try:
            for i, pending_task in self.PendingTasks.items():
                pending_task.cancel()
        except Exception:
            pass
        _DefaultLogger.debug(f"[{self.ProcessName} - {self.pid}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _setProcessPriority(self, priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = None) -> None:
        """
        Sets the priority of the process based on the provided priority level.

        :param priority: A string indicating the desired priority level ("IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"). If None, uses the configured process priority.
        :return: None
        :raise: Raises a ValueError if unable to obtain a valid process handle or an Exception if setting the priority fails.
        setup:
            1. Define a mapping of priority names to their corresponding values.
            2. Attempt to open the current process using its process ID:
                2.1. If the handle is invalid, raise a ValueError.
            3. Set the process priority using the appropriate value from the mapping:
                3.1. If the specified priority is None, use the configured process priority from the configuration manager.
                3.2. If setting the priority fails, retrieve and raise an exception with the error code.
            4. Ensure the process handle is closed in the finally block to avoid memory leaks.
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
            _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _setSystemExecutorThreadCount(self) -> int:
        """
        Determines the number of executor threads to allocate based on the number of physical CPU cores.

        :return: An integer representing the number of executor threads.
        setup:
            1. Define a mapping of core ranges to corresponding thread counts.
            2. Iterate through the mapping to find the appropriate thread count based on the current number of physical cores:
                2.1. If the number of physical cores falls within a defined range, return the associated thread count.
            3. If no suitable range is found, return a default thread count of 12.
        """

        count_mapping = {
            (0, 12): 2,
            (12, 24): 4,
            (24, 36): 6,
            (36, 48): 8,
            (48, 60): 10,
            (60, 72): 12,
        }
        for core_range, count in count_mapping.items():
            if core_range[0] < self.ConfigManager.PhysicalCores <= core_range[1]:
                return count
        return 12

    def _cleanupProcessMemory(self) -> None:
        """
        Cleans up the memory of the process by releasing unused memory resources.

        :return: None
        :raise: Raises an exception if there is an error in obtaining the process handle or performing the memory cleanup.
        setup:
            1. Check if the system type is Windows.
            2. Attempt to open the process using its PID:
                2.1. If the handle is invalid, raise a ValueError indicating the failure.
                2.2. If an exception occurs during the process opening, log the error and exit the method.
            3. Call the EmptyWorkingSet function to release unused memory resources:
                3.1. If the call fails, retrieve and log the error code.
            4. Close the handle to the process to avoid memory leaks.
        """

        if _SystemType == "Windows":
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.pid)
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed due to {e}.")
                return
            if not handle:
                _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                _DefaultLogger.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        """
        Retrieves task data from the highest priority queue available.

        :return: A tuple containing the task priority, the task object, and the retry count.
        :raise: Raises queue.Empty if all priority queues are empty.
        setup:
            1. Check if the high priority queue is not empty; if so, retrieve and return the task data.
            2. If the high priority queue is empty, check the medium priority queue; if not empty, retrieve and return the task data.
            3. If both high and medium priority queues are empty, check the low priority queue; if not empty, retrieve and return the task data.
            4. If all queues are empty, raise a queue.Empty exception.
        """

        if not self.HighPriorityQueue.empty():
            return self.HighPriorityQueue.get_nowait()
        if not self.MediumPriorityQueue.empty():
            return self.MediumPriorityQueue.get_nowait()
        if not self.LowPriorityQueue.empty():
            return self.LowPriorityQueue.get_nowait()
        raise queue.Empty


class _ThreadObject(threading.Thread):
    """
    Represents a thread that handles task execution for either core or expand operations.

    The class is a specialized thread that processes tasks of varying priorities within a multithreaded and asynchronous environment.
    It supports both synchronous and asynchronous task execution, offering fine-grained control over task prioritization, retry mechanisms, and resource management.
    This thread object is utilized for both core and expandable operations, adjusting dynamically to workload demands.

    InstanceAttribute:
        ThreadName: The name of the thread.
        ThreadType: The type of the thread, either 'Core' or 'Expand'.
        StatusManager: Manages the status of tasks and threads.
        ConfigManager: Handles configuration settings for task execution.
        PendingTasks: A dictionary storing pending tasks for execution.
        SystemExecutor: ThreadPoolExecutor for executing synchronous tasks.
        HighPriorityQueue: Queue for high-priority tasks.
        MediumPriorityQueue: Queue for medium-priority tasks.
        LowPriorityQueue: Queue for low-priority tasks.
        WorkingEvent: Event to indicate the thread is currently working.
        CloseEvent: Event to signal the thread to stop running.
        EventLoop: The asyncio event loop for handling asynchronous tasks.
    Method:
        run: The main loop for processing tasks.
        stop: Signals the thread to stop and waits for its completion.
        addThreadTask: Adds a new task to the appropriate priority queue.
        _taskProcessor: Processes tasks from the queues and executes them.
        _executeAsyncTask: Executes asynchronous tasks, handling locking if necessary.
        _executeSyncTask: Executes synchronous tasks, handling locking if necessary.
        _executeLockedAsyncTask: Executes a locked asynchronous task with timeout handling.
        _executeUnLockedAsyncTask: Executes an unlocked asynchronous task without timeout.
        _executeTimeoutAsyncTask: Handles asynchronous tasks that have a timeout set.
        _executeNonTimeoutAsyncTask: Handles asynchronous tasks that do not have a timeout set.
        _executeLockedSyncTask: Executes a locked synchronous task with timeout handling.
        _executeUnLockedSyncTask: Executes an unlocked synchronous task without timeout.
        _executeTimeoutSyncTask: Handles synchronous tasks that have a timeout set.
        _executeNonTimeoutSyncTask: Handles synchronous tasks that do not have a timeout set.
        _updateTaskStatus: Updates the status of tasks being processed.
        _taskResultProcessor: Processes the result of a completed task.
        _requeueTask: Requeues a task for execution based on its priority.
        _cleanup: Cleans up remaining tasks and pending tasks.
        _getTaskData: Retrieves task data from the appropriate priority queue.
    """

    def __init__(self, thread_name: str, thread_type: Literal['Core', 'Expand'], sm: _StatusManager, cm: _ConfigManager, system_executor: ThreadPoolExecutor):
        super().__init__(name=thread_name, daemon=True)
        self.ThreadName = thread_name
        self.ThreadType = thread_type
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.PendingTasks: Dict[str, asyncio.Task | Future] = {}
        self.SystemExecutor: ThreadPoolExecutor = system_executor
        self.HighPriorityQueue: queue.Queue = queue.Queue()
        self.MediumPriorityQueue: queue.Queue = queue.Queue()
        self.LowPriorityQueue: queue.Queue = queue.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self) -> None:
        """
        Runs the event loop for processing tasks asynchronously.

        :return: None
        setup:
            1. Create a new asyncio event loop and set it as the current event loop.
            2. Attempt to run the task processor until completion:
                2.1. If any exception occurs during execution, log the error with the thread's name and identifier.
            3. Ensure that the event loop is closed in the finally block to release resources.
            4. Log an informational message indicating that the thread has been stopped.
        """

        self.EventLoop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        except Exception as e:
            _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] has been terminated due to {e}.")
        finally:
            self.EventLoop.close()
            _DefaultLogger.info(f"[{self.ThreadName} - {self.ident}] has been stopped.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def addThreadTask(self, priority: int, task_object: _TaskObject) -> None:
        """
        Adds a task to the appropriate priority queue based on the given priority level.

        :param priority: An integer representing the priority of the task (0 to 10).
        :param task_object: An instance of _TaskObject representing the task to be added.
        :return: None
        setup:
            1. Set the working event to indicate that a task is being processed.
            2. Determine the appropriate queue for the task based on its priority:
                2.1. If the priority is between 0 and 3, add the task to the HighPriorityQueue.
                2.2. If the priority is between 4 and 7, add the task to the MediumPriorityQueue.
                2.3. If the priority is between 8 and 10, add the task to the LowPriorityQueue.
                2.4. If the priority is outside the range of 0 to 10, add the task to the MediumPriorityQueue and log a warning about the default priority being used.
        """

        self.WorkingEvent.set()
        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object, 0))
        elif 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
        elif 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object, 0))
        else:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
            _DefaultLogger.warning(f"[{self.ThreadName} - {self.ident}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self) -> None:
        """
        Processes tasks from the queue, executing them based on their type and handling any exceptions.

        :return: None
        setup:
            1. Enter a loop that continues until the CloseEvent is triggered:
                1.1. Attempt to retrieve task data from the task queue:
                    1.1.1. If the queue is empty, check if there are pending tasks:
                        1.1.1.1. If there are no pending tasks, clear the working event.
                        1.1.1.2. Sleep briefly to yield control and avoid busy waiting.
                        1.1.1.3. Continue to the next iteration of the loop.
                1.2. Extract task priority, task object, and retry count from the retrieved task data.
                1.3. Reinitialize parameters for the task object.
                1.4. Execute the task based on its type:
                    1.4.1. If the task is asynchronous, call _executeAsyncTask.
                    1.4.2. If the task is synchronous, call _executeSyncTask.
                1.5. If any exception occurs during execution, log the error with the task ID.
            2. After exiting the loop, call the cleanup method to finalize any necessary operations.
        """

        while not self.CloseEvent.is_set():
            await asyncio.sleep(0.001)
            try:
                task_data: Tuple[str, _TaskObject, int] = self._getTaskData()
                task_priority, task_object, retried = task_data
                try:
                    task_object.reinitializedParams()
                    await self._executeAsyncTask(task_priority, task_object, retried) if task_object.TaskType == "Async" else await self._executeSyncTask(task_priority, task_object, retried)
                except Exception as e:
                    _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] task {task_object.TaskID} failed due to {e}.")
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                continue
        await self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task, determining whether to acquire a task lock based on the task's properties.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task requires a lock:
                1.1. If the task has a lock, call _executeLockedAsyncTask to handle the task with the lock.
                1.2. If the task does not require a lock, call _executeUnLockedAsyncTask to handle the task without the lock.
        """

        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task, determining whether to acquire a task lock based on the task's properties.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task requires a lock:
                1.1. If the task has a lock, call _executeLockedSyncTask to handle the task with the lock.
                1.2. If the task does not require a lock, call _executeUnLockedSyncTask to handle the task without the lock.
        """

        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task while holding a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Attempt to acquire the task lock with a timeout defined by task_object.LockTimeout:
                1.1. If the lock cannot be acquired, requeue the task and exit the method.
            2. Check if the task has a specified timeout:
                2.1. If a timeout is set, call _executeTimeoutAsyncTask to handle the task with a timeout while the lock is held.
                2.2. If no timeout is set, call _executeNonTimeoutAsyncTask to handle the task without timeout constraints while the lock is held.
        """

        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes an asynchronous task without acquiring a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task has a specified timeout:
                1.1. If a timeout is set, call _executeTimeoutAsyncTask to handle the task with a timeout.
                1.2. If no timeout is set, call _executeNonTimeoutAsyncTask to handle the task without timeout constraints.
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes an asynchronous task with a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Create an asyncio Event to signal task completion.
            2. Define an inner asynchronous function _onTaskCancelled to handle task cancellation:
                2.1. Await the cancellation of the future object.
                2.2. Remove the task from PendingTasks.
                2.3. Update the task status.
                2.4. Release the task lock if it was held.
            3. Define an inner function _onTaskCompleted to handle task completion:
                3.1. If the future is cancelled, schedule the cancellation handler.
                3.2. Otherwise, retrieve the result of the completed task and set the wait_for_event to signal that the task has completed.
                3.3. Process the task result using _taskResultProcessor.
                3.4. If an exception occurs during processing:
                    3.4.1. Remove the task from PendingTasks.
                    3.4.2. If the task is marked for retry and the retry count is within limits, requeue the task.
                    3.4.3. If the task cannot be retried, update the task status and log the error.
                    3.4.4. Release the task lock if it was held.
            4. Create an asynchronous task using the event loop to execute the task method with recovered arguments.
            5. Store the future in the PendingTasks dictionary using the task ID as the key.
            6. Add the completion callback to the future to handle the result processing.
            7. Use asyncio.wait_for to wait for the wait_for_event to be set, with a timeout based on task_object.TimeOut:
                7.1. If the timeout is reached, cancel the future and log a warning about the timeout.
        """

        wait_for_event: asyncio.Event = asyncio.Event()

        async def _onTaskCancelled(future_object: asyncio.Task):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()

        def _onTaskCompleted(future_object: asyncio.Task):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result: Any = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs), name=f"{task_object.Task.__name__}[{task_object.TaskID}]")
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            _DefaultLogger.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes an asynchronous task without a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Define an inner asynchronous function _onTaskCancelled to handle task cancellation:
                1.1. Await the cancellation of the future object.
                1.2. Remove the task from PendingTasks.
                1.3. Update the task status.
                1.4. Release the task lock if it was held.
                1.5. Log a warning indicating the task was cancelled.
            2. Define an inner function _onTaskCompleted to handle task completion:
                2.1. If the future is cancelled, schedule the cancellation handler.
                2.2. Otherwise, retrieve the result of the completed task and process it using _taskResultProcessor.
                2.3. If an exception occurs during processing:
                    2.3.1. Remove the task from PendingTasks.
                    2.3.2. If the task is marked for retry and the retry count is within limits, requeue the task.
                    2.3.3. If the task cannot be retried, update the task status and log the error.
                    2.3.4. Release the task lock if it was held.
            3. Create an asynchronous task using the event loop to execute the task method with recovered arguments.
            4. Store the future in the PendingTasks dictionary using the task ID as the key.
            5. Add the completion callback to the future to handle the result processing.
        """

        async def _onTaskCancelled(future_object: asyncio.Task):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()
            _DefaultLogger.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")

        def _onTaskCompleted(future_object: asyncio.Task):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result: Any = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs), name=f"{task_object.Task.__name__}[{task_object.TaskID}]")
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task while holding a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Attempt to acquire the task lock with a timeout defined by task_object.LockTimeout:
                1.1. If the lock cannot be acquired, requeue the task and exit the method.
            2. Check if the task has a specified timeout:
                2.1. If a timeout is set, call _executeTimeoutSyncTask to handle the task with a timeout while the lock is held.
                2.2. If no timeout is set, call _executeNonTimeoutSyncTask to handle the task without timeout constraints while the lock is held.
        """

        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Executes a synchronous task without acquiring a task lock, handling timeouts if specified.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check if the task has a specified timeout:
                1.1. If a timeout is set, call _executeTimeoutSyncTask to handle the task with a timeout.
                1.2. If no timeout is set, call _executeNonTimeoutSyncTask to handle the task without timeout constraints.
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes a synchronous task with a timeout and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Create an asyncio Event to signal task completion.
            2. Define a callback function _onTaskCompleted that will be called when the task completes:
                2.1. Retrieve the result of the task and process it using _taskResultProcessor.
                2.2. If the task was cancelled, remove it from the PendingTasks and update the task status.
                2.3. If an exception occurs:
                    2.3.1. Remove the task from PendingTasks.
                    2.3.2. If the task is marked for retry and the retry count is within limits, requeue the task.
                    2.3.3. If the task cannot be retried, update the task status and log the error.
                2.4. Release the task lock if it was held.
                2.5. Set the wait_for_event to signal that the task has completed.
            3. Submit the task for execution using the system executor, capturing the future object.
            4. Store the future in the PendingTasks dictionary using the task ID as the key.
            5. Add the completion callback to the future to handle the result processing.
            6. Use asyncio.wait_for to wait for the wait_for_event to be set, with a timeout based on task_object.TimeOut:
                6.1. If the timeout is reached, cancel the future if it's still running and log a warning about the timeout.
        """

        wait_for_event: asyncio.Event = asyncio.Event()

        def _onTaskCompleted(future_object: Future):
            try:
                task_result: Any = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except CancelledError:
                del self.PendingTasks[task_object.TaskID]
                self._updateTaskStatus()
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            _DefaultLogger.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        """
        Executes a non-timeout synchronous task and processes its result upon completion.

        :param task_priority: A string indicating the priority level of the task.
        :param task_object: An instance of _TaskObject representing the task to be executed.
        :param retried: An integer indicating the number of times the task has been retried.
        :param locked: A boolean indicating whether the task lock is currently held.
        :return: None
        setup:
            1. Define a callback function _onTaskCompleted that will be called when the task completes:
                1.1. Retrieve the result of the task and process it using _taskResultProcessor.
                1.2. If the task was cancelled, log a warning and update the task status.
                1.3. If an exception occurs:
                    1.3.1. If the task is marked for retry and the retry count is within limits, requeue the task.
                    1.3.2. If the task cannot be retried, remove it from the PendingTasks and log the error.
                1.4. Release the task lock if it was held.
            2. Submit the task for execution using the system executor, capturing the future object.
            3. Store the future in the PendingTasks dictionary using the task ID as the key.
            4. Add the completion callback to the future to handle the result processing.
        """

        def _onTaskCompleted(future_object: Future):
            try:
                task_result: Any = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except CancelledError:
                self._updateTaskStatus()
                if locked:
                    self.StatusManager.TaskLock.release()
                _DefaultLogger.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DefaultLogger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self) -> None:
        """
        Updates the task status for the current thread based on its type.

        :return: None
        setup:
            1. Retrieve the current task status for the thread:
                1.1. If the thread type is "Core", get the status from the core thread status pool.
                1.2. If the thread type is "Expand", get the status from the expand thread status pool.
            2. Extract the task ID and current task count from the status.
            3. Calculate the new task count, ensuring it does not drop below zero.
            4. Update the task status in the appropriate status pool based on the thread type:
                4.1. For "Core" threads, call the method to update the core thread task status.
                4.2. For "Expand" threads, call the method to update the expand thread task status.
        """

        current_status: Tuple[int, int] = self.StatusManager.getCoreThreadTaskStatus(self.ThreadName) if self.ThreadType == "Core" else self.StatusManager.getExpandThreadTaskStatus(self.ThreadName)
        tid: int = current_status[0]
        task_count: int = current_status[1]
        new_task_count: int = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ThreadType == "Core":
            self.StatusManager.updateCoreThreadTaskStatus(self.ThreadName, tid, new_task_count)
        else:
            self.StatusManager.updateExpandThreadTaskStatus(self.ThreadName, tid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any) -> None:
        """
        Processes the result of a completed task and updates the task status.

        :param task_object: An instance of _TaskObject representing the completed task.
        :param task_result: The result returned by the completed task, which may be a tensor or module.
        :return: None
        setup:
            1. Check if the task uses GPU resources and if the result is of the expected type:
                1.1. If true, clone and detach the result to move it to the CPU and clean up GPU resources.
                1.2. Otherwise, use the result as is.
            2. Place the processed result along with the task ID into the ResultStorageQueue.
            3. Attempt to remove the task from the PendingTasks dictionary:
                3.1. If the task ID does not exist, handle the KeyError silently.
                3.2. If any other exception occurs, log an error message.
            4. Call the method to update the task status.
        """

        if task_object.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result: Any = task_result.clone().detach().cpu()
            task_object.cleanupGpuResources()
        else:
            cpu_result: Any = task_result
        self.StatusManager.ResultStorageQueue.put_nowait((cpu_result, task_object.TaskID))
        # noinspection PyBroadException
        try:
            del self.PendingTasks[task_object.TaskID]
            del cpu_result
        except KeyError:
            pass
        except Exception:
            _DefaultLogger.error(f"[{self.ThreadName} - {self.ident}] failed to remove task {task_object.TaskID} from PendingTasks.")
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        """
        Requeues a task into the appropriate priority queue based on its priority level.

        :param task_priority: A string indicating the priority level of the task ("HighPriority", "MediumPriority", or "LowPriority").
        :param task_object: An instance of _TaskObject representing the task to be requeued.
        :param retried: An integer indicating the number of times the task has been retried.
        :return: None
        setup:
            1. Check the task priority:
                1.1. If the priority is "HighPriority", place the task into the HighPriorityQueue.
                1.2. If the priority is "MediumPriority", place the task into the MediumPriorityQueue.
                1.3. If the priority is "LowPriority", place the task into the LowPriorityQueue.
        """

        if task_priority == "HighPriority":
            self.HighPriorityQueue.put_nowait((task_priority, task_object, retried))
            return
        if task_priority == "MediumPriority":
            self.MediumPriorityQueue.put_nowait((task_priority, task_object, retried))
            return
        if task_priority == "LowPriority":
            self.LowPriorityQueue.put_nowait((task_priority, task_object, retried))
            return

    async def _cleanup(self) -> None:
        """
        Cleans up pending tasks and discards any remaining tasks in the priority queues.

        :return: None
        setup:
            1. Initialize a counter for remaining tasks.
            2. Await the completion of all pending tasks stored in the PendingTasks dictionary.
            3. Check and discard tasks from the high priority queue until it's empty:
                3.1. Attempt to retrieve and count tasks from the high priority queue.
            4. Repeat the same process for the medium priority queue.
            5. Repeat the same process for the low priority queue.
            6. Log the number of discarded tasks using a debug message.
            7. Clear the PendingTasks dictionary to remove references to completed tasks.
        """

        remaining_tasks = 0
        for i, pending_task in self.PendingTasks.items():
            pending_task.cancel()
        while not self.HighPriorityQueue.empty():
            try:
                _, task_object, _ = self.HighPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.MediumPriorityQueue.empty():
            try:
                _, task_object, _ = self.MediumPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        while not self.LowPriorityQueue.empty():
            try:
                _, task_object, _ = self.LowPriorityQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        _DefaultLogger.debug(f"[{self.ThreadName} - {self.ident}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        """
        Retrieves task data from the highest priority queue available.

        :return: A tuple containing the task identifier, the task object, and its priority level.
        :raise: Raises queue.Empty if all priority queues are empty.
        setup:
            1. Check if the high priority queue is not empty; if so, retrieve and return the task data.
            2. If the high priority queue is empty, check the medium priority queue; if not empty, retrieve and return the task data.
            3. If both high and medium priority queues are empty, check the low priority queue; if not empty, retrieve and return the task data.
            4. If all queues are empty, raise a queue.Empty exception.
        """

        if not self.HighPriorityQueue.empty():
            return self.HighPriorityQueue.get_nowait()
        if not self.MediumPriorityQueue.empty():
            return self.MediumPriorityQueue.get_nowait()
        if not self.LowPriorityQueue.empty():
            return self.LowPriorityQueue.get_nowait()
        raise queue.Empty


class _LoadBalancer(threading.Thread):
    """
    The class is a specialized thread designed to dynamically manage the system's load distribution across core and expandable processes and threads.

    By implementing real-time monitoring and load-balancing mechanisms, it enhances the system's efficiency through resource allocation adjustments,
    process/thread expansion and shrinkage, and memory cleanup routines.
    This load balancer ensures that tasks are distributed optimally while maintaining system stability by adapting to changing workload demands.

    InstanceAttribute:
        StatusManager: Manages the status of processes and threads.
        ConfigManager: Handles configuration settings for load balancing policies.
        Logger: Logger instance for recording events and errors.
        SystemExecutor: ThreadPoolExecutor for managing thread execution.
        CloseEvent: Event to signal the load balancer to stop running.
    Method:
        run: The main loop for monitoring and adjusting the load of processes and threads.
        stop: Signals the load balancer to stop and waits for its completion.
        _showPerformanceReport: Displays the performance metrics of processes and threads.
        _cleanupMainProcessMemory: Cleans up memory used by the main process.
        _cleanupServiceProcessMemory: Cleans up memory used by service processes.
        _updateProcessLoadStatus: Updates the load status of core and expand processes.
        _expandPolicyExecutor: Executes the defined expansion policy for processes and threads.
        _shrinkagePolicyExecutor: Executes the defined shrinkage policy for processes and threads.
        _isAllowExpansion: Checks if expansion of processes or threads is allowed based on configuration.
        _expandProcess: Creates and starts a new expand process.
        _expandThread: Creates and starts a new expand thread.
        _generateExpandID: Generates a unique ID for new expand processes or threads.
        _autoExpand: Automatically expands processes and threads based on load conditions.
        _beforehandExpand: Expands processes and threads before they reach a defined task threshold.
        _noExpand: No expansion occurs.
        _autoShrink: Automatically shrinks processes and threads that are idle.
        _timeoutShrink: Shrinks processes and threads that have exceeded their timeout limit.
        _noShrink: No shrinkage occurs.
    """

    def __init__(self, sm: _StatusManager, cm: _ConfigManager, logger: TheSeedCoreLogger, system_executor: ThreadPoolExecutor):
        super().__init__(name='LoadBalancer', daemon=True)
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.Logger: TheSeedCoreLogger = logger
        self.SystemExecutor: ThreadPoolExecutor = system_executor
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        """
        Runs the load balancer, managing process load statuses and executing expansion and shrinkage policies.

        :return: None
        setup:
            1. Perform initial memory cleanup for the main process and service processes.
            2. Initialize timestamps for the last cleanup and performance report intervals.
            3. Enter a loop that continues until the CloseEvent is triggered:
                3.1. Update the load status of processes.
                3.2. Execute the current expansion policy.
                3.3. Execute the current shrinkage policy.
                3.4. Sleep briefly to reduce CPU usage.
                3.5. Check if it's time to display the performance report (every 10 seconds):
                    3.5.1. Call the method to show the performance report and reset the timer.
                3.6. Check if it's time for memory cleanup (every 300 seconds):
                    3.6.1. Perform memory cleanup for the main process and service processes.
            4. Log a message indicating that the load balancer has been closed when exiting the loop.
        """

        self._cleanupMainProcessMemory()
        self._cleanupServiceProcessMemory()
        last_cleanup_time = time.time()
        performance_report_time = time.time()
        while not self.CloseEvent.is_set():
            time.sleep(0.001)
            self._updateProcessLoadStatus()
            self._expandPolicyExecutor()
            self._shrinkagePolicyExecutor()
            if time.time() - performance_report_time >= 10:
                self._showPerformanceReport()
                performance_report_time = time.time()
            if time.time() - last_cleanup_time > 300:
                last_cleanup_time = time.time()
                self._cleanupMainProcessMemory()
                self._cleanupServiceProcessMemory()
        self.Logger.info(f"[LoadBalancer] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def _showPerformanceReport(self):
        """
        Displays a performance report for the main process, core processes, and expand processes.

        :return: None
        setup:
            1. Check if performance reporting is enabled in the configuration; exit the method if not.
            2. Retrieve the CPU and memory usage of the main process.
            3. Print the performance report header.
            4. Print the performance details of the main process, including its PID, CPU usage, and memory usage.
            5. Iterate over each core process in the core process pool:
                5.1. Retrieve and print the CPU and memory usage for each core process along with its PID.
            6. Iterate over each expand process in the expand process pool:
                6.1. Retrieve and print the CPU and memory usage for each expand process along with its PID.
        """

        if not self.ConfigManager.PerformanceReport.value:
            return
        global _CoreProcessPool, _ExpandProcessPool
        main_process_cpu_usage = _ResourceMonitor.processCpuUsage(os.getpid(), 0.001)
        main_process_memory_usage = _ResourceMonitor.processMemoryUsage(os.getpid())
        print(TextColor.PURPLE_BOLD.value + "\nPerformanceReport" + TextColor.RESET.value)
        print(TextColor.PURPLE_BOLD.value + f"CoreProcess: MainProcess - PID: {os.getpid()} - CPU: {main_process_cpu_usage:.2f}% - Memory: {main_process_memory_usage:.2f}MB" + TextColor.RESET.value)
        for process_name, process_object in _CoreProcessPool.items():
            pid = process_object.pid
            cpu_usage = _ResourceMonitor.processCpuUsage(pid, 0.001)
            memory_usage = _ResourceMonitor.processMemoryUsage(pid)
            print(TextColor.PURPLE_BOLD.value + f"CoreProcess: {process_name} - PID: {pid} - CPU: {cpu_usage:.2f}% - Memory: {memory_usage:.2f}MB" + TextColor.RESET.value)
        for process_name, process_object in _ExpandProcessPool.items():
            pid = process_object.pid
            cpu_usage = _ResourceMonitor.processCpuUsage(pid, 0.001)
            memory_usage = _ResourceMonitor.processMemoryUsage(pid)
            print(TextColor.PURPLE_BOLD.value + f"ExpandProcess: {process_name} - PID: {pid} - CPU: {cpu_usage:.2f}% - Memory: {memory_usage:.2f}MB" + TextColor.RESET.value)

    def _cleanupMainProcessMemory(self) -> None:
        """
        Cleans up the memory of the main process by releasing unused memory resources.

        :return: None
        :raise: Raises an exception if there is an error in obtaining the process handle or performing the memory cleanup.
        setup:
            1. Check if the system type is Windows.
            2. Attempt to open the current process using its process ID:
                2.1. If the handle is invalid, raise a ValueError.
                2.2. If an exception occurs during the process opening, log the error and exit the method.
            3. Call the EmptyWorkingSet function to release unused memory resources:
                3.1. If the call fails, retrieve and log the error code.
            4. Close the handle to the process to avoid memory leaks.
        """

        if _SystemType == "Windows":
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, os.getpid())
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {e}.")
                return
            if not handle:
                self.Logger.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)
            return

    def _cleanupServiceProcessMemory(self) -> None:
        """
        Cleans up the memory of the service process by releasing unused memory resources.

        :return: None
        :raise: Raises an exception if there is an error in obtaining the process handle or performing the memory cleanup.
        setup:
            1. Check if the system type is Windows.
            2. Attempt to open the process using the shared object manager ID:
                2.1. If the handle is invalid, raise a ValueError.
                2.2. If an exception occurs during the process opening, log the error and exit the method.
            3. Call the EmptyWorkingSet function to release unused memory resources:
                3.1. If the call fails, retrieve and log the error code.
            4. Close the handle to the process to avoid memory leaks.
        """

        if _SystemType == "Windows":
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.StatusManager.SharedObjectManagerID)
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {e}.")
                return
            if not handle:
                self.Logger.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                self.Logger.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)

    def _updateProcessLoadStatus(self) -> None:
        """
        Updates the load status of core and expand processes based on their CPU and memory usage.

        :return: None
        setup:
            1. Iterate over each process in the core process pool:
                1.1. Attempt to retrieve the CPU and memory usage of the process.
                1.2. Calculate the weighted load based on CPU usage, memory usage, and task load status.
                1.3. Update the load status in the status manager with the calculated weighted load.
                1.4. If an exception occurs during this process, reset the load status to zero.
            2. Repeat the same process for each process in the expand process pool, updating their load statuses accordingly.
        """

        global _CoreProcessPool, _ExpandProcessPool
        for process_name, process_obj in _CoreProcessPool.items():
            # noinspection PyBroadException
            try:
                process_cpu_usage = _ResourceMonitor.processCpuUsage(process_obj.pid, 0.001)
                process_memory_usage = _ResourceMonitor.processMemoryUsage(process_obj.pid)
                weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.5) + (self.StatusManager.CoreProcessTaskStatusPool[process_name][1] * 0.5)), 100))
                self.StatusManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, weighted_load)
            except Exception:
                self.StatusManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, 0)
        for process_name, process_obj in _ExpandProcessPool.items():
            # noinspection PyBroadException
            try:
                process_cpu_usage = _ResourceMonitor.processCpuUsage(process_obj.pid, 0.001)
                process_memory_usage = _ResourceMonitor.processMemoryUsage(process_obj.pid)
                weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.5) + (self.StatusManager.ExpandProcessTaskStatusPool[process_name][1] * 0.5)), 100))
                self.StatusManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, weighted_load)
            except Exception:
                self.StatusManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, 0)

    def _expandPolicyExecutor(self) -> None:
        """
        Executes the appropriate expansion policy method based on the configuration settings.

        :return: None
        setup:
            1. Define a mapping of expansion policy names to their corresponding methods.
            2. Retrieve the expansion policy method based on the current configuration setting.
            3. Call the selected expansion method to execute the policy.
        """

        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self.ConfigManager.ExpandPolicy.value]
        expand_method()

    def _noExpand(self) -> None:
        pass

    def _autoExpand(self) -> None:
        """
        Automatically handles the expansion of system processes based on current load.

        This method monitors the current load of core and expansion processes.
        If the combined load exceeds a certain threshold, it attempts to expand the processes accordingly.
        It also ensures that the system does not exceed its maximum allowable process capacity.

        :raises: None
        :return: None
        setup:
            1. Retrieve the current load for core processes from the StatusManager.
            2. Retrieve the current load for expansion processes from the StatusManager (if applicable).
            3. Calculate the total load by combining core and expansion process loads.
            4. Compare the total load to a predefined threshold (ideal load per process, set to 90%).
            5. If the load exceeds the threshold, check if process expansion is allowed.
                5.1 If expansion is allowed, trigger the process expansion.
                5.2 If expansion is not allowed, log a warning.
            6. Ensure that expansion happens only when the system is not already scheduling tasks.

        Note:
            - `_ProcessTaskSchedulingEvent`, `_ThreadTaskSchedulingEvent`, `_ProcessBalanceEvent`, and `_ThreadBalanceEvent`
              are global events used for controlling task scheduling and balancing during process expansion.
            - `ConfigManager.CoreProcessCount` and `StatusManager` are used to monitor and manage the system load and processes.
        """

        global _ProcessTaskSchedulingEvent, _ThreadTaskSchedulingEvent, _ProcessBalanceEvent, _ThreadBalanceEvent
        if self.ConfigManager.CoreProcessCount.value != 0:
            current_core_process_total_load: int = sum([self.StatusManager.getCoreProcessLoadStatus(name)[1] for name, load_status in self.StatusManager.CoreProcessLoadStatusPool.items()])
            if self.StatusManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load: int = sum([self.StatusManager.getExpandProcessLoadStatus(name)[1] for name, load_status in self.StatusManager.ExpandProcessLoadStatusPool.items()])
            else:
                current_expand_process_total_load: int = 0
            process_total_load = max(0, min(100, current_core_process_total_load + current_expand_process_total_load))
            ideal_load_per_process = 90
            if process_total_load >= ideal_load_per_process:
                allow_process_expansion = self._isAllowExpansion("Process")
                if allow_process_expansion and not _ProcessTaskSchedulingEvent.is_set():
                    _ProcessBalanceEvent.set()
                    self._expandProcess()
                    _ProcessBalanceEvent.clear()
                elif not allow_process_expansion:
                    self.Logger.warning(f"Load reaches {int(ideal_load_per_process)}%, but unable to expand more process")
                else:
                    pass

        current_core_thread_total_load: int = sum([self.StatusManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreThreadTaskStatusPool.items()])
        if self.StatusManager.ExpandThreadTaskStatusPool:
            current_expand_thread_total_load: int = sum([self.StatusManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandThreadTaskStatusPool.items()])
        else:
            current_expand_thread_total_load: int = 0
        thread_total_load: int = current_core_thread_total_load + current_expand_thread_total_load
        threshold: int = self.ConfigManager.GlobalTaskThreshold.value - (self.ConfigManager.CoreProcessCount.value * self.ConfigManager.TaskThreshold.value)
        if thread_total_load >= threshold * 0.9:
            allow_thread_expansion = self._isAllowExpansion("Thread")
            if allow_thread_expansion and not _ThreadTaskSchedulingEvent.is_set():
                _ThreadBalanceEvent.set()
                self._expandThread()
                _ThreadBalanceEvent.clear()
            elif not allow_thread_expansion:
                self.Logger.warning(f"Load reaches {int(threshold)}%, but unable to expand more thread")
            else:
                pass

    def _beforehandExpand(self) -> None:
        """
        Handles the expansion of system processes and threads based on the total task count.

        This method calculates the total load for both processes and threads, considering core and
        expansion tasks. If the combined load exceeds a specific threshold (80% of the global task limit),
        it attempts to expand either processes or threads, depending on the current system state.

        :raises: None
        :return: None
        setup:
            1. Retrieve the current load for core processes and expansion processes.
            2. Calculate the total task count by combining core and expansion process loads.
            3. Retrieve the current load for core threads and expansion threads.
            4. Calculate the total thread load by combining core and expansion thread loads.
            5. If the total task and thread load exceeds 80% of the global task threshold:
                5.1. Check if process expansion is allowed, and if no process task scheduling is in progress, expand processes.
                5.2. Check if thread expansion is allowed, and if thread task scheduling is in progress, expand threads.
            6. Log warnings if expansion is not possible.

        Note:
            - `_ProcessTaskSchedulingEvent` and `_ThreadTaskSchedulingEvent` are global events that control task scheduling for processes and threads.
            - `_ProcessBalanceEvent` and `_ThreadBalanceEvent` are global events used for controlling process and thread balancing during expansion.
            - `ConfigManager.GlobalTaskThreshold` is used to define the task threshold for expansion.
            - `StatusManager` is used to track the current load status of processes and threads.
        """

        global _ProcessTaskSchedulingEvent, _ThreadTaskSchedulingEvent, _ProcessBalanceEvent, _ThreadBalanceEvent
        if self.ConfigManager.CoreProcessCount.value != 0:
            current_core_process_total_load: int = sum([self.StatusManager.getCoreProcessTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreProcessTaskStatusPool.items()])
            if self.StatusManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load: int = sum([self.StatusManager.getExpandProcessTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandProcessTaskStatusPool.items()])
            else:
                current_expand_process_total_load: int = 0
            process_total_task_count: int = current_core_process_total_load + current_expand_process_total_load
        else:
            process_total_task_count: int = 0
        current_core_thread_total_load: int = sum([self.StatusManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreThreadTaskStatusPool.items()])
        if self.StatusManager.ExpandThreadTaskStatusPool:
            current_expand_thread_total_load: int = sum([self.StatusManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandThreadTaskStatusPool.items()])
        else:
            current_expand_thread_total_load: int = 0
        thread_total_load: int = current_core_thread_total_load + current_expand_thread_total_load
        if (process_total_task_count + thread_total_load) >= self.ConfigManager.GlobalTaskThreshold.value * 0.8:
            if self._isAllowExpansion("Process") and not _ProcessTaskSchedulingEvent.is_set():
                _ProcessBalanceEvent.set()
                self._expandProcess()
                _ProcessBalanceEvent.clear()
            else:
                self.Logger.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more process")
            if self._isAllowExpansion("Thread") and _ThreadTaskSchedulingEvent.is_set():
                _ThreadBalanceEvent.set()
                self._expandThread()
                _ThreadBalanceEvent.clear()
            else:
                self.Logger.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more thread")

    def _isAllowExpansion(self, expand_type: Literal["Process", "Thread"]) -> bool:
        """
        Determines whether expansion of processes or threads is allowed based on configuration limits.

        :param expand_type: A string indicating the type of expansion to check ("Process" or "Thread").
        :return: A boolean indicating whether expansion is allowed (True) or not (False).
        setup:
            1. If the expand type is "Process":
                1.1. Check if the total number of core and expand processes exceeds the maximum allowed process count.
                1.2. Return False if the limit is exceeded; otherwise, return True.
            2. If the expand type is "Thread":
                2.1. Check if the total number of core and expand threads exceeds the maximum allowed thread count.
                2.2. Return False if the limit is exceeded; otherwise, return True.
        """

        if expand_type == "Process":
            if (len(self.StatusManager.CoreProcessTaskStatusPool) + len(self.StatusManager.ExpandProcessTaskStatusPool)) >= self.ConfigManager.MaximumProcessCount.value:
                return False
            return True
        if expand_type == "Thread":
            if (len(_CoreThreadPool) + len(_ExpandThreadPool)) >= self.ConfigManager.MaximumThreadCount.value:
                return False
            return True

    def _expandProcess(self) -> None:
        """
        Creates and starts a new expand process, updating the relevant status tracking.

        :return: None
        :raise: Raises an exception if there is an error in creating or starting the process.
        setup:
            1. Generate a unique process name using the _generateExpandID method.
            2. Create a new _ProcessObject with the generated name and associated managers.
            3. Start the new process.
            4. Add the new process to the expand process pool.
            5. Update the status manager with the new process's ID and initial load and task counts.
            6. Record the current time as the survival time for the new process.
            7. Log any errors encountered during the process creation or starting process.
        """

        global _ExpandProcessPool, _ExpandProcessSurvivalTime
        try:
            process_name: str = self._generateExpandID("Process")
            process_object = _ProcessObject(process_name, "Expand", self.StatusManager, self.ConfigManager)
            process_object.start()
            _ExpandProcessPool[process_name] = process_object
            self.StatusManager.updateExpandProcessLoadStatus(process_name, process_object.pid, 0)
            self.StatusManager.updateExpandProcessTaskStatus(process_name, process_object.pid, 0)
            _ExpandProcessSurvivalTime[process_name] = time.time()
        except Exception as e:
            self.Logger.error(f"Expand process error: {e}.")

    def _expandThread(self) -> None:
        """
        Creates and starts a new expand thread, updating the relevant status tracking.

        :return: None
        :raise: Raises an exception if there is an error in creating or starting the thread.
        setup:
            1. Generate a unique thread name using the _generateExpandID method.
            2. Create a new _ThreadObject with the generated name and associated managers.
            3. Start the new thread.
            4. Update the status manager with the new thread's ID and initial task count.
            5. Record the current time as the survival time for the new thread.
            6. Log any errors encountered during the thread creation or starting process.
        """

        global _ExpandThreadPool, _ExpandThreadSurvivalTime
        try:
            thread_name: str = self._generateExpandID("Thread")
            thread_object = _ThreadObject(thread_name, "Expand", self.StatusManager, self.ConfigManager, self.SystemExecutor)
            thread_object.start()
            _ExpandThreadPool[thread_name] = thread_object
            self.StatusManager.updateExpandThreadTaskStatus(thread_name, thread_object.ident, 0)
            _ExpandThreadSurvivalTime[thread_name] = time.time()
        except Exception as e:
            self.Logger.error(f"Expand thread error: {e}.")

    @staticmethod
    def _generateExpandID(expand_type: Literal["Process", "Thread"]) -> str:
        """
        Generates a unique ID for an expand process or thread.

        :param expand_type: A string indicating the type of ID to generate ("Process" or "Thread").
        :return: A unique ID string for the specified expand type.
        setup:
            1. Define a mapping of expand type names to their corresponding pools.
            2. Initialize a basic ID format based on the expand type.
            3. Enter an infinite loop to find a unique ID:
                1. Check if the current ID exists in the corresponding pool.
                2. If it does not exist, return the current ID.
                3. If it exists, increment the numeric part of the ID and continue the loop.
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

    def _shrinkagePolicyExecutor(self) -> None:
        """
        Executes the appropriate shrinkage policy method based on the configuration settings.

        :return: None
        setup:
            1. Define a mapping of shrinkage policy names to their corresponding methods.
            2. Retrieve the shrinkage policy method based on the current configuration setting.
            3. Call the selected shrinkage method to execute the policy.
        """

        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self.ConfigManager.ShrinkagePolicy.value]
        shrink_method()

    def _noShrink(self) -> None:
        pass

    def _autoShrink(self) -> None:
        """
        Handles the automatic shrinkage of processes and threads based on their inactivity.

        This method evaluates whether processes and threads in the system can be closed due to inactivity.
        It checks if the time since the last activity exceeds the configured shrinkage timeout. If the processes or
        threads are idle, they are stopped and removed from the system.

        :raises: None
        :return: None
        setup:
            1. Retrieve the list of all expansion processes and threads from the pool.
            2. For processes, check if they have been inactive for a time period exceeding the configured shrinkage timeout.
            3. For threads, perform similar checks for inactivity.
            4. If any process or thread is found to be inactive, stop it and remove it from the respective pool and status tracking.
            5. Ensure that process and thread balancing events are properly set and cleared.

        Note:
            - `_ExpandProcessPool` and `_ExpandThreadPool` hold the active expansion processes and threads.
            - `_ExpandProcessSurvivalTime` and `_ExpandThreadSurvivalTime` track the time since each process/thread was last active.
            - `_ProcessTaskSchedulingEvent` and `_ThreadTaskSchedulingEvent` are used to ensure that task scheduling is not occurring during shrinkage.
            - `_ProcessBalanceEvent` and `_ThreadBalanceEvent` control the balance of processes and threads during shrinking.
            - The `ShrinkagePolicyTimeout` in the `ConfigManager` defines the inactivity period after which processes and threads can be shrunk.
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime, _ProcessTaskSchedulingEvent, _ThreadTaskSchedulingEvent, _ProcessBalanceEvent, _ThreadBalanceEvent
        if self.ConfigManager.CoreProcessCount.value != 0 and not _ProcessTaskSchedulingEvent.is_set():
            _ProcessBalanceEvent.set()
            expand_process_obj: List[_ProcessObject] = [obj for i, obj in _ExpandProcessPool.items()]
            allow_close_processes: List[_ProcessObject] = [
                obj for obj in expand_process_obj
                if not obj.WorkingEvent.is_set() and (time.time() - _ExpandProcessSurvivalTime[obj.ProcessName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value
            ]
            for obj in allow_close_processes:
                obj.stop()
                del _ExpandProcessPool[obj.ProcessName]
                del self.StatusManager.ExpandProcessTaskStatusPool[obj.ProcessName]
                del self.StatusManager.ExpandProcessLoadStatusPool[obj.ProcessName]
                del _ExpandProcessSurvivalTime[obj.ProcessName]
                self.Logger.debug(f"[{obj.ProcessName} - {obj.pid}] has been closed due to idle status.")
            _ProcessBalanceEvent.clear()

        if not _ThreadTaskSchedulingEvent.is_set():
            _ThreadBalanceEvent.set()
            expand_thread_obj: List[_ThreadObject] = [obj for i, obj in _ExpandThreadPool.items()]
            allow_close_threads: List[_ThreadObject] = [
                obj for obj in expand_thread_obj
                if not obj.WorkingEvent.is_set() and (time.time() - _ExpandThreadSurvivalTime[obj.ThreadName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value
            ]
            for obj in allow_close_threads:
                obj.stop()
                del _ExpandThreadPool[obj.ThreadName]
                del self.StatusManager.ExpandThreadTaskStatusPool[obj.ThreadName]
                del _ExpandThreadSurvivalTime[obj.ThreadName]
                self.Logger.debug(f"[{obj.ThreadName} - {obj.ident}] has been closed due to idle status.")
            _ThreadBalanceEvent.clear()

    def _timeoutShrink(self) -> None:
        """
        Handles the shrinkage of processes and threads based on timeout inactivity.

        This method checks for processes and threads that have been idle for a time period exceeding the configured
        shrinkage policy timeout. If they are idle for too long, they are stopped and removed from the system.

        :raises: None
        :return: None
        setup:
            1. Check if process task scheduling is not in progress and balance the process pool.
            2. For processes, evaluate whether their survival time exceeds the configured shrinkage timeout.
            3. Similarly, evaluate thread survival time to determine if they should be shrunk.
            4. Stop any processes or threads that exceed the timeout and remove them from the respective pools and status tracking.
            5. Ensure that process and thread balancing events are set and cleared properly.

        Note:
            - `_ExpandProcessPool` and `_ExpandThreadPool` hold the active expansion processes and threads.
            - `_ExpandProcessSurvivalTime` and `_ExpandThreadSurvivalTime` track the time since each process/thread was last active.
            - `_ProcessTaskSchedulingEvent` and `_ThreadTaskSchedulingEvent` are used to ensure that task scheduling is not occurring during shrinkage.
            - `_ProcessBalanceEvent` and `_ThreadBalanceEvent` control the balance of processes and threads during shrinking.
            - The `ShrinkagePolicyTimeout` in the `ConfigManager` defines the inactivity period after which processes and threads can be shrunk.
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime, _ProcessTaskSchedulingEvent, _ThreadTaskSchedulingEvent, _ProcessBalanceEvent, _ThreadBalanceEvent
        if self.ConfigManager.CoreProcessCount.value != 0 and not _ProcessTaskSchedulingEvent.is_set():
            _ProcessBalanceEvent.set()
            expand_process_obj: List[str] = [obj for obj, survival_time in _ExpandProcessSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
            for obj in expand_process_obj:
                _ExpandProcessPool[obj].stop()
                del _ExpandProcessPool[obj]
                del self.StatusManager.ExpandProcessTaskStatusPool[obj]
                del _ExpandProcessSurvivalTime[obj]
                self.Logger.debug(f"{obj} has been closed due to timeout.")
            _ProcessBalanceEvent.clear()

        if not _ThreadTaskSchedulingEvent.is_set():
            _ThreadBalanceEvent.set()
            expand_thread_obj: List[str] = [obj for obj, survival_time in _ExpandThreadSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
            for obj in expand_thread_obj:
                _ExpandThreadPool[obj].stop()
                del _ExpandThreadPool[obj]
                del self.StatusManager.ExpandThreadTaskStatusPool[obj]
                del _ExpandThreadSurvivalTime[obj]
                self.Logger.debug(f"{obj} has been closed due to timeout.")
            _ThreadBalanceEvent.clear()


class _ProcessTaskScheduler(threading.Thread):
    """
    The class is a thread-based scheduler designed to manage and distribute tasks across a pool of core and expandable processes.

    By leveraging multiprocessing queues and event-based signals, this class coordinates task allocation, balances workload,
    and efficiently schedules tasks based on priority and availability of resources.
    It focuses on optimizing the utilization of both core and expandable processes through dynamic task distribution, workload tracking,
    and process monitoring.

    InstanceAttribute:
        StatusManager: Manages the status of processes and their tasks.
        ConfigManager: Handles configuration settings for task management.
        ProcessTaskStorageQueue: Queue for storing tasks to be scheduled for processes.
        Logger: Logger instance for recording events and errors.
        LastSelectedProcess: Keeps track of the last selected process for task assignment.
        CloseEvent: Event to signal the scheduler to stop running.
    Method:
        run: The main loop for scheduling tasks from the queue to available processes.
        stop: Signals the scheduler to stop and waits for its completion.
        _scheduler: Assigns tasks to available processes based on priority and workload.
        _checkNotFullProcess: Checks for non-full processes of a specified type.
        _checkNotWorkingProcess: Checks for non-working processes of a specified type.
        _checkMinimumLoadProcess: Finds the process with the minimum load from a given list of processes.
    """

    def __init__(self, sm: _StatusManager, cm: _ConfigManager, process_task_storage_queue: multiprocessing.Queue, logger: TheSeedCoreLogger):
        super().__init__(name='ProcessTaskScheduler', daemon=True)
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.ProcessTaskStorageQueue: multiprocessing.Queue = process_task_storage_queue
        self.Logger: TheSeedCoreLogger = logger
        self.LastSelectedProcess: Optional[_ProcessObject] = None
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        """
        Main event loop for processing tasks in the system.

        This method continuously runs and processes tasks from the `ProcessTaskStorageQueue`. It checks for tasks
        that need to be scheduled based on the priority and manages task scheduling in a controlled manner by using events
        to prevent conflicts. If there are no tasks to process, the loop waits until new tasks are available.

        :raises: None
        :return: None
        setup:
            1. Continuously checks if the `CloseEvent` is set to determine if the loop should terminate.
            2. If no tasks are present, the loop waits briefly and tries again.
            3. Uses the `_ProcessBalanceEvent` to prevent task scheduling during balancing.
            4. Retrieves task data from the `ProcessTaskStorageQueue` and schedules the task using the `_scheduler`.
            5. Clears the `_ProcessTaskSchedulingEvent` flag after the task is scheduled, allowing the next task to be processed.
            6. Logs a message when the task scheduler is closed.

        Note:
            - The `ProcessTaskStorageQueue` holds the tasks to be processed.
            - The `_scheduler` method is used to assign tasks for execution.
            - The `_ProcessTaskSchedulingEvent` controls the task scheduling process to avoid concurrent scheduling conflicts.
            - The `_ProcessBalanceEvent` is used to block task scheduling when process balancing is in progress.
        """

        while not self.CloseEvent.is_set():
            global _ProcessTaskSchedulingEvent, _ProcessBalanceEvent
            time.sleep(0.001)
            try:
                if _ProcessBalanceEvent.is_set():
                    continue
                _ProcessTaskSchedulingEvent.set()
                task_data: Tuple[int, _TaskObject] = self.ProcessTaskStorageQueue.get_nowait()
                priority, task_object = task_data
                self._scheduler(priority, task_object)
                _ProcessTaskSchedulingEvent.clear()
            except queue.Empty:
                _ProcessTaskSchedulingEvent.clear()
                continue
        self.Logger.info(f"[ProcessTaskScheduler] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def _scheduler(self, priority: int, task_object: _TaskObject) -> None:
        """
        Schedules a task to be executed by available processes based on their workload and status.

        :param priority: An integer representing the priority of the task to be scheduled.
        :param task_object: An instance of _TaskObject representing the task to be scheduled.
        :return: None
        setup:
            1. Check for non-working core processes and collect them.
            2. Check for non-full core processes and collect them.
            3. If there are non-working core processes, assign the task to one of them, update its task status, and return.
            4. If no non-working processes are available but there are non-full core processes, find the one with the minimum load, assign the task, and update its task status.
            5. If no core processes are available, check the expand process pool for non-working and non-full processes.
            6. If there are non-working expand processes, assign the task to one of them, update its task status, and return.
            7. If no non-working processes are available but there are non-full expand processes, find the one with the minimum load, assign the task, and update its task status.
            8. If no suitable processes are found in either pool, enqueue the task for later processing.
        """

        global _ExpandProcessPool
        not_working_core_processes: List[_ProcessObject] = self._checkNotWorkingProcess("Core")
        not_full_core_processes: List[_ProcessObject] = self._checkNotFullProcess("Core")

        if not_working_core_processes:
            for i in not_working_core_processes:
                i.addProcessTask(priority, task_object)
                current_status: Tuple[int, int] = self.StatusManager.getCoreProcessTaskStatus(i.ProcessName)
                pid: int = current_status[0]
                task_count: int = current_status[1]
                new_task_count: int = task_count + 1
                self.StatusManager.updateCoreProcessTaskStatus(i.ProcessName, pid, new_task_count)
                return
        if not_full_core_processes:
            minimum_load_core_process: _ProcessObject = self._checkMinimumLoadProcess(not_full_core_processes, "Core")
            minimum_load_core_process.addProcessTask(priority, task_object)
            current_status: Tuple[int, int] = self.StatusManager.getCoreProcessTaskStatus(minimum_load_core_process.ProcessName)
            pid: int = current_status[0]
            task_count: int = current_status[1]
            new_task_count: int = task_count + 1
            self.StatusManager.updateCoreProcessTaskStatus(minimum_load_core_process.ProcessName, pid, new_task_count)
            return
        if _ExpandProcessPool:
            not_working_expand_processes: List[_ProcessObject] = self._checkNotWorkingProcess("Expand")
            not_full_expand_processes: List[_ProcessObject] = self._checkNotFullProcess("Expand")
            if not_working_expand_processes:
                for i in not_working_expand_processes:
                    i.addProcessTask(priority, task_object)
                    current_status: Tuple[int, int] = self.StatusManager.getExpandProcessTaskStatus(i.ProcessName)
                    pid: int = current_status[0]
                    task_count: int = current_status[1]
                    new_task_count: int = task_count + 1
                    self.StatusManager.updateExpandProcessTaskStatus(i.ProcessName, pid, new_task_count)
                    return
            if not_full_expand_processes:
                minimum_load_expand_process: _ProcessObject = self._checkMinimumLoadProcess(not_full_expand_processes, "Expand")
                minimum_load_expand_process.addProcessTask(priority, task_object)
                current_status: Tuple[int, int] = self.StatusManager.getExpandProcessTaskStatus(minimum_load_expand_process.ProcessName)
                pid: int = current_status[0]
                task_count: int = current_status[1]
                new_task_count: int = task_count + 1
                self.StatusManager.updateExpandProcessTaskStatus(minimum_load_expand_process.ProcessName, pid, new_task_count)
                return
        self.ProcessTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNotFullProcess(self, process_type: Literal["Core", "Expand"]) -> List[_ProcessObject]:
        """
        Checks for processes that are not full based on their current task load.

        :param process_type: A string indicating the type of processes to check ("Core" or "Expand").
        :return: A list of process objects that are not full, based on their task load.
        setup:
            1. Determine the appropriate process pool based on the specified process type.
            2. Select the corresponding function to retrieve the task status for the specified process type.
            3. Iterate through the process pool and collect processes that have a task load below the defined threshold.
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool: Union[_CoreProcessPool, _ExpandProcessPool] = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        function: Union[_StatusManager.getCoreProcessTaskStatus, _StatusManager.getExpandProcessTaskStatus] = self.StatusManager.getCoreProcessTaskStatus if process_type == "Core" else self.StatusManager.getExpandProcessTaskStatus
        not_full_processes: List[_ProcessObject] = [obj for index, obj in obj_pool.items() if function(obj.ProcessName)[1] < self.ConfigManager.TaskThreshold.value]
        return not_full_processes

    @staticmethod
    def _checkNotWorkingProcess(process_type: Literal["Core", "Expand"]) -> List[_ProcessObject]:
        """
        Checks for non-working processes in the specified process pool.

        :param process_type: A string indicating the type of processes to check ("Core" or "Expand").
        :return: A list of process objects that are not currently working.
        setup:
            1. Determine the appropriate process pool based on the specified process type.
            2. Iterate through the process pool and collect processes that are not working by checking the WorkingEvent status.
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool: Union[_CoreProcessPool, _ExpandProcessPool] = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        not_working_processes: List[_ProcessObject] = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_processes

    def _checkMinimumLoadProcess(self, processes: List[_ProcessObject], process_type: Literal["Core", "Expand"]) -> _ProcessObject:
        """
        Checks for the minimum load among the provided processes and selects one for processing.

        :param processes: A list of process objects to evaluate.
        :param process_type: A string indicating the type of processes ("Core" or "Expand").
        :return: The selected process object with the minimum load.
        :raise: Raises an exception if no processes are available for selection.
        setup:
            1. Determine the appropriate function for retrieving process task load status based on the process type.
            2. Create a list of available processes, excluding the last selected process if applicable.
            3. If there are no available processes, select the first process from the original list.
            4. Otherwise, select the process with the minimum load using the determined status function.
            5. Update the last selected process to the newly selected process.
        """

        function: Union[_StatusManager.getCoreProcessTaskStatus, _StatusManager.getExpandProcessTaskStatus] = self.StatusManager.getCoreProcessLoadStatus if process_type == "Core" else self.StatusManager.getExpandProcessLoadStatus
        available_processes: List[_ProcessObject] = [p for p in processes if p != self.LastSelectedProcess] if self.LastSelectedProcess is not None else processes
        if not available_processes:
            selected_process: _ProcessObject = processes[0]
        else:
            selected_process: _ProcessObject = min(available_processes, key=lambda x: function(x.ProcessName)[1])
        self.LastSelectedProcess: _ProcessObject = selected_process
        return selected_process


class _ThreadTaskScheduler(threading.Thread):
    """
    This class is a specialized threading-based scheduler that manages and coordinates task execution across a pool of core and expand threads.

    It continuously monitors a task queue, evaluates thread availability, and allocates tasks based on thread load and status.
    The scheduler uses a combination of priority-based task management, thread balancing,
    and workload distribution strategies to maximize the efficiency of task execution across a dynamically managed pool of threads.

    InstanceAttribute:
        StatusManager: Manages the status of threads and their tasks.
        ConfigManager: Handles configuration settings for task management.
        ThreadTaskStorageQueue: Queue for storing tasks to be scheduled.
        Logger: Logger instance for recording events and errors.
        LastSelectedThread: Keeps track of the last selected thread for task assignment.
        CloseEvent: Event to signal the scheduler to stop running.
    Method:
        run: The main loop for scheduling tasks from the queue to available threads.
        stop: Signals the scheduler to stop and waits for its completion.
        _scheduler: Assigns tasks to available threads based on priority and workload.
        _checkNonFullThread: Checks for non-full threads of a specified type.
        _checkNonWorkingThread: Checks for non-working threads of a specified type.
        _checkMinimumLoadThread: Finds the thread with the minimum load from a given list of threads.
    """

    def __init__(self, sm: _StatusManager, cm: _ConfigManager, thread_task_storage_queue: queue.Queue, logger: TheSeedCoreLogger):
        super().__init__(name='ThreadTaskScheduler', daemon=True)
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.ThreadTaskStorageQueue: queue.Queue = thread_task_storage_queue
        self.Logger: TheSeedCoreLogger = logger
        self.LastSelectedThread: Optional[_ThreadObject] = None
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        """
        Main event loop for processing thread tasks in the system.

        This method continuously runs and processes thread tasks from the `ThreadTaskStorageQueue`. It ensures that
        tasks are scheduled in an orderly manner by using events to manage the task scheduling and prevent conflicts.
        If no tasks are available, the loop waits briefly before checking again.

        :raises: None
        :return: None
        setup:
            1. Continuously checks if the `CloseEvent` is set to determine if the loop should terminate.
            2. If no tasks are present, the loop waits briefly and retries.
            3. Uses the `_ThreadBalanceEvent` to prevent task scheduling during thread balancing.
            4. Retrieves task data from the `ThreadTaskStorageQueue` and schedules the task using the `_scheduler`.
            5. Clears the `_ThreadTaskSchedulingEvent` flag after scheduling a task, allowing the next task to be processed.
            6. Logs a message when the thread task scheduler is closed.

        Note:
            - The `ThreadTaskStorageQueue` holds the thread tasks to be processed.
            - The `_scheduler` method is used to assign tasks for execution.
            - The `_ThreadTaskSchedulingEvent` controls the task scheduling to avoid concurrent scheduling conflicts.
            - The `_ThreadBalanceEvent` is used to block task scheduling when thread balancing is in progress.
        """

        while not self.CloseEvent.is_set():
            global _ThreadTaskSchedulingEvent, _ThreadBalanceEvent
            time.sleep(0.001)
            try:
                if _ThreadBalanceEvent.is_set():
                    continue
                _ThreadTaskSchedulingEvent.set()
                task_data: Tuple[int, _TaskObject] = self.ThreadTaskStorageQueue.get_nowait()
                priority, task_object = task_data
                self._scheduler(priority, task_object)
                _ThreadTaskSchedulingEvent.clear()
            except queue.Empty:
                _ThreadTaskSchedulingEvent.clear()
                continue
        self.Logger.info(f"[ThreadTaskScheduler] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def _scheduler(self, priority: int, task_object: _TaskObject) -> None:
        """
        Schedules a task to be executed by available threads based on their workload and status.

        :param priority: An integer representing the priority of the task to be scheduled.
        :param task_object: An instance of _TaskObject representing the task to be scheduled.
        :return: None
        setup:
            1. Check for non-working core threads and collect them.
            2. Check for non-full core threads and collect them.
            3. If there are non-working core threads, assign the task to one of them, update its task status, and return.
            4. If no non-working threads are available but there are non-full core threads, find the one with the minimum load, assign the task, and update its task status.
            5. If no core threads are available, check the expand thread pool for non-working and non-full threads.
            6. If there are non-working expand threads, assign the task to one of them, update its task status, and return.
            7. If no non-working threads are available but there are non-full expand threads, find the one with the minimum load, assign the task, and update its task status.
            8. If no suitable threads are found in either pool, enqueue the task for later processing.
        """

        global _ExpandThreadPool
        not_working_core_threads: List[_ThreadObject] = self._checkNonWorkingThread("Core")
        not_full_core_threads: List[_ThreadObject] = self._checkNonFullThread("Core")

        if not_working_core_threads:
            for i in not_working_core_threads:
                i.addThreadTask(priority, task_object)
                current_status: Tuple[int, int] = self.StatusManager.getCoreThreadTaskStatus(i.ThreadName)
                tid: int = current_status[0]
                task_count: int = current_status[1]
                new_task_count: int = task_count + 1
                self.StatusManager.updateCoreThreadTaskStatus(i.ThreadName, tid, new_task_count)
                return
        if not_full_core_threads:
            minimum_load_core_process: _ThreadObject = self._checkMinimumLoadThread(not_full_core_threads, "Core")
            minimum_load_core_process.addThreadTask(priority, task_object)
            current_status: Tuple[int, int] = self.StatusManager.getCoreThreadTaskStatus(minimum_load_core_process.ThreadName)
            tid: int = current_status[0]
            task_count: int = current_status[1]
            new_task_count: int = task_count + 1
            self.StatusManager.updateCoreThreadTaskStatus(minimum_load_core_process.ThreadName, tid, new_task_count)
            return
        if _ExpandThreadPool:
            not_working_expand_threads: List[_ThreadObject] = self._checkNonWorkingThread("Expand")
            not_full_expand_threads: List[_ThreadObject] = self._checkNonFullThread("Expand")
            if not_working_expand_threads:
                for i in not_working_expand_threads:
                    i.addThreadTask(priority, task_object)
                    current_status: Tuple[int, int] = self.StatusManager.getExpandThreadTaskStatus(i.ThreadName)
                    tid: int = current_status[0]
                    task_count: int = current_status[1]
                    new_task_count: int = task_count + 1
                    self.StatusManager.updateExpandThreadTaskStatus(i.ThreadName, tid, new_task_count)
                    return
            if not_full_expand_threads:
                minimum_load_expand_process: _ThreadObject = self._checkMinimumLoadThread(not_full_expand_threads, "Expand")
                minimum_load_expand_process.addThreadTask(priority, task_object)
                current_status: Tuple[int, int] = self.StatusManager.getExpandThreadTaskStatus(minimum_load_expand_process.ThreadName)
                tid: int = current_status[0]
                task_count: int = current_status[1]
                new_task_count: int = task_count + 1
                self.StatusManager.updateExpandThreadTaskStatus(minimum_load_expand_process.ThreadName, tid, new_task_count)
                return
        self.ThreadTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNonFullThread(self, thread_type: Literal["Core", "Expand"]) -> List[_ThreadObject]:
        """
        Checks for threads that are not full based on their current task load.

        :param thread_type: A string indicating the type of threads to check ("Core" or "Expand").
        :return: A list of thread objects that are not full, based on their task load.
        setup:
            1. Determine the appropriate thread pool based on the specified thread type.
            2. Select the corresponding function to retrieve the task status for the specified thread type.
            3. Iterate through the thread pool and collect threads that have a task load below the defined threshold.
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool: Union[_CoreThreadPool, _ExpandThreadPool] = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        function: Union[_StatusManager.getCoreThreadTaskStatus, _StatusManager.getExpandThreadTaskStatus] = self.StatusManager.getCoreThreadTaskStatus if thread_type == "Core" else self.StatusManager.getExpandThreadTaskStatus
        not_full_threads: List[_ThreadObject] = [obj for index, obj in obj_pool.items() if function(obj.ThreadName)[1] < self.ConfigManager.TaskThreshold.value]
        return not_full_threads

    @staticmethod
    def _checkNonWorkingThread(thread_type: Literal["Core", "Expand"]) -> List[_ThreadObject]:
        """
        Checks for non-working threads in the specified thread pool.

        :param thread_type: A string indicating the type of threads to check ("Core" or "Expand").
        :return: A list of thread objects that are not currently working.
        setup:
            1. Determine the appropriate thread pool based on the specified thread type.
            2. Iterate through the thread pool and collect threads that are not working by checking the WorkingEvent status.
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool: Union[_CoreThreadPool, _ExpandThreadPool] = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        not_working_threads: List[_ThreadObject] = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_threads

    def _checkMinimumLoadThread(self, threads: List[_ThreadObject], thread_type: Literal["Core", "Expand"]) -> _ThreadObject:
        """
        Checks for the minimum load among the provided threads and selects one for processing.

        :param threads: A list of thread objects to evaluate.
        :param thread_type: A string indicating the type of threads ("Core" or "Expand").
        :return: The selected thread object with the minimum load.
        :raise: Raises an exception if no threads are available for selection.
        setup:
            1. Determine the appropriate function for retrieving thread task status based on the thread type.
            2. Create a list of available threads, excluding the last selected thread if applicable.
            3. If there are no available threads, select the first thread from the original list.
            4. Otherwise, select the thread with the minimum load using the determined status function.
            5. Update the last selected thread to the newly selected thread.
        """

        function: Union[_StatusManager.getCoreThreadTaskStatus, _StatusManager.getExpandThreadTaskStatus] = self.StatusManager.getCoreThreadTaskStatus if thread_type == "Core" else self.StatusManager.getExpandThreadTaskStatus
        available_threads: List[_ThreadObject] = [t for t in threads if t != self.LastSelectedThread] if self.LastSelectedThread is not None else threads
        if not available_threads:
            selected_thread: _ThreadObject = threads[0]
        else:
            selected_thread: _ThreadObject = min(available_threads, key=lambda x: function(x.ThreadName)[1])
        self.LastSelectedThread: _ThreadObject = selected_thread
        return selected_thread


class _ConcurrentSystem:
    """
    Concurrent system main class

    Attribute:
        INSTANCE: Singleton instance of the _ConcurrentSystem class.
        _INITIALIZED: A boolean indicating if the system has been initialized.
    InstanceAttribute:
        StatusManager: Manages the status of core processes and threads.
        ConfigManager: Handles configuration settings for the system.
        MainEventLoop: The main event loop for asynchronous operations.
        ProcessTaskStorageQueue: Queue for storing process tasks.
        ThreadTaskStorageQueue: Queue for storing thread tasks.
        Logger: Logger instance for system events and errors.
        SystemThreadPoolExecutor: Thread pool executor for managing thread execution.
        SystemProcessPoolExecutor: Process pool executor for managing process execution (if applicable).
        LoadBalancer: Load balancer for distributing tasks among available resources.
        ProcessTaskScheduler: Scheduler for managing process tasks.
        ThreadTaskScheduler: Scheduler for managing thread tasks.
        CallbackExecutor: Executor for handling callbacks in the event loop.
    Method:
        _initSystem: Initializes the concurrent system, starting processes and threads.
        _setMainProcessPriority: Sets the priority of the main process based on configuration.
        _startCoreProcess: Starts a core process and registers it in the process pool.
        _startCoreThread: Starts a core thread and registers it in the thread pool.
    """

    INSTANCE: _ConcurrentSystem = None
    _INITIALIZED: bool = False

    def __new__(cls, sm: _StatusManager, cm: _ConfigManager, main_event_loop: asyncio.AbstractEventLoop):
        if cls.INSTANCE is None:
            cls.INSTANCE = super(_ConcurrentSystem, cls).__new__(cls)
        return cls.INSTANCE

    def __init__(self, sm: _StatusManager, cm: _ConfigManager, main_event_loop: asyncio.AbstractEventLoop):
        if _ConcurrentSystem._INITIALIZED:
            return
        self.StatusManager: _StatusManager = sm
        self.ConfigManager: _ConfigManager = cm
        self.MainEventLoop: asyncio.AbstractEventLoop = main_event_loop
        self.ProcessTaskStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.ThreadTaskStorageQueue: queue.Queue = queue.Queue()
        self.Logger: TheSeedCoreLogger = TheSeedCoreLogger("Concurrent")
        self.SystemThreadPoolExecutor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.ConfigManager.CoreProcessCount.value + self.ConfigManager.CoreThreadCount.value)
        if self.ConfigManager.CoreProcessCount.value != 0:
            self.SystemProcessPoolExecutor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=self.ConfigManager.CoreProcessCount.value)
        self.LoadBalancer: _LoadBalancer = _LoadBalancer(self.StatusManager, self.ConfigManager, self.Logger, self.SystemThreadPoolExecutor)
        self.ProcessTaskScheduler: _ProcessTaskScheduler = _ProcessTaskScheduler(self.StatusManager, self.ConfigManager, self.ProcessTaskStorageQueue, self.Logger)
        self.ThreadTaskScheduler: _ThreadTaskScheduler = _ThreadTaskScheduler(self.StatusManager, self.ConfigManager, self.ThreadTaskStorageQueue, self.Logger)
        self.CallbackExecutor: _CallbackExecutor = _CallbackExecutor(sm, main_event_loop)
        _ConcurrentSystem._INITIALIZED = True
        self._initSystem()

    def _initSystem(self) -> None:
        """
        Initializes the concurrent system by starting core processes and threads based on configuration settings.

        :return: None
        :raise: Raises an exception if there is an error starting the processes or threads.
        setup:
            1. Check the system type; if it's Windows, set the main process priority.
            2. Create a list to hold futures for the processes and threads being started.
            3. Submit tasks to start the specified number of core processes and store the futures.
            4. Submit tasks to start the specified number of core threads and store the futures.
            5. Wait for all submitted futures to complete, ensuring all processes and threads are started.
            6. Start the load balancer.
            7. If the core process count is not zero, start the process task scheduler.
            8. Start the thread task scheduler.
            9. Start the callback executor.
        """

        global _CoreProcessPool, _CoreThreadPool
        if _SystemType == "Windows":
            self._setMainProcessPriority()
        futures: List[Future] = []
        for i in range(self.ConfigManager.CoreProcessCount.value):
            process_name = f"Process-{i}"
            future: Future = self.SystemThreadPoolExecutor.submit(self._startCoreProcess, process_name)
            futures.append(future)
        for i in range(self.ConfigManager.CoreThreadCount.value):
            thread_name = f"Thread-{i}"
            future: Future = self.SystemThreadPoolExecutor.submit(self._startCoreThread, thread_name)
            futures.append(future)
        for future in futures:
            future.result()
        self.LoadBalancer.start()
        if self.ConfigManager.CoreProcessCount.value != 0:
            self.ProcessTaskScheduler.start()
        self.ThreadTaskScheduler.start()
        self.CallbackExecutor.startExecutor()

    def _setMainProcessPriority(self) -> None:
        """
        Sets the priority of the main process based on the configured process priority.

        :return: None
        :raise: Raises a ValueError if unable to obtain a valid process handle or if the priority cannot be set.
        :raise: Raises an Exception if setting the priority fails with an error code.
        setup:
            1. Define a mapping of process priority names to their corresponding values.
            2. Attempt to open the current process using its process ID.
            3. If the handle is invalid, raise a ValueError.
            4. Set the process priority using the priority mapping based on the configuration.
            5. If setting the priority fails, retrieve and raise an exception with the error code.
            6. Ensure the process handle is closed in the finally block.
        """

        priority_mapping: Dict[str, int] = {
            "IDLE": 0x00000040,
            "BELOW_NORMAL": 0x00004000,
            "NORMAL": 0x00000020,
            "ABOVE_NORMAL": 0x00008000,
            "HIGH": 0x00000080,
            "REALTIME": 0x00000100
        }
        handle = None
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, os.getpid())
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
            result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping.get(self.ConfigManager.ProcessPriority, priority_mapping["NORMAL"]))
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"Set priority failed with error code {error_code}.")
        except Exception as e:
            self.Logger.error(f"[MainProcess - {os.getpid()}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _startCoreProcess(self, process_name: str) -> _ProcessObject:
        """
        Starts a core process and registers it in the core process pool.

        :param process_name: The name of the process to be started.
        :return: An instance of _ProcessObject representing the started process.
        :raise: Raises an exception if the process cannot be started.
        setup:
            1. Create a new _ProcessObject with the provided process name and associated managers.
            2. Start the process.
            3. Register the process object in the global core process pool.
            4. Update the load status of the core process in the status manager.
            5. Update the task status of the core process in the status manager.
        """

        global _CoreProcessPool
        process_object: _ProcessObject = _ProcessObject(process_name, "Core", self.StatusManager, self.ConfigManager)
        process_object.start()
        _CoreProcessPool[process_name] = process_object
        self.StatusManager.updateCoreProcessLoadStatus(process_name, process_object.pid, 0)
        self.StatusManager.updateCoreProcessTaskStatus(process_name, process_object.pid, 0)
        return process_object

    def _startCoreThread(self, thread_name: str) -> _ThreadObject:
        """
        Starts a core thread and registers it in the core thread pool.

        :param thread_name: The name of the thread to be started.
        :return: An instance of _ThreadObject representing the started thread.
        :raise: Raises an exception if the thread cannot be started.
        setup:
            1. Create a new _ThreadObject with the provided thread name and associated managers.
            2. Start the thread.
            3. Register the thread object in the global core thread pool.
            4. Update the status of the core thread task in the status manager.
        """

        global _CoreThreadPool
        thread_object: _ThreadObject = _ThreadObject(thread_name, "Core", self.StatusManager, self.ConfigManager, self.SystemThreadPoolExecutor)
        thread_object.start()
        _CoreThreadPool[thread_name] = thread_object
        self.StatusManager.updateCoreThreadTaskStatus(thread_name, thread_object.ident, 0)
        return thread_object


def _ConnectConcurrentSystem(main_event_loop: asyncio.AbstractEventLoop, **config: Unpack[_Config]) -> _ConcurrentSystem:
    """
    Establishes a concurrent system with the provided event loop and configuration.

    :param main_event_loop: The main event loop for handling asynchronous operations.
    :param config: A variable length keyword argument dictionary containing configuration settings.
    :return: An instance of _ConcurrentSystem that is configured with the provided managers and event loop.
    :raise: Raises exceptions related to the configuration or manager initialization failures.
    setup:
        1. Create a shared object manager for inter-process communication.
        2. Initialize a status manager using the shared object manager.
        3. Create a configuration manager with the provided configuration settings.
        4. Instantiate the concurrent system using the status manager, configuration manager, and main event loop.
    """
    _shared_object_manager = multiprocessing.Manager()
    _status_manager = _StatusManager(_shared_object_manager)
    _config_manager = _ConfigManager(_shared_object_manager, **config)
    _concurrent_system = _ConcurrentSystem(_status_manager, _config_manager, main_event_loop)
    return _concurrent_system


def serviceProcessID() -> int:
    """
    Retrieves the process ID of the service.

    :return: The process ID as an integer.
    :raise: Raises a RuntimeError if the ConcurrentSystem has not been initialized.
    setup:
        1. Check if the _ConcurrentSystem instance is initialized.
        2. If not initialized, raise a RuntimeError with an appropriate message.
        3. If initialized, return the SharedObjectManagerID from the StatusManager.
    """

    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
    return _ConcurrentSystem.INSTANCE.StatusManager.SharedObjectManagerID


def submitAsyncTask(task: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs) -> asyncio.Future:
    """
    Submits an asynchronous task to the main event loop.

    This function allows scheduling a coroutine task for execution in the main event loop. It ensures the provided
    task is a coroutine function before submitting it.

    :param task: The coroutine function to execute asynchronously.
    :param args: Positional arguments to pass to the task function.
    :param kwargs: Keyword arguments to pass to the task function.
    :return: An asyncio `Future` object representing the scheduled coroutine task.
    :raises TypeError: If the provided task is not a coroutine function.
    setup:
        1. Imports the `MainEventLoop` function to access the primary event loop.
        2. Checks if the provided `task` is a coroutine function.
        3. Schedules the task on the main event loop and returns it as a `Future` object.
    """

    from . import MainEventLoop
    if not asyncio.iscoroutinefunction(task):
        raise TypeError(f"The task <{task.__name__}> must be a coroutine function.")
    task_future = MainEventLoop().create_task(task(*args, **kwargs))
    return task_future


def submitProcessTask(task: callable, priority: int = 0, callback: Optional[callable] = None, future: Optional[type(TaskFuture)] = None, *args, **kwargs: Unpack[_TaskConfig]) -> TaskFuture:
    """
    Submits a task for processing with an optional priority and callback.

    :param task: The callable task to be executed.
    :param priority: An integer representing the task's priority (default is 0).
    :param callback: An optional callable to be executed after the task completes.
    :param future: An optional future instance to track the task's execution.
    :param args: Additional positional arguments to pass to the task.
    :param kwargs: Additional keyword arguments to pass to the task configuration.
    :return: A TaskFuture instance associated with the submitted task.
    :raise: Raises a RuntimeError if the task submission is attempted outside the main process,
            if the ConcurrentSystem is not initialized, or if the core process count is zero.
    setup:
        1. Check if the current process is the main process; raise an error if not.
        2. Verify that the _ConcurrentSystem is initialized; raise an error if it is not.
        3. Ensure that the core process count is greater than zero; raise an error if it is zero.
        4. Generate a unique task ID.
        5. Attempt to serialize the task; log an error and return if serialization fails.
        6. Store the callback if provided.
        7. Create a task object with the provided parameters and put it in the processing queue.
    """

    global _CallbackObject, _CoreProcessPool, _ExpandProcessPool
    if multiprocessing.current_process().name != 'MainProcess':
        raise RuntimeError("Process task submission must be done in the main process.")
    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount.value == 0:
        raise RuntimeError("Core process count is set to 0. Process task submission is not allowed.")
    task_id: str = f"{uuid.uuid4()}"
    future_instance: TaskFuture = future() if future is not None else TaskFuture()
    future_instance.taskID = task_id
    try:
        pickle.dumps(task)
    except (pickle.PicklingError, AttributeError, TypeError) as e:
        _ConcurrentSystem.INSTANCE.Logger.error(f"Task [{task.__name__} - {task_id}] serialization failed. Task submission has been rejected.\n{e}")
        return future_instance
    if callback is not None:
        _CallbackObject[task_id] = callback
    task_object: _TaskObject = _TaskObject(task, task_id, False if callback is None else True, *args, **kwargs)
    _ConcurrentSystem.INSTANCE.ProcessTaskStorageQueue.put_nowait((priority if not priority > 10 else 10, task_object))
    return future_instance


def submitThreadTask(task: callable, priority: int = 0, callback: callable = None, future: type(TaskFuture) = None, *args, **kwargs: Unpack[_TaskConfig]) -> TaskFuture:
    """
    Submits a task for execution in a thread with an optional priority and callback.

    :param task: The callable task to be executed in a thread.
    :param priority: An integer representing the task's priority (default is 0).
    :param callback: An optional callable to be executed after the task completes.
    :param future: An optional future instance to track the task's execution.
    :param args: Additional positional arguments to pass to the task.
    :param kwargs: Additional keyword arguments to pass to the task configuration.
    :return: A TaskFuture instance associated with the submitted task.
    :raise: Raises a RuntimeError if the task submission is attempted outside the main process or if the ConcurrentSystem is not initialized.
    setup:
        1. Check if the current process is the main process; raise an error if not.
        2. Verify that the _ConcurrentSystem is initialized; raise an error if it is not.
        3. Generate a unique task ID.
        4. Store the callback if provided.
        5. Create a task object with the provided parameters and put it in the thread processing queue.
    """

    global _CallbackObject
    if multiprocessing.current_process().name != 'MainProcess':
        raise RuntimeError("Thread task submission must be done in the main process.")
    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
    task_id: str = f"{uuid.uuid4()}"
    future_instance: TaskFuture = future() if future is not None else TaskFuture()
    future_instance.taskID = task_id
    if callback is not None:
        _CallbackObject[task_id] = callback
    task_object: _TaskObject = _TaskObject(task, task_id, False if callback is None else True, *args, **kwargs)
    _ConcurrentSystem.INSTANCE.ThreadTaskStorageQueue.put_nowait((priority if not priority > 10 else 5, task_object))
    return future_instance


def submitSystemProcessTask(task: callable, count: int = 1, *args, **kwargs) -> Union[Future, List[Future]]:
    """
    Submits a task for execution in the system process pool with an optional count of instances.

    :param task: The callable task to be executed.
    :param count: An integer representing the number of instances to submit (default is 1).
    :param args: Additional positional arguments to pass to the task.
    :param kwargs: Additional keyword arguments to pass to the task configuration.
    :return: A Future object if count is 1; a list of Future objects if count is greater than 1.
    :raise: Raises a RuntimeError if the ConcurrentSystem is not initialized or if the core process count is zero.
    :raise: Raises a ValueError if the provided task is not callable.
    setup:
        1. Verify that the _ConcurrentSystem is initialized; raise an error if it is not.
        2. Check if the task is callable; raise a ValueError if not.
        3. Ensure that the core process count is greater than zero; raise an error if it is zero.
        4. Submit the specified number of task instances to the system process pool and collect the futures.
    """

    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("The ConcurrentSystem has not been initialized.")
    if not callable(task):
        raise ValueError("The task must be a callable.")
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount.value == 0:
        raise RuntimeError("Core process count is set to 0. Process task submission is not allowed.")
    futures: List[Future] = []
    if count > 1:
        for i in range(count):
            future: Future = _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.submit(task, *args, **kwargs)
            futures.append(future)
        return futures
    future: Future = _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.submit(task, *args, **kwargs)
    return future


def submitSystemThreadTask(task: callable, count: int = 1, *args, **kwargs) -> Union[Future, List[Future]]:
    """
    Submits a task for execution in the system thread pool with an optional count of instances.

    :param task: The callable task to be executed.
    :param count: An integer representing the number of instances to submit (default is 1).
    :param args: Additional positional arguments to pass to the task.
    :param kwargs: Additional keyword arguments to pass to the task configuration.
    :return: A Future object if count is 1; a list of Future objects if count is greater than 1.
    :raise: Raises a RuntimeError if the ConcurrentSystem is not initialized.
    :raise: Raises a ValueError if the provided task is not callable.
    setup:
        1. Verify that the _ConcurrentSystem is initialized; raise an error if it is not.
        2. Check if the task is callable; raise a ValueError if not.
        3. Submit the specified number of task instances to the system thread pool and collect the futures.
    """

    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("The ConcurrentSystem has not been initialized.")
    if not callable(task):
        raise ValueError("The task must be a callable.")
    futures: List[Future] = []
    if count > 1:
        for i in range(count):
            future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(task, *args, **kwargs)
            futures.append(future)
        return futures
    future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(task, *args, **kwargs)
    return future


def closeConcurrentSystem() -> None:
    """
    Closes the concurrent system, stopping all running processes and threads.

    :return: None
    :raise: Raises a RuntimeError if the system closing is attempted outside the main process or if the ConcurrentSystem is not initialized.
    setup:
        1. Verify that the current process is the main process; raise an error if not.
        2. Check if the _ConcurrentSystem is initialized; raise an error if it is not.
        3. Submit stop tasks for all processes in the core process pool and collect the futures.
        4. Submit stop tasks for all threads in the core thread pool and collect the futures.
        5. Submit stop tasks for all processes in the expand process pool and collect the futures.
        6. Submit stop tasks for all threads in the expand thread pool and collect the futures.
        7. Wait for all submitted stop tasks to complete.
        8. Stop the load balancer.
        9. If the core process count is not zero, stop the process task scheduler.
        10. Stop the thread task scheduler.
        11. Close the callback executor.
        12. Shutdown the system thread pool executor.
        13. If the core process count is not zero, shutdown the system process pool executor.
    """

    global _CoreProcessPool, _CoreThreadPool, _ExpandProcessPool, _ExpandThreadPool
    if multiprocessing.current_process().name != 'MainProcess':
        raise RuntimeError("System closing must be done in the main process.")
    if _ConcurrentSystem.INSTANCE is None:
        raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
    futures: List[Future] = []
    for process_name, process_obj in _CoreProcessPool.items():
        future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(process_obj.stop)
        futures.append(future)
    for thread_name, thread_obj in _CoreThreadPool.items():
        future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(thread_obj.stop)
        futures.append(future)
    for process_name, process_obj in _ExpandProcessPool.items():
        future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(process_obj.stop)
        futures.append(future)
    for thread_name, thread_obj in _ExpandThreadPool.items():
        future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(thread_obj.stop)
        futures.append(future)
    for future in futures:
        future.result()
    _ConcurrentSystem.INSTANCE.LoadBalancer.stop()
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount.value != 0:
        _ConcurrentSystem.INSTANCE.ProcessTaskScheduler.stop()
    _ConcurrentSystem.INSTANCE.ThreadTaskScheduler.stop()
    _ConcurrentSystem.INSTANCE.CallbackExecutor.closeExecutor()
    _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.shutdown(wait=True, cancel_futures=True)
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount.value != 0:
        _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.shutdown(wait=True, cancel_futures=True)
