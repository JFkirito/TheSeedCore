# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import ctypes
import multiprocessing
import os
import pickle
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError, ProcessPoolExecutor
from enum import Enum
from typing import TYPE_CHECKING, TypedDict, Literal, Optional, Dict, Any, Unpack, List, Tuple, Union, Callable, Coroutine

from .Logger import consoleLogger
from ._Common import SYSTEM_TYPE, TextColor, PerformanceMonitor

if TYPE_CHECKING:
    pass

__all__ = [
    "submitAsyncTask",
    "submitProcessTask",
    "submitThreadTask",
    "submitSystemProcessTask",
    "submitSystemThreadTask",
    "ProcessPriority",
    "ExpandPolicy",
    "ShrinkagePolicy",
    "TaskFuture",
]

_DEFAULT_LOGGER = consoleLogger("Concurrent")

if multiprocessing.current_process().name == "MainProcess":
    _CALLBACK_FUNCTION = {}
    _FUTURE_RESULT = {}
    _CORE_PROCESS_POOL = {}
    _EXPAND_PROCESS_POOL = {}
    _EXPAND_PROCESS_SURVIVAL_TIME = {}
    _CORE_THREAD_POOL = {}
    _EXPAND_THREAD_POOL = {}
    _EXPAND_THREAD_SURVIVAL_TIME = {}
    _PROCESS_TASK_SCHEDULING_EVENT: threading.Event = threading.Event()
    _THREAD_TASK_SCHEDULING_EVENT: threading.Event = threading.Event()
    _PROCESS_BALANCE_EVENT: threading.Event = threading.Event()
    _THREAD_BALANCE_EVENT: threading.Event = threading.Event()
    _RESOURCES_MONITOR = PerformanceMonitor()
    _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT = threading.Condition()
    _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT = threading.Condition()


class ProcessPriority(str, Enum):
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
    def __init__(self, task_id: str):
        self._TaskID: Optional[str] = task_id

    @property
    def taskID(self):
        return self._TaskID

    async def result(self, timeout: Optional[int] = None):
        global _FUTURE_RESULT
        _start_time = time.time()
        while True:
            await asyncio.sleep(0)
            if self._TaskID in _FUTURE_RESULT:
                task_result: Any = _FUTURE_RESULT[self._TaskID]
                del _FUTURE_RESULT[self._TaskID]
                return task_result
            if timeout is None:
                continue
            if time.time() - _start_time >= timeout:
                raise TimeoutError("Task execution timed out.")


class _Config(TypedDict, total=False):
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


class _TaskConfig(TypedDict, total=False):
    lock: bool
    lock_timeout: int
    timeout: Optional[int]
    retry: bool
    max_retries: int


class _StatusManager:
    def __init__(self, shared_manager: Optional[multiprocessing.Manager] = None):
        # noinspection PyProtectedMember
        self.SharedManagerID = shared_manager._process.pid if shared_manager is not None else 0
        self.CoreProcessTaskStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.ExpandProcessTaskStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.CoreProcessLoadStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.ExpandProcessLoadStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.CoreThreadTaskStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.ExpandThreadTaskStatusPool: Dict[str, Tuple[int, int]] = shared_manager.dict() if shared_manager is not None else {}
        self.ResultStorageQueue = multiprocessing.Queue()
        self.TaskLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ProcessTaskLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ProcessLoadLock: multiprocessing.Lock = multiprocessing.Lock()
        self._ThreadLock: multiprocessing.Lock = multiprocessing.Lock()

    def getCoreProcessTaskStatus(self, name: str) -> Tuple[int, int]:
        self._ProcessTaskLock.acquire()
        status = self.CoreProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getExpandProcessTaskStatus(self, name: str) -> Tuple[int, int]:
        self._ProcessTaskLock.acquire()
        status = self.ExpandProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getCoreProcessLoadStatus(self, name: str) -> Tuple[int, int]:
        self._ProcessLoadLock.acquire()
        status = self.CoreProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getExpandProcessLoadStatus(self, name: str) -> Tuple[int, int]:
        self._ProcessLoadLock.acquire()
        status = self.ExpandProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getCoreThreadTaskStatus(self, name: str) -> Tuple[int, int]:
        status = self.CoreThreadTaskStatusPool[name]
        return status

    def getExpandThreadTaskStatus(self, name: str) -> Tuple[int, int]:
        status = self.ExpandThreadTaskStatusPool[name]
        return status

    def updateCoreProcessTaskStatus(self, name: str, pid: int, task_count: int) -> None:
        self.CoreProcessTaskStatusPool[name] = (pid, task_count)

    def updateExpandProcessTaskStatus(self, name: str, pid: int, task_count: int) -> None:
        self.ExpandProcessTaskStatusPool[name] = (pid, task_count)

    def updateCoreProcessLoadStatus(self, name: str, pid: int, load: int) -> None:
        self.CoreProcessLoadStatusPool[name] = (pid, load)

    def updateExpandProcessLoadStatus(self, name: str, pid: int, load: int) -> None:
        self.ExpandProcessLoadStatusPool[name] = (pid, load)

    def updateCoreThreadTaskStatus(self, name: str, tid: int, task_count: int) -> None:
        self.CoreThreadTaskStatusPool[name] = (tid, task_count)

    def updateExpandThreadTaskStatus(self, name: str, tid: int, task_count: int) -> None:
        self.ExpandThreadTaskStatusPool[name] = (tid, task_count)


