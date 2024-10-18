# -*- coding: utf-8 -*-
"""
TheSeedCore ConcurrentSystem

Author: 疾风Kirito
Version: 1.1.0
Date: 2024-10-16

Description:
    The TheSeedCore ConcurrentSystem module provides a robust and scalable concurrent processing system.
    It is designed to efficiently manage and execute tasks across multiple processes and threads.
    The system supports both asynchronous and synchronous task execution.

    Additionally, it offers features such as task prioritization, retries on failure, and execution timeouts.
    Optional GPU acceleration using PyTorch is available.
    The system includes dynamic resource management policies that allow it to expand or shrink resources based on system load.

    This system abstracts the complexities of inter-process communication, synchronization, and resource allocation.
    It enables developers to focus on implementing the core logic of their tasks without worrying about the underlying concurrency mechanisms.

    The ConcurrentSystem module is particularly suitable for high-load, compute-intensive applications.
    It allows these applications to leverage multi-core CPUs and GPUs for optimal performance.

Key Features:
    - Asynchronous and Synchronous Task Execution: Supports both coroutine functions (`async def`) and regular functions.
    - Priority Queues: Tasks can be assigned priorities, ensuring that critical tasks are executed first.
    - Retry Mechanism: Tasks can be configured to retry on failure up to a specified maximum number of retries.
    - Timeout Handling: Tasks can have execution time limits, after which they are cancelled if not completed.
    - GPU Acceleration: Optional GPU boosting using PyTorch for tasks that can leverage GPU computation.
    - Resource Management Policies: Configurable policies for expanding or shrinking resources (processes and threads) based on load.
    - Thread and Process Pools: Manages pools of worker threads and processes for efficient task execution.
    - Load Balancing: Dynamically balances the load across processes and threads to optimize resource utilization.
    - Logging and Debugging: Comprehensive logging support for monitoring and debugging.

Dependencies:
    - Python 3.11+
    - Optional dependencies:
        - PyTorch: Required for GPU acceleration features.
        - PyQt5 or PySide6: Required if integrating with a Qt application.
        - qasync: Required if integrating the asyncio event loop with a Qt event loop.

Classes:
    - _Config:
        A data class that holds configuration settings for the system, including priority levels, core counts, maximum counts, thresholds, and policies.

    - _ConfigManager:
        Validates and manages configuration settings.
        Ensures that provided values are within acceptable ranges and provides default values when necessary.
        Sets up logging for the system.

    - _SynchronizationManager:
        Handles synchronization and shared state across processes and threads.
        Maintains task and load statuses, ensuring thread-safe updates using locks.
        Uses a multiprocessing manager to share state across different processes.

    - _TaskObject:
        Encapsulates all information related to a task, including:
        - The callable function to execute.
        - Task identifiers and types.
        - Execution configurations like timeouts, retries, and GPU acceleration.
        - Serialization and deserialization of arguments, handling cases where objects are not serializable.
        - Methods to prepare tasks for execution, including transferring data to GPU if necessary.

    - _ProcessObject:
        Represents a worker process that executes tasks. Key responsibilities include:
        - Managing task execution with respect to priorities.
        - Handling task retries, timeouts, and locking.
        - Synchronizing access to shared resources when tasks require locking.
        - Updating task statuses in the synchronization manager.
        - Performing memory cleanup.

    - _ThreadObject:
        Similar to `_ProcessObject`, but for threads within the same process.
        Handles task execution in a multithreaded environment, utilizing an asyncio event loop for asynchronous task execution.

    - _LoadBalancer:
        Manages load balancing across processes and threads by performing periodic cleanup and monitoring of resource usage.
        Dynamically adjusts the number of active processes and threads based on load and usage patterns, ensuring optimal resource utilization.

    - _ProcessTaskScheduler:
        Schedules and manages the execution of tasks in processes.
        Ensures efficient task allocation based on process availability, priority,
        and load conditions, and updates the synchronization manager with the current status of processes.

    - _ThreadTaskScheduler:
        Similar to `_ProcessTaskScheduler`, but for threads within the same process.
        Manages task scheduling and execution in a multithreaded environment, distributing tasks across threads efficiently.

    - TaskFuture:
        Represents the future result of a task execution, providing mechanisms to retrieve the result once the task is completed.
        Supports blocking retrieval with an optional timeout and is compatible with both synchronous and asynchronous tasks.

    - ConcurrentSystem:
        Manages the concurrent system for executing tasks in both process and thread pools.
        Implements the Singleton pattern to ensure only one instance is created, which is crucial for consistent task management and logging.
        Handles task submission, system initialization, resource management, and provides methods for submitting tasks and closing the system.

Methods:
    - _ConfigManager.validateConfig():
        Validates the configuration settings provided in the `_Config` instance,
        ensuring they are within acceptable ranges and setting default values when necessary.

    - _SynchronizationManager.updateCoreProcessLoadStatus(process_name, pid, load):
        Updates the load status of a core process in the synchronization manager.

    - _TaskObject.prepareForExecution():
        Prepares the task for execution, including deserializing arguments
        and transferring data to GPU if GPU boosting is enabled.

    - _ProcessObject.addProcessTask(priority, task_object):
        Adds a task to the process's priority queue for execution.

    - _ThreadObject.addThreadTask(priority, task_object):
        Adds a task to the thread's priority queue for execution.

    - _LoadBalancer.run():
        Runs the load balancer, performing periodic memory cleanup
        and managing process and thread loads based on the configured policies.

    - _ProcessTaskScheduler.run():
        Continuously runs the task scheduler for processes,
        processing tasks from the process task storage queue until closed.

    - _ThreadTaskScheduler.run():
        Continuously runs the task scheduler for threads,
        processing tasks from the thread task storage queue until closed.

    - TaskFuture.result(timeout=None):
        Retrieves the result of the task, waiting until it is available or the timeout is reached.
        Raises a `TimeoutError` if the task execution does not complete within the specified timeout.

    - ConcurrentSystem.submitProcessTask(...):
        Submits a task to be executed in the process pool with optional parameters and a callback function.
        Returns a `TaskFuture` instance for tracking the task execution.

    - ConcurrentSystem.submitThreadTask(...):
        Submits a task to be executed in the thread pool with optional parameters and a callback function.
        Returns a `TaskFuture` instance for tracking the task execution.

    - ConcurrentSystem.submitSystemProcessTask(task, count=1, *args, **kwargs):
        Submits a task to be executed in the system process pool.
        Used for internal or system-level tasks that require process-level isolation.

    - ConcurrentSystem.submitSystemThreadTask(task, count=1, *args, **kwargs):
        Submits a task to be executed in the system thread pool.
        Used for internal or system-level tasks that can be executed in threads.

    - ConcurrentSystem.closeSystem():
        Closes the concurrent system, stopping all processes and threads, and performing cleanup operations.

    - ConnectConcurrentSystem(**kwargs):
        Initializes and connects to the concurrent system with the given configuration settings.
        Returns an instance of `ConcurrentSystem`.

Exceptions:
    - RuntimeError:
        Raised when methods are called in inappropriate contexts, such as submitting tasks from a non-main process or before the system is initialized.

    - ValueError:
        Raised when invalid parameters are provided to methods, such as non-callable tasks.

    - TimeoutError:
        Raised by `TaskFuture.result()` if the task execution does not complete within the specified timeout.

    - NotImplementedError:
        Raised when abstract methods in `TaskFuture` are not implemented in subclasses.

    - pickle.PicklingError:
        Raised when a task cannot be serialized for process execution, indicating that the task submission has been rejected.

    -*TypeError:
        Raised when incorrect types are provided to methods or functions, such as non-boolean values for `DebugMode`.

Copyright Notice:
    Copyright (c) 2024 疾风Kirito <1453882193@qq.com>
    All rights reserved.

License:
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Disclaimer:
    The author of this software is not responsible for any damages, losses, or other liabilities resulting from the use of this software.
    Use at your own risk.
"""

from __future__ import annotations

