# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "TextColor",
    "PerformanceMonitor",
]

import ctypes
import importlib.util
import os
import platform
import subprocess
import sys
import time
from ctypes import wintypes
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Union, List, Dict, Optional

if TYPE_CHECKING:
    pass


class TextColor(Enum):
    RESET: str = "\033[0m"

    RED: str = "\033[31m"
    GREEN: str = "\033[32m"
    YELLOW: str = "\033[33m"
    BLUE: str = "\033[34m"
    PURPLE: str = "\033[35m"
    CYAN: str = "\033[36m"
    WHITE: str = "\033[37m"

    RED_BOLD: str = "\033[1m\033[31m"
    GREEN_BOLD: str = "\033[1m\033[32m"
    YELLOW_BOLD: str = "\033[1m\033[33m"
    BLUE_BOLD: str = "\033[1m\033[34m"
    PURPLE_BOLD: str = "\033[1m\033[35m"
    CYAN_BOLD: str = "\033[1m\033[36m"
    WHITE_BOLD: str = "\033[1m\033[37m"

    def apply(self, text: str) -> str:
        return f"{self.value}{text}{TextColor.RESET.value}"


class _LinuxMonitor:
    _INSTANCE: Optional[_LinuxMonitor] = None
    _INITIALIZED: bool = False

    def __new__(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE: _LinuxMonitor = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        self._stat_path: str = "/proc/stat"
        self._cpu_info_path: str = "/proc/cpuinfo"
        self._mem_info_path: str = "/proc/meminfo"

    @classmethod
    def physicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
        with open(cls._INSTANCE._cpu_info_path, 'r') as f:
            cpuinfo = f.read().splitlines()
            return sum(1 for line in cpuinfo if line.startswith('physical id'))

    @classmethod
    def logicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
        return os.cpu_count()

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
        with open(cls._INSTANCE._mem_info_path, 'r') as f:
            for line in f:
                if line.startswith('MemTotal'):
                    return int(line.split()[1]) * 1024

    @classmethod
    def totalVirtualMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
        with open(cls._INSTANCE._mem_info_path, 'r') as f:
            swap_total: int = 0
            for line in f:
                if line.startswith('SwapTotal'):
                    swap_total = int(line.split()[1]) * 1024
            return swap_total

    @classmethod
    def totalCpuUsage(cls, interval: Optional[float] = 1.0) -> float:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
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
    def processCpuUsage(cls, pid: Optional[int], interval: Optional[float] = 1.0) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")

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
        if not cls._INSTANCE:
            raise RuntimeError("LinuxResourceMonitor is not initialized.")
        with open(f'/proc/{pid}/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS'):
                    return int(line.split()[1]) * 1024


class _WindowsMonitor:
    _INSTANCE: Optional[_WindowsMonitor] = None
    _INITIALIZED: Optional[bool] = False
    _ULONG_PTR: Optional[str] = ctypes.c_ulonglong if platform.architecture()[0] == '64bit' else ctypes.c_ulong

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

    class ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    ProcessorRelationship._fields_ = _fields_ = [
        ("Flags", ctypes.c_byte),
        ("EfficiencyClass", ctypes.c_byte),
        ("Reserved", ctypes.c_byte * 20),  # type: ignore
        ("GroupCount", wintypes.WORD),
        ("GroupMask", ctypes.POINTER(ctypes.c_ulonglong))
    ]

    SystemLogicalProcessorInformationEx._fields_ = [
        ("Relationship", wintypes.DWORD),
        ("Size", wintypes.DWORD),
        ("Processor", ProcessorRelationship)
    ]

    def __new__(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        self.Kernel32 = ctypes.WinDLL('kernel32')
        self._INITIALIZED = True

    @classmethod
    def physicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        buffer_size = wintypes.DWORD(0)
        ctypes.windll.kernel32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(buffer_size))
        buffer = (ctypes.c_byte * buffer_size.value)()
        result = ctypes.windll.kernel32.GetLogicalProcessorInformationEx(0, ctypes.byref(buffer), ctypes.byref(buffer_size))
        if not result:
            raise OSError("GetLogicalProcessorInformationEx failed")

        num_physical_cores = 0
        offset = 0
        while offset < buffer_size.value:
            info = ctypes.cast(ctypes.byref(buffer, offset), ctypes.POINTER(cls.SystemLogicalProcessorInformationEx)).contents
            if info.Relationship == 0:  # Processor Core
                num_physical_cores += info.Processor.GroupCount
            offset += info.Size
        return num_physical_cores

    @classmethod
    def logicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        return ctypes.windll.kernel32.GetActiveProcessorCount(0)

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        memory_status = cls._INSTANCE.MemoryStatusEx()
        memory_status.dwLength = ctypes.sizeof(cls._INSTANCE.MemoryStatusEx)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        return memory_status.ullTotalPhys / 1024

    @classmethod
    def totalVirtualMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        memory_status = cls._INSTANCE.MemoryStatusEx()
        memory_status.dwLength = ctypes.sizeof(cls._INSTANCE.MemoryStatusEx)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
        return memory_status.ullTotalPageFile / 1024

    @classmethod
    def processCpuUsage(cls, pid: Optional[int], interval: Optional[float] = 0.001) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not handle:
            raise OSError(f"Failed to open process {pid}")

        kernel_time_start, user_time_start = cls.FileTime(), cls.FileTime()
        kernel_time_end, user_time_end = cls.FileTime(), cls.FileTime()
        result = ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(cls.FileTime()), ctypes.byref(cls.FileTime()),
            ctypes.byref(kernel_time_start), ctypes.byref(user_time_start)
        )
        if not result:
            ctypes.windll.kernel32.CloseHandle(handle)
            error_code = ctypes.windll.kernel32.GetLastError()
            raise OSError(f"Failed to get process times at end. Error code: {error_code}")
        time.sleep(interval)
        result = ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(cls.FileTime()), ctypes.byref(cls.FileTime()),
            ctypes.byref(kernel_time_end), ctypes.byref(user_time_end)
        )
        if not result:
            ctypes.windll.kernel32.CloseHandle(handle)
            error_code = ctypes.windll.kernel32.GetLastError()
            raise OSError(f"Failed to get process times at end. Error code: {error_code}")

        process_kernel_elapsed = ((kernel_time_end.dwLowDateTime + (kernel_time_end.dwHighDateTime << 32)) -
                                  (kernel_time_start.dwLowDateTime + (kernel_time_start.dwHighDateTime << 32))) / 10 ** 7
        process_user_elapsed = ((user_time_end.dwLowDateTime + (user_time_end.dwHighDateTime << 32)) -
                                (user_time_start.dwLowDateTime + (user_time_start.dwHighDateTime << 32))) / 10 ** 7
        process_total_elapsed = process_kernel_elapsed + process_user_elapsed
        num_cores = cls.logicalCpuCores()

        ctypes.windll.kernel32.CloseHandle(handle)
        cpu_usage_percentage = (process_total_elapsed / (interval * num_cores)) * 100
        return max(0, min(int(cpu_usage_percentage), 100))

    @classmethod
    def processMemoryUsage(cls, pid: Optional[int]) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("WindowsResourceMonitor is not initialized.")
        process_handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
        if not process_handle:
            raise OSError(f"Unable to open process {pid}")

        counters = cls._INSTANCE.ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(cls._INSTANCE.ProcessMemoryCountersEx)
        ctypes.windll.psapi.GetProcessMemoryInfo(process_handle, ctypes.byref(counters), counters.cb)
        ctypes.windll.kernel32.CloseHandle(process_handle)
        return int(counters.WorkingSetSize / (1024 * 1024))