class _ConfigManager:
    def __init__(self, shared_manager: Optional[multiprocessing.Manager] = None, **config: Unpack[_Config]):
        self.PhysicalCores: int = _RESOURCES_MONITOR.physicalCpuCores()
        self._MultiProcess = False if shared_manager is None else True
        self._MainProcessPriority = self._validateMainProcessPriority(shared_manager, config.get("MainProcessPriority", ProcessPriority.NORMAL))
        self._CoreProcessCount = self._validateCoreProcessCount(shared_manager, config.get("CoreProcessCount", None))
        self._CoreThreadCount = self._validateCoreThreadCount(shared_manager, config.get("CoreThreadCount", None))
        self._MaximumProcessCount = self._validateMaximumProcessCount(shared_manager, config.get("MaximumProcessCount", None))
        self._MaximumThreadCount = self._validateMaximumThreadCount(shared_manager, config.get("MaximumThreadCount", None))
        self._IdleCleanupThreshold = self._validateIdleCleanupThreshold(shared_manager, config.get("IdleCleanupThreshold", None))
        self._TaskThreshold = self._validateTaskThreshold(shared_manager, config.get("TaskThreshold", None))
        self._GlobalTaskThreshold = self._validateGlobalTaskThreshold(shared_manager, config.get("GlobalTaskThreshold", None))
        self._SubProcessPriority = self._validateSubProcessPriority(shared_manager, config.get("SubProcessPriority", None))
        self._ExpandPolicy = self._validateExpandPolicy(shared_manager, config.get("ExpandPolicy", None))
        self._ShrinkagePolicy = self._validateShrinkagePolicy(shared_manager, config.get("ShrinkagePolicy", None))
        self._ShrinkagePolicyTimeout = self._validateShrinkagePolicyTimeout(shared_manager, config.get("ShrinkagePolicyTimeout", None))
        self._PerformanceReport = shared_manager.Value("b", config.get("PerformanceReport", False)) if shared_manager is not None else config.get("PerformanceReport", False)

    @property
    def MainProcessPriority(self) -> str | multiprocessing.Manager.Value:
        return self._MainProcessPriority.value if self._MultiProcess else self._MainProcessPriority

    @property
    def CoreProcessCount(self) -> int | multiprocessing.Manager.Value:
        return self._CoreProcessCount.value if self._MultiProcess else self._CoreProcessCount

    @property
    def CoreThreadCount(self) -> int | multiprocessing.Manager.Value:
        return self._CoreThreadCount.value if self._MultiProcess else self._CoreThreadCount

    @property
    def MaximumProcessCount(self) -> int | multiprocessing.Manager.Value:
        return self._MaximumProcessCount.value if self._MultiProcess else self._MaximumProcessCount

    @property
    def MaximumThreadCount(self) -> int | multiprocessing.Manager.Value:
        return self._MaximumThreadCount.value if self._MultiProcess else self._MaximumThreadCount

    @property
    def IdleCleanupThreshold(self) -> int | multiprocessing.Manager.Value:
        return self._IdleCleanupThreshold.value if self._MultiProcess else self._IdleCleanupThreshold

    @property
    def TaskThreshold(self) -> int | multiprocessing.Manager.Value:
        return self._TaskThreshold.value if self._MultiProcess else self._TaskThreshold

    @property
    def GlobalTaskThreshold(self) -> int | multiprocessing.Manager.Value:
        return self._GlobalTaskThreshold.value if self._MultiProcess else self._GlobalTaskThreshold

    @property
    def SubProcessPriority(self) -> str | multiprocessing.Manager.Value:
        return self._SubProcessPriority.value if self._MultiProcess else self._SubProcessPriority

    @property
    def ExpandPolicy(self) -> str | multiprocessing.Manager.Value:
        return self._ExpandPolicy.value if self._MultiProcess else self._ExpandPolicy

    @property
    def ShrinkagePolicy(self) -> str | multiprocessing.Manager.Value:
        return self._ShrinkagePolicy.value if self._MultiProcess else self._ShrinkagePolicy

    @property
    def ShrinkagePolicyTimeout(self) -> int | multiprocessing.Manager.Value:
        return self._ShrinkagePolicyTimeout.value if self._MultiProcess else self._ShrinkagePolicyTimeout

    @property
    def PerformanceReport(self) -> bool:
        return self._PerformanceReport.value if self._MultiProcess else self._PerformanceReport

    @staticmethod
    def _validateMainProcessPriority(shared_manager: Optional[multiprocessing.Manager], priority: ProcessPriority) -> str | multiprocessing.Manager.Value:
        if shared_manager is None and priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            _DEFAULT_LOGGER.warning(f"Invalid priority level '{priority}'. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        if shared_manager is None and priority in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            return priority
        if shared_manager is not None and priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            _DEFAULT_LOGGER.warning(f"Invalid priority level '{priority}'. Default value ['NORMAL'] has been used.")
            return shared_manager.Value("c", "NORMAL")
        if shared_manager is not None and priority in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            return shared_manager.Value("c", priority)

    def _validateCoreProcessCount(self, shared_manager: Optional[multiprocessing.Manager], core_process_count: Optional[int]) -> int | multiprocessing.Manager.Value:
        if core_process_count is None:
            _DEFAULT_LOGGER.warning(f"Core process count not set, process pool will be unavailable")
            return shared_manager.Value("i", 0) if shared_manager is not None else 0

        default_value = self.PhysicalCores // 4
        if default_value < 1:
            default_value = 1

        if shared_manager is None and not isinstance(core_process_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for core process count '{core_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(core_process_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for core process count '{core_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if core_process_count <= 0 or core_process_count > self.PhysicalCores:
            if shared_manager is None:
                _DEFAULT_LOGGER.warning(f"Core process count exceeds the range of 1 - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return default_value
            if shared_manager is not None:
                _DEFAULT_LOGGER.warning(f"Core process count exceeds the range of 1 - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return core_process_count
        if shared_manager is not None:
            return shared_manager.Value("i", core_process_count)

    def _validateCoreThreadCount(self, shared_manager: Optional[multiprocessing.Manager], core_thread_count: Optional[int]) -> int | multiprocessing.Manager.Value:
        if core_thread_count is None:
            _DEFAULT_LOGGER.warning(f"Core thread count not set, thread pool will be unavailable")
            return shared_manager.Value("i", 0) if shared_manager is not None else 0

        default_value: int = self.PhysicalCores // 2
        if default_value < 1:
            default_value: int = 1

        if shared_manager is None and not isinstance(core_thread_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for core thread count '{core_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(core_thread_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for core thread count '{core_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if core_thread_count <= 0 or core_thread_count > self.PhysicalCores * 4:
            if shared_manager is None:
                _DEFAULT_LOGGER.warning(f"Core thread count exceeds the range of 1 - {self.PhysicalCores * 4}. Default value [{default_value}] has been used.")
                return default_value
            if shared_manager is not None:
                _DEFAULT_LOGGER.warning(f"Core thread count exceeds the range of 1 - {self.PhysicalCores * 4}. Default value [{default_value}] has been used.")
                return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return core_thread_count
        if shared_manager is not None:
            return shared_manager.Value("i", core_thread_count)

    def _validateMaximumProcessCount(self, shared_manager: Optional[multiprocessing.Manager], maximum_process_count: Optional[int]) -> int | multiprocessing.Manager.Value:
        if self.CoreProcessCount == 0:
            return shared_manager.Value("i", 0) if shared_manager is not None else 0

        default_value: int = self.PhysicalCores

        if shared_manager is None and self._CoreProcessCount is None:
            return 0
        if shared_manager is not None and self._CoreProcessCount is None:
            return shared_manager.Value("i", 0)

        if shared_manager is None and maximum_process_count is None:
            _DEFAULT_LOGGER.warning(f"Maximum process count not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and maximum_process_count is None:
            _DEFAULT_LOGGER.warning(f"Maximum process count not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        core_process_count = self._CoreProcessCount.value if shared_manager is not None else self._CoreProcessCount

        if shared_manager is None and not isinstance(maximum_process_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for maximum process count '{maximum_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(maximum_process_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for maximum process count '{maximum_process_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if maximum_process_count < core_process_count or maximum_process_count > self.PhysicalCores:
            if shared_manager is None:
                _DEFAULT_LOGGER.warning(f"Maximum process count exceeds the range of {core_process_count} - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return default_value
            if shared_manager is not None:
                _DEFAULT_LOGGER.warning(f"Maximum process count exceeds the range of {core_process_count} - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return maximum_process_count
        if shared_manager is not None:
            return shared_manager.Value("i", maximum_process_count)

    def _validateMaximumThreadCount(self, shared_manager: Optional[multiprocessing.Manager], maximum_thread_count: Optional[int]) -> int | multiprocessing.Manager.Value:
        if self.CoreThreadCount == 0:
            return shared_manager.Value("i", 0) if shared_manager is not None else 0

        default_value: int = self.PhysicalCores * 4

        if shared_manager is None and self._CoreThreadCount is None:
            return 0
        if shared_manager is not None and self._CoreThreadCount is None:
            return shared_manager.Value("i", 0)

        if shared_manager is None and maximum_thread_count is None:
            _DEFAULT_LOGGER.warning(f"Maximum thread count not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and maximum_thread_count is None:
            _DEFAULT_LOGGER.warning(f"Maximum thread count not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        core_thread_count = self._CoreProcessCount.value if shared_manager is not None else self._CoreProcessCount

        if shared_manager is None and not isinstance(maximum_thread_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for maximum thread count '{maximum_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(maximum_thread_count, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for maximum thread count '{maximum_thread_count}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if maximum_thread_count < core_thread_count or maximum_thread_count > self.PhysicalCores:
            if shared_manager is None:
                _DEFAULT_LOGGER.warning(f"Maximum thread count exceeds the range of {core_thread_count} - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return default_value
            if shared_manager is not None:
                _DEFAULT_LOGGER.warning(f"Maximum thread count exceeds the range of {core_thread_count} - {self.PhysicalCores}. Default value [{default_value}] has been used.")
                return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return maximum_thread_count
        if shared_manager is not None:
            return shared_manager.Value("i", maximum_thread_count)

    @staticmethod
    def _validateIdleCleanupThreshold(shared_manager: Optional[multiprocessing.Manager], idle_cleanup_threshold: Optional[int]) -> int | multiprocessing.Manager.Value:
        default_value: int = 60

        if shared_manager is None and idle_cleanup_threshold is None:
            _DEFAULT_LOGGER.warning(f"Idle cleanup threshold not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and idle_cleanup_threshold is None:
            _DEFAULT_LOGGER.warning(f"Idle cleanup threshold not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None and not isinstance(idle_cleanup_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for idle cleanup threshold '{idle_cleanup_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(idle_cleanup_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for idle cleanup threshold '{idle_cleanup_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return idle_cleanup_threshold
        if shared_manager is not None:
            return shared_manager.Value("i", idle_cleanup_threshold)

    def _validateTaskThreshold(self, shared_manager: Optional[multiprocessing.Manager], task_threshold: Optional[int]) -> int | multiprocessing.Manager.Value:
        default_value: int = self._calculateTaskThreshold()

        if shared_manager is None and task_threshold is None:
            _DEFAULT_LOGGER.warning(f"Task threshold not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and task_threshold is None:
            _DEFAULT_LOGGER.warning(f"Task threshold not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None and not isinstance(task_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for task threshold '{task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(task_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for task threshold '{task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return task_threshold
        if shared_manager is not None:
            return shared_manager.Value("i", task_threshold)

    def _validateGlobalTaskThreshold(self, shared_manager: Optional[multiprocessing.Manager], global_task_threshold: Optional[int]) -> int | multiprocessing.Manager.Value:
        core_process_count = self._CoreProcessCount.value if shared_manager is not None else self._CoreProcessCount
        if core_process_count is None:
            core_process_count = 0
        core_thread_count = self._CoreThreadCount.value if shared_manager is not None else self._CoreThreadCount
        if core_thread_count is None:
            core_thread_count = 0
        task_threshold = self._TaskThreshold.value if shared_manager is not None else self._TaskThreshold
        default_value: int = (core_process_count + core_thread_count) * task_threshold

        if shared_manager is None and global_task_threshold is None:
            _DEFAULT_LOGGER.warning(f"Global task threshold not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and global_task_threshold is None:
            _DEFAULT_LOGGER.warning(f"Global task threshold not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None and not isinstance(global_task_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for global task threshold '{global_task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(global_task_threshold, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for global task threshold '{global_task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return global_task_threshold
        if shared_manager is not None:
            return shared_manager.Value("i", global_task_threshold)

    def _validateSubProcessPriority(self, shared_manager: Optional[multiprocessing.Manager], process_priority: ProcessPriority.NORMAL) -> str | multiprocessing.Manager.Value:
        if self.CoreProcessCount == 0:
            return shared_manager.Value("c", "NORMAL") if shared_manager is not None else "NORMAL"

        if shared_manager is None and process_priority is None:
            _DEFAULT_LOGGER.warning("Process priority not set. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        if shared_manager is not None and process_priority is None:
            _DEFAULT_LOGGER.warning("Process priority not set. Default value ['NORMAL'] has been used.")
            return shared_manager.Value("c", "NORMAL")

        if shared_manager is None and process_priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            _DEFAULT_LOGGER.warning(f"Invalid process priority '{process_priority}'. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        if shared_manager is not None and process_priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            _DEFAULT_LOGGER.warning(f"Invalid process priority '{process_priority}'. Default value ['NORMAL'] has been used.")
            return shared_manager.Value("c", "NORMAL")

        core_process_count = self._CoreProcessCount.value if shared_manager is not None else self._CoreProcessCount

        if core_process_count == self.PhysicalCores and process_priority in ["HIGH", "REALTIME"]:
            if shared_manager is None:
                _DEFAULT_LOGGER.warning(f"Process priority {process_priority} is not recommended for all physical cores. Default value ['NORMAL'] has been used.")
                return "NORMAL"
            if shared_manager is not None:
                _DEFAULT_LOGGER.warning(f"Process priority {process_priority} is not recommended for all physical cores. Default value ['NORMAL'] has been used.")
                return shared_manager.Value("c", "NORMAL")

        if shared_manager is None:
            return process_priority
        if shared_manager is not None:
            return shared_manager.Value("c", process_priority)

    @staticmethod
    def _validateExpandPolicy(shared_manager: Optional[multiprocessing.Manager], expand_policy: ExpandPolicy) -> str | multiprocessing.Manager.Value:
        if shared_manager is None and expand_policy is None:
            _DEFAULT_LOGGER.warning("Expand policy not set. Default value ['NoExpand'] has been used.")
            return "NoExpand"
        if shared_manager is not None and expand_policy is None:
            _DEFAULT_LOGGER.warning("Expand policy not set. Default value ['NoExpand'] has been used.")
            return shared_manager.Value("c", "NoExpand")

        if shared_manager is None and expand_policy not in ["NoExpand", "AutoExpand", "BeforehandExpand"]:
            _DEFAULT_LOGGER.warning(f"Invalid expand policy '{expand_policy}'. Default value ['NoExpand'] has been used.")
            return "NoExpand"
        if shared_manager is not None and expand_policy not in ["NoExpand", "AutoExpand", "BeforehandExpand"]:
            _DEFAULT_LOGGER.warning(f"Invalid expand policy '{expand_policy}'. Default value ['NoExpand'] has been used.")
            return shared_manager.Value("c", "NoExpand")

        if shared_manager is None:
            return expand_policy
        if shared_manager is not None:
            return shared_manager.Value("c", expand_policy)

    @staticmethod
    def _validateShrinkagePolicy(shared_manager: Optional[multiprocessing.Manager], shrinkage_policy: ShrinkagePolicy) -> str | multiprocessing.Manager.Value:
        if shared_manager is None and shrinkage_policy is None:
            _DEFAULT_LOGGER.warning("Shrinkage policy not set. Default value ['NoShrink'] has been used.")
            return "NoShrink"
        if shared_manager is not None and shrinkage_policy is None:
            _DEFAULT_LOGGER.warning("Shrinkage policy not set. Default value ['NoShrink'] has been used.")
            return shared_manager.Value("c", "NoShrink")

        if shared_manager is None and shrinkage_policy not in ["NoShrink", "AutoShrink", "TimeoutShrink"]:
            _DEFAULT_LOGGER.warning(f"Invalid shrinkage policy '{shrinkage_policy}'. Default value ['NoShrink'] has been used.")
            return "NoShrink"
        if shared_manager is not None and shrinkage_policy not in ["NoShrink", "AutoShrink", "TimeoutShrink"]:
            _DEFAULT_LOGGER.warning(f"Invalid shrinkage policy '{shrinkage_policy}'. Default value ['NoShrink'] has been used.")
            return shared_manager.Value("c", "NoShrink")

        if shared_manager is None:
            return shrinkage_policy
        if shared_manager is not None:
            return shared_manager.Value("c", shrinkage_policy)

    @staticmethod
    def _validateShrinkagePolicyTimeout(shared_manager: Optional[multiprocessing.Manager], shrinkage_policy_timeout: Optional[int]) -> int | multiprocessing.Manager.Value:
        default_value: int = 5
        if shared_manager is None and shrinkage_policy_timeout is None:
            _DEFAULT_LOGGER.warning(f"Shrinkage policy timeout not set. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and shrinkage_policy_timeout is None:
            _DEFAULT_LOGGER.warning(f"Shrinkage policy timeout not set. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None and not isinstance(shrinkage_policy_timeout, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for shrinkage policy timeout '{shrinkage_policy_timeout}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value
        if shared_manager is not None and not isinstance(shrinkage_policy_timeout, int):
            _DEFAULT_LOGGER.warning(f"Invalid type for shrinkage policy timeout '{shrinkage_policy_timeout}'. Must be an integer. Default value [{default_value}] has been used.")
            return shared_manager.Value("i", default_value)

        if shared_manager is None:
            return shrinkage_policy_timeout
        if shared_manager is not None:
            return shared_manager.Value("i", shrinkage_policy_timeout)

    def _calculateTaskThreshold(self) -> int:
        physical_cores: int = self.PhysicalCores
        total_memory: int = int(_RESOURCES_MONITOR.totalPhysicalMemory() / (1024 ** 3))
        balanced_score: float = ((physical_cores / 128) + (total_memory / 3072)) / 2

        balanced_score_thresholds: List[float] = [0.2, 0.4, 0.6, 0.8]
        task_thresholds: List[int] = [10, 40, 70, 100, 130]
        for score_threshold, threshold in zip(balanced_score_thresholds, task_thresholds):
            if balanced_score <= score_threshold:
                return threshold
        return task_thresholds[-1]


class _TaskObject:
    def __init__(self, task: callable, task_id: str, callback: bool = False, *args, **kwargs):
        self.ConfigDefaultsValue = {
            "lock": False,
            "lock_timeout": 3,
            "timeout": None,
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
        self.IsRetry: bool = self.Config['retry']
        self.MaxRetries: int = self.Config['max_retries']

        self.RetriesCount: int = 0
        self.UnserializableInfo: Dict[int, Any] = {}

        self.TaskArgs = self._serialize(args)
        self.TaskKwargs = self._serialize(kwargs)
        self.RecoveredTaskArgs = None
        self.RecoveredTaskKwargs = None

    def reinitializedParams(self) -> None:
        self.RecoveredTaskArgs = self._deserialize(self.TaskArgs)
        self.RecoveredTaskKwargs = self._deserialize(self.TaskKwargs)

    def _serialize(self, obj) -> Any:
        if isinstance(obj, tuple):
            return tuple(self._serialize(item) for item in obj)
        elif isinstance(obj, dict):
            return {key: self._serialize(value) for key, value in obj.items()}
        elif not self._isSerializable(obj):
            obj_id = id(obj)
            self.UnserializableInfo[obj_id] = obj
            return {"__unserializable__": True, "id": obj_id, "type": type(obj).__name__}
        else:
            return obj

    def _deserialize(self, obj) -> Any:
        if isinstance(obj, tuple):
            return tuple(self._deserialize(item) for item in obj)
        elif isinstance(obj, dict):
            if "__unserializable__" in obj:
                return self.UnserializableInfo[obj["id"]]
            return {key: self._deserialize(value) for key, value in obj.items()}
        else:
            return obj

    @staticmethod
    def _isSerializable(obj) -> bool:
        try:
            pickle.dumps(obj)
            return True
        except (pickle.PicklingError, AttributeError, TypeError):
            return False


class _CallbackProcessor:
    def __init__(self, status_manager: _StatusManager):
        self.StatusManager: _StatusManager = status_manager
        self.CloseEvent: threading.Event = threading.Event()

    def start(self, main_event_loop: asyncio.AbstractEventLoop) -> None:
        main_event_loop.create_task(self.run())

    def close(self) -> None:
        self.CloseEvent.set()

    async def run(self) -> None:
        global _CALLBACK_FUNCTION, _FUTURE_RESULT
        while not self.CloseEvent.is_set():
            await asyncio.sleep(0.001)
            try:
                callback_data: Tuple[Any, str] = self.StatusManager.ResultStorageQueue.get_nowait()
                task_result, task_id = callback_data
                _FUTURE_RESULT[task_id] = task_result
                if task_id in _CALLBACK_FUNCTION:
                    callback_object = _CALLBACK_FUNCTION[task_id]
                    if asyncio.iscoroutinefunction(callback_object):
                        await callback_object(task_result)
                    else:
                        callback_object(task_result)
                    del _CALLBACK_FUNCTION[task_id]
            except queue.Empty:
                continue


class _ProcessObject(multiprocessing.Process):
    def __init__(self, process_name: str, process_type: Literal['Core', 'Expand'], status_manager: _StatusManager, config_manager: _ConfigManager):
        super().__init__(name=process_name, daemon=True)
        self.ProcessName: str = process_name
        self.ProcessType: Literal['Core', 'Expand'] = process_type
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.PendingTasks: Dict[str, asyncio.Task | Future] = {}
        self.SystemExecutor: Optional[ThreadPoolExecutor] = None
        self.HighPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.MediumPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.LowPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.WorkingEvent: multiprocessing.Event = multiprocessing.Event()
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self) -> None:
        self._setProcessPriority(self.ConfigManager.SubProcessPriority)
        self.SystemExecutor: ThreadPoolExecutor = ThreadPoolExecutor(self._setSystemExecutorThreadCount())
        self.EventLoop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        except Exception as e:
            self.terminate()
            _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] has been terminated due to {e}.")
        finally:
            self.EventLoop.close()
            _DEFAULT_LOGGER.info(f"[{self.ProcessName} - {self.pid}] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def addProcessTask(self, priority: int, task_object: _TaskObject) -> None:
        self.WorkingEvent.set()
        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object, 0))
            return
        if 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
            return
        if 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object, 0))
            return
        self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
        _DEFAULT_LOGGER.warning(f"[{self.ProcessName} - {self.pid}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self) -> None:
        self._cleanupProcessMemory()
        last_cleanup_time: float = time.time()
        while not self.CloseEvent.is_set():
            await asyncio.sleep(0.0001)
            current_time: float = time.time()
            if current_time - last_cleanup_time >= self.ConfigManager.IdleCleanupThreshold:
                self._cleanupProcessMemory()
                last_cleanup_time: float = current_time
            try:
                task_data: Tuple[str, _TaskObject, int] = self._getTaskData()
                task_priority, task_object, retried = task_data
                try:
                    task_object.reinitializedParams()
                    if task_object.TaskType == "Async":
                        await self._executeAsyncTask(task_priority, task_object, retried)
                    else:
                        await self._executeSyncTask(task_priority, task_object, retried)
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} failed due to {e}.")
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                continue
        self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
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
                    _DEFAULT_LOGGER.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            _DEFAULT_LOGGER.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        async def _onTaskCancelled(future_object: asyncio.Task) -> None:
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()
            _DEFAULT_LOGGER.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")

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
                    _DEFAULT_LOGGER.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        wait_for_event: asyncio.Event = asyncio.Event()

        def _onTaskCompleted(future_object: Future):
            try:
                task_result: Any = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.StatusManager.TaskLock.release()
            except CancelledError:  # concurrent.futures.CancelledError
                del self.PendingTasks[task_object.TaskID]
                self._updateTaskStatus()
                if locked:
                    self.StatusManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DEFAULT_LOGGER.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            _DEFAULT_LOGGER.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
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
                _DEFAULT_LOGGER.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DEFAULT_LOGGER.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self) -> None:
        current_status: Tuple[int, int] = self.StatusManager.getCoreProcessTaskStatus(self.ProcessName) if self.ProcessType == "Core" else self.StatusManager.getExpandProcessTaskStatus(self.ProcessName)
        pid: int = current_status[0]
        task_count: int = current_status[1]
        new_task_count: int = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ProcessType == "Core":
            self.StatusManager.updateCoreProcessTaskStatus(self.ProcessName, pid, new_task_count)
        else:
            self.StatusManager.updateExpandProcessTaskStatus(self.ProcessName, pid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any) -> None:
        self.StatusManager.ResultStorageQueue.put_nowait((task_result, task_object.TaskID))
        if task_object.TaskID in self.PendingTasks.keys():
            del self.PendingTasks[task_object.TaskID]
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
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
        _DEFAULT_LOGGER.debug(f"[{self.ProcessName} - {self.pid}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _setProcessPriority(self, priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]) -> None:
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
            result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping.get(priority, priority_mapping["NORMAL"]))
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"Set priority failed with error code {error_code}.")
        except Exception as e:
            _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _setSystemExecutorThreadCount(self) -> int:
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
        if SYSTEM_TYPE == "Windows":
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.pid)
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed due to {e}.")
                return
            if not handle:
                _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                _DEFAULT_LOGGER.error(f"[{self.ProcessName} - {self.pid}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        if not self.HighPriorityQueue.empty():
            return self.HighPriorityQueue.get_nowait()
        if not self.MediumPriorityQueue.empty():
            return self.MediumPriorityQueue.get_nowait()
        if not self.LowPriorityQueue.empty():
            return self.LowPriorityQueue.get_nowait()
        raise queue.Empty


class _ThreadObject(threading.Thread):
    def __init__(self, thread_name: str, thread_type: Literal['Core', 'Expand'], status_manager: _StatusManager, config_manager: _ConfigManager, system_executor: ThreadPoolExecutor):
        super().__init__(name=thread_name, daemon=True)
        self.ThreadName = thread_name
        self.ThreadType = thread_type
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.PendingTasks: Dict[str, asyncio.Task | Future] = {}
        self.SystemExecutor: ThreadPoolExecutor = system_executor
        self.HighPriorityQueue: queue.Queue = queue.Queue()
        self.MediumPriorityQueue: queue.Queue = queue.Queue()
        self.LowPriorityQueue: queue.Queue = queue.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self) -> None:
        self.EventLoop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        except Exception as e:
            _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] has been terminated due to {e}.")
        except (BrokenPipeError, EOFError, KeyboardInterrupt):
            self.CloseEvent.set()
        finally:
            self.EventLoop.close()
            _DEFAULT_LOGGER.info(f"[{self.ThreadName} - {self.ident}] has been closed.")

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()

    def addThreadTask(self, priority: int, task_object: _TaskObject) -> None:
        self.WorkingEvent.set()
        if 0 <= priority <= 3:
            self.HighPriorityQueue.put_nowait(("HighPriority", task_object, 0))
            return
        if 4 <= priority <= 7:
            self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
            return
        if 8 <= priority <= 10:
            self.LowPriorityQueue.put_nowait(("LowPriority", task_object, 0))
            return
        self.MediumPriorityQueue.put_nowait(("MediumPriority", task_object, 0))
        _DEFAULT_LOGGER.warning(f"[{self.ThreadName} - {self.ident}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self) -> None:
        while not self.CloseEvent.is_set():
            await asyncio.sleep(0.0001)
            try:
                task_data: Tuple[str, _TaskObject, int] = self._getTaskData()
                task_priority, task_object, retried = task_data
                try:
                    task_object.reinitializedParams()
                    await self._executeAsyncTask(task_priority, task_object, retried) if task_object.TaskType == "Async" else await self._executeSyncTask(task_priority, task_object, retried)
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] task {task_object.TaskID} failed due to {e}.")
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                continue
        await self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
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
                    _DEFAULT_LOGGER.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs), name=f"{task_object.Task.__name__}[{task_object.TaskID}]")
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            _DEFAULT_LOGGER.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
        async def _onTaskCancelled(future_object: asyncio.Task):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.StatusManager.TaskLock.release()
            _DEFAULT_LOGGER.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")

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
                    _DEFAULT_LOGGER.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        async_future: asyncio.Task = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs), name=f"{task_object.Task.__name__}[{task_object.TaskID}]")
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        acquired: bool = self.StatusManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
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
                    _DEFAULT_LOGGER.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            _DEFAULT_LOGGER.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool) -> None:
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
                _DEFAULT_LOGGER.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    _DEFAULT_LOGGER.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    _DEFAULT_LOGGER.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.StatusManager.TaskLock.release()

        sync_future: Future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredTaskArgs, **task_object.RecoveredTaskKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self) -> None:
        current_status: Tuple[int, int] = self.StatusManager.getCoreThreadTaskStatus(self.ThreadName) if self.ThreadType == "Core" else self.StatusManager.getExpandThreadTaskStatus(self.ThreadName)
        tid: int = current_status[0]
        task_count: int = current_status[1]
        new_task_count: int = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ThreadType == "Core":
            self.StatusManager.updateCoreThreadTaskStatus(self.ThreadName, tid, new_task_count)
        else:
            self.StatusManager.updateExpandThreadTaskStatus(self.ThreadName, tid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any) -> None:
        self.StatusManager.ResultStorageQueue.put_nowait((task_result, task_object.TaskID))
        if task_object.TaskID in self.PendingTasks.keys():
            del self.PendingTasks[task_object.TaskID]
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int) -> None:
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
        _DEFAULT_LOGGER.debug(f"[{self.ThreadName} - {self.ident}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        if not self.HighPriorityQueue.empty():
            return self.HighPriorityQueue.get_nowait()
        if not self.MediumPriorityQueue.empty():
            return self.MediumPriorityQueue.get_nowait()
        if not self.LowPriorityQueue.empty():
            return self.LowPriorityQueue.get_nowait()
        raise queue.Empty


class _LoadBalancer(threading.Thread):
    def __init__(self, status_manager: _StatusManager, config_manager: _ConfigManager, system_executor: ThreadPoolExecutor):
        super().__init__(name='LoadBalancer', daemon=True)
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.SystemExecutor: ThreadPoolExecutor = system_executor
        self.LastExpandCheckTime = time.time()
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        try:
            self._cleanupMainProcessMemory()
            self._cleanupServiceProcessMemory()
            last_cleanup_time: float = time.time()
            performance_report_time: float = time.time()
            while not self.CloseEvent.is_set():
                time.sleep(0.001)
                self._updateProcessLoadStatus()
                self._expandPolicyExecutor()
                self._shrinkagePolicyExecutor()
                if time.time() - performance_report_time >= 10:
                    self._showPerformanceReport()
                    performance_report_time: float = time.time()
                if time.time() - last_cleanup_time > 300:
                    last_cleanup_time: float = time.time()
                    self._cleanupMainProcessMemory()
                    self._cleanupServiceProcessMemory()
        except (BrokenPipeError, EOFError, Exception):
            pass

    def stop(self) -> None:
        self.CloseEvent.set()
        self.join()
        _DEFAULT_LOGGER.info(f"[LoadBalancer] has been closed.")

    def _showPerformanceReport(self):
        use_performance_report = self.ConfigManager.PerformanceReport
        if not use_performance_report:
            return
        global _CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL
        main_process_cpu_usage: int = _RESOURCES_MONITOR.processCpuUsage(os.getpid(), 0.001)
        main_process_memory_usage: int = _RESOURCES_MONITOR.processMemoryUsage(os.getpid())
        print(TextColor.PURPLE_BOLD.value + "\nPerformanceReport" + TextColor.RESET.value)
        print(TextColor.PURPLE_BOLD.value + f"CoreProcess: MainProcess - PID: {os.getpid()} - CPU: {main_process_cpu_usage:.2f}% - Memory: {main_process_memory_usage:.2f}MB" + TextColor.RESET.value)
        for process_name, process_object in _CORE_PROCESS_POOL.items():
            pid: int = process_object.pid
            cpu_usage: int = _RESOURCES_MONITOR.processCpuUsage(pid, 0.001)
            memory_usage: int = _RESOURCES_MONITOR.processMemoryUsage(pid)
            print(TextColor.PURPLE_BOLD.value + f"CoreProcess: {process_name} - PID: {pid} - CPU: {cpu_usage:.2f}% - Memory: {memory_usage:.2f}MB" + TextColor.RESET.value)
        for process_name, process_object in _EXPAND_PROCESS_POOL.items():
            pid: int = process_object.pid
            cpu_usage: int = _RESOURCES_MONITOR.processCpuUsage(pid, 0.001)
            memory_usage: int = _RESOURCES_MONITOR.processMemoryUsage(pid)
            print(TextColor.PURPLE_BOLD.value + f"ExpandProcess: {process_name} - PID: {pid} - CPU: {cpu_usage:.2f}% - Memory: {memory_usage:.2f}MB" + TextColor.RESET.value)

    def _cleanupMainProcessMemory(self) -> None:
        if SYSTEM_TYPE == "Windows":
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, os.getpid())
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {e}.")
                return
            if not handle:
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)
            return

    def _cleanupServiceProcessMemory(self) -> None:
        if SYSTEM_TYPE == "Windows" and self.StatusManager.SharedManagerID != 0:
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.StatusManager.SharedManagerID)
                if handle == 0:
                    raise ValueError("Failed to obtain a valid handle")
            except Exception as e:
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] memory cleanup failed due to {e}.")
                return
            if not handle:
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] failed to obtain a valid process handle.")
                return
            result = ctypes.windll.psapi.EmptyWorkingSet(handle)
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                _DEFAULT_LOGGER.error(f"[{self.name} - {self.ident}] memory cleanup failed with error code {error_code}.")
            ctypes.windll.kernel32.CloseHandle(handle)

    def _updateProcessLoadStatus(self) -> None:
        global _CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL
        for process_name, process_obj in _CORE_PROCESS_POOL.items():
            # noinspection PyBroadException
            try:
                process_cpu_usage = _RESOURCES_MONITOR.processCpuUsage(process_obj.pid, 0.001)
                process_memory_usage = _RESOURCES_MONITOR.processMemoryUsage(process_obj.pid)
                weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.1) + (self.StatusManager.CoreProcessTaskStatusPool[process_name][1] * 0.9)), 100))
                self.StatusManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, weighted_load)
            except Exception:
                self.StatusManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, 0)
        for process_name, process_obj in _EXPAND_PROCESS_POOL.items():
            # noinspection PyBroadException
            try:
                process_cpu_usage = _RESOURCES_MONITOR.processCpuUsage(process_obj.pid, 0.001)
                process_memory_usage = _RESOURCES_MONITOR.processMemoryUsage(process_obj.pid)
                weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.1) + (self.StatusManager.ExpandProcessTaskStatusPool[process_name][1] * 0.9)), 100))
                self.StatusManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, weighted_load)
            except Exception:
                self.StatusManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, 0)

    def _expandPolicyExecutor(self) -> None:
        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self.ConfigManager.ExpandPolicy]
        expand_method()

    def _noExpand(self) -> None:
        pass

    def _autoExpand(self) -> None:
        global _PROCESS_TASK_SCHEDULING_EVENT, _THREAD_TASK_SCHEDULING_EVENT, _PROCESS_BALANCE_EVENT, _THREAD_BALANCE_EVENT
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0:
            current_core_process_total_load: int = sum([self.StatusManager.getCoreProcessLoadStatus(name)[1] for name, load_status in self.StatusManager.CoreProcessLoadStatusPool.items()])
            if self.StatusManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load: int = sum([self.StatusManager.getExpandProcessLoadStatus(name)[1] for name, load_status in self.StatusManager.ExpandProcessLoadStatusPool.items()])
            else:
                current_expand_process_total_load: int = 0
            process_total_load = max(0, min(100, current_core_process_total_load + current_expand_process_total_load))
            ideal_load_per_process = 98
            if process_total_load >= ideal_load_per_process:
                allow_process_expansion = self._isAllowExpansion("Process")
                if allow_process_expansion and not _PROCESS_TASK_SCHEDULING_EVENT.is_set():
                    _PROCESS_BALANCE_EVENT.set()
                    self._expandProcess()
                    _PROCESS_BALANCE_EVENT.clear()
                elif not allow_process_expansion and time.time() - self.LastExpandCheckTime >= 30:
                    _DEFAULT_LOGGER.warning(f"Load reaches {int(ideal_load_per_process)}%, but unable to expand more process")
                    self.LastExpandCheckTime = time.time()
                else:
                    pass
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0:
            current_core_thread_total_load: int = sum([self.StatusManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreThreadTaskStatusPool.items()])
            if self.StatusManager.ExpandThreadTaskStatusPool:
                current_expand_thread_total_load: int = sum([self.StatusManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandThreadTaskStatusPool.items()])
            else:
                current_expand_thread_total_load: int = 0
            thread_total_load: int = current_core_thread_total_load + current_expand_thread_total_load
            ideal_load_per_thread: int = self.ConfigManager.GlobalTaskThreshold - (self.ConfigManager.CoreThreadCount * self.ConfigManager.TaskThreshold) * 0.95
            if thread_total_load >= ideal_load_per_thread:
                allow_thread_expansion = self._isAllowExpansion("Thread")
                if allow_thread_expansion and not _THREAD_TASK_SCHEDULING_EVENT.is_set():
                    _THREAD_BALANCE_EVENT.set()
                    self._expandThread()
                    _THREAD_BALANCE_EVENT.clear()
                elif not allow_thread_expansion and time.time() - self.LastExpandCheckTime >= 30:
                    _DEFAULT_LOGGER.warning(f"Load reaches {int(ideal_load_per_thread)}%, but unable to expand more thread")
                    self.LastExpandCheckTime = time.time()
                else:
                    pass

    def _beforehandExpand(self) -> None:
        global _PROCESS_TASK_SCHEDULING_EVENT, _THREAD_TASK_SCHEDULING_EVENT, _PROCESS_BALANCE_EVENT, _THREAD_BALANCE_EVENT
        # core_process_count = self.ConfigManager.CoreProcessCount if self.ConfigManager.SharedManager is None else self.ConfigManager.CoreProcessCount.value
        # core_thread_count = self.ConfigManager.CoreThreadCount if self.ConfigManager.SharedManager is None else self.ConfigManager.CoreThreadCount.value
        # global_task_threshold = self.ConfigManager.GlobalTaskThreshold if self.ConfigManager.SharedManager is None else self.ConfigManager.GlobalTaskThreshold.value
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0:
            current_core_process_total_load: int = sum([self.StatusManager.getCoreProcessTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreProcessTaskStatusPool.items()])
            if self.StatusManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load: int = sum([self.StatusManager.getExpandProcessTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandProcessTaskStatusPool.items()])
            else:
                current_expand_process_total_load: int = 0
            process_total_task_count: int = current_core_process_total_load + current_expand_process_total_load
        else:
            process_total_task_count: int = 0
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0:
            current_core_thread_total_load: int = sum([self.StatusManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.CoreThreadTaskStatusPool.items()])
            if self.StatusManager.ExpandThreadTaskStatusPool:
                current_expand_thread_total_load: int = sum([self.StatusManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.StatusManager.ExpandThreadTaskStatusPool.items()])
            else:
                current_expand_thread_total_load: int = 0
            thread_total_load: int = current_core_thread_total_load + current_expand_thread_total_load
        else:
            thread_total_load: int = 0
        if (process_total_task_count + thread_total_load) >= self.ConfigManager.GlobalTaskThreshold * 0.8:
            if self._isAllowExpansion("Process") and not _PROCESS_TASK_SCHEDULING_EVENT.is_set():
                _PROCESS_BALANCE_EVENT.set()
                self._expandProcess()
                _PROCESS_BALANCE_EVENT.clear()
            elif time.time() - self.LastExpandCheckTime >= 30:
                _DEFAULT_LOGGER.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold}, but unable to expand more process")
                self.LastExpandCheckTime = time.time()
            else:
                pass
            if self._isAllowExpansion("Thread") and _THREAD_TASK_SCHEDULING_EVENT.is_set():
                _THREAD_BALANCE_EVENT.set()
                self._expandThread()
                _THREAD_BALANCE_EVENT.clear()
            elif time.time() - self.LastExpandCheckTime >= 30:
                _DEFAULT_LOGGER.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold}, but unable to expand more thread")
                self.LastExpandCheckTime = time.time()
            else:
                pass

    def _isAllowExpansion(self, expand_type: Literal["Process", "Thread"]) -> bool:
        if expand_type == "Process":
            if (len(self.StatusManager.CoreProcessTaskStatusPool) + len(self.StatusManager.ExpandProcessTaskStatusPool)) >= self.ConfigManager.MaximumProcessCount:
                return False
            return True
        if expand_type == "Thread":
            if (len(_CORE_THREAD_POOL) + len(_EXPAND_THREAD_POOL)) >= self.ConfigManager.MaximumThreadCount:
                return False
            return True

    def _expandProcess(self) -> None:
        global _EXPAND_PROCESS_POOL, _EXPAND_PROCESS_SURVIVAL_TIME
        try:
            process_name: str = self._generateExpandID("Process")
            process_object = _ProcessObject(process_name, "Expand", self.StatusManager, self.ConfigManager)
            process_object.start()
            _EXPAND_PROCESS_POOL[process_name] = process_object
            self.StatusManager.updateExpandProcessLoadStatus(process_name, process_object.pid, 0)
            self.StatusManager.updateExpandProcessTaskStatus(process_name, process_object.pid, 0)
            _EXPAND_PROCESS_SURVIVAL_TIME[process_name] = time.time()
        except Exception as e:
            _DEFAULT_LOGGER.error(f"Expand process error: {e}.")

    def _expandThread(self) -> None:
        global _EXPAND_THREAD_POOL, _EXPAND_THREAD_SURVIVAL_TIME
        try:
            thread_name: str = self._generateExpandID("Thread")
            thread_object = _ThreadObject(thread_name, "Expand", self.StatusManager, self.ConfigManager, self.SystemExecutor)
            thread_object.start()
            _EXPAND_THREAD_POOL[thread_name] = thread_object
            self.StatusManager.updateExpandThreadTaskStatus(thread_name, thread_object.ident, 0)
            _EXPAND_THREAD_SURVIVAL_TIME[thread_name] = time.time()
        except Exception as e:
            _DEFAULT_LOGGER.error(f"Expand thread error: {e}.")

    @staticmethod
    def _generateExpandID(expand_type: Literal["Process", "Thread"]) -> str:
        global _EXPAND_PROCESS_POOL, _EXPAND_THREAD_POOL
        expand_type_mapping = {
            "Process": _EXPAND_PROCESS_POOL,
            "Thread": _EXPAND_THREAD_POOL,
        }
        basic_id = f"{expand_type}-{0}"
        while True:
            if basic_id not in expand_type_mapping[expand_type]:
                return basic_id
            basic_id = f"{expand_type}-{int(basic_id.split('-')[-1]) + 1}"

    def _shrinkagePolicyExecutor(self) -> None:
        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self.ConfigManager.ShrinkagePolicy]
        shrink_method()

    def _noShrink(self) -> None:
        pass

    def _autoShrink(self) -> None:
        global _EXPAND_PROCESS_POOL, _EXPAND_THREAD_POOL, _EXPAND_PROCESS_SURVIVAL_TIME, _EXPAND_THREAD_SURVIVAL_TIME, _PROCESS_TASK_SCHEDULING_EVENT, _THREAD_TASK_SCHEDULING_EVENT, _PROCESS_BALANCE_EVENT, _THREAD_BALANCE_EVENT
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0 and not _PROCESS_TASK_SCHEDULING_EVENT.is_set():
            _PROCESS_BALANCE_EVENT.set()
            expand_process_obj: List[_ProcessObject] = [obj for i, obj in _EXPAND_PROCESS_POOL.items()]
            allow_close_processes: List[_ProcessObject] = [
                obj for obj in expand_process_obj
                if not obj.WorkingEvent.is_set() and (time.time() - _EXPAND_PROCESS_SURVIVAL_TIME[obj.ProcessName]) >= self.ConfigManager.ShrinkagePolicyTimeout
            ]
            for obj in allow_close_processes:
                obj.stop()
                del _EXPAND_PROCESS_POOL[obj.ProcessName]
                del self.StatusManager.ExpandProcessTaskStatusPool[obj.ProcessName]
                del self.StatusManager.ExpandProcessLoadStatusPool[obj.ProcessName]
                del _EXPAND_PROCESS_SURVIVAL_TIME[obj.ProcessName]
                _DEFAULT_LOGGER.debug(f"[{obj.ProcessName} - {obj.pid}] has been closed due to idle status.")
            _PROCESS_BALANCE_EVENT.clear()
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0 and not _THREAD_TASK_SCHEDULING_EVENT.is_set():
            _THREAD_BALANCE_EVENT.set()
            expand_thread_obj: List[_ThreadObject] = [obj for i, obj in _EXPAND_THREAD_POOL.items()]
            allow_close_threads: List[_ThreadObject] = [
                obj for obj in expand_thread_obj
                if not obj.WorkingEvent.is_set() and (time.time() - _EXPAND_THREAD_SURVIVAL_TIME[obj.ThreadName]) >= self.ConfigManager.ShrinkagePolicyTimeout
            ]
            for obj in allow_close_threads:
                obj.stop()
                del _EXPAND_THREAD_POOL[obj.ThreadName]
                del self.StatusManager.ExpandThreadTaskStatusPool[obj.ThreadName]
                del _EXPAND_THREAD_SURVIVAL_TIME[obj.ThreadName]
                _DEFAULT_LOGGER.debug(f"[{obj.ThreadName} - {obj.ident}] has been closed due to idle status.")
            _THREAD_BALANCE_EVENT.clear()

    def _timeoutShrink(self) -> None:
        global _EXPAND_PROCESS_POOL, _EXPAND_THREAD_POOL, _EXPAND_PROCESS_SURVIVAL_TIME, _EXPAND_THREAD_SURVIVAL_TIME, _PROCESS_TASK_SCHEDULING_EVENT, _THREAD_TASK_SCHEDULING_EVENT, _PROCESS_BALANCE_EVENT, _THREAD_BALANCE_EVENT
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0 and not _PROCESS_TASK_SCHEDULING_EVENT.is_set():
            _PROCESS_BALANCE_EVENT.set()
            expand_process_obj: List[str] = [obj for obj, survival_time in _EXPAND_PROCESS_SURVIVAL_TIME.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout]
            for obj in expand_process_obj:
                _EXPAND_PROCESS_POOL[obj].stop()
                del _EXPAND_PROCESS_POOL[obj]
                del self.StatusManager.ExpandProcessTaskStatusPool[obj]
                del _EXPAND_PROCESS_SURVIVAL_TIME[obj]
                _DEFAULT_LOGGER.debug(f"{obj} has been closed due to timeout.")
            _PROCESS_BALANCE_EVENT.clear()
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0 and not _THREAD_TASK_SCHEDULING_EVENT.is_set():
            _THREAD_BALANCE_EVENT.set()
            expand_thread_obj: List[str] = [obj for obj, survival_time in _EXPAND_THREAD_SURVIVAL_TIME.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout]
            for obj in expand_thread_obj:
                _EXPAND_THREAD_POOL[obj].stop()
                del _EXPAND_THREAD_POOL[obj]
                del self.StatusManager.ExpandThreadTaskStatusPool[obj]
                del _EXPAND_THREAD_SURVIVAL_TIME[obj]
                _DEFAULT_LOGGER.debug(f"{obj} has been closed due to timeout.")
            _THREAD_BALANCE_EVENT.clear()