__author__ = "疾风Kirito"
__version__ = "1.1.0"
__date__ = "2024-10-16"
__all__ = [
    "ConcurrentSystem",
    "TaskFuture",
    "ConnectConcurrentSystem",
    "PyTorchSupport",
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
import platform
import queue
import subprocess
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import CancelledError, ProcessPoolExecutor, ThreadPoolExecutor
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, TYPE_CHECKING, Tuple, Union

if TYPE_CHECKING:
    pass

_SystemType = platform.system()
_IsMainProcess = True if multiprocessing.current_process().name == 'MainProcess' else False
_AvailableCUDADevicesID: list = []
PyTorchSupport: multiprocessing.Value = multiprocessing.Value('b', False)
PySide6Support: bool = False
PyQt6Support: bool = False
PyQt5Support: bool = False
_AllowQtMode = False
_CallbackObject: Dict[str, callable] = {}
_FutureResult: Dict[str, Any] = {}
_CoreProcessPool: Dict[str, _ProcessObject] = {}
_ExpandProcessPool: Dict[str, _ProcessObject] = {}
_ExpandProcessSurvivalTime: Dict[str, float] = {}
_CoreThreadPool: Dict[str, _ThreadObject] = {}
_ExpandThreadPool: Dict[str, _ThreadObject] = {}
_ExpandThreadSurvivalTime: Dict[str, float] = {}
_ProcessTaskSchedulingEvent = threading.Event()
_ThreadTaskSchedulingEvent = threading.Event()
_ProcessBalanceLock = threading.Lock()
_ThreadBalanceLock = threading.Lock()


def _showBanner(sm_pid: int):
    CYAN_BOLD = "\033[1m\033[36m"
    RESET = "\033[0m"
    print(CYAN_BOLD + "   ______                                                               __    _____                    __                   ")
    print(CYAN_BOLD + "  / ____/  ____    ____   _____  __  __   _____   _____  ___    ____   / /_  / ___/   __  __   _____  / /_  ___    ____ ___ ")
    print(CYAN_BOLD + " / /      / __ \\  / __ \\ / ___/ / / / /  / ___/  / ___/ / _ \\  / __ \\ / __/  \\__ \\   / / / /  / ___/ / __/ / _ \\  / __ `__ \\")
    print(CYAN_BOLD + "/ /___   / /_/ / / / / // /__  / /_/ /  / /     / /    /  __/ / / / // /_   ___/ /  / /_/ /  (__  ) / /_  /  __/ / / / / / /")
    print(CYAN_BOLD + "\\____/   \\____/ /_/ /_/ \\___/  \\__,_/  /_/     /_/     \\___/ /_/ /_/ \\__/  /____/   \\__, /  /____/  \\__/  \\___/ /_/ /_/ /_/ ")
    print(CYAN_BOLD + "                                                                                   /____/                                  " + RESET)
    print(CYAN_BOLD + f"MainProcess - {os.getpid()}" + RESET)
    print(CYAN_BOLD + f"ServiceProcess - {sm_pid}" + RESET)


def _checkDependencies() -> None:
    """
    Checks and verifies the availability of necessary dependencies for the application.

    :return: None
    :exception: None

    setup:
        - 1. Attempt to import the PyTorch library
            a. If successful, check if CUDA is available
                i. If CUDA is available, populate the list of available CUDA device IDs and set PyTorchSupport to True
                ii. If CUDA is not available, set PyTorchSupport to False and clear the available CUDA devices list
            b. If the import fails, set PyTorchSupport to False and clear the available CUDA devices list
        - 2. Attempt to import the PySide6 library
            a. If successful, set PySide6Support to True
            b. If the import fails, set PySide6Support to False
        - 3. Attempt to import the PyQt6 library
            a. If successful, set PyQt6Support to True
            b. If the import fails, set PyQt6Support to False
        - 4. Attempt to import the PyQt5 library
            a. If successful, set PyQt5Support to True
            b. If the import fails, set PyQt5Support to False
    """

    global PyTorchSupport, _AvailableCUDADevicesID, PySide6Support, PyQt6Support, PyQt5Support
    try:
        # noinspection PyUnresolvedReferences
        import torch

        if torch.cuda.is_available():
            _AvailableCUDADevicesID = [cuda_device_id for cuda_device_id in range(torch.cuda.device_count())]
            PyTorchSupport.value = True
        else:
            _AvailableCUDADevicesID = []
            PyTorchSupport.value = False
    except ImportError as _:
        _AvailableCUDADevicesID = []
        PyTorchSupport.value = False

    try:
        import qasync
        from PySide6.QtWidgets import QApplication

        PySide6Support = True
    except ImportError as _:
        PySide6Support = False

    try:
        import qasync
        from PyQt6.QtWidgets import QApplication
        PyQt6Support = True
    except ImportError as _:
        PyQt6Support = False

    try:
        import qasync
        from PyQt5.QtWidgets import QApplication
        PyQt5Support = True
    except ImportError as _:
        PyQt5Support = False


class _ColoredFormatter(logging.Formatter):
    """
    A custom logging formatter that adds color to log messages based on their severity level.

    Attributes:
        COLORS: A dictionary mapping logging levels to ANSI color codes for terminal output.
        RESET: A string used to reset the terminal color back to default.

    Methods:
        format: Formats the log record with appropriate color based on its level.
    """

    COLORS = {
        logging.DEBUG: "\033[1;34m",
        logging.INFO: "\033[1;32m",
        logging.WARNING: "\033[1;33m",
        logging.ERROR: "\033[0;31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        message = super().format(record)
        color = self.COLORS.get(record.levelno, self.RESET)
        return f"{color}{message}{self.RESET}"


class _LinuxMonitor:
    """
    A singleton class that monitors system resources on Linux, providing information about CPU and memory usage.

    Attributes:
        _INSTANCE: Singleton instance of the _LinuxMonitor class.
        _INITIALIZED: A flag indicating whether the monitor has been initialized.

    Methods:
        physicalCpuCores: Retrieves the number of physical CPU cores available on the system.
        logicalCpuCores: Retrieves the number of logical CPU cores available on the system.
        totalPhysicalMemory: Retrieves the total physical memory of the system in bytes.
        totalVirtualMemory: Retrieves the total virtual memory of the system in bytes.
        totalCpuUsage: Retrieves the total CPU usage of the system over a specified interval.
        processCpuUsage: Retrieves the CPU usage of a process given its process ID (pid) over a specified interval.
        processMemoryUsage: Retrieves the memory usage of a process given its process ID (pid).
    """

    _INSTANCE: _LinuxMonitor = None
    _INITIALIZED: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        self._stat_path = "/proc/stat"
        self._cpu_info_path = "/proc/cpuinfo"
        self._mem_info_path = "/proc/meminfo"

    @classmethod
    def physicalCpuCores(cls) -> int:
        """
        Retrieves the number of physical CPU cores available on the system.

        :return: The number of physical CPU cores
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the CPU info file cannot be found

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Open the CPU info file located at the specified path
            - 3. Read the contents of the file and split it into lines
            - 4. Count the number of lines that start with 'physical id' to determine the number of physical CPU cores
            - 5. Return the total count of physical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        with open(cls._INSTANCE._cpu_info_path, 'r') as f:
            cpuinfo = f.read().splitlines()
            return sum(1 for line in cpuinfo if line.startswith('physical id'))

    @classmethod
    def logicalCpuCores(cls) -> int:
        """
        Retrieves the number of logical CPU cores available on the system.

        :return: The number of logical CPU cores
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Use os.cpu_count() to retrieve the number of logical CPU cores
            - 3. Return the number of logical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        return os.cpu_count()

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        """
        Retrieves the total physical memory of the system.

        :return: The total physical memory in bytes
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the memory info file cannot be found
        :exception ValueError: Raised if the total memory size cannot be converted to an integer

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Open the memory info file located at the specified path
            - 3. Read through the file line by line to find the line starting with 'MemTotal'
                a. Extract the total memory value, converting it from kilobytes to bytes
            - 4. Return the total physical memory in bytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        with open(cls._INSTANCE._mem_info_path, 'r') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    return int(line.split()[1]) * 1024

    @classmethod
    def totalVirtualMemory(cls) -> int:
        """
        Retrieves the total virtual memory of the system, specifically the total swap memory.

        :return: The total virtual memory (swap memory) in bytes
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the memory info file cannot be found
        :exception ValueError: Raised if the swap memory size cannot be converted to an integer

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Open the memory info file located at the specified path
            - 3. Read through the file line by line to find the line starting with 'SwapTotal'
                a. Extract the swap total value, converting it from kilobytes to bytes
            - 4. Return the total swap memory in bytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        with open(cls._INSTANCE._mem_info_path, 'r') as f:
            swap_total = 0
            for line in f:
                if line.startswith('SwapTotal'):
                    swap_total = int(line.split()[1]) * 1024
            return swap_total

    @classmethod
    def totalCpuUsage(cls, interval: float = 1.0) -> float:
        """
        Retrieves the total CPU usage of the system over a specified interval on Linux.

        :param interval: The time interval (in seconds) to measure total CPU usage (default is 1.0 seconds)
        :return: The total CPU usage percentage of the system
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the CPU info file cannot be found
        :exception ValueError: Raised if CPU times cannot be converted to integers

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Open the CPU info file and read the initial CPU times
                a. Extract the relevant fields and convert them to integers
            - 3. Sleep for the specified interval to allow for CPU time accumulation
            - 4. Reopen the CPU info file and read the final CPU times
                a. Extract the relevant fields and convert them to integers
            - 5. Calculate the idle time and total time from the CPU times
            - 6. Calculate the CPU usage percentage based on the elapsed times
            - 7. Return the CPU usage as a float percentage
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        with open(cls._INSTANCE._cpu_info_path, 'r') as f:
            cpu_times_start = f.readline().split()[1:8]
            cpu_times_start = [int(x) for x in cpu_times_start]
        time.sleep(interval)
        with open(cls._INSTANCE._cpu_info_path, 'r') as f:
            cpu_times_end = f.readline().split()[1:8]
            cpu_times_end = [int(x) for x in cpu_times_end]
        idle_start = cpu_times_start[3]
        idle_end = cpu_times_end[3]
        total_start = sum(cpu_times_start)
        total_end = sum(cpu_times_end)
        idle_time = idle_end - idle_start
        total_time = total_end - total_start
        cpu_usage = (1 - idle_time / total_time) * 100
        return cpu_usage

    @classmethod
    def processCpuUsage(cls, pid: int, interval: float = 1.0) -> int:
        """
        Retrieves the CPU usage of a process given its process ID (pid) on Linux over a specified interval.

        :param pid: The process ID of the target process
        :param interval: The time interval (in seconds) to measure CPU usage (default is 1.0 seconds)
        :return: The CPU usage percentage of the process, capped between 0 and 100
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the specified process stat file cannot be found
        :exception ValueError: Raised if CPU times cannot be converted to integers

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Define the path to the process stat file for the specified PID
            - 3. Open the process stat file and read the initial CPU times (user time and system time)
            - 4. Calculate the total CPU time for the process at the start
            - 5. Open the system stat file to get the initial CPU times for all cores
            - 6. Sleep for the specified interval to allow for CPU time accumulation
            - 7. Reopen the process stat file and read the final CPU times
            - 8. Calculate the total CPU time for the process at the end
            - 9. Open the system stat file to get the final CPU times for all cores
            - 10. Calculate the difference in CPU time for the process and the system
            - 11. Determine the number of CPU cores
            - 12. Calculate the CPU usage percentage based on the elapsed times
            - 13. Return the CPU usage as an integer percentage, ensuring it is capped between 0 and 100
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")

        proc_stat_path = f'/proc/{pid}/stat'
        with open(proc_stat_path, 'r') as f:
            proc_stat_start = f.readline().split()
        utime_start = int(proc_stat_start[13])
        stime_start = int(proc_stat_start[14])
        total_start = utime_start + stime_start
        with open(cls._INSTANCE._stat_path, 'r') as f:
            cpu_times_start = f.readline().split()[1:8]
        total_cpu_start = sum([int(x) for x in cpu_times_start])
        time.sleep(interval)
        with open(proc_stat_path, 'r') as f:
            proc_stat_end = f.readline().split()
        utime_end = int(proc_stat_end[13])
        stime_end = int(proc_stat_end[14])
        total_end = utime_end + stime_end
        with open(cls._INSTANCE._stat_path, 'r') as f:
            cpu_times_end = f.readline().split()[1:8]
        total_cpu_end = sum([int(x) for x in cpu_times_end])
        proc_time = total_end - total_start
        total_time = total_cpu_end - total_cpu_start
        num_cores = os.cpu_count()
        cpu_usage = (proc_time / total_time) * num_cores * 100
        return max(0, min(int(cpu_usage), 100))

    @classmethod
    def processMemoryUsage(cls, pid: int) -> int:
        """
        Retrieves the memory usage of a process given its process ID (pid) on Linux.

        :param pid: The process ID of the target process
        :return: The memory usage of the process in bytes
        :exception RuntimeError: Raised if the LinuxMonitor is not initialized
        :exception FileNotFoundError: Raised if the specified process status file cannot be found
        :exception ValueError: Raised if the memory usage cannot be converted to an integer

        setup:
            - 1. Check if the LinuxMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Open the process status file located at /proc/{pid}/status
            - 3. Read through the file line by line
                a. Look for the line starting with 'VmRSS'
            - 4. Extract the memory usage value, converting it from kilobytes to bytes
            - 5. Return the memory usage in bytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("LinuxMonitor is not initialized.")
        with open(f'/proc/{pid}/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS'):
                    return int(line.split()[1]) * 1024


class _WindowsMonitor:
    """
    A singleton class that monitors system resources on Windows, providing information about CPU and memory usage.

    Attributes:
        _INSTANCE: Singleton instance of the _WindowsMonitor class.
        _INITIALIZED: A flag indicating whether the monitor has been initialized.
        _ULONG_PTR: Data type for pointer-sized integers, dependent on system architecture.

    Nested Classes:
        PdhFmtCounterValue: Structure to hold formatted counter values from the PDH API.
        ProcessorRelationship: Structure to describe processor relationships.
        SystemLogicalProcessorInformationEx: Structure to hold logical processor information.
        FileTime: Structure to represent a file time in Windows.
        MemoryStatusEx: Structure to hold memory information.

    Methods:
        physicalCpuCores: Retrieves the number of physical CPU cores available on the system.
        logicalCpuCores: Retrieves the number of logical CPU cores available on the system.
        totalPhysicalMemory: Retrieves the total physical memory of the system in bytes.
        totalVirtualMemory: Retrieves the total virtual memory of the system in bytes.
        totalCpuUsage: Retrieves the total CPU usage of the system over a specified interval.
        processCpuUsage: Retrieves the CPU usage of a process given its process ID (pid) over a specified interval.
        processMemoryUsage: Retrieves the memory usage of a process given its process ID (pid).
    """

    _INSTANCE: _WindowsMonitor = None
    _INITIALIZED: bool = False
    _ULONG_PTR = ctypes.c_ulonglong if platform.architecture()[0] == '64bit' else ctypes.c_ulong

    class PdhFmtCounterValue(ctypes.Structure):
        _fields_ = [('CStatus', wintypes.DWORD),
                    ('doubleValue', ctypes.c_double)]

    class ProcessorRelationship(ctypes.Structure):
        pass

    class SystemLogicalProcessorInformationEx(ctypes.Structure):
        pass

    class FileTime(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]

    ProcessorRelationship._fields_ = [
        ("Flags", ctypes.c_byte),  # type: ignore
        ("EfficiencyClass", ctypes.c_byte),  # type: ignore
        ("Reserved", ctypes.c_byte * 20),  # type: ignore
        ("GroupCount", wintypes.WORD),  # type: ignore
        ("GroupMask", ctypes.POINTER(_ULONG_PTR))
    ]

    SystemLogicalProcessorInformationEx._fields_ = [
        ("Relationship", wintypes.DWORD),
        ("Size", wintypes.DWORD),
        ("Processor", ProcessorRelationship)
    ]

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        self.Pdh = ctypes.WinDLL('pdh')
        self.Kernel32 = ctypes.WinDLL('kernel32')
        self.PdhFmtDouble = 0x00000200
        self.RelationProcessorCore = 0
        self.QueryHandle = ctypes.c_void_p()
        self.CpuCounterHandle = ctypes.c_void_p()
        self.Pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.QueryHandle))
        self.Pdh.PdhAddCounterW(self.QueryHandle, r'\Processor(_Total)\% Processor Time', 0, ctypes.byref(self.CpuCounterHandle))
        self._INITIALIZED = True

    @classmethod
    def physicalCpuCores(cls) -> int:
        """
        Retrieves the number of physical CPU cores available on the system.

        :return: The number of physical CPU cores
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized
        :exception OSError: Raised if retrieving logical processor information fails

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Initialize a buffer size variable to store the size needed for logical processor information
            - 3. Call GetLogicalProcessorInformationEx with a None buffer to determine the required buffer size
            - 4. Create a buffer of the appropriate size to hold the logical processor information
            - 5. Call GetLogicalProcessorInformationEx again to retrieve the actual information into the buffer
                a. Raise an OSError if the function call fails
            - 6. Initialize a counter for the number of physical cores
            - 7. Iterate through the buffer to extract information about each logical processor
                a. If the relationship indicates a processor core, increment the counter by the processor's group count
            - 8. Return the total number of physical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        buffer_size = wintypes.DWORD(0)
        ctypes.windll.kernel32.GetLogicalProcessorInformationEx(cls._INSTANCE.RelationProcessorCore, None, ctypes.byref(buffer_size))
        buffer = (ctypes.c_byte * buffer_size.value)()
        result = ctypes.windll.kernel32.GetLogicalProcessorInformationEx(cls._INSTANCE.RelationProcessorCore, ctypes.byref(buffer), ctypes.byref(buffer_size))
        if not result:
            error_code = ctypes.windll.kernel32.GetLastError()
            raise OSError(f"GetLogicalProcessorInformationEx failed with error code {error_code}")
        num_physical_cores = 0
        offset = 0
        while offset < buffer_size.value:
            info = ctypes.cast(ctypes.byref(buffer, offset), ctypes.POINTER(cls._INSTANCE.SystemLogicalProcessorInformationEx)).contents
            if info.Relationship == cls._INSTANCE.RelationProcessorCore:
                num_physical_cores += info.Processor.GroupCount
            offset += info.Size
        return num_physical_cores

    @classmethod
    def logicalCpuCores(cls) -> int:
        """
        Retrieves the number of logical CPU cores available on the system.

        :return: The number of logical CPU cores
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Call GetActiveProcessorCount from the kernel32 library to retrieve the number of logical CPU cores
            - 3. Return the number of logical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        return ctypes.windll.kernel32.GetActiveProcessorCount(0)

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        """
        Retrieves the total physical memory of the system.

        :return: The total physical memory in bytes
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Create an instance of MemoryStatusEx to hold memory information
            - 3. Set the length of the memory status structure to the size of MemoryStatusEx
            - 4. Call GlobalMemoryStatusEx to fill the memory status structure with current memory information
            - 5. Return the total physical memory size from the memory status structure
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        memory_status = cls._INSTANCE.MemoryStatusEx()
        memory_status.dwLength = ctypes.sizeof(cls._INSTANCE.MemoryStatusEx)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        return memory_status.ullTotalPhys

    @classmethod
    def totalVirtualMemory(cls) -> int:
        """
        Retrieves the total virtual memory of the system.

        :return: The total virtual memory in bytes
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Create an instance of MemoryStatusEx to hold memory information
            - 3. Set the length of the memory status structure to the size of MemoryStatusEx
            - 4. Call GlobalMemoryStatusEx to fill the memory status structure with current memory information
            - 5. Return the total page file size from the memory status structure as the total virtual memory
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        memory_status = cls._INSTANCE.MemoryStatusEx()
        memory_status.dwLength = ctypes.sizeof(cls._INSTANCE.MemoryStatusEx)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        return memory_status.ullTotalPageFile

    @classmethod
    def totalCpuUsage(cls, interval: float = 0.1) -> float:
        """
        Retrieves the total CPU usage of the system over a specified interval using Windows Performance Data Helper (PDH).

        :param interval: The time interval (in seconds) to measure total CPU usage (default is 0.1 seconds)
        :return: The total CPU usage percentage of the system
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized
        :exception OSError: Raised if the formatted counter value cannot be retrieved

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Collect initial CPU usage data using PdhCollectQueryData
            - 3. Sleep for the specified interval to allow for CPU usage data to accumulate
            - 4. Collect CPU usage data again using PdhCollectQueryData
            - 5. Retrieve the formatted counter value for CPU usage
                a. Raise an OSError if retrieving the counter value fails
            - 6. Return the CPU usage as a double value
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        cls._INSTANCE.Pdh.PdhCollectQueryData(cls._INSTANCE.QueryHandle)
        time.sleep(interval)
        cls._INSTANCE.Pdh.PdhCollectQueryData(cls._INSTANCE.QueryHandle)
        counter_value = cls._INSTANCE.PdhFmtCounterValue()
        status = cls._INSTANCE.Pdh.PdhGetFormattedCounterValue(cls._INSTANCE.CpuCounterHandle, cls._INSTANCE.PdhFmtDouble, None, ctypes.byref(counter_value))
        if status != 0:
            raise OSError(f"PdhGetFormattedCounterValue failed with error code {status}")
        return counter_value.doubleValue

    @classmethod
    def processCpuUsage(cls, pid: int, interval: float = 0.001) -> int:
        """
        Retrieves the CPU usage of a process given its process ID (pid) on Windows over a specified interval.

        :param pid: The process ID of the target process
        :param interval: The time interval (in seconds) to measure CPU usage (default is 0.001 seconds)
        :return: The CPU usage percentage of the process, capped between 0 and 100
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized
        :exception OSError: Raised if the process cannot be opened or if there are errors retrieving process/system times

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Define constants for process access rights
            - 3. Attempt to open the specified process using its process ID
                a. Raise an OSError if the process cannot be opened
            - 4. Initialize variables to hold kernel and user time for the process at the start
            - 5. Call GetProcessTimes to retrieve the initial times for the process
                a. Raise an OSError if this fails
            - 6. Call GetSystemTimes to retrieve the system-wide kernel and user times at the start
                a. Raise an OSError if this fails
            - 7. Sleep for the specified interval
            - 8. Retrieve the process times again using GetProcessTimes after the interval
                a. Raise an OSError if this fails
            - 9. Retrieve the system times again using GetSystemTimes
                a. Raise an OSError if this fails
            - 10. Calculate the elapsed CPU time for the process and the system
            - 11. Calculate the CPU usage percentage based on the elapsed times and the number of active processor cores
            - 12. Return the CPU usage as an integer percentage, ensuring it is capped between 0 and 100
            - 13. Ensure the process handle is closed in a finally block
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not handle:
            error_code = ctypes.windll.kernel32.GetLastError()
            raise OSError(f"Failed to open process {pid}. Error code: {error_code}")
        kernel_time_start = cls.FileTime()
        user_time_start = cls.FileTime()
        kernel_time_end = cls.FileTime()
        user_time_end = cls.FileTime()
        try:
            result = ctypes.windll.kernel32.GetProcessTimes(
                handle,
                ctypes.byref(cls.FileTime()),
                ctypes.byref(cls.FileTime()),
                ctypes.byref(kernel_time_start),
                ctypes.byref(user_time_start)
            )
            if not result:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise OSError(f"Failed to get process times for start. Error code: {error_code}")
            idle_time_start = cls.FileTime()
            kernel_time_system_start = cls.FileTime()
            user_time_system_start = cls.FileTime()
            result = ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle_time_start),
                ctypes.byref(kernel_time_system_start),
                ctypes.byref(user_time_system_start)
            )
            if not result:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise OSError(f"Failed to get system times. Error code: {error_code}")
            time.sleep(interval)
            result = ctypes.windll.kernel32.GetProcessTimes(
                handle,
                ctypes.byref(cls.FileTime()),
                ctypes.byref(cls.FileTime()),
                ctypes.byref(kernel_time_end),
                ctypes.byref(user_time_end)
            )
            if not result:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise OSError(f"Failed to get process times for end. Error code: {error_code}")
            idle_time_end = cls.FileTime()
            kernel_time_system_end = cls.FileTime()
            user_time_system_end = cls.FileTime()
            result = ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle_time_end),
                ctypes.byref(kernel_time_system_end),
                ctypes.byref(user_time_system_end)
            )
            if not result:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise OSError(f"Failed to get system times. Error code: {error_code}")
            process_kernel_elapsed = (kernel_time_end.dwLowDateTime + (kernel_time_end.dwHighDateTime << 32)) / 10 ** 7 - (kernel_time_start.dwLowDateTime + (kernel_time_start.dwHighDateTime << 32)) / 10 ** 7
            process_user_elapsed = (user_time_end.dwLowDateTime + (user_time_end.dwHighDateTime << 32)) / 10 ** 7 - (user_time_start.dwLowDateTime + (user_time_start.dwHighDateTime << 32)) / 10 ** 7
            process_total_elapsed = process_kernel_elapsed + process_user_elapsed
            system_kernel_elapsed = (kernel_time_system_end.dwLowDateTime + (kernel_time_system_end.dwHighDateTime << 32)) / 10 ** 7 - (kernel_time_system_start.dwLowDateTime + (kernel_time_system_start.dwHighDateTime << 32)) / 10 ** 7
            system_user_elapsed = (user_time_system_end.dwLowDateTime + (user_time_system_end.dwHighDateTime << 32)) / 10 ** 7 - (user_time_system_start.dwLowDateTime + (user_time_system_start.dwHighDateTime << 32)) / 10 ** 7
            system_total_elapsed = system_kernel_elapsed + system_user_elapsed
            num_cores = ctypes.windll.kernel32.GetActiveProcessorCount(0)
            cpu_usage_percentage = (process_total_elapsed / (system_total_elapsed * num_cores)) * 10000
            return max(0, min(int(cpu_usage_percentage), 100))
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    @classmethod
    def processMemoryUsage(cls, pid: int) -> int:
        """
        Retrieves the memory usage of a process given its process ID (pid) on Windows.

        :param pid: The process ID of the target process
        :return: The memory usage of the process in megabytes
        :exception RuntimeError: Raised if the WindowsMonitor is not initialized
        :exception OSError: Raised if the process cannot be opened

        setup:
            - 1. Check if the WindowsMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Attempt to open the specified process using its process ID
                a. Raise an OSError if the process cannot be opened
            - 3. Create a buffer to hold the process memory information
            - 4. Call GetProcessMemoryInfo to retrieve memory statistics for the process
            - 5. Extract the committed memory size from the memory counters
            - 6. Close the handle to the process
            - 7. Return the committed memory size in megabytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("WindowsMonitor is not initialized.")
        process_handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
        if not process_handle:
            raise OSError(f"Unable to open process {pid}")
        process_memory_counters = ctypes.create_string_buffer(72)
        ctypes.windll.psapi.GetProcessMemoryInfo(process_handle, process_memory_counters, 72)
        commit_size = ctypes.cast(process_memory_counters[16:24], ctypes.POINTER(ctypes.c_ulonglong)).contents.value
        ctypes.windll.kernel32.CloseHandle(process_handle)
        return commit_size / (1024 * 1024)


class _MacOSMonitor:
    """
    A singleton class that monitors system resources on macOS, providing information about CPU and memory usage.

    Attributes:
        _INSTANCE: Singleton instance of the _MacOSMonitor class.
        _INITIALIZED: A flag indicating whether the monitor has been initialized.

    Methods:
        physicalCpuCores: Retrieves the number of physical CPU cores available on the system.
        logicalCpuCores: Retrieves the number of logical CPU cores available on the system.
        totalPhysicalMemory: Retrieves the total physical memory of the system in bytes.
        totalVirtualMemory: Retrieves the total virtual memory by checking the number of swapped out pages.
        totalCpuUsage: Retrieves the total CPU usage of the system over a specified interval.
        processCpuUsage: Calculates the CPU usage of a process given its process ID (pid) over a specified interval.
        processMemoryUsage: Retrieves the memory usage of a process given its process ID (pid).
    """

    _INSTANCE: _MacOSMonitor = None
    _INITIALIZED: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        ...

    @classmethod
    def physicalCpuCores(cls) -> int:
        """
        Retrieves the number of physical CPU cores available on the system.

        :return: The number of physical CPU cores
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the core count cannot be converted to an integer

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the number of physical CPU cores using the sysctl command
            - 3. Decode the output and convert it to an integer
            - 4. Return the number of physical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.physicalcpu']).decode())

    @classmethod
    def logicalCpuCores(cls) -> int:
        """
        Retrieves the number of logical CPU cores available on the system.

        :return: The number of logical CPU cores
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the core count cannot be converted to an integer

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the number of logical CPU cores using the sysctl command
            - 3. Decode the output and convert it to an integer
            - 4. Return the number of logical CPU cores
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.logicalcpu']).decode())

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        """
        Retrieves the total physical memory of the system.

        :return: The total physical memory in bytes
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the memory size cannot be converted to an integer

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the total physical memory using the sysctl command
            - 3. Decode the output and convert it to an integer
            - 4. Return the total physical memory in bytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode())

    @classmethod
    def totalVirtualMemory(cls) -> int:
        """
        Retrieves the total virtual memory by checking the number of swapped out pages.

        :return: The total virtual memory in bytes
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the number of pages cannot be converted to an integer

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the output from the vm_stat command
            - 3. Parse the output line by line to find the line containing 'Pages swapped out'
                a. Extract and convert the number of swapped out pages from the relevant line
            - 4. Multiply the number of swapped out pages by 4096 to get the total virtual memory in bytes
            - 5. Return the total virtual memory as an integer
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        vm_stat_output = subprocess.check_output(['vm_stat']).decode()
        for line in vm_stat_output.splitlines():
            if 'Pages swapped out' in line:
                swap_out_pages = int(line.split()[3].replace('.', ''))
                return swap_out_pages * 4096

    @classmethod
    def totalCpuUsage(cls, interval: float = 1.0) -> float:
        """
        Retrieves the total CPU usage of the system over a specified interval.

        :param interval: The time interval (in seconds) to measure total CPU usage (default is 1.0 second)
        :return: The total CPU usage percentage of the system
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the CPU usage cannot be converted to a float

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the output from the top command for the specified interval
            - 3. Parse the output line by line to find the line containing 'CPU usage'
                a. Extract and convert the CPU usage percentage from the relevant line
            - 4. Return the total CPU usage as a float
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        top_output = subprocess.check_output(['top', '-l', f"{str(int(interval))}"]).decode()
        for line in top_output.splitlines():
            if 'CPU usage' in line:
                cpu_usage = float(line.split()[2].replace('%', ''))
                return cpu_usage

    @classmethod
    def processCpuUsage(cls, pid: int, interval: float = 1) -> int:
        """
        Calculates the CPU usage of a process given its process ID (pid) over a specified interval.

        :param pid: The process ID of the target process
        :param interval: The time interval (in seconds) to measure CPU usage (default is 1 second)
        :return: The CPU usage percentage of the process, capped between 0 and 100
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the CPU usage cannot be converted to a float

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Retrieve the number of logical CPU cores using the sysctl command
            - 3. Execute a subprocess command to get the initial CPU usage of the process using the ps command
                a. Parse the output to extract the initial CPU usage percentage
            - 4. Sleep for the specified interval
            - 5. Execute the subprocess command again to get the CPU usage of the process after the interval
                a. Parse the output to extract the final CPU usage percentage
            - 6. Calculate the CPU usage over the interval
                a. Compute the difference between the final and initial CPU usage, normalized by the interval and the number of cores
            - 7. Return the CPU usage as an integer percentage, ensuring it is capped between 0 and 100
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        num_cores = int(subprocess.check_output(['sysctl', '-n', 'hw.logicalcpu']).decode().strip())
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu']).decode()
        cpu_usage_start = float(ps_output.splitlines()[1].strip())
        time.sleep(interval)
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu']).decode()
        cpu_usage_end = float(ps_output.splitlines()[1].strip())
        cpu_usage = (cpu_usage_end - cpu_usage_start) / interval / num_cores
        return max(0, min(int(cpu_usage), 100))

    @classmethod
    def processMemoryUsage(cls, pid: int) -> int:
        """
        Retrieves the memory usage of a process given its process ID (pid) on macOS.

        :param pid: The process ID of the target process
        :return: The memory usage of the process in bytes
        :exception RuntimeError: Raised if the MacOSMonitor is not initialized
        :exception ValueError: Raised if the memory usage cannot be converted to an integer

        setup:
            - 1. Check if the MacOSMonitor instance is initialized
                a. If not, raise a RuntimeError
            - 2. Execute a subprocess command to get the memory usage of the process using the ps command
                a. Capture the output and decode it from bytes to a string
            - 3. Parse the output to extract the memory usage value (in kilobytes)
                a. Convert the value to bytes by multiplying by 1024
            - 4. Return the memory usage in bytes
        """

        if not cls._INSTANCE:
            raise RuntimeError("MacOSMonitor is not initialized.")
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', 'rss']).decode()
        memory_usage = int(ps_output.splitlines()[1].strip())
        return memory_usage * 1024


_checkDependencies()
_MonitorMapping = {
    'Linux': _LinuxMonitor,
    'Windows': _WindowsMonitor,
    'Darwin': _MacOSMonitor
}
_Monitor = _MonitorMapping[_SystemType]()
if bool(PyTorchSupport.value):
    # noinspection PyUnresolvedReferences
    import torch
if PySide6Support:
    # noinspection PyUnresolvedReferences
    import qasync
    # noinspection PyUnresolvedReferences
    from PySide6.QtCore import Signal, QThread
    # noinspection PyUnresolvedReferences
    from PySide6.QtWidgets import QApplication

    _AllowQtMode = True
elif PyQt6Support:
    # noinspection PyUnresolvedReferences
    import qasync
    # noinspection PyUnresolvedReferences
    from PyQt6.QtCore import pyqtSignal, QThread
    # noinspection PyUnresolvedReferences
    from PyQt6.QtWidgets import QApplication

    _AllowQtMode = True
elif PyQt5Support:
    # noinspection PyUnresolvedReferences
    import qasync
    # noinspection PyUnresolvedReferences
    from PyQt5.QtCore import pyqtSignal, QThread
    # noinspection PyUnresolvedReferences
    from PyQt5.QtWidgets import QApplication

    _AllowQtMode = True
else:
    QThread = None
    QApplication = None
if _AllowQtMode:
    class _QtCallbackExecutor(QThread):
        """
        QT callback executor

        Manage the execution of callback functions associated with completed tasks in a Qt application.

        Attributes:
            SynchronizationManager: An instance of _SynchronizationManager to handle shared resources.
            CloseEvent: An event used to signal when the executor should stop running.
            ExecuteSignal: A signal emitted to execute the callback functions.

        Methods:
            startExecutor: Starts the executor by starting the thread.
            closeExecutor: Signals the executor to close and waits for cleanup.
            run: Continuously processes results from the result storage queue and emits the associated callback functions.
            callbackExecutor: Executes a callback function with the provided task result, supporting both synchronous and asynchronous callbacks.
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
            self.start()

        def closeExecutor(self):
            """
            Signals the executor to close by setting the CloseEvent and waits for a specified duration.

            :return: None
            :exception: None

            setup:
                - 1. Set the CloseEvent to signal that the executor should stop running
                - 2. Wait for a specified duration (2 seconds) to allow for cleanup or graceful shutdown
            """

            self.CloseEvent.set()
            self.wait(2)

        def run(self):
            """
            The main loop for the thread, responsible for processing tasks from the synchronization manager.

            This method continuously checks for completed tasks in the ResultStorageQueue and emits the results to the corresponding callback objects.
            It runs at the highest priority to ensure timely processing of tasks.

            :return: None

            setup:
                - 1. Set the thread's priority to the highest level to ensure prompt execution.
                - 2. Continuously run a loop until the CloseEvent is set.
                    a. Attempt to retrieve callback data from the ResultStorageQueue.
                    b. If successful, extract the task result and task ID.
                    c. Store the task result in the _FutureResult dictionary using the task ID as the key.
                    d. Check if the task ID has an associated callback object in _CallbackObject.
                        i. If found, emit the ExecuteSignal with the callback object and task result.
                        ii. Remove the callback object from _CallbackObject.
                    e. If the queue is empty, pause briefly to avoid busy waiting.
             """

            global _CallbackObject, _FutureResult
            self.setPriority(self.Priority.HighestPriority)
            while not self.CloseEvent.is_set():
                try:
                    callback_data = self.SynchronizationManager.ResultStorageQueue.get_nowait()
                    task_result, task_id = callback_data
                    _FutureResult[task_id] = task_result
                    if task_id in _CallbackObject:
                        callback_object = _CallbackObject[task_id]
                        self.ExecuteSignal.emit((callback_object, task_result))
                        del _CallbackObject[task_id]
                except queue.Empty:
                    time.sleep(0.001)

        @qasync.asyncSlot(tuple)
        async def callbackExecutor(self, callback_data: tuple):
            """
            Executes a callback function with the provided task result, supporting both synchronous and asynchronous callbacks.

            :param callback_data: A tuple containing the callback function and the task result to be passed to it
            :return: None
            :exception: None

            setup:
                - 1. Extract the callback function and task result from the callback_data tuple
                - 2. Check if the callback function is a coroutine function
                    a. If true, await the execution of the asynchronous callback with the task result
                - 3. If the callback function is not asynchronous, call it directly with the task result
            """

            callback_object, task_result = callback_data
            if asyncio.iscoroutinefunction(callback_object):
                await callback_object(task_result)
                return
            callback_object(task_result)


class _CoreCallbackExecutor:
    """
    Core callback executor

    It executes the callback function associated with the completed task

    Attributes:
        SynchronizationManager: An instance of _SynchronizationManager to handle shared resources.
        CloseEvent: An event used to signal when the executor should stop running.
        MainEventLoop: The main event loop for asynchronous operations.

    Methods:
        startExecutor: Starts the executor by scheduling the main loop for execution.
        closeExecutor: Signals the executor to close and stop processing.
        run: Continuously processes results from the result storage queue and executes the associated callback functions.
    """

    def __init__(self, SM: _SynchronizationManager):
        self.SynchronizationManager = SM
        self.CloseEvent = threading.Event()
        self.MainEventLoop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    def startExecutor(self):
        """
        Starts the executor by creating an asynchronous task to run the executor's main loop.

        :return: None
        :exception: None

        setup:
            - 1. Create an asynchronous task in the main event loop to execute the run method
        """

        self.MainEventLoop.create_task(self.run())

    def closeExecutor(self):
        """
        Signals the executor to close by setting the CloseEvent.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal that the executor should stop running
        """

        self.CloseEvent.set()

    async def run(self):
        """
        Continuously processes results from the result storage queue and executes the associated callback functions.

        :return: None
        :exception: None

        setup:
            - 1. Enter a loop that runs until the CloseEvent is set
            - 2. Attempt to retrieve callback data from the ResultStorageQueue
                a. If successful, unpack the task result and task ID
                b. Store the task result in the _FutureResult dictionary using the task ID as the key
                c. Check if the task ID has an associated callback in _CallbackObject
                    i. If found, retrieve the callback object
                    ii. Create a new asynchronous task to execute the callback using the callbackExecutor
                    iii. Remove the callback from _CallbackObject to prevent duplicate execution
            - 3. If the ResultStorageQueue is empty, wait briefly before the next iteration
        """

        global _CallbackObject, _FutureResult
        while not self.CloseEvent.is_set():
            try:
                callback_data = self.SynchronizationManager.ResultStorageQueue.get_nowait()
                task_result, task_id = callback_data
                _FutureResult[task_id] = task_result
                if task_id in _CallbackObject:
                    callback_object = _CallbackObject[task_id]
                    self.MainEventLoop.create_task(self.callbackExecutor((callback_object, task_result)))
                    del _CallbackObject[task_id]
            except queue.Empty:
                await asyncio.sleep(0.001)

    @staticmethod
    async def callbackExecutor(callback_data: tuple):
        """
        Executes a callback function with the provided task result, supporting both synchronous and asynchronous callbacks.

        :param callback_data: A tuple containing the callback function and the task result to be passed to it
        :return: None
        :exception: None

        setup:
            - 1. Extract the callback function and task result from the callback_data tuple
            - 2. Check if the callback function is a coroutine function
                a. If true, await the execution of the asynchronous callback with the task result
            - 3. If the callback function is not asynchronous, call it directly with the task result
        """

        callback_object, task_result = callback_data
        if asyncio.iscoroutinefunction(callback_object):
            await callback_object(task_result)
            return
        callback_object(task_result)


@dataclass
class _Config:
    """
    A data class representing the configuration settings for the concurrent processing system.

    Attributes:
        - Priority: The priority level of processes, which can be one of the following:
            - "IDLE"
            - "BELOW_NORMAL"
            - "NORMAL"
            - "ABOVE_NORMAL"
            - "HIGH"
            - "REALTIME"
            Default is "NORMAL".
        - CoreProcessCount: Optional integer indicating the number of core processes to be used.
        - CoreThreadCount: Optional integer indicating the number of core threads to be used.
        - MaximumProcessCount: Optional integer specifying the maximum number of processes allowed.
        - MaximumThreadCount: Optional integer specifying the maximum number of threads allowed.
        - IdleCleanupThreshold: Optional integer indicating the threshold for idle cleanup (in seconds).
        - ProcessPriority: The priority level for processes, which can be one of the following:
            - "IDLE"
            - "BELOW_NORMAL"
            - "NORMAL"
            - "ABOVE_NORMAL"
            - "HIGH"
            - "REALTIME"
            Default is "NORMAL".
        - TaskThreshold: Optional integer representing the threshold for task count.
            - GlobalTaskThreshold: Optional integer representing the global threshold for tasks across the system.
            - ExpandPolicy: Optional policy for resource expansion, which can be one of:
                - "NoExpand"
                - "AutoExpand"
                - "BeforehandExpand"
        - ShrinkagePolicy: Optional policy for resource shrinking, which can be one of:
            - "NoShrink"
            - "AutoShrink"
            - "TimeoutShrink"
        - ShrinkagePolicyTimeout: Optional integer specifying the timeout for the shrinkage policy (in seconds).
        """

    Priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = "NORMAL"
    CoreProcessCount: Optional[int] = None
    CoreThreadCount: Optional[int] = None
    MaximumProcessCount: Optional[int] = None
    MaximumThreadCount: Optional[int] = None
    IdleCleanupThreshold: Optional[int] = None
    ProcessPriority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = "NORMAL"
    TaskThreshold: Optional[int] = None
    GlobalTaskThreshold: Optional[int] = None
    ExpandPolicy: Optional[Literal["NoExpand", "AutoExpand", "BeforehandExpand"]] = None
    ShrinkagePolicy: Optional[Literal["NoShrink", "AutoShrink", "TimeoutShrink"]] = None
    ShrinkagePolicyTimeout: Optional[int] = None


class _ConfigManager:
    """
    Manages configuration settings for the concurrent processing system.

    It validates various parameters related to process and thread counts, priorities, policies, and thresholds, ensuring they conform to the expected formats and limits.
    Configuration values are shared across multiple processes using a multiprocessing Manager.

    Attributes:
        - DebugMode: A boolean indicating if debug mode is enabled.
        - Logger: A configured logger instance for logging messages.
        - PhysicalCores: The number of physical CPU cores available on the system.
        - Priority: A shared value representing the process priority.
        - CoreProcessCount: A shared value representing the number of core processes.
        - CoreThreadCount: A shared value representing the number of core threads.
        - MaximumProcessCount: A shared value representing the maximum number of processes allowed.
        - MaximumThreadCount: A shared value representing the maximum number of threads allowed.
        - IdleCleanupThreshold: A shared value representing the threshold for idle cleanup.
        - TaskThreshold: A shared value representing the threshold for task count.
        - GlobalTaskThreshold: A shared value representing the global threshold for tasks across the system.
        - ProcessPriority: A shared value representing the priority of processes.
        - ExpandPolicy: A shared value representing the policy for expanding resources.
        - ShrinkagePolicy: A shared value representing the policy for shrinking resources.
        - ShrinkagePolicyTimeout: A shared value representing the timeout for the shrinkage policy.

    Methods:
        - _setLogger: Configures and returns a logger instance for the concurrent system.
        - _validatePriority: Validates and returns a priority level, defaulting to "NORMAL" if invalid.
        - _validateCoreProcessCount: Validates and returns the core process count, defaulting if invalid.
        - _validateCoreThreadCount: Validates and returns the core thread count, defaulting if invalid.
        - _validateMaximumProcessCount: Validates and returns the maximum process count, defaulting if invalid.
        - _validateMaximumThreadCount: Validates and returns the maximum thread count, defaulting if invalid.
        - _validateIdleCleanupThreshold: Validates and returns the idle cleanup threshold, defaulting if invalid.
        - _validateTaskThreshold: Validates and returns the task threshold, defaulting if invalid.
        - _validateGlobalTaskThreshold: Validates and returns the global task threshold, defaulting if invalid.
        - _validateProcessPriority: Validates and returns the process priority, defaulting if invalid.
        - _validateExpandPolicy: Validates and returns the expand policy, defaulting if invalid.
        - _validateShrinkagePolicy: Validates and returns the shrinkage policy, defaulting if invalid.
        - _validateShrinkagePolicyTimeout: Validates and returns the shrinkage policy timeout, defaulting if invalid.
        - calculateTaskThreshold: Calculates and returns the task threshold based on system resources.
    """

    def __init__(self, SharedObjectManager: multiprocessing.Manager, Config: _Config, DebugMode: bool = False):
        self.DebugMode = DebugMode
        self.Logger = self._setLogger()
        self.PhysicalCores = _Monitor.physicalCpuCores()
        self.Priority = SharedObjectManager.Value("c", self._validatePriority(Config.Priority))
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
        Sets up and configures a logger for the ConcurrentSystem.

        :return: The configured logger instance
        :exception: None

        setup:
            - 1. Create a logger instance for the ConcurrentSystem with the name 'ConcurrentSystem'
            - 2. Set the logging level to DEBUG
            - 3. Create a console handler for logging output
                a. Set the handler's logging level based on the DebugMode
            - 4. Configure the formatter for the console handler
                a. Use _ColoredFormatter for formatted log messages
            - 5. Add the console handler to the logger instance
        """
        logger = logging.getLogger('ConcurrentSystem')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if self.DebugMode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        return logger

    def _validatePriority(self, priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]) -> Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
        """
        Validates the priority level, providing a default if the input is invalid.

        :param priority: The priority level to validate, which can be "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", or "REALTIME"
        :return: The validated priority level, defaulting to "NORMAL" if the input is invalid
        :exception: None

        setup:
            - 1. Check if the provided priority is valid
                a. If not valid, log a warning and return the default value "NORMAL"
            - 2. If the provided value is valid, return it as is
        """

        if priority not in ["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            self.Logger.warning(f"Invalid priority level '{priority}'. Default value ['NORMAL'] has been used.")
            return "NORMAL"
        return priority

    def _validateCoreProcessCount(self, core_process_count: Optional[int]) -> int:
        """
        Validates the core process count value, providing a default if the input is invalid or out of range.

        :param core_process_count: The core process count value, which can be None or an integer
        :return: The validated core process count value, defaulting to a calculated value if the input is invalid or out of range
        :exception: None

        setup:
            - 1. Calculate the default value for the core process count as half of the number of physical cores
                a. If the default value is less than or equal to 0, set it to 1
            - 2. Check if the provided core process count is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided core process count is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. Check if the core process count is less than 0 or exceeds the number of physical cores
                a. If out of range, log a warning and return the default value
            - 5. If the core process count is 0, log a warning indicating that the process pool will be unavailable
            - 6. If the provided value is valid, return it as is
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
        Validates the core thread count value, providing a default if the input is invalid or out of range.

        :param core_thread_count: The core thread count value, which can be None or an integer
        :return: The validated core thread count value, defaulting to a calculated value if the input is invalid or out of range
        :exception: None

        setup:
            - 1. Calculate the default value for the core thread count as half of the number of physical cores
                a. If the default value is less than or equal to 0, set it to 1
            - 2. Check if the provided core thread count is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided core thread count is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. Check if the core thread count is less than or equal to 0 or exceeds four times the number of physical cores
                a. If out of range, log a warning and return the default value
            - 5. If the provided value is valid, return it as is
        """

        default_value = self.PhysicalCores // 2
        if default_value <= 0:
            default_value = 1
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
        Validates the maximum process count value, providing a default if the input is invalid or out of range.

        :param maximum_process_count: The maximum process count value, which can be None or an integer
        :return: The validated maximum process count value, defaulting to the number of physical cores if the input is invalid or out of range
        :exception: None

        setup:
            - 1. Set the default value for the maximum process count to the number of physical cores
            - 2. If the core process count is zero, return 0 immediately
            - 3. Check if the provided maximum process count is None
                a. If true, log a warning and return the default value
            - 4. Check if the provided maximum process count is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 5. Check if the maximum process count is less than the core process count or exceeds the physical core count
                a. If out of range, log a warning and return the default value
            - 6. If the provided value is valid, return it as is
        """

        default_value = self.PhysicalCores
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
        Validates the maximum thread count value, providing a default if the input is invalid or out of range.

        :param maximum_thread_count: The maximum thread count value, which can be None or an integer
        :return: The validated maximum thread count value, defaulting to a calculated value if the input is invalid or out of range
        :exception: None

        setup:
            - 1. Calculate the default value for the maximum thread count based on physical cores multiplied by 4
            - 2. Check if the provided maximum thread count is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided maximum thread count is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. Check if the maximum thread count is less than the core thread count or exceeds the calculated limit
                a. If out of range, log a warning and return the default value
            - 5. If the provided value is valid, return it as is
        """

        default_value = self.PhysicalCores * 4
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
        Validates the idle cleanup threshold value, providing a default if the input is invalid.

        :param idle_cleanup_threshold: The idle cleanup threshold value, which can be None or an integer
        :return: The validated idle cleanup threshold value, defaulting to 60 if the input is invalid or None
        :exception: None

        setup:
            - 1. Define a default value for the idle cleanup threshold (60)
            - 2. Check if the provided threshold is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided threshold is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. If the provided value is valid, return it as is
        """

        default_value = 60
        if idle_cleanup_threshold is None:
            self.Logger.warning(f"Idle cleanup threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(idle_cleanup_threshold, int):
            self.Logger.warning(f"Invalid type for idle cleanup threshold '{idle_cleanup_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return idle_cleanup_threshold

    def _validateTaskThreshold(self, task_threshold: Optional[int]) -> int:
        """
        Validates the task threshold value, providing a default if the input is invalid.

        :param task_threshold: The task threshold value, which can be None or an integer
        :return: The validated task threshold value, defaulting to a calculated value if the input is invalid or None
        :exception: None

        setup:
            - 1. Calculate the default value for the task threshold using the calculateTaskThreshold method
            - 2. Check if the provided threshold is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided threshold is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. If the provided value is valid, return it as is
        """

        default_value = self.calculateTaskThreshold()
        if task_threshold is None:
            self.Logger.warning(f"Task threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(task_threshold, int):
            self.Logger.warning(f"Invalid type for task threshold '{task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return task_threshold

    def _validateGlobalTaskThreshold(self, global_task_threshold: Optional[int]) -> int:
        """
        Validates the global task threshold value, providing a default if the input is invalid.

        :param global_task_threshold: The global task threshold value, which can be None or an integer
        :return: The validated global task threshold value, defaulting to a calculated value if the input is invalid or None
        :exception: None

        setup:
            - 1. Calculate the default value for the global task threshold based on core process and thread counts
            - 2. Check if the provided threshold is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided threshold is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. If the provided value is valid, return it as is
        """

        default_value = (self.CoreProcessCount.value + self.CoreThreadCount.value) * self.TaskThreshold.value
        if global_task_threshold is None:
            self.Logger.warning(f"Global task threshold not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(global_task_threshold, int):
            self.Logger.warning(f"Invalid type for global task threshold '{global_task_threshold}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return global_task_threshold

    def _validateProcessPriority(self, process_priority: Literal[None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]) -> str:
        """
        Validates the process priority value, providing a default if the input is invalid or not recommended.

        :param process_priority: The process priority value, which can be None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", or "REALTIME"
        :return: The validated process priority value, defaulting to "NORMAL" if the input is invalid or not recommended
        :exception: None

        setup:
            - 1. Check if the provided process priority is valid
                a. If not valid, log a warning and return the default value "NORMAL"
            - 2. Check if the provided process priority is None
                a. If true, log a warning and return the default value "NORMAL"
            - 3. If the core process count equals the number of physical cores and the priority is "HIGH" or "REALTIME":
                a. Log a warning that using this priority is not recommended and return the default value "NORMAL"
            - 4. If the provided value is valid and recommended, return it as is
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

    def _validateExpandPolicy(self, expand_policy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand"]) -> str:
        """
        Validates the expand policy value, providing a default if the input is invalid.

        :param expand_policy: The expand policy value, which can be None, "NoExpand", "AutoExpand", or "BeforehandExpand"
        :return: The validated expand policy value, defaulting to "NoExpand" if the input is invalid or None
        :exception: None

        setup:
            - 1. Check if the provided expand policy is valid
                a. If not valid, log a warning and return the default value "NoExpand"
            - 2. Check if the provided expand policy is None
                a. If true, log a warning and return the default value "NoExpand"
            - 3. If the provided value is valid, return it as is
        """

        if expand_policy not in [None, "NoExpand", "AutoExpand", "BeforehandExpand"]:
            self.Logger.warning(f"Invalid expand policy '{expand_policy}'. Default value ['NoExpand'] has been used.")
            return "NoExpand"

        if expand_policy is None:
            self.Logger.warning("Expand policy not set. Default value ['NoExpand'] has been used.")
            return "NoExpand"

        return expand_policy

    def _validateShrinkagePolicy(self, shrinkage_policy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink"]) -> str:
        """
        Validates the shrinkage policy value, providing a default if the input is invalid.

        :param shrinkage_policy: The shrinkage policy value, which can be None, "NoShrink", "AutoShrink", or "TimeoutShrink"
        :return: The validated shrinkage policy value, defaulting to "NoShrink" if the input is invalid or None
        :exception: None

        setup:
            - 1. Check if the provided shrinkage policy is valid
                a. If not valid, log a warning and return the default value "NoShrink"
            - 2. Check if the provided shrinkage policy is None
                a. If true, log a warning and return the default value "NoShrink"
            - 3. If the provided value is valid, return it as is
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
        Validates the shrinkage policy timeout value, providing a default if the input is invalid.

        :param shrinkage_policy_timeout: The timeout value for the shrinkage policy, which can be None or an integer
        :return: The validated timeout value, defaulting to 5 if the input is None or invalid
        :exception: None

        setup:
            - 1. Define a default value for the shrinkage policy timeout (5)
            - 2. Check if the provided timeout value is None
                a. If true, log a warning and return the default value
            - 3. Check if the provided timeout value is not an integer
                a. If true, log a warning about the invalid type and return the default value
            - 4. If the provided value is valid, return it as is
        """

        default_value = 5
        if shrinkage_policy_timeout is None:
            self.Logger.warning(f"Shrinkage policy timeout not set. Default value [{default_value}] has been used.")
            return default_value

        if not isinstance(shrinkage_policy_timeout, int):
            self.Logger.warning(f"Invalid type for shrinkage policy timeout '{shrinkage_policy_timeout}'. Must be an integer. Default value [{default_value}] has been used.")
            return default_value

        return shrinkage_policy_timeout

    def calculateTaskThreshold(self):
        """
        Calculates the task threshold based on the number of physical CPU cores and total physical memory.

        :return: The calculated task threshold value
        :exception: None

        setup:
            - 1. Retrieve the number of physical CPU cores
            - 2. Get the total physical memory in gigabytes
            - 3. Calculate the balanced score based on the ratio of physical cores and memory
                a. Use the formula: ((physical_cores / 128) + (total_memory / 3072)) / 2
            - 4. Define thresholds for balanced scores and corresponding task thresholds
            - 5. Iterate over the balanced score thresholds and task thresholds
                a. If the balanced score is less than or equal to a threshold, return the corresponding task threshold
            - 6. If no thresholds are met, return the highest task threshold
        """

        physical_cores = self.PhysicalCores
        total_memory = _Monitor.totalPhysicalMemory() / (1024 ** 3)
        balanced_score = ((physical_cores / 128) + (total_memory / 3072)) / 2

        balanced_score_thresholds = [0.2, 0.4, 0.6, 0.8]
        task_thresholds = [10, 40, 70, 100, 130]
        for score_threshold, threshold in zip(balanced_score_thresholds, task_thresholds):
            if balanced_score <= score_threshold:
                return threshold
        return task_thresholds[-1]


class _SynchronizationManager:
    """
    Manages synchronization and state information for processes and threads in the system.

    It maintains task statuses and load statuses for both core and expand processes and threads, ensuring thread safety through locks.
    It uses a multiprocessing Manager to facilitate shared state across processes.

    Attributes:
        - SharedObjectManagerID: The process ID of the shared object manager.
        - CoreProcessTaskStatusPool: A dictionary that holds task statuses for core processes,
            where the key is the process name and the value is a tuple containing the process ID and task count.
        - ExpandProcessTaskStatusPool: A dictionary that holds task statuses for expand processes.
        - CoreProcessLoadStatusPool: A dictionary that holds load statuses for core processes.
        - ExpandProcessLoadStatusPool: A dictionary that holds load statuses for expand processes.
        - CoreThreadTaskStatusPool: A dictionary that holds task statuses for core threads.
        - ExpandThreadTaskStatusPool: A dictionary that holds task statuses for expand threads.
        - ResultStorageQueue: A multiprocessing queue for storing results of completed tasks.
        - TaskLock: A lock for ensuring thread-safe access to task status pools.
        - _ProcessTaskLock: A lock for ensuring thread-safe access to process task status updates.
        - _ProcessLoadLock: A lock for ensuring thread-safe access to process load status updates.
        - _ThreadLock: A lock for ensuring thread-safe access to thread task status updates.

    Methods:
        - getCoreProcessTaskStatus: Retrieves the task status for a core process by its name.
        - getExpandProcessTaskStatus: Retrieves the task status for an expand process by its name.
        - getCoreProcessLoadStatus: Retrieves the load status for a core process by its name.
        - getExpandProcessLoadStatus: Retrieves the load status for an expand process by its name.
        - getCoreThreadTaskStatus: Retrieves the task status for a core thread by its name.
        - getExpandThreadTaskStatus: Retrieves the task status for an expand thread by its name.
        - updateCoreProcessTaskStatus: Updates the task status for a core process.
        - updateExpandProcessTaskStatus: Updates the task status for an expand process.
        - updateCoreProcessLoadStatus: Updates the load status for a core process.
        - updateExpandProcessLoadStatus: Updates the load status for an expand process.
        - updateCoreThreadTaskStatus: Updates the task status for a core thread.
        - updateExpandThreadTaskStatus: Updates the task status for an expand thread.
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

    def getCoreProcessTaskStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the task status for a core process from the task status pool, ensuring thread safety.

        :param name: The name of the core process whose task status is being retrieved
        :return: A tuple containing the process ID and the current task count, or None if the process is not found
        :exception KeyError: Raised if the specified process name does not exist in the task status pool

        setup:
            - 1. Acquire the process task lock to ensure thread safety
            - 2. Access the CoreProcessTaskStatusPool using the provided process name
            - 3. Release the process task lock
            - 4. Return the status, which is a tuple containing the process ID and task count
        """

        self._ProcessTaskLock.acquire()
        status = self.CoreProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getExpandProcessTaskStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the task status for an expand process from the task status pool, ensuring thread safety.

        :param name: The name of the expand process whose task status is being retrieved
        :return: A tuple containing the process ID and the current task count, or None if the process is not found
        :exception KeyError: Raised if the specified process name does not exist in the task status pool

        setup:
            - 1. Acquire the process task lock to ensure thread safety
            - 2. Access the ExpandProcessTaskStatusPool using the provided process name
            - 3. Release the process task lock
            - 4. Return the status, which is a tuple containing the process ID and task count
        """

        self._ProcessTaskLock.acquire()
        status = self.ExpandProcessTaskStatusPool[name]
        self._ProcessTaskLock.release()
        return status

    def getCoreProcessLoadStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the load status for a core process from the load status pool, ensuring thread safety.

        :param name: The name of the core process whose load status is being retrieved
        :return: A tuple containing the process ID and the current load value, or None if the process is not found
        :exception KeyError: Raised if the specified process name does not exist in the load status pool

        setup:
            - 1. Acquire the process load lock to ensure thread safety
            - 2. Access the CoreProcessLoadStatusPool using the provided process name
            - 3. Release the process load lock
            - 4. Return the status, which is a tuple containing the process ID and load value
        """

        self._ProcessLoadLock.acquire()
        status = self.CoreProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getExpandProcessLoadStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the load status for an expand process from the load status pool, ensuring thread safety.

        :param name: The name of the expand process whose load status is being retrieved
        :return: A tuple containing the process ID and the current load value, or None if the process is not found
        :exception KeyError: Raised if the specified process name does not exist in the load status pool

        setup:
            - 1. Acquire the process load lock to ensure thread safety
            - 2. Access the ExpandProcessLoadStatusPool using the provided process name
            - 3. Release the process load lock
            - 4. Return the status, which is a tuple containing the process ID and load value
        """

        self._ProcessLoadLock.acquire()
        status = self.ExpandProcessLoadStatusPool[name]
        self._ProcessLoadLock.release()
        return status

    def getCoreThreadTaskStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the task status for a core thread from the task status pool.

        :param name: The name of the core thread whose task status is being retrieved
        :return: A tuple containing the thread ID and the current task count, or None if the thread is not found
        :exception KeyError: Raised if the specified thread name does not exist in the task status pool

        setup:
            - 1. Access the CoreThreadTaskStatusPool using the provided thread name
            - 2. Return the status, which is a tuple containing the thread ID and task count
        """

        status = self.CoreThreadTaskStatusPool[name]
        return status

    def getExpandThreadTaskStatus(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the task status for an expand thread from the task status pool.

        :param name: The name of the expand thread whose task status is being retrieved
        :return: A tuple containing the thread ID and the current task count, or None if the thread is not found
        :exception KeyError: Raised if the specified thread name does not exist in the task status pool

        setup:
            - 1. Access the ExpandThreadTaskStatusPool using the provided thread name
            - 2. Return the status, which is a tuple containing the thread ID and task count
        """

        status = self.ExpandThreadTaskStatusPool[name]
        return status

    def updateCoreProcessTaskStatus(self, name: str, pid: int, task_count: int):
        """
        Updates the task status for a core process in the task status pool.

        :param name: The name of the process whose task status is being updated
        :param pid: The process ID of the core process
        :param task_count: The current task count for the core process
        :return: None
        :exception: None

        setup:
            - 1. Update the CoreProcessTaskStatusPool with the new task status for the specified process
                a. Store the process ID and task count as a tuple in the pool using the process name as the key
        """

        self.CoreProcessTaskStatusPool[name] = (pid, task_count)

    def updateExpandProcessTaskStatus(self, name: str, pid: int, task_count: int):
        """
        Updates the task status for an expand process in the task status pool.

        :param name: The name of the process whose task status is being updated
        :param pid: The process ID of the expand process
        :param task_count: The current task count for the expand process
        :return: None
        :exception: None

        setup:
            - 1. Update the ExpandProcessTaskStatusPool with the new task status for the specified process
                a. Store the process ID and task count as a tuple in the pool using the process name as the key
        """

        self.ExpandProcessTaskStatusPool[name] = (pid, task_count)

    def updateCoreProcessLoadStatus(self, name: str, pid: int, load: int):
        """
        Updates the load status for a core process in the load status pool.

        :param name: The name of the process whose load status is being updated
        :param pid: The process ID of the core process
        :param load: The current load value for the core process
        :return: None
        :exception: None

        setup:
            - 1. Update the CoreProcessLoadStatusPool with the new load status for the specified process
                a. Store the process ID and load value as a tuple in the pool using the process name as the key
        """

        self.CoreProcessLoadStatusPool[name] = (pid, load)

    def updateExpandProcessLoadStatus(self, name: str, pid: int, load: int):
        """
        Updates the load status for an expand process in the load status pool.

        :param name: The name of the process whose load status is being updated
        :param pid: The process ID of the expand process
        :param load: The current load value for the expand process
        :return: None
        :exception: None

        setup:
            - 1. Update the ExpandProcessLoadStatusPool with the new load status for the specified process
                a. Store the process ID and load value as a tuple in the pool using the process name as the key
        """

        self.ExpandProcessLoadStatusPool[name] = (pid, load)

    def updateCoreThreadTaskStatus(self, name: str, tid: int, task_count: int):
        """
        Updates the task status for a core thread in the task status pool.

        :param name: The name of the thread whose task status is being updated
        :param tid: The thread ID of the core thread
        :param task_count: The current task count for the core thread
        :return: None
        :exception: None

        setup:
            - 1. Update the CoreThreadTaskStatusPool with the new task status for the specified thread
                a. Store the thread ID and task count as a tuple in the pool using the thread name as the key
        """

        self.CoreThreadTaskStatusPool[name] = (tid, task_count)

    def updateExpandThreadTaskStatus(self, name: str, tid: int, task_count: int):
        """
        Updates the task status for an expand thread in the task status pool.

        :param name: The name of the thread whose task status is being updated
        :param tid: The thread ID of the expand thread
        :param task_count: The current task count for the expand thread
        :return: None
        :exception: None

        setup:
            - 1. Update the ExpandThreadTaskStatusPool with the new task status for the specified thread
                a. Store the thread ID and task count as a tuple in the pool using the thread name as the key
        """

        self.ExpandThreadTaskStatusPool[name] = (tid, task_count)


class _TaskObject:
    """
    Represents a task object for managing task execution within the system.

    It encapsulates the task to be executed, its parameters, and configurations related to execution, such as timeouts and retry mechanisms.
    The task can be either synchronous or asynchronous, and it can also utilize GPU resources if enabled.

    Attributes:
        - Task: The callable function that represents the task to be executed.
        - TaskID: A unique identifier for the task.
        - TaskType: The type of the task, determined by whether the task is an asynchronous coroutine function or not.
        - IsCallback: A boolean indicating if a callback is associated with the task.
        - Lock: A boolean indicating whether the task requires a lock during execution.
        - LockTimeout: An integer specifying the timeout duration for acquiring the lock.
        - TimeOut: An optional integer specifying the maximum time duration allowed for task execution.
        - IsGpuBoost: A boolean indicating if GPU resources should be utilized for task execution.
        - GpuID: An integer representing the ID of the GPU to use.
        - IsRetry: A boolean indicating if the task is eligible for retries in case of failure.
        - MaxRetries: An integer specifying the maximum number of retries allowed for the task.
        - RetriesCount: An integer counting the current number of retries for the task.
        - UnserializableInfo: A dictionary storing information about objects that cannot be serialized.
        - Args: The serialized representation of positional arguments for the task.
        - Kwargs: The serialized representation of keyword arguments for the task.
        - RecoveredArgs: The deserialized positional arguments to be used during task execution.
        - RecoveredKwargs: The deserialized keyword arguments to be used during task execution.

    Methods:
        - __init__: Initializes the task object with the provided parameters and serializes the args and kwargs.
        - reinitializedParams: Reinitializes parameters by deserializing arguments and setting up GPU parameters if applicable.
        - setupGpuParams: Sets up GPU parameters by transferring arguments and keyword arguments to the specified GPU device.
        - paramsTransfer: Transfers parameters (tensors or models) to the specified device, handling nested structures.
        - cleanupGpuResources: Cleans up GPU resources by synchronizing and emptying the CUDA cache.
        - serialize: Serializes an object that may be a tuple, dictionary, or other types, handling special cases for unserializable objects.
        - deserialize: Deserializes an object that may be a tuple, dictionary, or other types, handling special cases for unserializable objects.
        - isSerializable: Checks if an object is serializable using the pickle module.
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

    def reinitializedParams(self):
        """
        Reinitialized the parameters by deserializing arguments and setting up GPU parameters if applicable.

        :return: None
        :exception: None

        setup:
            - 1. Deserialize the positional arguments from Args and assign them to RecoveredArgs
            - 2. Deserialize the keyword arguments from Kwargs and assign them to RecoveredKwargs
            - 3. If GPU boosting is enabled and PyTorch is supported:
                a. Call setupGpuParams to transfer parameters to the appropriate GPU device
        """

        self.RecoveredArgs = self.deserialize(self.Args)
        self.RecoveredKwargs = self.deserialize(self.Kwargs)
        if self.IsGpuBoost and PyTorchSupport:
            self.setupGpuParams()

    def setupGpuParams(self):
        """
        Sets up GPU parameters by transferring arguments and keyword arguments to the specified GPU device.

        :return: None
        :exception: None

        setup:
            - 1. Check if the specified GPU ID is in the list of available CUDA device IDs
                a. If not, reset the GPU ID to 0 (the default device)
            - 2. Create a device object for the specified GPU
            - 3. Transfer all positional arguments in RecoveredArgs to the specified GPU device using paramsTransfer
            - 4. Transfer all keyword arguments in RecoveredKwargs to the specified GPU device using paramsTransfer
        """

        if self.GpuID not in _AvailableCUDADevicesID:
            self.GpuID = 0
        device = torch.device(f"cuda:{self.GpuID}")
        self.RecoveredArgs = [self.paramsTransfer(arg, device) for arg in self.RecoveredArgs]
        self.RecoveredKwargs = {key: self.paramsTransfer(value, device) for key, value in self.RecoveredKwargs.items()}

    def paramsTransfer(self, obj, device):
        """
        Transfers parameters (tensors or models) to the specified device, handling nested structures.

        :param obj: The object (tensor, model, list, tuple, or dictionary) to be transferred
        :param device: The target device to which the object should be transferred (e.g., "cpu" or "cuda")
        :return: The object transferred to the specified device
        :exception: None

        setup:
            - 1. Check if the object is a tensor or a neural network module
                a. If true, transfer the object to the specified device
            - 2. Check if the object is a list or tuple
                a. If true, recursively transfer each element to the specified device, preserving the type
            - 3. Check if the object is a dictionary
                a. If true, recursively transfer each key-value pair to the specified device
            - 4. If the object is none of the above types, return it as is
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
        Cleans up GPU resources by synchronizing and emptying the CUDA cache.

        :return: None
        :exception: None

        setup:
            - 1. Synchronize the CUDA device to ensure all pending operations are completed
            - 2. Clear the CUDA cache to free up unused memory
        """

        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    def serialize(self, obj):
        """
        Serializes an object that may be a tuple, dictionary, or other types, handling special cases for unserializable objects.

        :param obj: The object to be serialized
        :return: The serialized representation of the object
        :exception: None

        setup:
            - 1. Check if the object is a tuple
                a. If true, recursively serialize each item in the tuple
            - 2. Check if the object is a dictionary
                a. Recursively serialize each key-value pair in the dictionary
            - 3. Check if the object is not serializable
                a. If not serializable, store it in UnserializableInfo and return a dictionary indicating it is unserializable
            - 4. If the object is serializable, return the object as is
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
        Deserializes an object that may be a tuple, dictionary, or other types, handling special cases for unserializable objects.

        :param obj: The object to be deserialized
        :return: The deserialized object
        :exception: None

        setup:
            - 1. Check if the object is a tuple
                a. If true, recursively deserialize each item in the tuple
            - 2. Check if the object is a dictionary
                a. If the dictionary contains the key "__unserializable__", return the corresponding unserializable info
                b. Otherwise, recursively deserialize each key-value pair in the dictionary
            - 3. If the object is neither a tuple nor a dictionary, return the object as is
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
        Checks if an object is serializable using the pickle module.

        :param obj: The object to be checked for serializability
        :return: True if the object can be serialized, False otherwise
        :exception: None

        setup:
            - 1. Attempt to serialize the object using pickle.dumps
                a. If successful, return True
            - 2. If a PicklingError, AttributeError, or TypeError occurs, return False
        """

        try:
            pickle.dumps(obj)
            return True
        except (pickle.PicklingError, AttributeError, TypeError):
            return False


class _ProcessObject(multiprocessing.Process):
    """
    Represents a process dedicated to executing tasks with varying priority levels in a multiprocessing environment.

    This class extends the `multiprocessing.Process` class and is designed to manage the execution of tasks
    asynchronously within a separate process. It maintains separate queues for high, medium, and low-priority tasks,
    ensuring that tasks are executed based on their importance. The process can be stopped gracefully, ensuring all
    tasks are completed or appropriately canceled. Additionally, it provides logging capabilities for tracking task
    execution and any errors that may arise during processing.

    Attributes:
        - ProcessName: The name assigned to the process.
        - ProcessType: The type of process, either 'Core' or 'Expand'.
        - SynchronizationManager: An instance of the _SynchronizationManager for managing synchronization.
        - ConfigManager: An instance of the _ConfigManager for accessing configuration settings.
        - DebugMode: A boolean indicating whether debug mode is enabled.
        - Logger: Logger instance for logging process activities and events.
        - PendingTasks: Dictionary storing tasks that are currently pending execution.
        - SystemExecutor: Optional ThreadPoolExecutor for managing thread execution.
        - HighPriorityQueue: Queue for storing high-priority tasks.
        - MediumPriorityQueue: Queue for storing medium-priority tasks.
        - LowPriorityQueue: Queue for storing low-priority tasks.
        - WorkingEvent: Event signaling that tasks are being processed.
        - CloseEvent: Event signaling when the process should stop running.
        - EventLoop: Optional asyncio event loop for processing tasks asynchronously.

    Methods:
        - __init__: Initializes the process with a name, type, synchronization and configuration managers, and debug mode.
        - run: Initializes the logger, sets the process priority, creates a thread pool executor, and runs the asynchronous task processor.
        - stop: Stops the process by signaling the close event and waiting for the thread to finish execution.
        - addProcessTask: Adds a task object to the appropriate priority queue based on the given priority level.
        - _taskProcessor: Processes tasks from the task queues, performing memory cleanup and executing tasks until the close event is set.
        - _executeAsyncTask: Executes an asynchronous task, determining if the task should be executed with or without locking.
        - _executeSyncTask: Executes a synchronous task, determining if the task should be executed with or without locking.
        - _executeLockedAsyncTask: Executes an asynchronous task with locking, determining if the task should have a timeout.
        - _executeUnLockedAsyncTask: Executes an asynchronous task without locking, determining if the task should have a timeout.
        - _executeTimeoutAsyncTask: Executes an asynchronous task with a timeout, handling its result and potential retries.
        - _executeNonTimeoutAsyncTask: Executes an asynchronous task that is not subject to timeout, handling its result and potential retries.
        - _executeLockedSyncTask: Executes a synchronous task with locking, determining if the task should have a timeout.
        - _executeUnLockedSyncTask: Executes a synchronous task without locking, determining if the task should have a timeout.
        - _executeTimeoutSyncTask: Executes a synchronous task with a timeout, handling its result and potential retries.
        - _executeNonTimeoutSyncTask: Executes a synchronous task that is not subject to timeout, handling its result and potential retries.
        - _updateTaskStatus: Updates the task status for the current process based on its type.
        - _taskResultProcessor: Processes the result of a completed task and updates the task status.
        - _requeueTask: Requeues a task object to the appropriate priority queue based on its priority level.
        - _cleanup: Cleans up remaining tasks in the priority queues and cancels pending tasks.
        - _setLogger: Sets up and configures a logger for the process object.
        - _setProcessPriority: Sets the priority of the process based on the specified priority level.
        - _setSystemExecutorThreadCount: Determines the number of executor threads based on the number of physical CPU cores.
        - _cleanupProcessMemory: Cleans up the memory of the process by emptying its working set.
        - _getTaskData: Retrieves task data from the priority queues in order of priority.
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
        self.SystemExecutor: Optional[ThreadPoolExecutor] = None
        self.HighPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.MediumPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.LowPriorityQueue: multiprocessing.Queue = multiprocessing.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        """
        Initializes the logger, sets the process priority, creates a thread pool executor, and runs the asynchronous task processor.

        :return: None
        :exception: None

        setup:
            - 1. Set up the logger for the process
            - 2. Configure the priority of the process
            - 3. Create a ThreadPoolExecutor with a number of threads determined by _setSystemExecutorThreadCount
            - 4. Create a new asyncio event loop and set it as the current event loop
            - 5. Attempt to run the _taskProcessor method until completion
            - 6. Ensure the event loop is closed after processing
            - 7. Log a message indicating that the process has been closed upon exiting the loop
        """

        self._setLogger()
        self._setProcessPriority()
        self.SystemExecutor = ThreadPoolExecutor(self._setSystemExecutorThreadCount())
        self.EventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.EventLoop)
        try:
            self.EventLoop.run_until_complete(self._taskProcessor())
        finally:
            self.EventLoop.close()
            self.Logger.debug(f"[{self.ProcessName} - {self.pid}] has been closed.")

    def stop(self):
        """
        Stops the process by signaling the close event and waiting for the thread to finish execution.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal the thread to stop running
            - 2. Wait for the thread to complete its execution by calling join()
        """

        self.CloseEvent.set()
        self.join()

    def addProcessTask(self, priority: int, task_object: _TaskObject):
        """
        Adds a task object to the appropriate priority queue based on the given priority level.

        :param priority: An integer representing the priority of the task (0-10)
        :param task_object: The _TaskObject representing the task to be added
        :return: None
        :exception: None

        setup:
            - 1. Set the WorkingEvent to indicate that tasks are being processed
            - 2. Check the priority level and add the task object to the corresponding queue:
                a. If the priority is between 0 and 3, add to the HighPriorityQueue
                b. If the priority is between 4 and 7, add to the MediumPriorityQueue
                c. If the priority is between 8 and 10, add to the LowPriorityQueue
                d. If the priority is out of range (less than 0 or greater than 10), add to the MediumPriorityQueue
                    i. Log a warning that the priority exceeds the allowed range and that a default priority level of 5 has been used
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
            self.Logger.warning(f"[{self.ProcessName} - {self.pid}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self):
        """
        Processes tasks from the task queues, performing memory cleanup and executing tasks until the close event is set.

        :return: None
        :exception: None

        setup:
            - 1. Perform an initial cleanup of the process memory
            - 2. Initialize the last cleanup time
            - 3. Enter a loop that runs until the CloseEvent is set
                a. Check if the time since the last cleanup exceeds the idle cleanup threshold
                    i. If so, perform cleanup of the process memory and update the last cleanup time
                b. Attempt to retrieve task data from the task queues
                    i. If a queue is empty and there are no pending tasks, clear the WorkingEvent
                    ii. If no tasks are available, sleep briefly and continue the loop
                c. Extract the task priority, task object, and retry count from the task data
                d. Reinitialize parameters for the task object
                e. Execute the task based on its type
                    i. If the task type is "Async", call _executeAsyncTask
                    ii. If the task type is not "Async", call _executeSyncTask
                f. Handle any exceptions that occur during task execution, logging the error
            - 4. Call _cleanup to perform any necessary cleanup when exiting the loop
        """

        self._cleanupProcessMemory()
        last_cleanup_time = time.time()
        while not self.CloseEvent.is_set():
            current_time = time.time()
            if current_time - last_cleanup_time >= self.ConfigManager.IdleCleanupThreshold.value:
                self._cleanupProcessMemory()
                last_cleanup_time = current_time
            try:
                task_data = self._getTaskData()
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                await asyncio.sleep(0.001)
                continue
            task_priority, task_object, retried = task_data
            try:
                task_object.reinitializedParams()
                await self._executeAsyncTask(task_priority, task_object, retried) if task_object.TaskType == "Async" else await self._executeSyncTask(task_priority, task_object, retried)
            except Exception as e:
                self.Logger.error(f"[{self.ProcessName} - {self.pid}] task {task_object.TaskID} failed due to {e}.")
        self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task, determining if the task should be executed with or without locking.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object requires a lock
                a. If locking is required, call _executeLockedAsyncTask to execute the task with locking
            - 2. If no lock is required, call _executeUnLockedAsyncTask to execute the task without locking
        """

        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes a synchronous task, determining if the task should be executed with or without locking.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object requires a lock
                a. If locking is required, call _executeLockedSyncTask to execute the task with locking
            - 2. If no lock is required, call _executeUnLockedSyncTask to execute the task without locking
        """

        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task with locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Attempt to acquire the task lock with a specified timeout
                a. If the lock cannot be acquired, requeue the task for another attempt
            - 2. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutAsyncTask to execute the task with a timeout
                b. If no timeout is specified, call _executeNonTimeoutAsyncTask to execute the task without a timeout
        """

        acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task without locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutAsyncTask to execute the task with a timeout
            - 2. If no timeout is specified, call _executeNonTimeoutAsyncTask to execute the task without a timeout
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried, locked: bool):
        """
        Executes an asynchronous task with a timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Create an asyncio Event to signal task completion
            - 2. Define an inner asynchronous function (_onTaskCancelled) to handle task cancellation
                a. Wait for the future object to complete
                b. Remove the task from PendingTasks and update the task status
                c. Release the task lock if it was locked
            - 3. Define a callback function (_onTaskCompleted) to handle task completion
                a. Check if the future is cancelled
                    i. If cancelled, call the cancellation handler
                b. Attempt to retrieve the task result from the future object
                    i. Signal the wait_for_event and process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 4. Create an asynchronous task for the task object's function with the provided arguments
            - 5. Store the future object in PendingTasks and attach the completion callback
            - 6. Use asyncio.wait_for to await the event with a specified timeout
                a. If a TimeoutError occurs:
                    i. Cancel the task if it is still running
                    ii. Log a warning about the task timeout and cancellation
        """

        wait_for_event = asyncio.Event()

        async def _onTaskCancelled(future_object):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.SynchronizationManager.TaskLock.release()

        def _onTaskCompleted(future_object):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        async_future = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            self.Logger.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes an asynchronous task that is not subject to timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Define an inner asynchronous function (_onTaskCancelled) to handle task cancellation
                a. Wait for the future object to complete
                b. Remove the task from PendingTasks and update the task status
                c. Release the task lock if it was locked
                d. Log a warning about the task cancellation
            - 2. Define a callback function (_onTaskCompleted) to handle task completion
                a. Check if the future is cancelled
                    i. If cancelled, call the cancellation handler
                b. Attempt to retrieve the task result from the future object
                    i. Process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 3. Create an asynchronous task for the task object's function with the provided arguments
            - 4. Store the future object in PendingTasks and attach the completion callback
        """

        async def _onTaskCancelled(future_object):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.SynchronizationManager.TaskLock.release()
            self.Logger.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")

        def _onTaskCompleted(future_object):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        async_future = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Executes a synchronous task with locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Attempt to acquire the task lock with a specified timeout
                a. If the lock cannot be acquired, requeue the task for another attempt
            - 2. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutSyncTask to execute the task with a timeout
                b. If no timeout is specified, call _executeNonTimeoutSyncTask to execute the task without a timeout
        """

        acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Executes a synchronous task without locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutSyncTask to execute the task with a timeout
            - 2. If no timeout is specified, call _executeNonTimeoutSyncTask to execute the task without a timeout
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes a synchronous task with a timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Create an asyncio Event to signal task completion
            - 2. Define a callback function (_onTaskCompleted) to handle task completion
                a. Attempt to retrieve the task result from the future object
                    i. Signal the wait_for_event and process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                b. Handle task cancellation
                    i. Remove the task from PendingTasks and update its status
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 3. Submit the task to the SystemExecutor for execution and store the future object in PendingTasks
            - 4. Attach the completion callback (_onTaskCompleted) to the future object
            - 5. Use asyncio.wait_for to await the event with a specified timeout
                a. If a TimeoutError occurs:
                    i. Cancel the task if it is still running
                    ii. Log a warning about the task timeout and cancellation
        """

        wait_for_event = asyncio.Event()

        def _onTaskCompleted(future_object):
            try:
                task_result = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except CancelledError:
                del self.PendingTasks[task_object.TaskID]
                self._updateTaskStatus()
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        sync_future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            self.Logger.warning(f"[{self.ProcessName} - {self.pid}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes a synchronous task that is not subject to timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Define a callback function (_onTaskCompleted) to handle task completion
                a. Attempt to retrieve the task result from the future object
                    i. Process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                b. Handle task cancellation
                    i. Update the task status and log a warning if cancelled
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    ii. If retries are exhausted, remove the task from PendingTasks, update its status, and log the error
                    iii. Release the task lock if it was locked
            - 2. Submit the task to the SystemExecutor for execution and store the future object in PendingTasks
            - 3. Attach the completion callback (_onTaskCompleted) to the future object
        """

        def _onTaskCompleted(future_object):
            try:
                task_result = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except CancelledError:
                self._updateTaskStatus()
                if locked:
                    self.SynchronizationManager.TaskLock.release()
                self.Logger.warning(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ProcessName} - {self.pid}] Task {task_object.Task.__name__} failed due to {e}\n\n{traceback.format_exc()}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        sync_future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self):
        """
        Updates the task status for the current process based on its type.

        :return: None
        :exception: None

        setup:
            - 1. Retrieve the current task status for the process
                a. Check the process type (Core or Expand) to determine which status to get
            - 2. Extract the task ID and current task count from the status
            - 3. Calculate the new task count, ensuring it does not go below zero
            - 4. Update the task status in the synchronization manager based on the thread type
                a. If the process is Core, update the core process task status
                b. If the process is Expand, update the expand process task status
        """

        current_status = self.SynchronizationManager.getCoreProcessTaskStatus(self.ProcessName) if self.ProcessType == "Core" else self.SynchronizationManager.getExpandProcessTaskStatus(self.ProcessName)
        pid = current_status[0]
        task_count = current_status[1]
        new_task_count = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ProcessType == "Core":
            self.SynchronizationManager.updateCoreProcessTaskStatus(self.ProcessName, pid, new_task_count)
        else:
            self.SynchronizationManager.updateExpandProcessTaskStatus(self.ProcessName, pid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any):
        """
        Processes the result of a completed task and updates the task status.

        :param task_object: The _TaskObject representing the task whose result is being processed
        :param task_result: The result of the task, which may be a GPU tensor or other data type
        :return: None
        :exception: None

        setup:
            - 1. Check if GPU boosting is enabled for the task and if the task result is a tensor or module
                a. If true, clone the result to CPU and clean up GPU resources
                b. Otherwise, use the task result as is
            - 2. Store the processed result in the ResultStorageQueue along with the task ID
            - 3. Attempt to remove the task from the PendingTasks dictionary
                a. Handle KeyError if the task ID does not exist
                b. Log an error if any other exception occurs during removal
            - 4. Update the status of the task
        """

        if task_object.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result = task_result.clone().detach().cpu()
            task_object.cleanupGpuResources()
        else:
            cpu_result = task_result
        self.SynchronizationManager.ResultStorageQueue.put_nowait((cpu_result, task_object.TaskID))
        # noinspection PyBroadException
        try:
            del self.PendingTasks[task_object.TaskID]
            del cpu_result
        except KeyError:
            pass
        except Exception:
            self.Logger.error(f"[{self.ProcessName} - {self.pid}] failed to remove task {task_object.TaskID} from PendingTasks.")
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Requeues a task object to the appropriate priority queue based on its priority level.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", or "LowPriority")
        :param task_object: The _TaskObject representing the task to be requeued
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check the task priority level
                a. If the priority is "HighPriority", put the task in the HighPriorityQueue
                b. If the priority is "MediumPriority", put the task in the MediumPriorityQueue
                c. If the priority is "LowPriority", put the task in the LowPriorityQueue
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

    def _cleanup(self):
        """
        Cleans up remaining tasks in the priority queues and cancels pending tasks.

        :return: None
        :exception: None

        setup:
            - 1. Initialize a counter for remaining tasks
            - 2. Process the HighPriorityQueue:
                a. While the queue is not empty, attempt to retrieve tasks
                    i. Increment the counter for each retrieved task
            - 3. Process the MediumPriorityQueue in the same manner
            - 4. Process the LowPriorityQueue in the same manner
            - 5. Cancel all pending tasks stored in PendingTasks
            - 6. Log the number of discarded tasks
            - 7. Clear the PendingTasks collection
        """

        remaining_tasks = 0
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
        self.Logger.debug(f"[{self.ProcessName} - {self.pid}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _setLogger(self):
        """
        Sets up and configures a logger for the process object.

        :return: None
        :exception: None

        setup:
            - 1. Create a logger instance for the ConcurrentSystem with the name "ConcurrentSystem"
                a. Set the logging level to DEBUG
            - 2. Create a console handler for logging output
                a. Set the handler's logging level based on the DebugMode
            - 3. Configure the formatter for the console handler
                a. Use _ColoredFormatter for formatted log messages
            - 4. Add the console handler to the logger instance
            - 5. Assign the configured logger to the Logger attribute of the instance
        """

        logger = logging.getLogger(f"ConcurrentSystem")
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
        Sets the priority of the process based on the specified priority level.

        :param priority: The priority level to set for the process (default is based on ConfigManager)
        :return: None
        :exception ValueError: Raised if a valid handle to the process cannot be obtained
        :exception Exception: Raised if setting the priority fails

        setup:
            - 1. Define a mapping of priority levels to their corresponding values
            - 2. Attempt to open the current process using its process ID
                a. Raise a ValueError if a valid handle cannot be obtained
            - 3. Set the priority class of the process using SetPriorityClass
                a. If the operation fails, retrieve and raise an exception with the error code
            - 4. Log any exceptions that occur during the priority setting process
            - 5. Ensure the process handle is closed in the finally block to avoid resource leaks
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

    def _setSystemExecutorThreadCount(self):
        """
        Determines the number of executor threads based on the number of physical CPU cores.

        :return: The number of threads to be used by the system executor
        :exception: None

        setup:
            - 1. Define a mapping of core ranges to corresponding thread counts
            - 2. Iterate over the core range and count mapping
                a. If the number of physical cores falls within a defined range, return the corresponding thread count
            - 3. If no suitable range is found, return a default thread count of 12
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

    def _cleanupProcessMemory(self):
        """
        Cleans up the memory of the process by emptying its working set.

        :return: None
        :exception: None

        setup:
            - 1. Check the operating system type
                a. If the system is Windows:
                    i. Attempt to open the process using its process ID
                        - Raise a ValueError if a valid handle cannot be obtained
                    ii. Log an error if the handle is not valid
                    iii. Call EmptyWorkingSet on the process handle to clean up memory
                        - Log an error if the cleanup fails and obtain the error code
                    iv. Close the handle to the process
            - 2. Log any exceptions that occur during the memory cleanup process
        """

        system = platform.system()
        if system == "Windows":
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

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        """
        Retrieves task data from the priority queues in order of priority.

        :return: A tuple containing the task ID, the _TaskObject, and its priority level
        :exception queue.Empty: Raised if all priority queues are empty

        setup:
            - 1. Check if the HighPriorityQueue is not empty
                a. If not empty, retrieve and return the task data
            - 2. If the HighPriorityQueue is empty, check the MediumPriorityQueue
                a. If not empty, retrieve and return the task data
            - 3. If both High and Medium priority queues are empty, check the LowPriorityQueue
                a. If not empty, retrieve and return the task data
            - 4. If all queues are empty, raise queue.Empty
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
    Represents a thread dedicated to processing tasks with varying priority levels in a multithreaded environment.

    This class extends the `threading.Thread` class and is designed to manage the execution of tasks asynchronously.
    It maintains separate queues for high, medium, and low-priority tasks, ensuring that tasks are executed in order
    of importance. The thread uses an asyncio event loop to process tasks, allowing for non-blocking execution of
    asynchronous tasks. The thread can be stopped gracefully, ensuring all tasks are completed or appropriately canceled.
    Additionally, it provides logging capabilities for tracking task execution and any errors that may arise during processing.

    Attributes:
        - ThreadName: The name assigned to the thread.
        - ThreadType: The type of thread, either 'Core' or 'Expand'.
        - SynchronizationManager: An instance of the _SynchronizationManager for managing synchronization.
        - ConfigManager: An instance of the _ConfigManager for accessing configuration settings.
        - Logger: Logger instance for logging thread activities and events.
        - PendingTasks: Dictionary storing tasks that are currently pending execution.
        - SystemExecutor: Optional ThreadPoolExecutor for managing thread execution.
        - HighPriorityQueue: Queue for storing high-priority tasks.
        - MediumPriorityQueue: Queue for storing medium-priority tasks.
        - LowPriorityQueue: Queue for storing low-priority tasks.
        - WorkingEvent: Event signaling that tasks are being processed.
        - CloseEvent: Event signaling when the thread should stop running.
        - EventLoop: Optional asyncio event loop for processing tasks asynchronously.

    Methods:
        - __init__: Initializes the thread with a name, type, synchronization and configuration managers, logger, and executor.
        - run: Runs the asynchronous event loop for processing tasks.
        - stop: Stops the thread by signaling the close event and waiting for the thread to finish execution.
        - addThreadTask: Adds a task object to the appropriate priority queue based on the given priority level.
        - _taskProcessor: Processes tasks from the task queues until the close event is set.
        - _executeAsyncTask: Executes an asynchronous task, determining if the task should be executed with or without locking.
        - _executeSyncTask: Executes a synchronous task, determining if the task should be executed with or without locking.
        - _executeLockedAsyncTask: Executes an asynchronous task with locking, determining if the task should have a timeout.
        - _executeUnLockedAsyncTask: Executes an asynchronous task without locking, determining if the task should have a timeout.
        - _executeTimeoutAsyncTask: Executes an asynchronous task with a timeout, handling its result and potential retries.
        - _executeNonTimeoutAsyncTask: Executes an asynchronous task that is not subject to timeout, handling its result and potential retries.
        - _executeLockedSyncTask: Executes a synchronous task with locking, determining if the task should have a timeout.
        - _executeUnLockedSyncTask: Executes a synchronous task without locking, determining if the task should have a timeout.
        - _executeTimeoutSyncTask: Executes a synchronous task with a timeout, handling its result and potential retries.
        - _executeNonTimeoutSyncTask: Executes a synchronous task that is not subject to timeout, handling its result and potential retries.
        - _updateTaskStatus: Updates the task status for the current thread based on its type.
        - _taskResultProcessor: Processes the result of a completed task and updates the task status.
        - _requeueTask: Requeues a task object to the appropriate priority queue based on its priority level.
        - _cleanup: Cleans up remaining tasks in the priority queues and cancels pending tasks.
        - _getTaskData: Retrieves task data from the priority queues in order of priority.
    """

    def __init__(self, ThreadName: str, ThreadType: Literal['Core', 'Expand'], SM: _SynchronizationManager, CM: _ConfigManager, Logger: logging.Logger, SystemExecutor: Optional[ThreadPoolExecutor]):
        super().__init__(name=ThreadName, daemon=True)
        self.ThreadName = ThreadName
        self.ThreadType = ThreadType
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.Logger = Logger
        self.PendingTasks = {}
        self.SystemExecutor: Optional[ThreadPoolExecutor] = SystemExecutor
        self.HighPriorityQueue: queue.Queue = queue.Queue()
        self.MediumPriorityQueue: queue.Queue = queue.Queue()
        self.LowPriorityQueue: queue.Queue = queue.Queue()
        self.WorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.EventLoop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        """
        Runs the asynchronous event loop for processing tasks.

        :return: None
        :exception: None

        setup:
            - 1. Create a new asyncio event loop and set it as the current event loop
            - 2. Attempt to run the _taskProcessor method until completion
            - 3. Ensure the event loop is closed after processing
            - 4. Log a message indicating that the thread has been stopped
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
        Stops the thread by signaling the close event and waiting for the thread to finish execution.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal the thread to stop running
            - 2. Wait for the thread to complete its execution by calling join()
        """

        self.CloseEvent.set()
        self.join()

    def addThreadTask(self, priority: int, task_object: _TaskObject):
        """
        Adds a task object to the appropriate priority queue based on the given priority level.

        :param priority: An integer representing the priority of the task (0-10)
        :param task_object: The _TaskObject representing the task to be added
        :return: None
        :exception: None

        setup:
            - 1. Set the WorkingEvent to indicate that tasks are being processed
            - 2. Check the priority level and add the task object to the corresponding queue:
                a. If the priority is between 0 and 3, add to the HighPriorityQueue
                b. If the priority is between 4 and 7, add to the MediumPriorityQueue
                c. If the priority is between 8 and 10, add to the LowPriorityQueue
                d. If the priority is out of range (less than 0 or greater than 10), add to the MediumPriorityQueue
                    i. Log a warning that the priority exceeds the allowed range and that a default priority level of 5 has been used
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
            self.Logger.warning(f"[{self.ThreadName} - {self.ident}] exceeds the range of 0 - 10 for task {task_object.Task.__name__}. Default priority level 5 has been used.")

    async def _taskProcessor(self):
        """
        Processes tasks from the task queues until the close event is set.

        :return: None
        :exception: None

        setup:
            - 1. Enter a loop that runs until the CloseEvent is set
            - 2. Attempt to retrieve task data from the task queues
                a. If a queue is empty and there are no pending tasks, clear the WorkingEvent
                b. If no tasks are available, sleep briefly and continue the loop
            - 3. Extract the task priority, task object, and retry count from the task data
            - 4. Reinitialize parameters for the task object
            - 5. Execute the task based on its type
                a. If the task type is "Async", call _executeAsyncTask
                b. If the task type is not "Async", call _executeSyncTask
            - 6. Handle any exceptions that occur during task execution, logging the error
            - 7. Call _cleanup to perform any necessary cleanup when exiting the loop
        """

        while not self.CloseEvent.is_set():
            try:
                task_data = self._getTaskData()
            except queue.Empty:
                if len(self.PendingTasks) == 0:
                    self.WorkingEvent.clear()
                await asyncio.sleep(0.001)
                continue
            task_priority, task_object, retried = task_data
            try:
                task_object.reinitializedParams()
                await self._executeAsyncTask(task_priority, task_object, retried) if task_object.TaskType == "Async" else await self._executeSyncTask(task_priority, task_object, retried)
            except Exception as e:
                self.Logger.error(f"[{self.ThreadName} - {self.ident}] task {task_object.TaskID} failed due to {e}.")
        self._cleanup()

    async def _executeAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task, determining if the task should be executed with or without locking.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object requires a lock
                a. If locking is required, call _executeLockedAsyncTask to execute the task with locking
            - 2. If no lock is required, call _executeUnLockedAsyncTask to execute the task without locking
        """

        if task_object.Lock:
            await self._executeLockedAsyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedAsyncTask(task_priority, task_object, retried)

    async def _executeSyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes a synchronous task, determining if the task should be executed with or without locking.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object requires a lock
                a. If locking is required, call _executeLockedSyncTask to execute the task with locking
            - 2. If no lock is required, call _executeUnLockedSyncTask to execute the task without locking
        """

        if task_object.Lock:
            await self._executeLockedSyncTask(task_priority, task_object, retried)
            return
        await self._executeUnLockedSyncTask(task_priority, task_object, retried)

    async def _executeLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task with locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Attempt to acquire the task lock with a specified timeout
                a. If the lock cannot be acquired, requeue the task for another attempt
            - 2. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutAsyncTask to execute the task with a timeout
                b. If no timeout is specified, call _executeNonTimeoutAsyncTask to execute the task without a timeout
        """

        acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedAsyncTask(self, task_priority: str, task_object: _TaskObject, retried):
        """
        Executes an asynchronous task without locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutAsyncTask to execute the task with a timeout
            - 2. If no timeout is specified, call _executeNonTimeoutAsyncTask to execute the task without a timeout
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutAsyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutAsyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried, locked: bool):
        """
        Executes an asynchronous task with a timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Create an asyncio Event to signal task completion
            - 2. Define an inner asynchronous function (_onTaskCancelled) to handle task cancellation
                a. Wait for the future object to complete
                b. Remove the task from PendingTasks and update the task status
                c. Release the task lock if it was locked
            - 3. Define a callback function (_onTaskCompleted) to handle task completion
                a. Check if the future is cancelled
                    i. If cancelled, call the cancellation handler
                b. Attempt to retrieve the task result from the future object
                    i. Signal the wait_for_event and process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 4. Create an asynchronous task for the task object's function with the provided arguments
            - 5. Store the future object in PendingTasks and attach the completion callback
            - 6. Use asyncio.wait_for to await the event with a specified timeout
                a. If a TimeoutError occurs:
                    i. Cancel the task if it is still running
                    ii. Log a warning about the task timeout and cancellation
        """

        wait_for_event = asyncio.Event()

        async def _onTaskCancelled(future_object):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.SynchronizationManager.TaskLock.release()

        def _onTaskCompleted(future_object):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        async_future = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            async_future.cancel()
            self.Logger.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutAsyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes an asynchronous task that is not subject to timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Define an inner asynchronous function (_onTaskCancelled) to handle task cancellation
                a. Wait for the future object to complete
                b. Remove the task from PendingTasks and update the task status
                c. Release the task lock if it was locked
                d. Log a warning about the task cancellation
            - 2. Define a callback function (_onTaskCompleted) to handle task completion
                a. Check if the future is cancelled
                    i. If cancelled, call the cancellation handler
                b. Attempt to retrieve the task result from the future object
                    i. Process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 3. Create an asynchronous task for the task object's function with the provided arguments
            - 4. Store the future object in PendingTasks and attach the completion callback
        """

        async def _onTaskCancelled(future_object):
            await future_object
            del self.PendingTasks[task_object.TaskID]
            self._updateTaskStatus()
            if locked:
                self.SynchronizationManager.TaskLock.release()
            self.Logger.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")

        def _onTaskCompleted(future_object):
            if future_object.cancelled():
                self.EventLoop.create_task(_onTaskCancelled(future_object))
                return
            try:
                task_result = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        async_future = self.EventLoop.create_task(task_object.Task(*task_object.RecoveredArgs, **task_object.RecoveredKwargs))
        self.PendingTasks[task_object.TaskID] = async_future
        async_future.add_done_callback(_onTaskCompleted)

    async def _executeLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Executes a synchronous task with locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Attempt to acquire the task lock with a specified timeout
                a. If the lock cannot be acquired, requeue the task for another attempt
            - 2. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutSyncTask to execute the task with a timeout
                b. If no timeout is specified, call _executeNonTimeoutSyncTask to execute the task without a timeout
        """

        acquired = self.SynchronizationManager.TaskLock.acquire(timeout=task_object.LockTimeout)
        if not acquired:
            self._requeueTask(task_priority, task_object, retried)
            return
        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, True)
        else:
            await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, True)

    async def _executeUnLockedSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Executes a synchronous task without locking, determining if the task should have a timeout.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check if the task object has a timeout set
                a. If a timeout is specified, call _executeTimeoutSyncTask to execute the task with a timeout
            - 2. If no timeout is specified, call _executeNonTimeoutSyncTask to execute the task without a timeout
        """

        if task_object.TimeOut is not None:
            await self._executeTimeoutSyncTask(task_priority, task_object, retried, False)
            return
        await self._executeNonTimeoutSyncTask(task_priority, task_object, retried, False)

    async def _executeTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes a synchronous task with a timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Create an asyncio Event to signal task completion
            - 2. Define a callback function (_onTaskCompleted) to handle task completion
                a. Attempt to retrieve the task result from the future object
                    i. Signal the wait_for_event and process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                b. Handle task cancellation
                    i. Remove the task from PendingTasks and update its status
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. Remove the task from PendingTasks
                    ii. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    iii. If retries are exhausted, update the task status and log the error
                    iv. Release the task lock if it was locked
            - 3. Submit the task to the SystemExecutor for execution and store the future object in PendingTasks
            - 4. Attach the completion callback (_onTaskCompleted) to the future object
            - 5. Use asyncio.wait_for to await the event with a specified timeout
                a. If a TimeoutError occurs:
                    i. Cancel the task if it is still running
                    ii. Log a warning about the task timeout and cancellation
        """

        wait_for_event = asyncio.Event()

        def _onTaskCompleted(future_object):
            try:
                task_result = future_object.result()
                wait_for_event.set()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except CancelledError:
                del self.PendingTasks[task_object.TaskID]
                self._updateTaskStatus()
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except Exception as e:
                del self.PendingTasks[task_object.TaskID]
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        sync_future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)
        try:
            await asyncio.wait_for(wait_for_event.wait(), timeout=task_object.TimeOut)
        except asyncio.TimeoutError:
            if not sync_future.done():
                sync_future.cancel()
            self.Logger.warning(f"[{self.ThreadName} - {self.ident}] task {task_object.Task.__name__} timed out and has been cancelled.")

    async def _executeNonTimeoutSyncTask(self, task_priority: str, task_object: _TaskObject, retried: int, locked: bool):
        """
        Executes a synchronous task that is not subject to timeout, handling its result and potential retries.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", "LowPriority")
        :param task_object: The _TaskObject representing the task to be executed
        :param retried: The number of times the task has been retried
        :param locked: Indicates whether the task lock should be released upon completion
        :return: None
        :exception: None

        setup:
            - 1. Define a callback function (_onTaskCompleted) to handle task completion
                a. Attempt to retrieve the task result from the future object
                    i. Process the task result using _taskResultProcessor
                    ii. Release the task lock if it was locked
                b. Handle task cancellation
                    i. Update the task status and log a warning if cancelled
                    ii. Release the task lock if it was locked
                c. Handle any exceptions that occur during execution
                    i. If the task is set to retry and the maximum retries have not been reached:
                        - Requeue the task for another attempt
                        - Log the retry information
                    ii. If retries are exhausted, remove the task from PendingTasks, update its status, and log the error
                    iii. Release the task lock if it was locked
            - 2. Submit the task to the SystemExecutor for execution and store the future object in PendingTasks
            - 3. Attach the completion callback (_onTaskCompleted) to the future object
        """

        def _onTaskCompleted(future_object):
            try:
                task_result = future_object.result()
                self._taskResultProcessor(task_object, task_result)
                if locked:
                    self.SynchronizationManager.TaskLock.release()
            except CancelledError:
                self._updateTaskStatus()
                if locked:
                    self.SynchronizationManager.TaskLock.release()
                self.Logger.warning(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} was cancelled.")
            except Exception as e:
                if task_object.IsRetry and retried < task_object.MaxRetries:
                    self._requeueTask(task_priority, task_object, retried + 1)
                    self.Logger.info(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} is requeued for retry {retried + 1}.")
                else:
                    del self.PendingTasks[task_object.TaskID]
                    self._updateTaskStatus()
                    self.Logger.error(f"[{self.ThreadName} - {self.ident}] Task {task_object.Task.__name__} failed due to {e}\n\n{traceback.format_exc()}.")
                if locked:
                    self.SynchronizationManager.TaskLock.release()

        sync_future = self.SystemExecutor.submit(task_object.Task, *task_object.RecoveredArgs, **task_object.RecoveredKwargs)
        self.PendingTasks[task_object.TaskID] = sync_future
        sync_future.add_done_callback(_onTaskCompleted)

    def _updateTaskStatus(self):
        """
        Updates the task status for the current thread based on its type.

        :return: None
        :exception: None

        setup:
            - 1. Retrieve the current task status for the thread
                a. Check the thread type (Core or Expand) to determine which status to get
            - 2. Extract the task ID and current task count from the status
            - 3. Calculate the new task count, ensuring it does not go below zero
            - 4. Update the task status in the synchronization manager based on the thread type
                a. If the thread is Core, update the core thread task status
                b. If the thread is Expand, update the expand thread task status
        """

        current_status = self.SynchronizationManager.getCoreThreadTaskStatus(self.ThreadName) if self.ThreadType == "Core" else self.SynchronizationManager.getExpandThreadTaskStatus(self.ThreadName)
        tid = current_status[0]
        task_count = current_status[1]
        new_task_count = task_count - 1 if task_count - 1 >= 0 else 0
        if self.ThreadType == "Core":
            self.SynchronizationManager.updateCoreThreadTaskStatus(self.ThreadName, tid, new_task_count)
        else:
            self.SynchronizationManager.updateExpandThreadTaskStatus(self.ThreadName, tid, new_task_count)

    def _taskResultProcessor(self, task_object: _TaskObject, task_result: Any):
        """
        Processes the result of a completed task and updates the task status.

        :param task_object: The _TaskObject representing the task whose result is being processed
        :param task_result: The result of the task, which may be a GPU tensor or other data type
        :return: None
        :exception: None

        setup:
            - 1. Check if GPU boosting is enabled for the task and if the task result is a tensor or module
                a. If true, clone the result to CPU and clean up GPU resources
                b. Otherwise, use the task result as is
            - 2. Store the processed result in the ResultStorageQueue along with the task ID
            - 3. Attempt to remove the task from the PendingTasks dictionary
                a. Handle KeyError if the task ID does not exist
                b. Log an error if any other exception occurs during removal
            - 4. Update the status of the task
        """

        if task_object.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result = task_result.clone().detach().cpu()
            task_object.cleanupGpuResources()
        else:
            cpu_result = task_result
        self.SynchronizationManager.ResultStorageQueue.put_nowait((cpu_result, task_object.TaskID))
        # noinspection PyBroadException
        try:
            del self.PendingTasks[task_object.TaskID]
            del cpu_result
        except KeyError:
            pass
        except Exception:
            self.Logger.error(f"[{self.ThreadName} - {self.ident}] failed to remove task {task_object.TaskID} from PendingTasks.")
        self._updateTaskStatus()

    def _requeueTask(self, task_priority: str, task_object: _TaskObject, retried: int):
        """
        Requeues a task object to the appropriate priority queue based on its priority level.

        :param task_priority: The priority level of the task ("HighPriority", "MediumPriority", or "LowPriority")
        :param task_object: The _TaskObject representing the task to be requeued
        :param retried: The number of times the task has been retried
        :return: None
        :exception: None

        setup:
            - 1. Check the task priority level
                a. If the priority is "HighPriority", put the task in the HighPriorityQueue
                b. If the priority is "MediumPriority", put the task in the MediumPriorityQueue
                c. If the priority is "LowPriority", put the task in the LowPriorityQueue
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

    def _cleanup(self):
        """
        Cleans up remaining tasks in the priority queues and cancels pending tasks.

        :return: None
        :exception: None

        setup:
            - 1. Initialize a counter for remaining tasks
            - 2. Process the HighPriorityQueue:
                a. While the queue is not empty, attempt to retrieve tasks
                    i. Increment the counter for each retrieved task
            - 3. Process the MediumPriorityQueue in the same manner
            - 4. Process the LowPriorityQueue in the same manner
            - 5. Cancel all pending tasks stored in PendingTasks
            - 6. Log the number of discarded tasks
            - 7. Clear the PendingTasks collection
        """

        remaining_tasks = 0
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
        for i, pending_task in self.PendingTasks.items():
            pending_task.cancel()
        self.Logger.debug(f"[{self.ThreadName} - {self.ident}] discarded {remaining_tasks} tasks.")
        self.PendingTasks.clear()

    def _getTaskData(self) -> Tuple[str, _TaskObject, int]:
        """
        Retrieves task data from the priority queues in order of priority.

        :return: A tuple containing the task ID, the _TaskObject, and its priority level
        :exception queue.Empty: Raised if all priority queues are empty

        setup:
            - 1. Check if the HighPriorityQueue is not empty
                a. If not empty, retrieve and return the task data
            - 2. If the HighPriorityQueue is empty, check the MediumPriorityQueue
                a. If not empty, retrieve and return the task data
            - 3. If both High and Medium priority queues are empty, check the LowPriorityQueue
                a. If not empty, retrieve and return the task data
            - 4. If all queues are empty, raise queue.Empty
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
    Manages load balancing across processes and threads in the system by performing periodic cleanup and monitoring of resource usage.

    This class extends the `threading.Thread` class,
    allowing it to operate as a background daemon thread. It ensures that resources are optimally
    utilized by dynamically expanding or shrinking the number of active processes and threads
    based on their load and usage patterns. The load balancer can automatically manage memory
    cleanup for both the main and service processes, helping to prevent memory leaks and ensure
    the system remains responsive. It also supports logging for tracking load balancing operations
    and potential issues.

    Attributes:
        - SynchronizationManager: An instance of the _SynchronizationManager for managing synchronization.
        - ConfigManager: An instance of the _ConfigManager for accessing configuration settings.
        - Logger: Logger instance for logging load balancer activities and events.
        - DebugMode: Boolean indicating if debug mode is enabled, affecting logging behavior.
        - SystemExecutor: Optional ThreadPoolExecutor for managing thread execution.
        - CloseEvent: Event signaling when the load balancer should stop running.

    Methods:
        - __init__: Initializes the LoadBalancer with necessary managers, logger, and configurations.
        - run: Runs the load balancer, performing periodic memory cleanup and managing process and thread loads.
        - stop: Stops the load balancer by signaling the close event and waiting for the thread to finish.
        - _cleanupMainProcessMemory: Cleans up the memory of the main process by emptying its working set.
        - _cleanupServiceProcessMemory: Cleans up the memory of the service process by emptying its working set.
        - _updateProcessLoadStatus: Updates the load status of core and expand processes based on CPU and memory usage.
        - _expandPolicyExecutor: Executes the expansion policy based on the configuration.
        - _noExpand: A placeholder method for the no expansion policy.
        - _autoExpand: Automatically expands processes and threads if their load exceeds specified thresholds.
        - _beforehandExpand: Checks the current load on processes and threads, expanding them if the load exceeds a certain threshold.
        - _isAllowExpansion: Determines whether expansion is allowed for the specified type (Process or Thread).
        - _expandProcess: Expands the process pool by creating and starting a new process.
        - _expandThread: Expands the thread pool by creating and starting a new thread.
        - _generateExpandID: Generates a unique ID for the specified expand type (Process or Thread).
        - _shrinkagePolicyExecutor: Executes the shrinkage policy based on the configuration.
        - _noShrink: A placeholder method for the no shrinkage policy.
        - _autoShrink: Automatically shrinks the expand process and thread pools by terminating idle processes and threads.
        - _timeoutShrink: Shrinks the expand process and thread pools by terminating those that exceed their survival time.
    """

    def __init__(self, SM: _SynchronizationManager, CM: _ConfigManager, Logger: logging.Logger, DebugMode: bool, SystemExecutor: Optional[ThreadPoolExecutor]):
        super().__init__(name='LoadBalancer', daemon=True)
        self.SynchronizationManager = SM
        self.ConfigManager = CM
        self.Logger = Logger
        self.DebugMode = DebugMode
        self.SystemExecutor: Optional[ThreadPoolExecutor] = SystemExecutor
        self.CloseEvent = multiprocessing.Event()

    def run(self):
        """
        Runs the load balancer, performing periodic memory cleanup and managing process and thread loads.

        :return: None
        :exception: None

        setup:
            - 1. Perform an initial cleanup of the main process and service process memory
            - 2. Initialize the last cleanup time
            - 3. Enter a loop that runs until the CloseEvent is set
                a. Update the load status of processes
                b. Execute the expansion policy
                c. Execute the shrinkage policy
                d. Sleep briefly to avoid busy-waiting
                e. If more than 300 seconds have passed since the last cleanup:
                    i. Update the last cleanup time
                    ii. Perform cleanup of the main process and service process memory
            - 4. Log that the LoadBalancer has been closed upon exiting the loop
        """

        self._cleanupMainProcessMemory()
        self._cleanupServiceProcessMemory()
        last_cleanup_time = time.time()
        while not self.CloseEvent.is_set():
            self._updateProcessLoadStatus()
            self._expandPolicyExecutor()
            self._shrinkagePolicyExecutor()
            time.sleep(0.001)
            if time.time() - last_cleanup_time > 300:
                last_cleanup_time = time.time()
                self._cleanupMainProcessMemory()
                self._cleanupServiceProcessMemory()
        self.Logger.debug(f"[LoadBalancer] has been closed.")

    def stop(self):
        """
        Stops the load balancer by signaling the close event and waiting for the thread to finish.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal the load balancer to stop running
            - 2. Wait for the load balancer thread to complete execution by calling join()
        """

        self.CloseEvent.set()
        self.join()

    def _cleanupMainProcessMemory(self):
        """
        Cleans up the memory of the main process by emptying its working set.

        :return: None
        :exception: None

        setup:
            - 1. Check the operating system type
                a. If the system is Windows:
                    i. Attempt to open the main process using its process ID
                        - Raise a ValueError if a valid handle cannot be obtained
                    ii. Log an error if the handle is not valid
                    iii. Call EmptyWorkingSet on the process handle to clean up memory
                        - Log an error if the cleanup fails and obtain the error code
                    iv. Close the handle to the main process
            - 2. Log any exceptions that occur during the memory cleanup process
        """

        system = platform.system()
        if system == "Windows":
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
            return

    def _cleanupServiceProcessMemory(self):
        """
        Cleans up the memory of the service process by emptying its working set.

        :return: None
        :exception: None

        setup:
            - 1. Check the operating system type
                a. If the system is Windows:
                    i. Attempt to open the process using its ID from the shared object manager
                        - Raise a ValueError if a valid handle cannot be obtained
                    ii. Log an error if the handle is not valid
                    iii. Call EmptyWorkingSet on the process handle to clean up memory
                        - Log an error if the cleanup fails and obtain the error code
                    iv. Close the handle to the process
            - 2. Log any exceptions that occur during the memory cleanup process
        """

        system = platform.system()
        if system == "Windows":
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

    def _updateProcessLoadStatus(self):
        """
        Updates the load status of core and expand processes based on CPU and memory usage.

        :return: None
        :exception: None

        setup:
            - 1. Iterate over each process in the core process pool
                a. Attempt to retrieve the CPU and memory usage for each process
                    i. Calculate the weighted load based on CPU usage, memory usage, and current task status
                    ii. Update the load status for the core process in the synchronization manager
                b. If an exception occurs, set the load status to 0 for the process
            - 2. If there are processes in the expand process pool, repeat the above steps for each expand process
                a. Attempt to retrieve the CPU and memory usage for each expand process
                    i. Calculate the weighted load based on CPU usage, memory usage, and current task status
                    ii. Update the load status for the expand process in the synchronization manager
                b. If an exception occurs, set the load status to 0 for the expand process
        """

        global _CoreProcessPool, _ExpandProcessPool
        for process_name, process_obj in _CoreProcessPool.items():
            # noinspection PyBroadException
            try:
                process_cpu_usage = _Monitor.processCpuUsage(process_obj.pid, 0.001)
                process_memory_usage = _Monitor.processMemoryUsage(process_obj.pid)
                weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.5) + (self.SynchronizationManager.CoreProcessTaskStatusPool[process_name][1] * 0.5)), 100))
                self.SynchronizationManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, weighted_load)
            except Exception:
                self.SynchronizationManager.updateCoreProcessLoadStatus(process_name, process_obj.pid, 0)
        if _ExpandProcessPool:
            for process_name, process_obj in _ExpandProcessPool.items():
                # noinspection PyBroadException
                try:
                    process_cpu_usage = _Monitor.processCpuUsage(process_obj.pid, 0.001)
                    process_memory_usage = _Monitor.processMemoryUsage(process_obj.pid)
                    weighted_load = max(0, min(int(process_cpu_usage + (process_memory_usage * 0.5) + (self.SynchronizationManager.ExpandProcessTaskStatusPool[process_name][1] * 0.5)), 100))
                    self.SynchronizationManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, weighted_load)
                except Exception:
                    self.SynchronizationManager.updateExpandProcessLoadStatus(process_name, process_obj.pid, 0)

    def _expandPolicyExecutor(self):
        """
        Executes the expansion policy based on the configuration.

        :return: None
        :exception KeyError: Raised if the configured expansion policy is not recognized

        setup:
            - 1. Define a mapping of expansion policy names to their corresponding methods
            - 2. Retrieve the expansion method based on the current configuration value
            - 3. Call the selected expansion method to execute the policy
        """

        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self.ConfigManager.ExpandPolicy.value]
        expand_method()

    def _noExpand(self):
        """No expansion policy method."""
        pass

    def _autoExpand(self):
        """
        Automatically expands processes and threads if their load exceeds specified thresholds.

        :return: None
        :exception: None

        setup:
            - 1. Check if the core process count is greater than zero
                a. Calculate the total load of core processes
                b. Calculate the total load of expand processes, if any
                c. Sum the total load from core and expand processes
                d. Check if the total load exceeds the ideal load per process
                    i. If true, check if process expansion is allowed and attempt to expand processes
                        - Log a warning if expansion is not possible
            - 2. Calculate the total load of core threads
                a. Calculate the total load of expand threads, if any
                b. Sum the total load from core and expand threads
                c. Check if the total load exceeds the ideal load per thread
                    i. If true, check if thread expansion is allowed and attempt to expand threads
                        - Log a warning if expansion is not possible
        """

        if self.ConfigManager.CoreProcessCount.value != 0:
            current_core_process_total_load = sum([self.SynchronizationManager.getCoreProcessLoadStatus(name)[1] for name, load_status in self.SynchronizationManager.CoreProcessLoadStatusPool.items()])
            if self.SynchronizationManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load = sum([self.SynchronizationManager.getExpandProcessLoadStatus(name)[1] for name, load_status in self.SynchronizationManager.ExpandProcessLoadStatusPool.items()])
            else:
                current_expand_process_total_load = 0
            process_total_load = current_core_process_total_load + current_expand_process_total_load
            ideal_load_per_process = 60
            if process_total_load > ideal_load_per_process:
                if self._isAllowExpansion("Process") and _ProcessBalanceLock.acquire(timeout=0):
                    self._expandProcess()
                    _ProcessBalanceLock.release()
                else:
                    self.Logger.warning(f"Load reaches {int(ideal_load_per_process)}%, but unable to expand more process")
        current_core_thread_total_load = sum([self.SynchronizationManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.CoreThreadTaskStatusPool.items()])
        if self.SynchronizationManager.ExpandThreadTaskStatusPool:
            current_expand_thread_total_load = sum([self.SynchronizationManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.ExpandThreadTaskStatusPool.items()])
        else:
            current_expand_thread_total_load = 0
        thread_total_load = current_core_thread_total_load + current_expand_thread_total_load
        ideal_load_per_thread = 80
        if thread_total_load > ideal_load_per_thread:
            if self._isAllowExpansion("Thread") and _ThreadBalanceLock.acquire(timeout=0.):
                self._expandThread()
                _ThreadBalanceLock.release()
            else:
                self.Logger.warning(f"Load reaches {int(ideal_load_per_thread)}%, but unable to expand more thread")

    def _beforehandExpand(self):
        """
        Checks the current load on processes and threads, and expands them if the load exceeds a certain threshold.

        :return: None
        :exception: None

        setup:
            - 1. Check if the core process count is greater than zero
                a. If true, calculate the total load of core processes
                b. Calculate the total load of expand processes, if any
                c. Sum the total task count from core and expand processes
            - 2. Calculate the total load of core threads
                a. Calculate the total load of expand threads, if any
                b. Sum the total load from core and expand threads
            - 3. If the combined load of processes and threads exceeds 80% of the global task threshold:
                a. Check if process expansion is allowed and attempt to expand processes
                    i. Log a warning if expansion is not possible
                b. Check if thread expansion is allowed and attempt to expand threads
                    i. Log a warning if expansion is not possible
        """

        if self.ConfigManager.CoreProcessCount.value != 0:
            current_core_process_total_load = sum([self.SynchronizationManager.getCoreProcessTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.CoreProcessTaskStatusPool.items()])
            if self.SynchronizationManager.ExpandProcessTaskStatusPool:
                current_expand_process_total_load = sum([self.SynchronizationManager.getExpandProcessTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.ExpandProcessTaskStatusPool.items()])
            else:
                current_expand_process_total_load = 0
            process_total_task_count = current_core_process_total_load + current_expand_process_total_load
        else:
            process_total_task_count = 0
        current_core_thread_total_load = sum([self.SynchronizationManager.getCoreThreadTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.CoreThreadTaskStatusPool.items()])
        if self.SynchronizationManager.ExpandThreadTaskStatusPool:
            current_expand_thread_total_load = sum([self.SynchronizationManager.getExpandThreadTaskStatus(name)[1] for name, load_status in self.SynchronizationManager.ExpandThreadTaskStatusPool.items()])
        else:
            current_expand_thread_total_load = 0
        thread_total_load = current_core_thread_total_load + current_expand_thread_total_load
        if (process_total_task_count + thread_total_load) >= self.ConfigManager.GlobalTaskThreshold.value * 0.8:
            if self._isAllowExpansion("Process") and _ProcessBalanceLock.acquire(timeout=0):
                self._expandProcess()
                _ProcessBalanceLock.release()
            else:
                self.Logger.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more process")
            if self._isAllowExpansion("Thread") and _ThreadBalanceLock.acquire(timeout=0):
                self._expandThread()
                _ThreadBalanceLock.release()
            else:
                self.Logger.warning(f"Task count reaches {self.ConfigManager.GlobalTaskThreshold.value}, but unable to expand more thread")

    def _isAllowExpansion(self, expand_type: Literal["Process", "Thread"]) -> bool:
        """
        Determines whether expansion is allowed for the specified type (Process or Thread).

        :param expand_type: The type of expansion to check ("Process" or "Thread")
        :return: True if expansion is allowed, False otherwise
        :exception: None

        setup:
            - 1. Use a match statement to evaluate the expand type
                a. If the type is "Process":
                    i. Check if the total number of core and expand processes meets or exceeds the maximum allowed
                        - Return False if the limit is reached, otherwise return True
                b. If the type is "Thread":
                    i. Check if the total number of core and expand threads meets or exceeds the maximum allowed
                        - Return False if the limit is reached, otherwise return True
        """

        match expand_type:
            case "Process":
                if (len(self.SynchronizationManager.CoreProcessTaskStatusPool) + len(self.SynchronizationManager.ExpandProcessTaskStatusPool)) >= self.ConfigManager.MaximumProcessCount.value:
                    return False
                return True
            case "Thread":
                if (len(self.SynchronizationManager.CoreThreadTaskStatusPool) + len(self.SynchronizationManager.ExpandThreadTaskStatusPool)) >= self.ConfigManager.MaximumThreadCount.value:
                    return False
                return True

    def _expandProcess(self):
        """
        Expands the process pool by creating and starting a new process.

        :return: None
        :exception: None

        setup:
            - 1. Generate a unique ID for the new process using the _generateExpandID method
            - 2. Create a new _ProcessObject with the generated ID and relevant configurations
            - 3. Start the newly created process
            - 4. Add the new process object to the expand process pool
            - 5. Update the load and task status for the new process in the synchronization manager
            - 6. Record the survival time of the new process
        """

        global _ExpandProcessPool, _ExpandProcessSurvivalTime
        process_id = self._generateExpandID("Process")
        process_object = _ProcessObject(process_id, "Expand", self.SynchronizationManager, self.ConfigManager, self.DebugMode)
        process_object.start()
        _ExpandProcessPool[process_id] = process_object
        self.SynchronizationManager.updateExpandProcessLoadStatus(process_id, process_object.pid, 0)
        self.SynchronizationManager.updateExpandProcessTaskStatus(process_id, process_object.pid, 0)
        _ExpandProcessSurvivalTime[process_id] = time.time()

    def _expandThread(self):
        """
        Expands the thread pool by creating and starting a new thread.

        :return: None
        :exception: None

        setup:
            - 1. Generate a unique ID for the new thread using the _generateExpandID method
            - 2. Create a new _ThreadObject with the generated ID and relevant configurations
            - 3. Start the newly created thread
            - 4. Update the task status for the new thread in the synchronization manager
            - 5. Record the survival time of the new thread
        """

        global _ExpandThreadPool, _ExpandThreadSurvivalTime
        thread_id = self._generateExpandID("Thread")
        thread_object = _ThreadObject(thread_id, "Expand", self.SynchronizationManager, self.ConfigManager, self.Logger, self.SystemExecutor)
        thread_object.start()
        self.SynchronizationManager.updateExpandThreadTaskStatus(thread_id, thread_object.ident, 0)
        _ExpandThreadSurvivalTime[thread_id] = time.time()

    @staticmethod
    def _generateExpandID(expand_type: Literal["Process", "Thread"]):
        """
        Generates a unique ID for the specified expand type (Process or Thread).

        :param expand_type: The type of expansion for which to generate an ID ("Process" or "Thread")
        :return: A unique ID string for the specified expand type
        :exception: None

        setup:
            - 1. Define a mapping of expand types to their corresponding pools
            - 2. Initialize a basic ID using the expand type and a starting index of 0
            - 3. Enter a loop to check for uniqueness of the generated ID
                a. If the generated ID does not exist in the respective pool, return it
                b. If it exists, increment the index and generate a new ID
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
        Executes the shrinkage policy based on the configuration.

        :return: None
        :exception KeyError: Raised if the configured shrinkage policy is not recognized

        setup:
            - 1. Define a mapping of shrinkage policy names to their corresponding methods
            - 2. Retrieve the shrinkage method based on the current configuration value
            - 3. Call the selected shrinkage method to execute the policy
        """

        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self.ConfigManager.ShrinkagePolicy.value]
        shrink_method()

    def _noShrink(self):
        """No shrinkage policy method."""
        pass

    def _autoShrink(self):
        """
        Automatically shrinks the expand process and thread pools by terminating idle processes and threads that exceed their survival time.

        :return: None
        :exception: None

        setup:
            - 1. Check if the core process count is greater than zero and if process task scheduling is not active
                a. Identify expand processes that are not working and have exceeded their survival time
                b. If there are processes eligible for closure and the process balance lock can be acquired:
                    i. Stop each identified expand process
                    ii. Remove the process from the expand process pool and its associated statuses
                    iii. Log that the process has been closed due to idle status
                c. Release the process balance lock
            - 2. Check if thread task scheduling is active
                a. If it is active, exit the method
            - 3. Identify expand threads that are not working and have exceeded their survival time
                a. If there are threads eligible for closure and the thread balance lock can be acquired:
                    i. Stop each identified expand thread
                    ii. Remove the thread from the expand thread pool and its associated statuses
                    iii. Log that the thread has been closed due to idle status
                b. Release the thread balance lock
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime, _ProcessTaskSchedulingEvent, _ThreadTaskSchedulingEvent, _ProcessBalanceLock, _ThreadBalanceLock
        if self.ConfigManager.CoreProcessCount.value != 0 and not _ProcessTaskSchedulingEvent.is_set():
            expand_process_obj = [obj for i, obj in _ExpandProcessPool.items()]
            allow_close_processes = [
                obj for obj in expand_process_obj
                if not obj.WorkingEvent.is_set() and (time.time() - _ExpandProcessSurvivalTime[obj.ProcessName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value
            ]
            if allow_close_processes and _ProcessBalanceLock.acquire(timeout=0):
                for obj in allow_close_processes:
                    obj.stop()
                    del _ExpandProcessPool[obj.ProcessName]
                    del self.SynchronizationManager.ExpandProcessTaskStatusPool[obj.ProcessName]
                    del self.SynchronizationManager.ExpandProcessLoadStatusPool[obj.ProcessName]
                    del _ExpandProcessSurvivalTime[obj.ProcessName]
                    self.Logger.debug(f"[{obj.ProcessName} - {obj.pid}] has been closed due to idle status.")
                _ProcessBalanceLock.release()

        if _ThreadTaskSchedulingEvent.is_set():
            return
        expand_thread_obj = [obj for i, obj in _ExpandThreadPool.items()]
        allow_close_threads = [
            obj for obj in expand_thread_obj
            if not obj.WorkingEvent.is_set() and (time.time() - _ExpandThreadSurvivalTime[obj.ThreadName]) >= self.ConfigManager.ShrinkagePolicyTimeout.value
        ]
        if allow_close_threads and _ThreadBalanceLock.acquire(timeout=0):
            for obj in allow_close_threads:
                obj.stop()
                del _ExpandThreadPool[obj.ThreadName]
                del self.SynchronizationManager.ExpandThreadTaskStatusPool[obj.ThreadName]
                del _ExpandThreadSurvivalTime[obj.ThreadName]
                self.Logger.debug(f"[{obj.ThreadName} - {obj.ident}] has been closed due to idle status.")
            _ThreadBalanceLock.release()

    def _timeoutShrink(self):
        """
        Shrinks the expand process and thread pools by terminating those that exceed their survival time.

        :return: None
        :exception: None

        setup:
            - 1. Check if the core process count is greater than zero
                a. If true, identify expand processes that have exceeded their survival time
                b. If there are any such processes and the process balance lock can be acquired:
                    i. Stop each identified expand process
                    ii. Remove the process from the expand process pool and its associated status
                    iii. Log that the process has been closed due to timeout
            - 2. Identify expand threads that have exceeded their survival time
                a. If there are any such threads and the thread balance lock can be acquired:
                    i. Stop each identified expand thread
                    ii. Remove the thread from the expand thread pool and its associated status
                    iii. Log that the thread has been closed due to timeout
        """

        global _ExpandProcessPool, _ExpandThreadPool, _ExpandProcessSurvivalTime, _ExpandThreadSurvivalTime
        if self.ConfigManager.CoreProcessCount.value != 0:
            expand_process_obj = [obj for obj, survival_time in _ExpandProcessSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
            if expand_process_obj and _ProcessBalanceLock.acquire(timeout=0):
                for obj in expand_process_obj:
                    _ExpandProcessPool[obj].stop()
                    del _ExpandProcessPool[obj]
                    del self.SynchronizationManager.ExpandProcessTaskStatusPool[obj]
                    del _ExpandProcessSurvivalTime[obj]
                    self.Logger.debug(f"{obj} has been closed due to timeout.")
                _ProcessBalanceLock.release()

        expand_thread_obj = [obj for obj, survival_time in _ExpandThreadSurvivalTime.items() if (time.time() - survival_time) >= self.ConfigManager.ShrinkagePolicyTimeout.value]
        if expand_thread_obj and _ThreadBalanceLock.acquire(timeout=0):
            for obj in expand_thread_obj:
                _ExpandThreadPool[obj].stop()
                del _ExpandThreadPool[obj]
                del self.SynchronizationManager.ExpandThreadTaskStatusPool[obj]
                del _ExpandThreadSurvivalTime[obj]
                self.Logger.debug(f"{obj} has been closed due to timeout.")
            _ThreadBalanceLock.release()


class _ProcessTaskScheduler(threading.Thread):
    """
    Schedules and manages the execution of tasks in a dedicated process for processing tasks from a queue.

    This class extends the `threading.Thread` class, allowing it
    to run as a background daemon thread that continuously processes tasks until instructed
    to stop. It utilizes a process task storage queue to receive tasks and a synchronization
    manager to maintain the state and load of processes. The scheduler prioritizes task allocation
    based on process availability and load conditions, ensuring efficient resource utilization.
    It logs its operations for debugging and monitoring purposes, providing insights into the
    scheduling process and any issues that may arise.

    Attributes:
        - SynchronizationManager: An instance of the _SynchronizationManager for managing synchronization.
        - ConfigManager: An instance of the _ConfigManager for accessing configuration settings.
        - ProcessTaskStorageQueue: Queue for storing tasks that need to be processed by processes.
        - Logger: Logger instance for logging scheduler activities and events.
        - LastSelectedProcess: Reference to the last selected process for task assignment.
        - CloseEvent: Event signaling when the scheduler should stop processing tasks.

    Methods:
        - __init__: Initializes the ProcessTaskScheduler with necessary managers, queues, and logger.
        - run: Continuously runs the task scheduler for processes, processing tasks from the process task storage queue until closed.
        - stop: Stops the process task scheduler by signaling the close event and waiting for the thread to finish.
        - _scheduler: Schedules a task object to an available process based on priority and load conditions.
        - _checkNotFullProcess: Checks for processes in the specified pool that are not full based on the task threshold.
        - _checkNotWorkingProcess: Checks for non-working processes in the specified process pool.
        - _checkMinimumLoadProcess: Checks and selects a process with the minimum load from a list of processes.
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
        Continuously runs the task scheduler for processes, processing tasks from the process task storage queue until closed.

        :return: None
        :exception: None

        setup:
            - 1. Enter a loop that runs until the CloseEvent is set
            - 2. Attempt to retrieve task data from the ProcessTaskStorageQueue
                a. If successful, signal that task scheduling is active
                b. If the queue is empty, sleep briefly and continue the loop
            - 3. Extract the priority and task object from the retrieved task data
            - 4. Try to acquire the process balance lock
                a. If acquired, schedule the task using the _scheduler method
                b. Release the lock after scheduling
                c. If not acquired, reinsert the task back into the queue
            - 5. Log that the ProcessTaskScheduler has been closed upon exiting the loop
        """

        while not self.CloseEvent.is_set():
            global _ProcessTaskSchedulingEvent
            try:
                task_data = self.ProcessTaskStorageQueue.get_nowait()
                _ProcessTaskSchedulingEvent.set()
            except queue.Empty:
                time.sleep(0.001)
                _ProcessTaskSchedulingEvent.clear()
                continue
            priority, task_object = task_data
            acquire = _ProcessBalanceLock.acquire(timeout=0)
            if acquire:
                self._scheduler(priority, task_object)
                _ProcessBalanceLock.release()
            else:
                self.ProcessTaskStorageQueue.put_nowait((priority, task_object))
        self.Logger.debug(f"[ProcessTaskScheduler] has been closed.")

    def stop(self):
        """
        Stops the process task scheduler by setting the close event and waiting for the thread to finish.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal the thread to stop running
            - 2. Wait for the thread to finish execution by calling join()
        """

        self.CloseEvent.set()
        self.join()

    def _scheduler(self, priority: int, task_object: _TaskObject):
        """
        Schedules a task object to an available process based on priority and load conditions.

        :param priority: The priority level of the task to be scheduled
        :param task_object: The _TaskObject representing the task to be scheduled
        :return: None
        :exception: None

        setup:
            - 1. Check for non-working core processes
            - 2. Check for non-full core processes
            - 3. If there are non-working core processes:
                a. Assign the task to the first available non-working core process
                b. Update the task status for the assigned process
            - 4. If there are no non-working processes but there are non-full core processes:
                a. Find the core process with the minimum load
                b. Assign the task to the selected core process
                c. Update the task status for the assigned process
            - 5. If there are no available core processes, check the expand process pool
                a. Check for non-working expand processes
                b. Check for non-full expand processes
                c. If there are non-working expand processes:
                    i. Assign the task to the first available non-working expand process
                    ii. Update the task status for the assigned process
                d. If there are no non-working expand processes but there are non-full expand processes:
                    i. Find the expand process with the minimum load
                    ii. Assign the task to the selected expand process
                    iii. Update the task status for the assigned process
            - 6. If no processes are available, place the task in the ProcessTaskStorageQueue for later scheduling
        """

        global _ExpandProcessPool
        not_working_core_processes = self._checkNotWorkingProcess("Core")
        not_full_core_processes = self._checkNotFullProcess("Core")

        if not_working_core_processes:
            for i in not_working_core_processes:
                i.addProcessTask(priority, task_object)
                current_status = self.SynchronizationManager.getCoreProcessTaskStatus(i.ProcessName)
                pid = current_status[0]
                task_count = current_status[1]
                new_task_count = task_count + 1
                self.SynchronizationManager.updateCoreProcessTaskStatus(i.ProcessName, pid, new_task_count)
                return
        if not_full_core_processes:
            minimum_load_core_process = self._checkMinimumLoadProcess(not_full_core_processes, "Core")
            minimum_load_core_process.addProcessTask(priority, task_object)
            current_status = self.SynchronizationManager.getCoreProcessTaskStatus(minimum_load_core_process.ProcessName)
            pid = current_status[0]
            task_count = current_status[1]
            new_task_count = task_count + 1
            self.SynchronizationManager.updateCoreProcessTaskStatus(minimum_load_core_process.ProcessName, pid, new_task_count)
            return
        if _ExpandProcessPool:
            not_working_expand_processes = self._checkNotWorkingProcess("Expand")
            not_full_expand_processes = self._checkNotFullProcess("Expand")
            if not_working_expand_processes:
                for i in not_working_expand_processes:
                    i.addProcessTask(priority, task_object)
                    current_status = self.SynchronizationManager.getExpandProcessTaskStatus(i.ProcessName)
                    pid = current_status[0]
                    task_count = current_status[1]
                    new_task_count = task_count + 1
                    self.SynchronizationManager.updateExpandProcessTaskStatus(i.ProcessName, pid, new_task_count)
                    return
            if not_full_expand_processes:
                minimum_load_expand_process = self._checkMinimumLoadProcess(not_full_expand_processes, "Expand")
                minimum_load_expand_process.addProcessTask(priority, task_object)
                current_status = self.SynchronizationManager.getExpandProcessTaskStatus(minimum_load_expand_process.ProcessName)
                pid = current_status[0]
                task_count = current_status[1]
                new_task_count = task_count + 1
                self.SynchronizationManager.updateExpandProcessTaskStatus(minimum_load_expand_process.ProcessName, pid, new_task_count)
                return
        self.ProcessTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNotFullProcess(self, process_type: Literal["Core", "Expand"]) -> list:
        """
        Checks for processes in the specified pool that are not full based on the task threshold.

        :param process_type: The type of process pool to check ("Core" or "Expand")
        :return: A list of processes that are not currently full
        :exception: None

        setup:
            - 1. Determine the appropriate process pool based on the process type
            - 2. Determine the function to check the task status based on the process type
            - 3. Filter the process pool to find processes that have a load below the defined task threshold
                a. Use the task status function to evaluate the load of each process object
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        function = self.SynchronizationManager.getCoreProcessTaskStatus if process_type == "Core" else self.SynchronizationManager.getExpandProcessTaskStatus
        not_full_processes = [obj for index, obj in obj_pool.items() if function(obj.ProcessName)[1] < self.ConfigManager.TaskThreshold.value]
        return not_full_processes

    @staticmethod
    def _checkNotWorkingProcess(process_type: Literal["Core", "Expand"]) -> list:
        """
        Checks for non-working processes in the specified process pool.

        :param process_type: The type of process pool to check ("Core" or "Expand")
        :return: A list of processes that are not currently working
        :exception: None

        setup:
            - 1. Determine the appropriate process pool based on the process type
            - 2. Filter the process pool to find processes that are not working
                a. Check the WorkingEvent attribute of each process object
        """

        global _CoreProcessPool, _ExpandProcessPool
        obj_pool = _CoreProcessPool if process_type == "Core" else _ExpandProcessPool
        not_working_processes = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_processes

    def _checkMinimumLoadProcess(self, processes: list, process_type: Literal["Core", "Expand"]) -> _ProcessObject:
        """
        Checks and selects a process with the minimum load from a list of processes.

        :param processes: A list of processes to evaluate
        :param process_type: The type of process to check ("Core" or "Expand")
        :return: The selected _ProcessObject with the minimum load
        :exception: None

        setup:
            - 1. Determine the function to get the load status based on the process type
            - 2. Filter the list of available processes, excluding the last selected process if it exists
                a. If no processes are available, select the first process in the original list
            - 3. Select the process with the minimum load using the appropriate function
            - 4. Update LastSelectedProcess to the newly selected process
        """

        function = self.SynchronizationManager.getCoreProcessLoadStatus if process_type == "Core" else self.SynchronizationManager.getExpandProcessLoadStatus
        available_processes = [p for p in processes if p != self.LastSelectedProcess] if self.LastSelectedProcess is not None else processes
        if not available_processes:
            selected_process = processes[0]
        else:
            selected_process = min(available_processes, key=lambda x: function(x.ProcessName)[1])
        self.LastSelectedProcess = selected_process
        return selected_process