class _MacOSMonitor:
    _INSTANCE: Optional[_MacOSMonitor] = None
    _INITIALIZED: Optional[bool] = False

    def __new__(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        ...

    @classmethod
    def physicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.physicalcpu']).decode())

    @classmethod
    def logicalCpuCores(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.logicalcpu']).decode())

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        return int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode())

    @classmethod
    def totalVirtualMemory(cls) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        vm_stat_output = subprocess.check_output(['vm_stat']).decode()
        for line in vm_stat_output.splitlines():
            if 'Pages swapped out' in line:
                swap_out_pages = int(line.split()[3].replace('.', ''))
                return swap_out_pages * 4096

    @classmethod
    def totalCpuUsage(cls, interval: Optional[float] = 1.0) -> float:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        top_output = subprocess.check_output(['top', '-l', f"{str(int(interval))}"]).decode()
        for line in top_output.splitlines():
            if 'CPU usage' in line:
                cpu_usage = float(line.split()[2].replace('%', ''))
                return cpu_usage

    @classmethod
    def processCpuUsage(cls, pid: Optional[int], interval: Optional[float] = 1) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        num_cores = int(subprocess.check_output(['sysctl', '-n', 'hw.logicalcpu']).decode().strip())
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu']).decode()
        cpu_usage_start = float(ps_output.splitlines()[1].strip())
        time.sleep(interval)
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu']).decode()
        cpu_usage_end = float(ps_output.splitlines()[1].strip())
        cpu_usage = (cpu_usage_end - cpu_usage_start) / interval / num_cores
        return max(0, min(int(cpu_usage), 100))

    @classmethod
    def processMemoryUsage(cls, pid: Optional[int]) -> int:
        if not cls._INSTANCE:
            raise RuntimeError("MacOSResourceMonitor is not initialized.")
        ps_output = subprocess.check_output(['ps', '-p', str(pid), '-o', 'rss']).decode()
        memory_usage = int(ps_output.splitlines()[1].strip())
        return memory_usage * 1024


class PerformanceMonitor:
    """
    PerformanceMonitor is a singleton class that provides methods for monitoring system resources such as CPU and memory.

    The class is a singleton designed to monitor system resources, providing methods to retrieve information about CPU
    and memory usage at both system-wide and per-process levels.
    It is used to help optimize application performance by tracking resource usage and detecting potential bottlenecks.

    ClassAttributes:
        _INSTANCE: The singleton instance of the PerformanceMonitor class.
        _INITIALIZED: A flag to indicate whether the instance has been initialized.

    Methods:
        physicalCpuCores: Returns the number of physical CPU cores.
        logicalCpuCores: Returns the number of logical CPU cores.
        totalPhysicalMemory: Returns the total physical memory available in the system.
        totalVirtualMemory: Returns the total virtual memory available in the system.
        totalCpuUsage: Returns the total CPU usage over a specified interval.
        processCpuUsage: Returns the CPU usage for a specified process ID over a given interval.
        processMemoryUsage: Returns the memory usage for a specified process ID.
    """

    _INSTANCE: PerformanceMonitor = None
    _INITIALIZED: bool = False

    def __new__(cls, system_type: str):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self, system_type: str):
        if PerformanceMonitor._INITIALIZED:
            return
        self._BaseMonitor = _selectResourceMonitor(system_type)
        PerformanceMonitor._INITIALIZED = True

    @classmethod
    def physicalCpuCores(cls) -> int:
        """
        Retrieves the number of physical CPU cores available in the system.

        This class method accesses the appropriate method in the base monitor instance
        to return the count of physical CPU cores, excluding any hyper-threaded cores.

        :return: The number of physical CPU cores.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `physicalCpuCores` method of the base monitor instance.
        """

        return cls._INSTANCE._BaseMonitor.physicalCpuCores()

    @classmethod
    def logicalCpuCores(cls) -> int:
        """
        Retrieves the number of logical CPU cores available in the system.

        This class method accesses the appropriate method in the base monitor instance
        to return the count of logical CPU cores, which includes both physical cores and
        any hyper-threaded cores.

        :return: The number of logical CPU cores.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `logicalCpuCores` method of the base monitor instance.
        """

        return cls._INSTANCE._BaseMonitor.logicalCpuCores()

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        """
        Retrieves the total physical memory of the system.

        This class method returns the total amount of physical memory (RAM) available
        in the system by accessing the appropriate method in the base monitor instance.

        :return: The total physical memory in bytes.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `totalPhysicalMemory` method of the base monitor instance.
        """

        return cls._INSTANCE._BaseMonitor.totalPhysicalMemory()

    @classmethod
    def totalVirtualMemory(cls) -> int:
        """
        Retrieves the total virtual memory of the system.

        This class method returns the total amount of virtual memory available
        in the system by accessing the appropriate method in the base monitor instance.

        :return: The total virtual memory in bytes.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `totalVirtualMemory` method of the base monitor instance.
        """

        return cls._INSTANCE._BaseMonitor.totalVirtualMemory()

    @classmethod
    def totalCpuUsage(cls, interval: Optional[float] = 1.0) -> float:
        """
        Retrieves the total CPU usage across all processes.

        This class method calculates the total CPU usage of the system over
        a specified interval. It uses the base monitor instance to access
        the required functionality for measuring the total CPU usage.

        :param interval: The time interval in seconds over which to measure the CPU usage.
                         Defaults to 1.0 second if not specified.
        :return: The total CPU usage as a percentage.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `totalCpuUsage` method of the base monitor instance with the specified interval.
        """

        return cls._INSTANCE._BaseMonitor.totalCpuUsage(interval)

    @classmethod
    def processCpuUsage(cls, pid: Optional[int], interval: Optional[float] = 1.0) -> int:
        """
        Retrieves the CPU usage of a specified process.

        This class method accesses the CPU usage information of a process
        identified by its process ID (pid) over a specified interval. The
        method delegates the call to the corresponding method in the base
        monitor instance.

        :param pid: The process ID of the target process whose CPU usage is to be retrieved.
        :param interval: The time interval in seconds over which to measure the CPU usage.
                         Defaults to 1.0 second if not specified.
        :return: The CPU usage of the specified process as a percentage.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `processCpuUsage` method of the base monitor instance with the given pid and interval.
        """

        return cls._INSTANCE._BaseMonitor.processCpuUsage(pid, interval)

    @classmethod
    def processMemoryUsage(cls, pid: int) -> int:
        """
        Retrieves the memory usage of a specified process.

        This class method accesses the memory usage information of a process
        identified by its process ID (pid) by invoking the corresponding method
        from the base monitor instance.

        :param pid: The process ID of the target process whose memory usage is to be retrieved.
        :return: The memory usage of the specified process in bytes.

        setup:
            1. Ensure that the class has a valid instance of the base monitor.
            2. Call the `processMemoryUsage` method of the base monitor instance with the given pid.
        """

        return cls._INSTANCE._BaseMonitor.processMemoryUsage(pid)