class _ProcessTaskScheduler(threading.Thread):
    def __init__(self, status_manager: _StatusManager, config_manager: _ConfigManager, process_task_storage_queue: multiprocessing.Queue):
        super().__init__(name='ProcessTaskScheduler', daemon=True)
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.ProcessTaskStorageQueue: multiprocessing.Queue = process_task_storage_queue
        self.LastSelectedProcess: Optional[_ProcessObject] = None
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        while not self.CloseEvent.is_set():
            global _PROCESS_TASK_SCHEDULING_EVENT, _PROCESS_BALANCE_EVENT
            time.sleep(0.001)
            try:
                if _PROCESS_BALANCE_EVENT.is_set():
                    continue
                _PROCESS_TASK_SCHEDULING_EVENT.set()
                task_data: Tuple[int, _TaskObject] = self.ProcessTaskStorageQueue.get_nowait()
                priority, task_object = task_data
                self._scheduler(priority, task_object)
                _PROCESS_TASK_SCHEDULING_EVENT.clear()
            except queue.Empty:
                _PROCESS_TASK_SCHEDULING_EVENT.clear()
                _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
                _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.wait()
                _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.release()
                continue

    def stop(self) -> None:
        global _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT
        self.CloseEvent.set()
        _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
        _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.notify_all()
        _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.release()
        self.join()
        _DEFAULT_LOGGER.info(f"[ProcessTaskScheduler] has been closed.")

    def _scheduler(self, priority: int, task_object: _TaskObject) -> None:
        global _EXPAND_PROCESS_POOL
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
        if _EXPAND_PROCESS_POOL:
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
        global _CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL
        obj_pool: Union[_CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL] = _CORE_PROCESS_POOL if process_type == "Core" else _EXPAND_PROCESS_POOL
        function: Union[_StatusManager.getCoreProcessTaskStatus, _StatusManager.getExpandProcessTaskStatus] = self.StatusManager.getCoreProcessTaskStatus if process_type == "Core" else self.StatusManager.getExpandProcessTaskStatus
        not_full_processes: List[_ProcessObject] = [obj for index, obj in obj_pool.items() if function(obj.ProcessName)[1] < self.ConfigManager.TaskThreshold]
        return not_full_processes

    @staticmethod
    def _checkNotWorkingProcess(process_type: Literal["Core", "Expand"]) -> List[_ProcessObject]:
        global _CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL
        obj_pool: Union[_CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL] = _CORE_PROCESS_POOL if process_type == "Core" else _EXPAND_PROCESS_POOL
        not_working_processes: List[_ProcessObject] = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_processes

    def _checkMinimumLoadProcess(self, processes: List[_ProcessObject], process_type: Literal["Core", "Expand"]) -> _ProcessObject:
        function: Union[_StatusManager.getCoreProcessTaskStatus, _StatusManager.getExpandProcessTaskStatus] = self.StatusManager.getCoreProcessLoadStatus if process_type == "Core" else self.StatusManager.getExpandProcessLoadStatus
        available_processes: List[_ProcessObject] = [p for p in processes if p != self.LastSelectedProcess] if self.LastSelectedProcess is not None else processes
        if not available_processes:
            selected_process: _ProcessObject = processes[0]
        else:
            selected_process: _ProcessObject = min(available_processes, key=lambda x: function(x.ProcessName)[1])
        self.LastSelectedProcess: _ProcessObject = selected_process
        return selected_process