class _ThreadTaskScheduler(threading.Thread):
    """
    Schedules and manages the execution of tasks in a dedicated thread for processing tasks from a queue.

    This class extends the `threading.Thread` class, allowing it
    to run as a background daemon thread that continuously processes tasks until instructed
    to stop. It utilizes a thread task storage queue to receive tasks and a synchronization
    manager to maintain the state and load of threads. The scheduler prioritizes task allocation
    based on thread availability and load conditions, ensuring efficient use of resources.
    It also logs its operations for debugging and monitoring purposes.

    Attributes:
        - SynchronizationManager: An instance of the _SynchronizationManager for managing synchronization.
        - ConfigManager: An instance of the _ConfigManager for accessing configuration settings.
        - ThreadTaskStorageQueue: Queue for storing tasks that need to be processed.
        - Logger: Logger instance for logging scheduler activities and events.
        - LastSelectedThread: Reference to the last selected thread for task assignment.
        - CloseEvent: Event signaling when the scheduler should stop processing tasks.

    Methods:
        - __init__: Initializes the ThreadTaskScheduler with necessary managers, queues, and logger.
        - run: Continuously runs the task scheduler, processing tasks from the thread task storage queue until closed.
        - stop: Stops the task scheduler by signaling the close event and waiting for the thread to finish.
        - _scheduler: Schedules a task object to an available thread based on priority and load conditions.
        - _checkNonFullThread: Checks for threads in the specified pool that are not full based on the task threshold.
        - _checkNonWorkingThread: Checks for non-working threads in the specified thread pool.
        - _checkMinimumLoadThread: Checks and selects a thread with the minimum load from a list of threads.
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
        Continuously runs the task scheduler, processing tasks from the thread task storage queue until closed.

        :return: None
        :exception: None

        setup:
            - 1. Enter a loop that runs until the CloseEvent is set
            - 2. Attempt to retrieve task data from the ThreadTaskStorageQueue
                a. If successful, signal that task scheduling is active
                b. If the queue is empty, sleep briefly and continue the loop
            - 3. Extract the priority and task object from the retrieved task data
            - 4. Try to acquire the thread balance lock
                a. If acquired, schedule the task using the _scheduler method
                b. Release the lock after scheduling
                c. If not acquired, reinsert the task back into the queue
            - 5. Log that the ThreadTaskScheduler has been closed upon exiting the loop
        """

        while not self.CloseEvent.is_set():
            global _ThreadTaskSchedulingEvent
            try:
                task_data = self.ThreadTaskStorageQueue.get_nowait()
                _ThreadTaskSchedulingEvent.set()
            except queue.Empty:
                time.sleep(0.001)
                _ThreadTaskSchedulingEvent.clear()
                continue
            priority, task_object = task_data
            acquire = _ThreadBalanceLock.acquire(timeout=0)
            if acquire:
                self._scheduler(priority, task_object)
                _ThreadBalanceLock.release()
            else:
                self.ThreadTaskStorageQueue.put_nowait((priority, task_object))
        self.Logger.debug(f"[ThreadTaskScheduler] has been closed.")

    def stop(self):
        """
        Stops the task scheduler by setting the close event and waiting for the thread to finish.

        :return: None
        :exception: None

        setup:
            - 1. Set the CloseEvent to signal the thread to stop running
            - 2. Wait for the thread to finish execution by calling join()
        """

        self.CloseEvent.set()
        self.join()

    def _scheduler(self, priority: int, task_object: _TaskObject):
        """
        Schedules a task object to an available thread based on priority and load conditions.

        :param priority: The priority level of the task to be scheduled
        :param task_object: The _TaskObject representing the task to be scheduled
        :return: None
        :exception: None

        setup:
            - 1. Check for non-working core threads
            - 2. Check for non-full core threads
            - 3. If there are non-working core threads:
                a. Assign the task to the first available non-working core thread
                b. Update the task status for the assigned thread
            - 4. If there are no non-working threads but there are non-full core threads:
                a. Find the core thread with the minimum load
                b. Assign the task to the selected core thread
                c. Update the task status for the assigned thread
            - 5. If there are no available core threads, check the expand thread pool
                a. Check for non-working expand threads
                b. Check for non-full expand threads
                c. If there are non-working expand threads:
                    i. Assign the task to the first available non-working expand thread
                    ii. Update the task status for the assigned thread
                d. If there are no non-working expand threads but there are non-full expand threads:
                    i. Find the expand thread with the minimum load
                    ii. Assign the task to the selected expand thread
                    iii. Update the task status for the assigned thread
            - 6. If no threads are available, place the task in the ThreadTaskStorageQueue for later scheduling
        """

        global _ExpandThreadPool
        not_working_core_threads = self._checkNonWorkingThread("Core")
        not_full_core_threads = self._checkNonFullThread("Core")

        if not_working_core_threads:
            for i in not_working_core_threads:
                i.addThreadTask(priority, task_object)
                current_status = self.SynchronizationManager.getCoreThreadTaskStatus(i.ThreadName)
                tid = current_status[0]
                task_count = current_status[1]
                new_task_count = task_count + 1
                self.SynchronizationManager.updateCoreThreadTaskStatus(i.ThreadName, tid, new_task_count)
                return
        if not_full_core_threads:
            minimum_load_core_process = self._checkMinimumLoadThread(not_full_core_threads, "Core")
            minimum_load_core_process.addThreadTask(priority, task_object)
            current_status = self.SynchronizationManager.getCoreThreadTaskStatus(minimum_load_core_process.ThreadName)
            tid = current_status[0]
            task_count = current_status[1]
            new_task_count = task_count + 1
            self.SynchronizationManager.updateCoreThreadTaskStatus(minimum_load_core_process.ThreadName, tid, new_task_count)
            return
        if _ExpandThreadPool:
            not_working_expand_threads = self._checkNonWorkingThread("Expand")
            not_full_expand_threads = self._checkNonFullThread("Expand")
            if not_working_expand_threads:
                for i in not_working_expand_threads:
                    i.addThreadTask(priority, task_object)
                    current_status = self.SynchronizationManager.getExpandThreadTaskStatus(i.ThreadName)
                    tid = current_status[0]
                    task_count = current_status[1]
                    new_task_count = task_count + 1
                    self.SynchronizationManager.updateExpandThreadTaskStatus(i.ThreadName, tid, new_task_count)
                    return
            if not_full_expand_threads:
                minimum_load_expand_process = self._checkMinimumLoadThread(not_full_expand_threads, "Expand")
                minimum_load_expand_process.addThreadTask(priority, task_object)
                current_status = self.SynchronizationManager.getExpandThreadTaskStatus(minimum_load_expand_process.ThreadName)
                tid = current_status[0]
                task_count = current_status[1]
                new_task_count = task_count + 1
                self.SynchronizationManager.updateExpandThreadTaskStatus(minimum_load_expand_process.ThreadName, tid, new_task_count)
                return
        self.ThreadTaskStorageQueue.put_nowait((priority, task_object))

    def _checkNonFullThread(self, thread_type: Literal["Core", "Expand"]) -> list:
        """
        Checks for threads in the specified pool that are not full based on the task threshold.

        :param thread_type: The type of thread pool to check ("Core" or "Expand")
        :return: A list of threads that are not currently full
        :exception: None

        setup:
            - 1. Determine the appropriate thread pool based on the thread type
            - 2. Determine the function to check the task status based on the thread type
            - 3. Filter the thread pool to find threads that have a load below the defined task threshold
                a. Use the task status function to evaluate the load of each thread object
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        function = self.SynchronizationManager.getCoreThreadTaskStatus if thread_type == "Core" else self.SynchronizationManager.getExpandThreadTaskStatus
        not_full_threads = [obj for index, obj in obj_pool.items() if function(obj.ThreadName)[1] < self.ConfigManager.TaskThreshold.value]
        return not_full_threads

    @staticmethod
    def _checkNonWorkingThread(thread_type: Literal["Core", "Expand"]) -> list:
        """
        Checks for non-working threads in the specified thread pool.

        :param thread_type: The type of thread pool to check ("Core" or "Expand")
        :return: A list of threads that are not currently working
        :exception: None

        setup:
            - 1. Determine the appropriate thread pool based on the thread type
            - 2. Filter the thread pool to find threads that are not working
                a. Check the WorkingEvent attribute of each thread object
        """

        global _CoreThreadPool, _ExpandThreadPool
        obj_pool = _CoreThreadPool if thread_type == "Core" else _ExpandThreadPool
        not_working_threads = [obj for index, obj in obj_pool.items() if not obj.WorkingEvent.is_set()]
        return not_working_threads

    def _checkMinimumLoadThread(self, threads: list, thread_type: Literal["Core", "Expand"]) -> _ThreadObject:
        """
        Checks and selects a thread with the minimum load from a list of threads.

        :param threads: A list of threads to evaluate
        :param thread_type: The type of thread to check ("Core" or "Expand")
        :return: The selected _ThreadObject with the minimum load
        :exception: None

        setup:
            - 1. Determine the function to get the task status based on the thread type
            - 2. Filter the list of available threads, excluding the last selected thread if it exists
                a. If no threads are available, select the first thread in the original list
            - 3. Select the thread with the minimum load using the appropriate function
            - 4. Update LastSelectedThread to the newly selected thread
        """

        function = self.SynchronizationManager.getCoreThreadTaskStatus if thread_type == "Core" else self.SynchronizationManager.getExpandThreadTaskStatus
        available_threads = [t for t in threads if t != self.LastSelectedThread] if self.LastSelectedThread is not None else threads
        if not available_threads:
            selected_thread = threads[0]
        else:
            selected_thread = min(available_threads, key=lambda x: function(x.ThreadName)[1])
        self.LastSelectedThread = selected_thread
        return selected_thread


class TaskFuture:
    """
    Represents the future result of a task execution, providing mechanisms to retrieve the result once the task is completed.

    This class is designed to work with asynchronous
    and synchronous task execution systems, allowing for flexible handling of task results.
    It encapsulates a task identifier and provides methods to fetch the result of the task
    based on that identifier. The `result` method implements a blocking call that waits for
    the task to complete and retrieves its result, with optional timeout handling to prevent
    indefinite waiting. This class also defines abstract methods for executing tasks, which
    must be implemented in subclasses for specific task behavior.

    Attributes:
        - _TaskID: An optional string representing the unique identifier for the task.

    Methods:
        - __init__: Initializes a new TaskFuture instance with an optional task ID.
        - taskID: Property to get or set the task identifier.
        - result: Retrieves the result of the task, waiting until it is available or the timeout is reached.
        - execute: Synchronous task execution method that must be implemented in a subclass.
        - asyncExecute: Asynchronous task execution method that must be implemented in a subclass.
    """

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
        Retrieves the result of the task, waiting until it is available or the timeout is reached.

        :param timeout: Optional time in seconds to wait for the task result (default is None)
        :return: The result of the task if available
        :exception TimeoutError: Raised is the task execution does not complete within the specified timeout

        setup:
            - 1. Record the start time for timeout tracking
            - 2. Enter a loop to check for the task result
                a. If the task result is found in the global _FutureResult, retrieve and delete it
                b. If timeout is specified, sleep briefly to avoid busy-waiting
                c. If the elapsed time exceeds the timeout, raise a TimeoutError
        """

        global _FutureResult
        _start_time = time.time()
        while True:
            if self._TaskID in _FutureResult:
                task_result = _FutureResult[self._TaskID]
                del _FutureResult[self._TaskID]
                return task_result
            if timeout is None:
                continue
            time.sleep(0.001)
            if time.time() - _start_time >= timeout:
                raise TimeoutError("Task execution timed out.")

    def execute(self):
        """ Synchronous task execution method. """
        raise NotImplementedError("The execute method must be implemented in a subclass.")

    async def asyncExecute(self):
        """ Asynchronous task execution method. """
        raise NotImplementedError("The asyncExecute method must be implemented in a subclass.")