def _checkPackage(package_name: str) -> bool:
    """
    Checks if a specified package is installed in the current environment.

    This function uses the `importlib.util.find_spec` method to determine
    if the given package can be found. It returns True if the package is
    installed and False otherwise.

    :param package_name: The name of the package to check for installation.
    :return: True if the package is installed, False if it is not.

    setup:
        1. Attempt to find the package using `importlib.util.find_spec`.
        2. Return True if the package is found; otherwise, return False.
    """

    if importlib.util.find_spec(package_name) is not None:
        return True
    return False


def _checkPackageVersion(package_name: str) -> Optional[str]:
    """
    Checks the installed version of the specified package.

    This function attempts to retrieve the version of a given package using
    the `importlib.metadata` module. If the package is found, it returns
    the version string. If the package is not installed, it returns None.

    :param package_name: The name of the package whose version is to be checked.
    :return: The version of the package as a string, or None if the package is not found.

    setup:
        1. Try to retrieve the package version:
            1.1. If the package is found, return its version.
            1.2. If the package is not found, return None.
    """

    try:
        package_version = version(package_name)
        return package_version
    except PackageNotFoundError:
        return None


def _createPath(path: str) -> None:
    """
    Creates the specified directory path if it does not already exist.

    This function checks if the provided path exists. If the path does not exist,
    it creates the entire directory tree specified by the path. This is useful
    for ensuring that directories exist before attempting to write files to them.

    :param path: The directory path to be created.
    :return: None

    setup:
        1. Check if the specified path exists:
            1.1. If it does not exist, create the directory (and any necessary parent directories).
    """

    if not os.path.exists(path):
        os.makedirs(path)