class _ThreadTaskScheduler(threading.Thread):
    def __init__(self, status_manager: _StatusManager, config_manager: _ConfigManager, thread_task_storage_queue: queue.Queue):
        super().__init__(name='ThreadTaskScheduler', daemon=True)
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.ThreadTaskStorageQueue: queue.Queue = thread_task_storage_queue
        self.LastSelectedThread: Optional[_ThreadObject] = None
        self.CloseEvent: multiprocessing.Event = multiprocessing.Event()

    def run(self) -> None:
        while not self.CloseEvent.is_set():
            global _THREAD_TASK_SCHEDULING_EVENT, _THREAD_BALANCE_EVENT, _THREAD_TASK_SCHEDULING_EVENT
            time.sleep(0.001)
            try:
                if _THREAD_BALANCE_EVENT.is_set():
                    continue
                _THREAD_TASK_SCHEDULING_EVENT.set()
                task_data: Tuple[int, _TaskObject] = self.ThreadTaskStorageQueue.get_nowait()
                priority, task_object = task_data
                self._scheduler(priority, task_object)
                _THREAD_TASK_SCHEDULING_EVENT.clear()
            except queue.Empty:
                _THREAD_TASK_SCHEDULING_EVENT.clear()
                _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
                _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.wait()
                _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.release()
                continue

    def stop(self) -> None:
        global _THREAD_TASK_SCHEDULING_EVENT
        self.CloseEvent.set()
        _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
        _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.notify_all()
        _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.release()
        self.join()
        _DEFAULT_LOGGER.info(f"[ThreadTaskScheduler] has been closed.")

    def _scheduler(self, priority: int, task_object: _TaskObject) -> None:
        global _EXPAND_THREAD_POOL
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
        if _EXPAND_THREAD_POOL:
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
        global _CORE_THREAD_POOL, _EXPAND_THREAD_POOL
        obj_pool: Union[_CORE_THREAD_POOL, _EXPAND_THREAD_POOL] = _CORE_THREAD_POOL if thread_type == "Core" else _EXPAND_THREAD_POOL
        function: Union[_StatusManager.getCoreThreadTaskStatus, _StatusManager.getExpandThreadTaskStatus] = self.StatusManager.getCoreThreadTaskStatus if thread_type == "Core" else self.StatusManager.getExpandThreadTaskStatus
        not_full_threads: List[_ThreadObject] = [obj for index, obj in obj_pool.items() if function(obj.ThreadName)[1] < self.ConfigManager.TaskThreshold]
        return not_full_threads

    @staticmethod
    def _checkNonWorkingThread(thread_type: Literal["Core", "Expand"]) -> List[_ThreadObject]:
        global _CORE_THREAD_POOL, _EXPAND_THREAD_POOL
        obj_pool: Union[_CORE_THREAD_POOL, _EXPAND_THREAD_POOL] = _CORE_THREAD_POOL if thread_type == "Core" else _EXPAND_THREAD_POOL
        not_working_threads: List[_ThreadObject] = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_threads

    def _checkMinimumLoadThread(self, threads: List[_ThreadObject], thread_type: Literal["Core", "Expand"]) -> _ThreadObject:
        function: Union[_StatusManager.getCoreThreadTaskStatus, _StatusManager.getExpandThreadTaskStatus] = self.StatusManager.getCoreThreadTaskStatus if thread_type == "Core" else self.StatusManager.getExpandThreadTaskStatus
        available_threads: List[_ThreadObject] = [t for t in threads if t != self.LastSelectedThread] if self.LastSelectedThread is not None else threads
        if not available_threads:
            selected_thread: _ThreadObject = threads[0]
        else:
            selected_thread: _ThreadObject = min(available_threads, key=lambda x: function(x.ThreadName)[1])
        self.LastSelectedThread: _ThreadObject = selected_thread
        return selected_thread


