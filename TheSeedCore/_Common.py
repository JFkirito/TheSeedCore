# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import importlib.util
import os
import platform
import subprocess
import time
from ctypes import wintypes
from enum import Enum
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    pass

SYSTEM_TYPE: str = platform.system()


def _checkPackage(package_name: str) -> bool:
    if importlib.util.find_spec(package_name) is not None:
        return True
    return False


def _selectResourceMonitor() -> Union[_LinuxMonitor, _WindowsMonitor, _MacOSMonitor]:
    if SYSTEM_TYPE == "Linux":
        return _LinuxMonitor()
    elif SYSTEM_TYPE == "Windows":
        return _WindowsMonitor()
    elif SYSTEM_TYPE == "Darwin":
        return _MacOSMonitor()
    else:
        raise OSError("The current system is not supported.")


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
    _INSTANCE: PerformanceMonitor = None
    _INITIALIZED: bool = False

    def __new__(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    def __init__(self):
        if PerformanceMonitor._INITIALIZED:
            return
        self._BaseMonitor = _selectResourceMonitor()
        PerformanceMonitor._INITIALIZED = True

    @classmethod
    def physicalCpuCores(cls) -> int:
        return cls._INSTANCE._BaseMonitor.physicalCpuCores()

    @classmethod
    def logicalCpuCores(cls) -> int:
        return cls._INSTANCE._BaseMonitor.logicalCpuCores()

    @classmethod
    def totalPhysicalMemory(cls) -> int:
        return cls._INSTANCE._BaseMonitor.totalPhysicalMemory()

    @classmethod
    def totalVirtualMemory(cls) -> int:
        return cls._INSTANCE._BaseMonitor.totalVirtualMemory()

    @classmethod
    def totalCpuUsage(cls, interval: Optional[float] = 1.0) -> float:
        return cls._INSTANCE._BaseMonitor.totalCpuUsage(interval)

    @classmethod
    def processCpuUsage(cls, pid: Optional[int], interval: Optional[float] = 1.0) -> int:
        return cls._INSTANCE._BaseMonitor.processCpuUsage(pid, interval)

    @classmethod
    def processMemoryUsage(cls, pid: int) -> int:
        return cls._INSTANCE._BaseMonitor.processMemoryUsage(pid)


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