def _addSystemPath(path: str) -> None:
    """
    Adds the specified path to the system path if it is not already present.

    This function checks if the provided path exists in the system's module search path
    (sys.path). If the path is not already included, it appends the path to sys.path,
    allowing for modules located in that directory to be imported.

    :param path: The path to be added to the system path.
    :return: None

    setup:
        1. Check if the provided path is not already in sys.path:
            1.1. If not, append the path to sys.path.
    """

    if path not in sys.path:
        sys.path.append(path)


def _checkPath(*paths: Union[str, list, tuple, dict]) -> Union[str, List[str], Dict[str, str]]:
    """
    Checks the validity of the provided paths and processes them by creating necessary directories
    and adding them to the system path.

    This function can accept a single path as a string, multiple paths as a list or tuple, or
    a dictionary of paths. For each path provided, it will ensure that the directory exists
    (creating it if necessary) and add the path to the system path.

    :param paths: A single path as a string, multiple paths as a list or tuple, or a dictionary
                  where keys are identifiers and values are paths to be processed.
    :return: The processed path if a single string is provided, a list of processed paths if
             a list or tuple is provided, or a dictionary of processed paths if a dictionary is provided.

    :raise TypeError: Raises a TypeError if the provided parameters are not strings, lists/tuples, or dictionaries.

    setup:
        1. Define a helper function process_single_path to handle individual paths:
            1.1. Call _createPath to create the directory if it does not exist.
            1.2. Call _addSystemPath to add the path to the system path.
            1.3. Return the processed path.
        2. Check the type of paths:
            2.1. If paths is a string, process it using process_single_path and return the result.
            2.2. If paths is a list or tuple, process each path using process_single_path and return a list of results.
            2.3. If paths is a dictionary, process each value using process_single_path and return a dictionary of results.
        3. If paths is none of the above types, raise a TypeError.
    """

    def process_single_path(p: str) -> str:
        _createPath(p)
        _addSystemPath(p)
        return p

    if isinstance(paths, str):
        return process_single_path(paths)
    if isinstance(paths, (list, tuple)):
        return [process_single_path(p) for p in paths]
    if isinstance(paths, dict):
        return {k: process_single_path(v) for k, v in paths.items()}
    raise TypeError("Parameters must be strings, lists/tuples, or dictionaries")


def _selectResourceMonitor(system_type) -> Union[_LinuxMonitor, _WindowsMonitor, _MacOSMonitor]:
    """
    Selects the appropriate resource monitor class based on the provided system type.

    This function instantiates and returns a resource monitor object corresponding to the operating system.
    It supports Linux, Windows, and macOS (Darwin) systems. If the provided system type is unsupported,
    it raises an OSError.

    :param system_type: A string representing the type of operating system ("Linux", "Windows", or "Darwin").
    :return: An instance of the corresponding resource monitor class for the specified operating system.

    :raise OSError: If the provided system type is not supported, an OSError is raised indicating that the current system is not supported.

    setup:
        1. Check the value of the system_type parameter.
        2. If system_type is "Linux", instantiate and return _LinuxMonitor.
        3. If system_type is "Windows", instantiate and return _WindowsMonitor.
        4. If system_type is "Darwin", instantiate and return _MacOSMonitor.
        5. If system_type is any other value, raise an OSError indicating unsupported system type.
    """

    if system_type == "Linux":
        return _LinuxMonitor()
    elif system_type == "Windows":
        return _WindowsMonitor()
    elif system_type == "Darwin":
        return _MacOSMonitor()
    else:
        raise OSError("The current system is not supported.")
