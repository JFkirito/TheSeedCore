# -*- coding: utf-8 -*-
"""
TheSeed Thread Pool Module

# This module manages synchronized and asynchronous tasks through a sophisticated thread pool system, enabling effective
# concurrency control and performance optimization. It provides functionalities for task execution, load balancing,
# and performance monitoring, making it crucial for applications requiring efficient task management and execution.

# Key Components:
# 1. TheSeedCoreLogger: Central logging facility for tracking operations and errors within the thread pool.
# 2. PerformanceMode: Manages operational modes of the thread pool based on system performance needs.
# 3. TaskThreshold: Sets the threshold for dynamic thread allocation based on queued tasks.
# 4. LoadBalancing: Toggles on or off the load balancing feature to optimize task distribution and thread utilization.
# 5. Thread Labels: Identifies each thread uniquely for synchronous and asynchronous operations.

# Module Functions:
# - Manages both synchronous and asynchronous tasks using separate thread pools.
# - Dynamically adjusts thread count based on workload, improving resource allocation efficiency.
# - Provides detailed logging of all operations, enhancing transparency and aiding in troubleshooting.
# - Supports encrypted and secure task execution in compliance with system security policies.

# Usage Scenarios:
# - Applications that require handling multiple tasks simultaneously without performance degradation.
# - Systems that need to adjust operational performance dynamically based on real-time data processing demands.
# - Environments where task execution order and completion must be logged and monitored rigorously.

# Dependencies:
# - threading: Manages individual threads within the thread pools.
# - asyncio: Facilitates asynchronous task operations.
# - queue: Implements queue mechanisms for task handling.
# - subprocess, os: Used for handling system-level operations and commands within threads.
# - LoggerModule: Provides logging functionalities essential for monitoring thread pool operations.

"""

from __future__ import annotations

__all__ = ["TheSeedThreadPool"]

import asyncio
import queue
import subprocess
import threading
import traceback
from typing import TYPE_CHECKING, List, Optional, Callable, Any, Coroutine, Literal

import psutil
import pyautogui

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

_SyncTaskLock = threading.Lock()
_AsyncTaskLock = asyncio.Lock()