class ConcurrentSystem:
    """
    TheSeedCore concurrent system main class

    Manages a concurrent system for executing tasks in both process and thread pools.
    This class is designed to handle complex task scheduling and execution across multiple
    processes and threads, ensuring efficient resource utilization and maintaining
    synchronization between various components of the system. It employs the Singleton
    design pattern to guarantee that only one instance of the system is created, which is
    crucial for consistent task management and logging. The system supports both process-based
    and thread-based task execution, allowing for flexibility in how tasks are handled depending
    on the nature of the workload and available resources. It integrates with a configuration manager
    to allow dynamic adjustment of operational parameters such as the number of processes and threads,
    as well as debugging options. The main event loop serves as the backbone of the application,
    particularly for GUI-based contexts, ensuring that all asynchronous operations are handled smoothly.

    Attributes:
        - _INSTANCE: Singleton instance of the ConcurrentSystem.
        - _INITIALIZED: Indicates if the system has been initialized.
        - MainEventLoop: The main event loop for the application.
        - _SynchronizationManager: Manager for synchronization across processes and threads.
        - _ConfigManager: Manager for system configuration settings.
        - _DebugMode: Boolean indicating if debug mode is enabled.
        - _ProcessTaskStorageQueue: Queue for storing process tasks.
        - _ThreadTaskStorageQueue: Queue for storing thread tasks.
        - _Logger: Logger instance for logging system activities.
        - _QtMode: Indicates if the system is running in Qt mode.
        - _SystemThreadPoolExecutor: Thread pool executor for managing thread execution.
        - _SystemProcessPoolExecutor: Process pool executor for managing process execution.
        - _LoadBalancer: Load balancer for distributing tasks.
        - _ProcessTaskScheduler: Scheduler for managing process tasks.
        - _ThreadTaskScheduler: Scheduler for managing thread tasks.
        - _CallbackExecutor: Executor for managing callbacks.

    Methods:
        - __new__: Creates or returns the singleton instance of the ConcurrentSystem.
        - __init__: Initializes the ConcurrentSystem, setting up various managers and executors.
        - submitProcessTask: Submits a task to be executed in the process pool.
        - submitThreadTask: Submits a task to be executed in the thread pool.
        - submitSystemProcessTask: Submits a task to be executed in the system process pool.
        - submitSystemThreadTask: Submits a task to be executed in the system thread pool.
        - closeSystem: Closes the concurrent system and stops all processes and threads.
        - _setLogger: Configures and returns a logger for the ConcurrentSystem.
        - _setCallbackExecutor: Sets the appropriate callback executor based on the application mode.
        - _initSystem: Initializes the concurrent system by starting core processes and threads.
        - _setMainProcessPriority: Sets the priority of the main process based on the configuration.
        - _startCoreProcess: Starts a core process and manages its lifecycle.
        - _startCoreThread: Starts a core thread and manages its lifecycle.
    """

    _INSTANCE: ConcurrentSystem = None
    _INITIALIZED: bool = False

    def __new__(cls, SM: _SynchronizationManager = None, CM: _ConfigManager = None, DebugMode: bool = False):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(ConcurrentSystem, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, SM: _SynchronizationManager = None, CM: _ConfigManager = None, DebugMode: bool = False):
        if ConcurrentSystem._INITIALIZED:
            return
        self._SynchronizationManager = SM
        self._ConfigManager = CM
        self._DebugMode = DebugMode
        self._ProcessTaskStorageQueue: multiprocessing.Queue = multiprocessing.Queue()
        self._ThreadTaskStorageQueue: queue.Queue = queue.Queue()
        self._Logger = self._setLogger()
        self._QtMode = False
        self._SystemThreadPoolExecutor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self._ConfigManager.CoreProcessCount.value + self._ConfigManager.CoreThreadCount.value)
        if self._ConfigManager.CoreProcessCount.value != 0:
            self._SystemProcessPoolExecutor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=self._ConfigManager.CoreProcessCount.value)
        self._LoadBalancer = _LoadBalancer(self._SynchronizationManager, self._ConfigManager, self._Logger, self._DebugMode, self._SystemThreadPoolExecutor)
        self._ProcessTaskScheduler = _ProcessTaskScheduler(self._SynchronizationManager, self._ConfigManager, self._ProcessTaskStorageQueue, self._Logger)
        self._ThreadTaskScheduler = _ThreadTaskScheduler(self._SynchronizationManager, self._ConfigManager, self._ThreadTaskStorageQueue, self._Logger)
        self._CallbackExecutor: Union[_QtCallbackExecutor, _CoreCallbackExecutor] = self._setCallbackExecutor()
        ConcurrentSystem._INITIALIZED = True
        self._initSystem()

    @classmethod
    def serviceProcessPID(cls):
        return cls._INSTANCE._SynchronizationManager.SharedObjectManagerID

    @classmethod
    def mainProcessPID(cls):
        return os.getpid()

    @classmethod
    def submitProcessTask(cls, task: callable, priority: int = 0, callback: callable = None, future: type(TaskFuture) = None, lock: bool = False, lock_timeout: int = 3, timeout: int = None, gpu_boost: bool = False, gpu_id: int = 0, retry: bool = False, max_retries: int = 3, *args, **kwargs) -> TaskFuture:
        """
        Submits a process task for execution with optional parameters and callback.

        :param task: The callable task to be executed
        :param priority: The priority of the task (default is 0, with a maximum of 10)
        :param callback: An optional callback function to be executed upon task completion
        :param future: Optional future type to use for tracking the task (default is TaskFuture)
        :param lock: Indicates whether to use a lock for task execution (default is False)
        :param lock_timeout: Timeout for the lock in seconds (default is 3)
        :param timeout: Maximum time to wait for task completion (default is None)
        :param gpu_boost: Indicates whether to enable GPU boosting (default is False)
        :param gpu_id: The ID of the GPU to use (default is 0)
        :param retry: Indicates whether to allow task retries on failure (default is False)
        :param max_retries: Maximum number of retries if the task fails (default is 3)
        :param args: Positional arguments to pass to the task
        :param kwargs: Keyword arguments to pass to the task
        :return: An instance of the future tracking the task execution
        :exception RuntimeError: Raised if the method is not called from the main process,
                                 if the ConcurrentSystem has not been initialized,
                                 or if the core process count is set to 0
        :exception pickle.PicklingError: Raised if the task cannot be serialized for process execution

        setup:
            - 1. Check if the current process is the main process
                a. Raise a RuntimeError if not
            - 2. Check if the system instance is initialized
                a. Raise a RuntimeError if the instance is None
            - 3. Check the core process count in the configuration
                a. Raise a RuntimeError if the core process count is set to 0
            - 4. Generate a unique task ID for the submitted task
            - 5. Create a future instance to track the task
                a. Use the specified future type or default to TaskFuture
            - 6. Attempt to serialize the task to ensure it can be passed to a process
                a. Log an error and reject the submission if serialization fails
            - 7. Store the callback in a global callback object if provided
            - 8. Create a task object with the provided parameters and options
            - 9. Submit the task object to the process task storage queue with its priority
        """

        global _CallbackObject, _CoreProcessPool, _ExpandProcessPool
        if multiprocessing.current_process().name != 'MainProcess':
            raise RuntimeError("Process task submission must be done in the main process.")
        if cls._INSTANCE is None:
            raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
        if cls._INSTANCE._ConfigManager.CoreProcessCount.value == 0:
            raise RuntimeError("Core process count is set to 0. Process task submission is not allowed.")
        task_id = f"{uuid.uuid4()}"
        future_instance = future() if future is not None else TaskFuture()
        future_instance.taskID = task_id
        try:
            pickle.dumps(task)
        except (pickle.PicklingError, AttributeError, TypeError) as e:
            cls._INSTANCE._Logger.error(f"Task [{task.__name__} - {task_id}] serialization failed. Task submission has been rejected.\n{e}")
            return future_instance
        if callback is not None:
            _CallbackObject[task_id] = callback
        task_object = _TaskObject(task, task_id, False if callback is None else True, lock, lock_timeout, timeout, gpu_boost, gpu_id, retry, max_retries, *args, **kwargs)
        cls._INSTANCE._ProcessTaskStorageQueue.put_nowait((priority if not priority > 10 else 10, task_object))
        return future_instance

    @classmethod
    def submitThreadTask(cls, task: callable, priority: int = 0, callback: callable = None, future: type(TaskFuture) = None, lock: bool = False, lock_timeout: int = 3, timeout: int = None, gpu_boost: bool = False, gpu_id: int = 0, retry: bool = False, max_retries: int = 3, *args, **kwargs):
        """
        Submits a thread task for execution with optional parameters and callback.

        :param task: The callable task to be executed
        :param priority: The priority of the task (default is 0, with a maximum of 10)
        :param callback: An optional callback function to be executed upon task completion
        :param future: Optional future type to use for tracking the task (default is TaskFuture)
        :param lock: Indicates whether to use a lock for task execution (default is False)
        :param lock_timeout: Timeout for the lock in seconds (default is 3)
        :param timeout: Maximum time to wait for task completion (default is None)
        :param gpu_boost: Indicates whether to enable GPU boosting (default is False)
        :param gpu_id: The ID of the GPU to use (default is 0)
        :param retry: Indicates whether to allow task retries on failure (default is False)
        :param max_retries: Maximum number of retries if the task fails (default is 3)
        :param args: Positional arguments to pass to the task
        :param kwargs: Keyword arguments to pass to the task
        :return: An instance of the future tracking the task execution
        :exception RuntimeError: Raised if the method is not called from the main process or if the system has not been initialized

        setup:
            - 1. Check if the current process is the main process
                a. Raise a RuntimeError if not
            - 2. Check if the system instance is initialized
                a. Raise a RuntimeError if the instance is None
            - 3. Generate a unique task ID for the submitted task
            - 4. Create a future instance to track the task
                a. Use the specified future type or default to TaskFuture
            - 5. Store the callback in a global callback object if provided
            - 6. Create a task object with the provided parameters and options
            - 7. Submit the task object to the thread task storage queue with its priority
        """

        global _CallbackObject
        if multiprocessing.current_process().name != 'MainProcess':
            raise RuntimeError("Thread task submission must be done in the main process.")
        if cls._INSTANCE is None:
            raise RuntimeError("TheSeedCore ConcurrentSystem has not been initialized.")
        task_id = f"{uuid.uuid4()}"
        future_instance = future() if future is not None else TaskFuture()
        future_instance.taskID = task_id
        if callback is not None:
            _CallbackObject[task_id] = callback
        task_object = _TaskObject(task, task_id, False if callback is None else True, lock, lock_timeout, timeout, gpu_boost, gpu_id, retry, max_retries, *args, **kwargs)
        cls._INSTANCE._ThreadTaskStorageQueue.put_nowait((priority if not priority > 10 else 5, task_object))
        return future_instance

    @classmethod
    def submitSystemProcessTask(cls, task: callable, count: int = 1, *args, **kwargs):
        """
        Submits a task to be executed in the system process pool.

        :param task: The callable task to be executed
        :param count: The number of times to submit the task (default is 1)
        :param args: Positional arguments to pass to the task
        :param kwargs: Keyword arguments to pass to the task
        :return: A future object or a list of future objects representing the submitted tasks
        :exception RuntimeError: Raised if the ConcurrentSystem has not been initialized,
                                 if the core process count is set to 0, or if the system instance is not initialized
        :exception ValueError: Raised if the provided task is not callable

        setup:
            - 1. Check if the system instance is initialized
                a. Raise a RuntimeError if the instance is None
            - 2. Validate that the task is a callable
                a. Raise a ValueError if the task is not callable
            - 3. Check the core process count in the configuration
                a. Raise a RuntimeError if the core process count is set to 0
            - 4. Submit the task to the system process pool executor
                a. If count is greater than 1, submit the task multiple times and collect futures in a list
                b. If count is 1, submit the task once and return the single future
        """

        if cls._INSTANCE is None:
            raise RuntimeError("The ConcurrentSystem has not been initialized.")
        if not callable(task):
            raise ValueError("The task must be a callable.")
        if cls._INSTANCE._ConfigManager.CoreProcessCount.value == 0:
            raise RuntimeError("Core process count is set to 0. Process task submission is not allowed.")
        futures = []
        if count > 1:
            for i in range(count):
                future = cls._INSTANCE._SystemProcessPoolExecutor.submit(task, *args, **kwargs)
                futures.append(future)
            return futures
        future = cls._INSTANCE._SystemProcessPoolExecutor.submit(task, *args, **kwargs)
        return future

    @classmethod
    def submitSystemThreadTask(cls, task: callable, count: int = 1, *args, **kwargs):
        """
        Submits a task to be executed in the system thread pool.

        :param task: The callable task to be executed
        :param count: The number of times to submit the task (default is 1)
        :param args: Positional arguments to pass to the task
        :param kwargs: Keyword arguments to pass to the task
        :return: A future object or a list of future objects representing the submitted tasks
        :exception RuntimeError: Raised if the ConcurrentSystem has not been initialized
        :exception ValueError: Raised if the provided task is not callable

        setup:
            - 1. Check if the system instance is initialized
                a. Raise a RuntimeError if the instance is None
            - 2. Validate that the task is a callable
                a. Raise a ValueError if the task is not callable
            - 3. Submit the task to the system thread pool executor
                a. If count is greater than 1, submit the task multiple times and collect futures in a list
                b. If count is 1, submit the task once and return the single future
        """

        if cls._INSTANCE is None:
            raise RuntimeError("The ConcurrentSystem has not been initialized.")
        if not callable(task):
            raise ValueError("The task must be a callable.")
        futures = []
        if count > 1:
            for i in range(count):
                future = cls._INSTANCE._SystemThreadPoolExecutor.submit(task, *args, **kwargs)
                futures.append(future)
            return futures
        future = cls._INSTANCE._SystemThreadPoolExecutor.submit(task, *args, **kwargs)
        return future

    @classmethod
    def closeSystem(cls):
        """
        Closes the concurrent system, stopping all processes and threads.

        :return: None
        :exception RuntimeError: Raised if the method is not called from the main process or if the system has not been initialized

        setup:
            - 1. Check if the current process is the main process
                a. Raise a RuntimeError if not
            - 2. Check if the system instance is initialized
                a. Raise a RuntimeError if the instance is None
            - 3. Stop all core processes and threads
                a. Submit the stop method of each process and thread to the system thread pool executor
            - 4. Stop all expanded processes and threads
                a. Submit the stop method of each expanded process and thread to the system thread pool executor
            - 5. Wait for all submitted stop tasks to complete
            - 6. Stop the load balancer and task schedulers
                a. Stop the ProcessTaskScheduler if core processes exist
                b. Stop the ThreadTaskScheduler
            - 7. Close the callback executor and shut down the system thread pool executor
                a. Shut down the SystemProcessPoolExecutor if core processes exist
            - 8. Stop the main event loop if not in Qt mode
            - 9. Delete the system instance
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
        if cls._INSTANCE._ConfigManager.CoreProcessCount.value != 0:
            cls._INSTANCE._ProcessTaskScheduler.stop()
        cls._INSTANCE._ThreadTaskScheduler.stop()
        cls._INSTANCE._CallbackExecutor.closeExecutor()
        cls._INSTANCE._SystemThreadPoolExecutor.shutdown(wait=True, cancel_futures=True)
        if cls._INSTANCE._ConfigManager.CoreProcessCount.value != 0:
            cls._INSTANCE._SystemProcessPoolExecutor.shutdown(wait=True, cancel_futures=True)
        del cls._INSTANCE

    def _setLogger(self) -> logging.Logger:
        """
        Sets up and returns a logger for the ConcurrentSystem.

        :return: An instance of logging.Logger configured for the ConcurrentSystem
        :exception: None

        setup:
            - 1. Create a logger for the ConcurrentSystem
                a. Set the logging level to DEBUG
            - 2. Create a console handler for logging output
                a. Set the handler's logging level based on the DebugMode
            - 3. Configure the formatter for the console handler
                a. Use _ColoredFormatter for formatted log messages
            - 4. Add the console handler to the logger
        """

        logger = logging.getLogger('ConcurrentSystem')
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
        Sets the appropriate callback executor based on the application mode.

        :return: An instance of either _QtCallbackExecutor or _CoreCallbackExecutor
        :exception: None

        setup:
            - 1. Check if the application is running in Qt mode
                a. If QApplication exists and has an active instance, set _QtMode to True
                b. Return an instance of _QtCallbackExecutor
            - 2. If not in Qt mode, set _QtMode to False
                a. Return an instance of _CoreCallbackExecutor
        """

        # noinspection PyUnresolvedReferences
        if QApplication and QApplication.instance():
            self._QtMode = True
            return _QtCallbackExecutor(self._SynchronizationManager)
        self._QtMode = False
        return _CoreCallbackExecutor(self._SynchronizationManager)

    def _initSystem(self):
        """
        Initializes the concurrent system by setting process priorities and starting core processes and threads.

        :return: None
        :exception: None

        setup:
            - 1. Set the priority of the main process
            - 2. Start core processes based on the configured process count
                a. Submits the _startCoreProcess method to the system thread pool for each core process
            - 3. Start core threads based on the configured thread count
                a. Submits the _startCoreThread method to the system thread pool for each core thread
            - 4. Wait for all submitted tasks to complete
            - 5. Start the load balancer and task schedulers
                a. Starts the ProcessTaskScheduler if there are core processes
                b. Starts the ThreadTaskScheduler and CallbackExecutor
        """

        global _CoreProcessPool, _CoreThreadPool
        self._setMainProcessPriority()
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
        if self._ConfigManager.CoreProcessCount.value != 0:
            self._ProcessTaskScheduler.start()
        self._ThreadTaskScheduler.start()
        self._CallbackExecutor.startExecutor()

    def _setMainProcessPriority(self):
        """
        Sets the priority of the main process based on the configuration.

        :return: None
        :exception ValueError: Raised if a valid handle cannot be obtained
        :exception Exception: Raised if setting the priority fails

        setup:
            - 1. Define a mapping of priority levels to their corresponding values
            - 2. Attempt to open the current process using its process ID
                a. If handle retrieval fails, raise a ValueError
            - 3. Set the priority class of the process
                a. If setting the priority fails, log the error with the corresponding error code
            - 4. Ensure the process handle is closed in the finally block to avoid resource leaks
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
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, os.getpid())
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
            result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping.get(self._ConfigManager.ProcessPriority, priority_mapping["NORMAL"]))
            if result == 0:
                error_code = ctypes.windll.kernel32.GetLastError()
                raise Exception(f"Set priority failed with error code {error_code}.")
        except Exception as e:
            self._Logger.error(f"[MainProcess - {os.getpid()}] set priority failed due to {str(e)}")
        finally:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)

    def _startCoreProcess(self, process_name):
        """
        Starts a core process and manages its lifecycle.

        :param process_name: The name of the process to be started
        :return: An instance of _ProcessObject representing the started core process
        :exception: None

        setup:
            - 1. Create a process object for the core process
                a. Initializes _ProcessObject with the provided process name and associated managers
            - 2. Start the process object
                a. Invokes the start method on the process object
            - 3. Update the core process pool and load/task status
                a. Adds the process object to the global core process pool
                b. Updates the load status and task status for the process in the synchronization manager
        """

        global _CoreProcessPool
        process_object: _ProcessObject = _ProcessObject(process_name, "Core", self._SynchronizationManager, self._ConfigManager, self._DebugMode)
        process_object.start()
        _CoreProcessPool[process_name] = process_object
        self._SynchronizationManager.updateCoreProcessLoadStatus(process_name, process_object.pid, 0)
        self._SynchronizationManager.updateCoreProcessTaskStatus(process_name, process_object.pid, 0)
        return process_object

    def _startCoreThread(self, thread_name):
        """
        Starts a core thread and manages its lifecycle.

        :param thread_name: The name of the thread to be started
        :return: An instance of _ThreadObject representing the started core thread
        :exception: None

        setup:
            - 1. Create a thread object for the core thread
                a. Initializes _ThreadObject with the provided thread name and associated managers
            - 2. Start the thread object
                a. Invokes the start method on the thread object
            - 3. Update the core thread pool and task status
                a. Adds the thread object to the global core thread pool
                b. Initializes the task status for the thread in the synchronization manager
        """

        global _CoreThreadPool
        thread_object = _ThreadObject(thread_name, "Core", self._SynchronizationManager, self._ConfigManager, self._Logger, self._SystemThreadPoolExecutor)
        thread_object.start()
        _CoreThreadPool[thread_name] = thread_object
        self._SynchronizationManager.updateCoreThreadTaskStatus(thread_name, thread_object.ident, 0)
        return thread_object


def ConnectConcurrentSystem(**kwargs) -> ConcurrentSystem:
    """
    Connects to a concurrent system and initializes the event loop and configuration.

    :param kwargs: Key-value arguments for configuration settings
        - DebugMode: Boolean indicating whether to enable debug mode (default is development environment status)
        - Priority: The priority level for the system (default is "NORMAL")
        - CoreProcessCount: Number of core processes (default is None)
        - CoreThreadCount: Number of core threads (default is None)
        - MaximumProcessCount: Maximum allowed process count (default is None)
        - MaximumThreadCount: Maximum allowed thread count (default is None)
        - IdleCleanupThreshold: Threshold for idle cleanup (default is None)
        - ProcessPriority: Priority level for individual processes (default is "NORMAL")
        - TaskThreshold: Threshold for task management (default is None)
        - GlobalTaskThreshold: Global threshold for task management (default is None)
        - ExpandPolicy: Policy for expanding resources (default is None)
        - ShrinkagePolicy: Policy for shrinking resources (default is None)
        - ShrinkagePolicyTimeout: Timeout for shrinkage policy (default is None)
    :return: An instance of ConcurrentSystem
    :exception TypeError: Raised if DebugMode is not a boolean

    setup:
        - 1. Initialize the main event loop based on the application state
            a. If QApplication exists, use its event loop; otherwise, use asyncio event loop
        - 2. Create configuration and managers
            a. Initialize _Config, _SynchronizationManager, and _ConfigManager
        - 3. Instantiate the ConcurrentSystem with the created managers and configuration
    """

    _development_env = not hasattr(sys, "frozen") and not globals().get("__compiled__", False)
    _debug_mode = kwargs.get('DebugMode', _development_env)
    if not isinstance(_debug_mode, bool):
        raise TypeError("DebugMode must be a boolean.")
    # noinspection PyTypeChecker
    _config = _Config(
        Priority=kwargs.get('Priority', "NORMAL"),
        CoreProcessCount=kwargs.get('CoreProcessCount', None),
        CoreThreadCount=kwargs.get('CoreThreadCount', None),
        MaximumProcessCount=kwargs.get('MaximumProcessCount', None),
        MaximumThreadCount=kwargs.get('MaximumThreadCount', None),
        IdleCleanupThreshold=kwargs.get('IdleCleanupThreshold', None),
        ProcessPriority=kwargs.get('ProcessPriority', "NORMAL"),
        TaskThreshold=kwargs.get('TaskThreshold', None),
        GlobalTaskThreshold=kwargs.get('GlobalTaskThreshold', None),
        ExpandPolicy=kwargs.get('ExpandPolicy', None),
        ShrinkagePolicy=kwargs.get('ShrinkagePolicy', None),
        ShrinkagePolicyTimeout=kwargs.get('ShrinkagePolicyTimeout', None),
    )
    _shared_object_manager = multiprocessing.Manager()
    _synchronization_manager = _SynchronizationManager(_shared_object_manager)
    _config_manager = _ConfigManager(_shared_object_manager, _config)
    _concurrent_system = ConcurrentSystem(_synchronization_manager, _config_manager, _debug_mode)
    # noinspection PyProtectedMember
    return _concurrent_system