class _ConcurrentSystem:
    INSTANCE: _ConcurrentSystem = None
    _INITIALIZED: bool = False

    def __new__(cls, status_manager: _StatusManager, config_manager: _ConfigManager, main_event_loop: asyncio.AbstractEventLoop):
        if cls.INSTANCE is None:
            cls.INSTANCE = super(_ConcurrentSystem, cls).__new__(cls)
        return cls.INSTANCE

    def __init__(self, status_manager: _StatusManager, config_manager: _ConfigManager, main_event_loop: asyncio.AbstractEventLoop):
        if _ConcurrentSystem._INITIALIZED:
            return
        self.StatusManager: _StatusManager = status_manager
        self.ConfigManager: _ConfigManager = config_manager
        self.MainEventLoop: asyncio.AbstractEventLoop = main_event_loop
        self.ProcessTaskStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.ThreadTaskStorageQueue: queue.Queue = queue.Queue()
        self.SystemProcessPoolExecutor: Optional[ProcessPoolExecutor] = None
        self.SystemThreadPoolExecutor: Optional[ThreadPoolExecutor] = None
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0:
            self.SystemProcessPoolExecutor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=self.ConfigManager.CoreProcessCount)
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0:
            self.SystemThreadPoolExecutor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.ConfigManager.CoreThreadCount)
        self.LoadBalancer: _LoadBalancer = _LoadBalancer(self.StatusManager, self.ConfigManager, self.SystemThreadPoolExecutor)
        self.ProcessTaskScheduler: _ProcessTaskScheduler = _ProcessTaskScheduler(self.StatusManager, self.ConfigManager, self.ProcessTaskStorageQueue)
        self.ThreadTaskScheduler: _ThreadTaskScheduler = _ThreadTaskScheduler(self.StatusManager, self.ConfigManager, self.ThreadTaskStorageQueue)
        self.CallbackProcessor: _CallbackProcessor = _CallbackProcessor(status_manager)
        self._initSystem()
        _ConcurrentSystem._INITIALIZED = True

    def _initSystem(self) -> None:
        global _CORE_PROCESS_POOL, _CORE_THREAD_POOL
        if SYSTEM_TYPE == "Windows":
            self._setMainProcessPriority()
        futures: List[Future] = []
        default_thread_pool = ThreadPoolExecutor(max_workers=self.ConfigManager.CoreProcessCount + self.ConfigManager.CoreThreadCount)
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0:
            for i in range(self.ConfigManager.CoreProcessCount):
                process_name = f"Process-{i}"
                future: Future = default_thread_pool.submit(self._startCoreProcess, process_name)
                futures.append(future)
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0:
            for i in range(self.ConfigManager.CoreThreadCount):
                thread_name = f"Thread-{i}"
                future: Future = default_thread_pool.submit(self._startCoreThread, thread_name)
                futures.append(future)
        for future in futures:
            future.result()
        if self.ConfigManager.CoreProcessCount is not None and self.ConfigManager.CoreProcessCount > 0:
            self.ProcessTaskScheduler.start()
        if self.ConfigManager.CoreThreadCount is not None and self.ConfigManager.CoreThreadCount > 0:
            self.ThreadTaskScheduler.start()
        self.LoadBalancer.start()
        self.CallbackProcessor.start(self.MainEventLoop)
        default_thread_pool.shutdown(wait=True, cancel_futures=True)

    def _setMainProcessPriority(self) -> None:
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
            result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping.get(self.ConfigManager.MainProcessPriority, priority_mapping["NORMAL"]))
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"Set priority failed with error code {error_code}.")
        except Exception as e:
            _DEFAULT_LOGGER.error(f"[MainProcess - {os.getpid()}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _startCoreProcess(self, process_name: str) -> _ProcessObject:
        global _CORE_PROCESS_POOL
        process_object: _ProcessObject = _ProcessObject(process_name, "Core", self.StatusManager, self.ConfigManager)
        process_object.start()
        _CORE_PROCESS_POOL[process_name] = process_object
        self.StatusManager.updateCoreProcessLoadStatus(process_name, process_object.pid, 0)
        self.StatusManager.updateCoreProcessTaskStatus(process_name, process_object.pid, 0)
        return process_object

    def _startCoreThread(self, thread_name: str) -> _ThreadObject:
        global _CORE_THREAD_POOL
        thread_object: _ThreadObject = _ThreadObject(thread_name, "Core", self.StatusManager, self.ConfigManager, self.SystemThreadPoolExecutor)
        thread_object.start()
        _CORE_THREAD_POOL[thread_name] = thread_object
        self.StatusManager.updateCoreThreadTaskStatus(thread_name, thread_object.ident, 0)
        return thread_object


def _connectConcurrentSystem(shared_manager: multiprocessing.Manager, main_event_loop: asyncio.AbstractEventLoop, **config: Unpack[_Config]) -> _ConcurrentSystem:
    _status_manager = _StatusManager(shared_manager)
    _config_manager = _ConfigManager(shared_manager, **config)
    _concurrent_system = _ConcurrentSystem(_status_manager, _config_manager, main_event_loop)
    return _concurrent_system


def _closeConcurrentSystem() -> None:
    global _CORE_PROCESS_POOL, _CORE_THREAD_POOL, _EXPAND_PROCESS_POOL, _EXPAND_THREAD_POOL
    if multiprocessing.current_process().name != 'MainProcess':
        raise RuntimeError("System closing must be done in the main process.")
    if _ConcurrentSystem.INSTANCE is None:
        return
    futures: List[Future] = []
    default_thread_pool = ThreadPoolExecutor(max_workers=_ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount + _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount)
    for process_name, process_obj in _CORE_PROCESS_POOL.items():
        future: Future = default_thread_pool.submit(process_obj.stop)
        futures.append(future)
    for thread_name, thread_obj in _CORE_THREAD_POOL.items():
        future: Future = default_thread_pool.submit(thread_obj.stop)
        futures.append(future)
    for process_name, process_obj in _EXPAND_PROCESS_POOL.items():
        future: Future = default_thread_pool.submit(process_obj.stop)
        futures.append(future)
    for thread_name, thread_obj in _EXPAND_THREAD_POOL.items():
        future: Future = default_thread_pool.submit(thread_obj.stop)
        futures.append(future)
    for future in futures:
        future.result()
    _ConcurrentSystem.INSTANCE.LoadBalancer.stop()
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount is not None and _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount > 0:
        _ConcurrentSystem.INSTANCE.ProcessTaskScheduler.stop()
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount is not None and _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount > 0:
        _ConcurrentSystem.INSTANCE.ThreadTaskScheduler.stop()
    _ConcurrentSystem.INSTANCE.CallbackProcessor.close()
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount is not None and _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount > 0:
        _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.shutdown(wait=True, cancel_futures=True)
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount is not None and _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount > 0:
        _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.shutdown(wait=True, cancel_futures=True)
    default_thread_pool.shutdown(wait=True, cancel_futures=True)


def submitAsyncTask(task: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs) -> asyncio.Future | None:
    from . import MainEventLoop
    if not asyncio.iscoroutinefunction(task):
        _DEFAULT_LOGGER.warning(f"The task <{task.__name__}> must be a coroutine function.")
        return None
    task_future = MainEventLoop().create_task(task(*args, **kwargs))
    return task_future


def submitProcessTask(task: callable, priority: int = 0, callback: Optional[callable] = None, future: Optional[type(TaskFuture)] = None, *args, **kwargs: Unpack[_TaskConfig]) -> TaskFuture | None:
    global _CALLBACK_FUNCTION, _CORE_PROCESS_POOL, _EXPAND_PROCESS_POOL, _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT
    if multiprocessing.current_process().name != 'MainProcess':
        _DEFAULT_LOGGER.warning("Process task submission must be done in the main process.")
        return None
    if _ConcurrentSystem.INSTANCE is None:
        _DEFAULT_LOGGER.warning("TheSeedCore ConcurrentSystem has not been initialized.")
        return None
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount == 0:
        _DEFAULT_LOGGER.warning("Core process count not set. Process task submission is not allowed.")
        return None
    task_id: str = str(uuid.uuid4())
    future_instance: TaskFuture = future() if future is not None else TaskFuture(task_id)
    try:
        pickle.dumps(task)
    except (pickle.PicklingError, AttributeError, TypeError) as e:
        _DEFAULT_LOGGER.error(f"Task [{task.__name__} - {task_id}] serialization failed. Task submission has been rejected.\n{e}")
        return None
    if callback is not None:
        _CALLBACK_FUNCTION[task_id] = callback
    task_object: _TaskObject = _TaskObject(task, task_id, False if callback is None else True, *args, **kwargs)
    _ConcurrentSystem.INSTANCE.ProcessTaskStorageQueue.put_nowait((priority if not priority > 10 else 0, task_object))
    _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
    _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.notify_all()
    _PROCESS_TASK_SCHEDULING_ADD_TASK_EVENT.release()
    return future_instance


def submitThreadTask(task: callable, priority: int = 0, callback: callable = None, future: type(TaskFuture) = None, *args, **kwargs: Unpack[_TaskConfig]) -> TaskFuture | None:
    global _CALLBACK_FUNCTION, _THREAD_TASK_SCHEDULING_EVENT
    if multiprocessing.current_process().name != 'MainProcess':
        _DEFAULT_LOGGER.warning("Thread task submission must be done in the main process.")
        return None
    if _ConcurrentSystem.INSTANCE is None:
        _DEFAULT_LOGGER.warning("TheSeedCore ConcurrentSystem has not been initialized.")
        return None
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount == 0:
        _DEFAULT_LOGGER.warning("Core thread count not set. Thread task submission is not allowed.")
        return None
    task_id: str = str(uuid.uuid4())
    future_instance: TaskFuture = future() if future is not None else TaskFuture(task_id)
    if callback is not None:
        _CALLBACK_FUNCTION[task_id] = callback
    task_object: _TaskObject = _TaskObject(task, task_id, False if callback is None else True, *args, **kwargs)
    _ConcurrentSystem.INSTANCE.ThreadTaskStorageQueue.put_nowait((priority if not priority > 10 else 0, task_object))
    _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.acquire()
    _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.notify_all()
    _THREAD_TASK_SCHEDULING_ADD_TASK_EVENT.release()
    return future_instance


def submitSystemProcessTask(task: callable, count: int = 1, *args, **kwargs) -> Union[Future, List[Future], None]:
    if _ConcurrentSystem.INSTANCE is None:
        _DEFAULT_LOGGER.warning("The ConcurrentSystem has not been initialized.")
        return None
    if not callable(task):
        _DEFAULT_LOGGER.warning("The task must be a callable.")
        return None
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreProcessCount == 0:
        _DEFAULT_LOGGER.warning("Core process count not set. Process task submission is not allowed.")
        return None
    futures: List[Future] = []
    if count > 1:
        for i in range(count):
            future: Future = _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.submit(task, *args, **kwargs)
            futures.append(future)
        return futures
    future: Future = _ConcurrentSystem.INSTANCE.SystemProcessPoolExecutor.submit(task, *args, **kwargs)
    return future


def submitSystemThreadTask(task: callable, count: int = 1, *args, **kwargs) -> Union[Future, List[Future], None]:
    if _ConcurrentSystem.INSTANCE is None:
        _DEFAULT_LOGGER.warning("The ConcurrentSystem has not been initialized.")
        return None
    if not callable(task):
        _DEFAULT_LOGGER.warning("The task must be a callable.")
        return None
    if _ConcurrentSystem.INSTANCE.ConfigManager.CoreThreadCount == 0:
        _DEFAULT_LOGGER.warning("Core thread count not set. Thread task submission is not allowed.")
        return None
    futures: List[Future] = []
    if count > 1:
        for i in range(count):
            future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(task, *args, **kwargs)
            futures.append(future)
        return futures
    future: Future = _ConcurrentSystem.INSTANCE.SystemThreadPoolExecutor.submit(task, *args, **kwargs)
    return future