class TheSeedThreadPool:
    """
    TheSeed 线程池，管理同步和异步任务。

    参数:
        :param Logger : 日志记录器。
        :param PerformanceMode : 性能模式。
        :param TaskThreshold : 任务阈值。
        :param LoadBalancing : 负载均衡开关。
        :param TotalThreadCount : 线程总数。
        :param SyncThreadLabels : 同步线程标签。
        :param ASyncThreadLabels : 异步线程标签。

    属性:
        - _INSTANCE: 单例实例。
        - _Logger: 日志记录器。
        - _PerformanceMode: 性能模式。
        - _TaskThreshold: 任务阈值。
        - _LoadBalancing: 负载均衡开关。
        - _TotalThreadCount: 线程数总量。
        - _SyncThreadLabels: 同步线程标签。
        - _AsyncThreadLabels: 异步线程标签。
        - _SyncWorkerThreadPool: 同步任务线程池。
        - _AsyncWorkerThreadPool: 异步任务线程池。
        - _PerformanceMonitorEvent: 性能监控事件。
        - _MaxAllowedThreads: 最大允许线程数。
        - _MonitorThread: 性能监控线程。
    """

    class _ConsoleThread:
        def __init__(self):
            self._Thread = threading.Thread(target=self._run)
            self._Thread.daemon = True
            self._Active = threading.Event()
            self._Active.set()
            self._CommandProcessor = None
            self._CommandQueue = queue.Queue()
            self._CustomCommand = None

        def setCommandProcessor(self, command_processor: Callable[[str], Any], command_list: list):
            self._CommandProcessor = command_processor
            self._CustomCommand = command_list

        def startThread(self):
            if self._CommandProcessor is None:
                raise RuntimeError("Command processor is not set.")
            self._Thread.start()

        def closeThread(self):
            self._Active.clear()
            self._CommandQueue.put(None)
            if self._Thread.is_alive():
                pyautogui.typewrite('\n')
                self._Thread.join()

        def _run(self):
            while True:
                try:
                    if not self._Active.is_set():
                        break
                    command = input("")
                    try:
                        if command in self._CustomCommand:
                            self._CommandProcessor(command)
                        else:
                            system_command = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            self._CommandProcessor(system_command.stdout.strip())
                    except subprocess.CalledProcessError:
                        continue
                except UnicodeDecodeError:
                    continue

    class _TheSeedSyncThread:
        """
        TheSeed 同步任务线程，支持同步任务的添加、执行和取消。

        参数:
            :param ThreadName : 线程名称。
            :param Logger : 日志记录器。
        属性:
            - _ThreadName: 线程名称。
            - _Logger: 日志记录器。
            - _TaskQueue: 任务队列。
            - _Thread: 线程对象。
            - _Active: 线程活动状态。
        """

        def __init__(self, ThreadName: str, Logger: TheSeedCoreLogger):
            self._ThreadName = ThreadName
            self._Logger = Logger
            self._TaskQueue = queue.Queue()
            self._Thread = threading.Thread(target=self._run)
            self._Thread.daemon = True
            self._Active = threading.Event()
            self._Active.set()

        def startThread(self):
            self._Thread.start()
            self._Logger.info(f"SyncThread {self._ThreadName} has been started.")

        def addTask(self, task: Callable[..., Any], callback: Optional[Callable[[Any], Any]], lock: bool, *args, **kwargs):
            self._TaskQueue.put((task, args, kwargs, callback, lock))

        def getThreadName(self) -> str:
            return self._ThreadName

        def getTaskQueueCount(self) -> int:
            return self._TaskQueue.qsize()

        def closeThread(self):
            self._Active.clear()
            self._TaskQueue.put(None)
            self._Thread.join()
            self._Logger.info(f"SyncThread {self._ThreadName} has been closed.")

        def _run(self):
            while self._Active.is_set():
                task_tuple = self._TaskQueue.get()
                if task_tuple is None:
                    break
                task, args, kwargs, callback, lock = task_tuple
                try:
                    if lock:
                        with _SyncTaskLock:
                            result = task(*args, **kwargs)
                    else:
                        result = task(*args, **kwargs)
                    if callback:
                        callback(result)
                except Exception as e:
                    self._Logger.error(f"SyncThread {self._ThreadName} run task error: {e}\n\n{traceback.format_exc()}")

    class _TheSeedAsyncThread:
        """
        TheSeed 异步任务线程，支持异步任务的添加、执行和取消。

        参数:
            :param ThreadName : 线程名称。
            :param Logger : 日志记录器。
        属性:
            - _ThreadName: 线程名称。
            - _Logger: 日志记录器。
            - _TaskQueue: 任务队列。
            - _RunningTasks: 正在运行的任务集合。
            - _EventLoop: 事件循环。
            - _Thread: 线程对象。
        """

        def __init__(self, ThreadName: str, Logger: TheSeedCoreLogger):
            self._ThreadName = ThreadName
            self._Logger = Logger
            self._TaskQueue = asyncio.Queue()
            self._RunningTasks = set()
            self._EventLoop = asyncio.new_event_loop()
            self._Thread = threading.Thread(target=self._runEventLoop)
            self._Thread.daemon = True

        def startThread(self):
            self._Thread.start()
            self._Logger.info(f"AsyncThread {self._ThreadName} has been started.")

        def addTask(self, task: Callable[..., Coroutine[Any, Any, Any]], callback: Optional[Callable[[Any], Any]], lock: bool, *args, **kwargs):
            self._EventLoop.call_soon_threadsafe(lambda: self._TaskQueue.put_nowait((task, args, kwargs, callback, lock)))

        def getThreadName(self) -> str:
            return self._ThreadName

        def getTaskQueueCount(self) -> int:
            return self._TaskQueue.qsize()

        def closeThread(self):
            self._EventLoop.call_soon_threadsafe(self._TaskQueue.put_nowait, None)
            self._cancelPendingTasks()
            self._Thread.join()
            self._Logger.info(f"AsyncThread {self._ThreadName} has been closed.")

        def _runEventLoop(self):
            asyncio.set_event_loop(self._EventLoop)
            try:
                self._EventLoop.run_until_complete(self._run())
            finally:
                self._EventLoop.close()

        async def _run(self):
            while True:
                await asyncio.sleep(0.01)
                task_tuple = await self._TaskQueue.get()
                if task_tuple is None:
                    break
                task, args, kwargs, callback, lock = task_tuple
                try:
                    asyncio_task = asyncio.create_task(task(*args, **kwargs))
                    self._RunningTasks.add(asyncio_task)
                    asyncio_task.add_done_callback(self._RunningTasks.discard)
                    if lock:
                        async with _AsyncTaskLock:
                            result = await asyncio_task
                    else:
                        result = await asyncio_task
                    if callback is not None:
                        self._EventLoop.call_soon_threadsafe(callback, result)
                except Exception as e:
                    self._Logger.error(f"AsyncThread {self._ThreadName} run task error: {e}\n\n{traceback.format_exc()}")

        def _cancelPendingTasks(self):
            for task in list(self._RunningTasks):
                task.cancel()
            self._RunningTasks.clear()

    _INSTANCE = None

    def __new__(cls, Logger: TheSeedCoreLogger, PerformanceMode: Literal["HighestPerformance", "Balance", "LowPerformance"] = "Balance", TaskThreshold: int = 10, LoadBalancing: bool = True, TotalThreadCount: int = None, SyncThreadLabels: List[str] = None, ASyncThreadLabels: List[str] = None):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(TheSeedThreadPool, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Logger: TheSeedCoreLogger, PerformanceMode: Literal["HighestPerformance", "Balance", "LowPerformance"] = "Balance", TaskThreshold: int = 10, LoadBalancing: bool = True, TotalThreadCount: int = None, SyncThreadLabels: List[str] = None, ASyncThreadLabels: List[str] = None):
        self._Logger = Logger
        self._PerformanceMode = PerformanceMode
        self._TaskThreshold = TaskThreshold
        self._LoadBalancing = LoadBalancing
        self._TotalThreadCount = self._setThreadCount(TotalThreadCount) if TotalThreadCount is None else TotalThreadCount
        self._SyncThreadLabels = SyncThreadLabels or []
        self._ASyncThreadLabels = ASyncThreadLabels or []
        self._SyncThreadPool = {}
        self._AsyncThreadPool = {}
        self._ConsoleThread = TheSeedThreadPool._ConsoleThread()
        self._PerformanceMonitorThread = None
        self._PerformanceMonitorEvent = threading.Event()
        self._MaxAllowedThreads = int(self._TotalThreadCount * 0.5)
        self._initThreadPools(self._TotalThreadCount // 2, self._SyncThreadLabels, self._ASyncThreadLabels)

    def addSyncTask(self, task: Callable[..., Any], callback: Optional[Callable[[Any], Any]] = None, thread_label: Optional[str] = None, lock: bool = False, *args, **kwargs):
        """
        添加同步任务到线程池。

        参数:
            :param task : 要添加的任务。
            :param callback: 任务完成后的回调函数。
            :param thread_label: 线程标签。
            :param lock: 是否加锁。
            :param args: 任务参数。
            :param kwargs: 任务关键字参数。
        """
        try:
            if thread_label is not None:
                if thread_label in self._SyncThreadPool:
                    self._SyncThreadPool[thread_label].addTask(task, callback, lock, *args, **kwargs)
                else:
                    error_msg = f"SyncThread with label '{thread_label}' does not exist."
                    self._Logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                free_thread = min(self._SyncThreadPool, key=lambda label: self._SyncThreadPool[label].getTaskQueueCount())
                self._SyncThreadPool[free_thread].addTask(task, callback, lock, *args, **kwargs)
                self._Logger.info(f"Task added to SyncThread with the smallest queue: {free_thread}.")
        except Exception as e:
            error_msg = f"TheSeedThreadPool add sync task error: {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)

    def addAsyncTask(self, task: Callable[..., Coroutine[Any, Any, Any]], callback: Optional[Callable[[Any], Any]] = None, thread_label: Optional[str] = None, lock: bool = False, *args, **kwargs):
        """
        添加异步任务到线程池。

        参数:
            :param task : 要添加的任务。
            :param callback: 任务完成后的回调函数。
            :param thread_label: 线程标签。
            :param lock: 是否加锁。
            :param args: 任务参数。
            :param kwargs: 任务关键字参数。
        """
        try:
            if thread_label is not None:
                if thread_label in self._AsyncThreadPool:
                    self._AsyncThreadPool[thread_label].addTask(task, callback, lock, *args, **kwargs)
                else:
                    error_msg = f"AsyncThread with label '{thread_label}' does not exist."
                    self._Logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                free_thread = min(self._AsyncThreadPool, key=lambda label: self._AsyncThreadPool[label].getTaskQueueCount())
                self._AsyncThreadPool[free_thread].addTask(task, callback, lock, *args, **kwargs)
                self._Logger.info(f"Task added to AsyncThread with the smallest queue: {free_thread}.")
        except Exception as e:
            error_msg = f"TheSeedThreadPool add async task error: {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)

    def createSyncThread(self, thread_label: str):
        """创建同步线程。"""
        if thread_label in self._SyncThreadPool:
            raise ValueError(f"SyncThread with label '{thread_label}' already exists.")
        new_thread = TheSeedThreadPool._TheSeedSyncThread(thread_label, self._Logger)
        new_thread.startThread()
        self._SyncThreadPool[thread_label] = new_thread
        self._Logger.info(f"Created new SyncThread with label '{thread_label}'.")

    def createAsyncThread(self, thread_label: str):
        """创建异步线程。"""
        if thread_label in self._AsyncThreadPool:
            raise ValueError(f"AsyncThread with label '{thread_label}' already exists.")
        new_thread = TheSeedThreadPool._TheSeedAsyncThread(thread_label, self._Logger)
        new_thread.startThread()
        self._AsyncThreadPool[thread_label] = new_thread
        self._Logger.info(f"Created new AsyncThread with label '{thread_label}'.")

    def getSyncThreadCount(self) -> int:
        """获取创建的同步线程数"""
        return len(self._SyncThreadPool)

    def getAsyncThreadCount(self) -> int:
        """获取创建的异步线程数"""
        return len(self._AsyncThreadPool)

    def loadBalancingSwitch(self, switch: bool):
        """开启或关闭负载均衡。"""
        self._LoadBalancing = switch
        if self._LoadBalancing:
            self._startPerformanceMonitorThread()
            self._Logger.info("Load balancing is enabled.")
        else:
            self._PerformanceMonitorEvent.set()
            if self._PerformanceMonitorThread.is_alive():
                self._PerformanceMonitorThread.join()
            self._Logger.info("Load balancing is disabled.")

    def closeThreadPool(self):
        """关闭所有线程和线程池，包括监控线程，清理资源。"""
        self._PerformanceMonitorEvent.set()
        if self._PerformanceMonitorThread.is_alive():
            self._PerformanceMonitorThread.join()
        self._ConsoleThread.closeThread()
        self._Logger.info("Console thread has been closed..")
        try:
            for thread_pool in [self._SyncThreadPool, self._AsyncThreadPool]:
                for thread_name, thread in list(thread_pool.items()):
                    try:
                        thread.closeThread()
                        del thread_pool[thread_name]
                    except Exception as e:
                        self._Logger.error(f"Error closing thread {thread_name}: {e}")
                        continue
            self._Logger.info("TheSeedThreadPool closed all threads and the monitoring thread.")
            return True
        except Exception as e:
            error_msg = f'TheSeedThreadPool close error: {e}\n\n{traceback.format_exc()}'
            self._Logger.error(error_msg)
            return False

    def startConsoleThread(self, command_processor: Callable[[str], Any], command_list: list):
        """启动控制台线程。"""
        self._ConsoleThread.setCommandProcessor(command_processor, command_list)
        self._ConsoleThread.startThread()
        self._Logger.info("Console thread started.")

    def _setThreadCount(self, thread_count: int | None) -> int:
        """根据数据库配置和系统性能模式设置线程数。

        参数:
            :param thread_count : 线程数。
        返回:
            :return : 线程数。
        """
        try:
            if thread_count is not None:
                if thread_count >= 4:
                    if thread_count % 2 == 0:
                        return thread_count
                    return thread_count - 1
                return 4
            performance_mode = self._PerformanceMode
            cpu_threads = psutil.cpu_count(logical=True)

            performance_mapping = {
                "HighestPerformance": cpu_threads,
                "Balance": {
                    4: 4, 8: 4, 10: 4, 16: 4, 20: 6, 24: 6, 28: 8, 32: 8, 36: 10,
                    40: 12, 56: 16, 64: 16
                },
                "LowPerformance": {
                    4: 4, 8: 4, 10: 4, 16: 4, 20: 4, 24: 4, 28: 4, 32: 4, 36: 4,
                    40: 4, 56: 4, 64: 4
                }
            }

            if performance_mode == "HighestPerformance":
                return performance_mapping["HighestPerformance"]
            elif performance_mode in ["Balance", "LowPerformance"]:
                return performance_mapping[performance_mode].get(cpu_threads, 4)
            else:
                raise ValueError("Unknown performance mode")
        except Exception as e:
            error_msg = f"TheSeedThreadPool set cpu thread count error: {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return 4

    def _initThreadPools(self, thread_count: int, sync_labels: Optional[List[str]] = None, async_labels: Optional[List[str]] = None):
        """初始化同步和异步线程池。

        参数:
            :param thread_count : 线程数。
            :param sync_labels : 同步线程标签。
            :param async_labels : 异步线程标签。
        """
        if sync_labels is not None:
            if len(sync_labels) > thread_count:
                raise ValueError("The number of sync labels exceeds the number of threads")
            sync_label_count = len(sync_labels)
        else:
            sync_label_count = 0

        if async_labels is not None:
            if len(async_labels) > thread_count:
                raise ValueError("The number of async labels exceeds the number of threads")
            async_label_count = len(async_labels)
        else:
            async_label_count = 0
        try:
            for i in range(thread_count):
                sync_label = self._SyncThreadLabels[i] if i < sync_label_count else str(i)
                async_label = self._ASyncThreadLabels[i] if i < async_label_count else str(i)
                self._SyncThreadPool[sync_label] = TheSeedThreadPool._TheSeedSyncThread(sync_label, self._Logger)
                self._AsyncThreadPool[async_label] = TheSeedThreadPool._TheSeedAsyncThread(async_label, self._Logger)
                self._SyncThreadPool[sync_label].startThread()
                self._AsyncThreadPool[async_label].startThread()
            if self._LoadBalancing:
                self._startPerformanceMonitorThread()
                self._Logger.info("Load balancing is enabled.")
            self._Logger.info(f"SyncThread and AsyncThread pools initialized with {thread_count} threads.")
        except Exception as e:
            error_msg = f"TheSeedThreadPool init thread pools error: {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)

    def _startPerformanceMonitorThread(self):
        """启动线程池性能监控线程。"""
        self._PerformanceMonitorThread = threading.Thread(target=self._monitorThreadPoolsPerformance, daemon=True)
        self._PerformanceMonitorThread.start()
        self._Logger.info("ThreadPool performance monitor thread started.")

    def _monitorThreadPoolsPerformance(self):
        """监控线程池性能，根据负载动态调整线程数。"""
        while not self._PerformanceMonitorEvent.is_set():
            if self._PerformanceMonitorEvent.wait(timeout=15):
                break
            self._adjustThreadPool(self._SyncThreadPool, self._SyncThreadLabels, "Sync")
            self._adjustThreadPool(self._AsyncThreadPool, self._ASyncThreadLabels, "Async")

    def _adjustThreadPool(self, thread_pool, protected_labels, type_label):
        """
        根据负载动态调整线程数。

        参数:
            :param thread_pool : 线程池。
            :param protected_labels : 受保护的标签。
            :param type_label : 线程类型标签。
        """
        total_tasks = sum(thread.getTaskQueueCount() for thread in thread_pool.values())
        total_threads = len(thread_pool)
        average_tasks = total_tasks / total_threads if total_threads else 0

        idle_threads = [label for label, thread in thread_pool.items() if thread.getTaskQueueCount() == 0 and label not in protected_labels]
        if len(idle_threads) > 1:
            for label in idle_threads[:-1]:
                thread_pool[label].closeThread()
                del thread_pool[label]
                self._Logger.info(f"Closed one {type_label} thread due to low load. Remaining idle: {len(idle_threads) - 1}")

        current_total_threads = len(self._SyncThreadPool) + len(self._AsyncThreadPool)
        if current_total_threads < self._MaxAllowedThreads:
            if average_tasks >= self._TaskThreshold or len(idle_threads) == 0:
                self._addThread(thread_pool, protected_labels, type_label)

    def _addThread(self, thread_pool, protected_labels, type_label):
        """
        添加新线程。

        参数:
            :param thread_pool : 线程池。
            :param protected_labels : 受保护的标签。
            :param type_label : 线程类型标签。
        """
        current_labels = set(thread_pool.keys())
        protected_labels_set = set(protected_labels)
        i = 0
        while True:
            potential_label = str(i)
            if potential_label not in current_labels and potential_label not in protected_labels_set:
                new_label = potential_label
                break
            i += 1
        if type_label == "Sync":
            new_thread = TheSeedThreadPool._TheSeedSyncThread(new_label, self._Logger)
        else:
            new_thread = TheSeedThreadPool._TheSeedAsyncThread(new_label, self._Logger)
        new_thread.startThread()
        thread_pool[new_label] = new_thread
        self._Logger.info(f"Added one {type_label} thread with new label {new_label}. Total: {len(thread_pool) + 1}")
