# -*- coding: utf-8 -*-
"""
TheSeedCore Concurrency System Module.

# This module handles task management across multiple processing units using a mix of multiprocessing and multithreading strategies.
# It efficiently schedules and executes tasks that can be either asynchronous or synchronous, utilizing both CPU and GPU resources.
# The module can adaptively allocate tasks between threads and processes based on the current load and system capabilities.

# Key Components:
# 1. _BaseTaskObject: Base class for all task objects, providing common attributes and methods for task execution.
# 2. _AsyncTaskObject: Derived from _BaseTaskObject, designed for managing and executing asynchronous tasks.
# 3. _SyncTaskObject: Inherits from _BaseTaskObject, tailored for synchronous task execution.
# 4. _BaseThreadObject: Base class for thread management, encapsulating the threading logic and task queue handling.
# 5. _AsyncThreadObject: Extends _BaseThreadObject for handling asynchronous tasks within threads.
# 6. _SyncThreadObject: Extends _BaseThreadObject, manages the execution of synchronous tasks in a dedicated thread.
# 7. _ProcessObject: Manages process-level operations, task distribution, and inter-process communication.

# Module Functions:
# - Provides robust task scheduling and execution mechanisms for both CPU and GPU tasks.
# - Supports dynamic resource allocation based on task load and system performance metrics.
# - Facilitates detailed logging and monitoring of all task and thread activities to ensure smooth operations.
# - Includes mechanisms for task prioritization, retries, and failure handling to enhance reliability and efficiency.

# Usage Scenarios:
# - Suitable for applications requiring high throughput task processing across multiple CPUs and GPUs.
# - Can be used in server environments where task distribution and efficient resource utilization are critical.
# - Ideal for scenarios requiring a mix of synchronous and asynchronous task processing.

# Dependencies:
# - multiprocessing: For managing processes and shared resources.
# - threading: Utilized for creating and managing threads.
# - asyncio: Required for managing asynchronous operations.
# - torch: Optional, used for GPU-related tasks and operations if available.
# - psutil: Utilized for monitoring system performance and resources.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import multiprocessing
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from typing import TYPE_CHECKING, Union, Literal

import psutil

if TYPE_CHECKING:
    from .ConfigModule import ConcurrencySystemConfig
    from .LoggerModule import TheSeedCoreLogger

_AvailableCUDADevicesID = []
try:
    # noinspection PyUnresolvedReferences
    import torch

    if torch.cuda.is_available():
        num_gpus = torch.cuda.device_count()
        for cuda_device_id in range(num_gpus):
            _AvailableCUDADevicesID.append(cuda_device_id)
        _PyTorchSupport = True
        print(f"\033[92mTheSeedCore Concurrency System - Process({os.getpid()}) : PyTorch is available and CUDA is available. Allow GPU boost\033[0m")
    else:
        _PyTorchSupport = False
        print(f"\033[33mTheSeedCore Concurrency System - Process({os.getpid()}) : PyTorch is available but CUDA is not available. GPU boost will be unavailable\033[0m")
except ImportError as PyTorchImportError:
    _PyTorchSupport = False
    print(f"\033[31mTheSeedCore Concurrency System - Process({os.getpid()}) : {str(PyTorchImportError)}. GPU boost will be unavailable\033[0m")


class _BaseTaskObject:
    """
    任务对象基类，用于封装任务执行相关的属性和方法。

    属性:
        - Task: 执行的任务函数。
        - Callback: 回调函数，任务执行完后调用。
        - Lock: 是否需要锁定任务执行。
        - MaximumLockHoldingTime: 最大锁定时间。
        - GpuBoost: 是否启用GPU加速。
        - GpuID: 使用的GPU编号。
        - ReTry: 是否需要重试任务执行。
        - MaxRetries: 最大重试次数。
        - _Retries: 当前重试次数。
        - _Timer: 定时器，用于任务超时处理。
        - _Args: 任务函数的位置参数。
        - _Kwargs: 任务函数的关键字参数。
    """

    def __init__(self, Task: callable, Callback: callable = None, Lock: bool = False, MaximumLockHoldingTime: int = 3, GpuBoost: bool = False, GpuID: int = 0, ReTry: bool = False, MaxRetries: int = 3, *args, **kwargs):
        """
        初始化任务对象。

        在初始化时，如果启用GPU加速且环境支持，将检查GPU设备的可用性，否则将抛出异常。
        """
        self._Task: callable = Task
        self._Callback: callable = Callback
        self._IsLock: bool = Lock
        self._MaximumLockHoldingTime: int = MaximumLockHoldingTime
        self._GpuBoost: bool = GpuBoost
        self._GpuID: int = GpuID
        self._IsReTry: bool = ReTry
        self._MaxRetries: int = MaxRetries
        self._Retries: int = 0
        self._Timer: Union[threading.Timer, None] = None
        self._Args = args
        self._Kwargs = kwargs
        if self._GpuBoost:
            if _PyTorchSupport:
                if self._GpuID not in _AvailableCUDADevicesID:
                    self._GpuID = 0
                    raise ValueError(f"GPU ID {self._GpuID} is not available. Use GPU ID 0 instead.")
                self._Args, self._Kwargs = self.PrepareGpuBoostParams()
            else:
                self._GpuBoost = False
                raise ValueError("TheSeedCore ConcurrencySystem error : Failed to import torch. GPU boost unavailable.")

    def taskName(self) -> str:
        """返回任务函数的名称。"""
        return self._Task.__name__

    def isCallback(self) -> bool:
        """判断是否设置了回调函数。"""
        return self._Callback is not None

    def callback(self) -> callable:
        """返回设置的回调函数。"""
        return self._Callback

    def isLock(self) -> bool:
        """返回是否需要锁定任务执行。"""
        return self._IsLock

    def maximumLockHoldingTime(self) -> int:
        """返回最大锁定持续时间。"""
        return self._MaximumLockHoldingTime

    def isGpuBoost(self) -> bool:
        """返回是否启用GPU加速。"""
        return self._GpuBoost

    def PrepareGpuBoostParams(self) -> tuple[list, dict]:
        """
        准备GPU加速的参数。

        遍历任务参数，将支持的对象移动到指定的GPU设备。
        """
        device = torch.device(f"cuda:{self._GpuID}")
        args = [self.recursivelyCheckGpuBoostParams(arg, device) for arg in self._Args]
        kwargs = {k: self.recursivelyCheckGpuBoostParams(v, device) for k, v in self._Kwargs.items()}
        return args, kwargs

    def recursivelyCheckGpuBoostParams(self, obj, device):
        """
        递归检查并更新支持GPU加速的参数。

        支持的类型包括torch.Tensor和torch.nn.Module，会将它们移动到指定的GPU设备。
        """
        if isinstance(obj, torch.Tensor):
            return obj.to(device)
        elif isinstance(obj, torch.nn.Module):
            return obj.to(device)
        elif isinstance(obj, dict):
            return {k: self.recursivelyCheckGpuBoostParams(v, device) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.recursivelyCheckGpuBoostParams(v, device) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self.recursivelyCheckGpuBoostParams(v, device) for v in obj)
        return obj

    @staticmethod
    def cleanupGpuResources() -> None:
        """
        清理GPU资源。

        同步并清空GPU缓存。
        """
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    def isReTry(self) -> bool:
        """返回是否启用任务重试。"""
        return self._IsReTry

    def maxRetries(self) -> int:
        """返回最大重试次数。"""
        return self._MaxRetries

    def setTimer(self, timer: threading.Timer) -> None:
        """设置任务的定时器。"""
        self._Timer = timer

    def cancelTimer(self) -> None:
        """取消任务的定时器。"""
        if self._Timer is not None:
            self._Timer.cancel()
            self._Timer = None

    def execute(self):
        """
        执行任务。

        该方法必须在子类中具体实现。
        """
        raise NotImplementedError("This method must be implemented by subclasses.")

    def _retryExecution(self):
        """
        重试任务执行。

        该方法必须在子类中具体实现。
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class _AsyncTaskObject(_BaseTaskObject):
    """
    异步任务对象类，继承自_BaseTaskObject，用于处理异步任务的执行和管理。

    该类重写execute方法以支持异步操作，并增加了对GPU资源的管理和错误处理的逻辑。
    """

    async def execute(self):
        """
        异步执行任务。

        1. 异步调用_Task函数，传入参数。
        2. 如果启用了GPU加速，并且任务结果为torch.Tensor或torch.nn.Module，则将结果复制到CPU，并清理GPU资源。
        3. 如果启用了重试机制，且任务执行抛出异常，则进行重试。
        4. 如果重试次数耗尽或未启用重试，抛出异常。
        """
        try:
            task_result = await self._Task(*self._Args, **self._Kwargs)
            if self.isGpuBoost():
                if isinstance(task_result, torch.Tensor) or isinstance(task_result, torch.nn.Module):
                    cpu_result = task_result.clone().detach().cpu()
                    del task_result
                    self.cleanupGpuResources()
                    return cpu_result
                elif isinstance(task_result, list) or isinstance(task_result, tuple):
                    cpu_result = [item.clone().detach().cpu() if isinstance(item, torch.Tensor) else item for item in task_result]
                    del task_result
                    self.cleanupGpuResources()
                    return cpu_result
            return task_result
        except Exception as e:
            if self.isReTry():
                return await self._retryExecution()
            else:
                raise Exception(f"TheSeedCore Concurrency System : Failed to execute async task {self.taskName()} due to {str(e)}.")

    async def _retryExecution(self):
        """
        异步任务重试执行。

        在最大重试次数范围内，如果任务执行失败，将等待一段时间后再次尝试执行任务。
        时间间隔根据重试次数指数增加，以尝试解决暂时性的执行问题。
        如果重试次数耗尽仍然失败，则抛出异常。
        """
        retries = 0
        while retries < self._MaxRetries:
            try:
                task_result = await self._Task(*self._Args, **self._Kwargs)
                if self.isGpuBoost():
                    if isinstance(task_result, torch.Tensor) or isinstance(task_result, torch.nn.Module):
                        cpu_result = task_result.clone().detach().cpu()
                        del task_result
                        self.cleanupGpuResources()
                        return cpu_result
                    elif isinstance(task_result, list) or isinstance(task_result, tuple):
                        cpu_result = [item.clone().detach().cpu() if isinstance(item, torch.Tensor) else item for item in task_result]
                        del task_result
                        self.cleanupGpuResources()
                        return cpu_result
                return task_result
            except Exception as e:
                retries += 1
                if retries >= self._MaxRetries:
                    raise Exception(f"TheSeedCore ConcurrencySystem error : Failed to execute async task {self.taskName()} after {self._MaxRetries} attempts due to {str(e)}.")
                await asyncio.sleep(0.1 * (2 ** retries))


class _SyncTaskObject(_BaseTaskObject):
    """
    同步任务对象类，继承自_BaseTaskObject，用于处理同步任务的执行和管理。

    该类实现任务的同步执行，并包括了对GPU资源的管理以及错误处理的逻辑。
    """

    def execute(self):
        """
        同步执行任务。

        1. 同步调用_Task函数，传入参数。
        2. 如果启用了GPU加速，并且任务结果为torch.Tensor或torch.nn.Module，则将结果复制到CPU，并清理GPU资源。
        3. 如果启用了重试机制，且任务执行抛出异常，则进行重试。
        4. 如果重试次数耗尽或未启用重试，抛出异常。
        """
        try:
            task_result = self._Task(*self._Args, **self._Kwargs)
            if self.isGpuBoost():
                if isinstance(task_result, torch.Tensor) or isinstance(task_result, torch.nn.Module):
                    cpu_result = task_result.clone().detach().cpu()
                    del task_result
                    self.cleanupGpuResources()
                    return cpu_result
                elif isinstance(task_result, list) or isinstance(task_result, tuple):
                    cpu_result = [item.clone().detach().cpu() if isinstance(item, torch.Tensor) else item for item in task_result]
                    del task_result
                    self.cleanupGpuResources()
                    return cpu_result
            return task_result
        except Exception as e:
            if self.isReTry():
                return self._retryExecution()
            else:
                raise Exception(f"TheSeedCore Concurrency System : Failed to execute sync task {self.taskName()} due to {str(e)}.")

    def _retryExecution(self):
        """
        同步任务重试执行。

        在最大重试次数范围内，如果任务执行失败，将等待一段时间后再次尝试执行任务。
        时间间隔根据重试次数指数增加，以尝试解决暂时性的执行问题。
        如果重试次数耗尽仍然失败，则抛出异常。
        """
        retries = 0
        while retries < self._MaxRetries:
            try:
                task_result = self._Task(*self._Args, **self._Kwargs)
                if self.isGpuBoost():
                    if isinstance(task_result, torch.Tensor) or isinstance(task_result, torch.nn.Module):
                        cpu_result = task_result.clone().detach().cpu()
                        del task_result
                        self.cleanupGpuResources()
                        return cpu_result
                    elif isinstance(task_result, list) or isinstance(task_result, tuple):
                        cpu_result = [item.clone().detach().cpu() if isinstance(item, torch.Tensor) else item for item in task_result]
                        del task_result
                        self.cleanupGpuResources()
                        return cpu_result
                return task_result
            except Exception as e:
                retries += 1
                if retries >= self._MaxRetries:
                    raise Exception(f"TheSeedCore Concurrency System : Failed to execute sync task {self.taskName()} after {self._MaxRetries} attempts due to {str(e)}.")
                time.sleep(0.1 * (2 ** retries))


class _BaseThreadObject:
    """
    线程对象基类，用于封装线程操作的公共逻辑。

    属性:
        - _Logger: 日志记录器，用于记录线程和任务的执行信息。
        - _ThreadID: 线程的唯一标识。
        - _CallbackQueue: 回调队列，用于存放任务执行后的回调函数。
        - _TaskLock: 任务执行的锁，防止多线程同时执行同一任务。
        - _TaskQueue: 优先级队列，用于存放待执行的任务。
        - _TaskUniqueID: 生成任务的唯一标识。
        - _Thread: 实际执行任务的线程。
        - _CloseEvent: 用于通知线程关闭的事件。
    """

    def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], ThreadID: int, CallbackQueue: multiprocessing.Queue, TaskLock: multiprocessing.Lock):
        """
        初始化线程对象。

        创建一个线程，并设置为守护线程，以确保主程序结束时线程也会结束。
        初始化任务队列，任务唯一标识生成器，以及关闭事件。
        """
        self._Logger = Logger
        self._ThreadID = ThreadID
        self._CallbackQueue = CallbackQueue
        self._TaskLock = TaskLock
        self._TaskQueue = queue.PriorityQueue()
        self._TaskUniqueID = count()
        self._Thread = threading.Thread(target=self._run, daemon=True)
        self._CloseEvent = threading.Event()

    def startThread(self):
        """
        启动线程。

        线程开始执行_run方法。
        """
        self._Thread.start()

    def closeThread(self):
        """
        关闭线程。

        设置关闭事件，等待线程结束，然后删除线程对象。
        """
        self._CloseEvent.set()
        if self._Thread.is_alive():
            self._Thread.join()
        del self

    def addThreadTask(self, priority: int, task_object):
        """
        向线程的任务队列添加一个任务。

        任务被封装为一个元组，包含任务的优先级，唯一标识和任务对象本身。
        """
        task_data = (priority, next(self._TaskUniqueID), task_object)
        self._TaskQueue.put(task_data)

    def getThreadTaskCount(self):
        """获取任务队列中的任务数量。"""
        return self._TaskQueue.qsize()

    def threadID(self):
        """返回线程的唯一标识。"""
        return self._ThreadID

    def _run(self):
        """
        定义线程的执行流程。

        该方法必须在子类中具体实现，通常包括任务的获取、执行和异常处理。
        """
        raise NotImplementedError("This method must be implemented by subclasses.")


class _AsyncThreadObject(_BaseThreadObject):
    """
    异步线程对象类，继承自_BaseThreadObject，专门处理异步任务的执行。

    该类提供一个完整的异步任务处理流程，包括任务的调度、执行、结果回调处理以及异常管理。
    """

    def _run(self):
        """
        定义异步线程的运行逻辑。

        设置并运行一个新的事件循环，直到完成任务处理或者接收到关闭信号。
        """
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        try:
            event_loop.run_until_complete(self._taskProcessor())
        finally:
            event_loop.close()

    async def _taskProcessor(self):
        """
        异步任务处理器。

        循环处理任务队列中的任务，直到接收到线程关闭事件。
        """
        while not self._CloseEvent.is_set():
            try:
                item: tuple[int, int, _AsyncTaskObject] = self._TaskQueue.get(block=True, timeout=0.5)
            except queue.Empty:
                continue
            priority, uniqueid, task_object = item
            if task_object.isLock():
                if self._TaskLock.acquire(timeout=task_object.maximumLockHoldingTime()):
                    try:
                        task_timer = threading.Timer(task_object.maximumLockHoldingTime(), self._TaskLock)
                        task_object.setTimer(task_timer)
                        task_timer.start()
                        await self._executeTask(task_object)
                    finally:
                        task_object.cancelTimer()
                        try:
                            self._TaskLock.release()
                        except RuntimeError:
                            pass
                else:
                    retry_delay = 0.1 * (2 ** task_object.maxRetries())
                    time.sleep(min(retry_delay, 10))
                    task_data = (priority, uniqueid, task_object)
                    self._TaskQueue.put(task_data)
            else:
                await self._executeTask(task_object)
        self._cleanUp()

    async def _executeTask(self, task_object: _AsyncTaskObject):
        """
        执行单个异步任务。

        完成任务后，如果任务设置了回调，将回调及其结果放入回调队列。
        """
        task_execute_result = await task_object.execute()
        if task_object.isCallback():
            task_callback = task_object.callback()
            self._CallbackQueue.put(("Callback", task_callback, task_execute_result))
        del task_object

    def _cleanUp(self):
        """
        清理线程资源。

        在线程关闭时执行，处理并记录任何剩余的任务。
        """
        remaining_tasks = self._TaskQueue.qsize()
        while not self._TaskQueue.empty():
            remaining_task = self._TaskQueue.get()
            self._Logger.debug(f"Async thread {self._ThreadID} discarded remaining task: {remaining_task}")
            del remaining_task
        self._Logger.debug(f"Async thread {self._ThreadID} {remaining_tasks} tasks discarded.")


class _SyncThreadObject(_BaseThreadObject):
    """
    同步线程对象类，继承自_BaseThreadObject，专门处理同步任务的执行。

    该类提供一个同步任务处理流程，包括任务的调度、执行、结果回调处理以及异常管理。
    """

    def _run(self):
        """
        定义同步线程的运行逻辑。

        循环处理任务队列中的任务，直到接收到线程关闭事件。
        """
        while not self._CloseEvent.is_set():
            self._taskProcessor()
        self._cleanUp()

    def _taskProcessor(self):
        """
        同步任务处理器。

        尝试从任务队列中获取任务，如果成功则根据任务的锁定状态进行处理。
        """
        try:
            item: tuple[int, int, _SyncTaskObject] = self._TaskQueue.get(block=True, timeout=0.5)
        except queue.Empty:
            return
        priority, uniqueid, task_object = item
        if task_object.isLock():
            if self._TaskLock.acquire(timeout=task_object.maximumLockHoldingTime()):
                try:
                    task_timer = threading.Timer(task_object.maximumLockHoldingTime(), self._TaskLock)
                    task_object.setTimer(task_timer)
                    task_timer.start()
                    self._executeTask(task_object)
                finally:
                    task_object.cancelTimer()
                    try:
                        self._TaskLock.release()
                    except RuntimeError:
                        pass
            else:
                retry_delay = 0.1 * (2 ** task_object.maxRetries())
                time.sleep(min(retry_delay, 10))
                task_data = (priority, uniqueid, task_object)
                self._TaskQueue.put(task_data)
        else:
            self._executeTask(task_object)

    def _executeTask(self, task_object: _SyncTaskObject):
        """
        执行单个同步任务。

        完成任务后，如果任务设置了回调，将回调及其结果放入回调队列。
        """
        task_execute_result = task_object.execute()
        if task_object.isCallback():
            task_callback = task_object.callback()
            self._CallbackQueue.put(("Callback", task_callback, task_execute_result))
        del task_object

    def _cleanUp(self):
        """
        清理线程资源。

        在线程关闭时执行，处理并记录任何剩余的任务。
        """
        remaining_tasks = self._TaskQueue.qsize()
        while not self._TaskQueue.empty():
            remaining_task = self._TaskQueue.get()
            self._Logger.debug(f"Sync thread {self._ThreadID} discarded remaining task: {remaining_task}")
            del remaining_task
        self._Logger.debug(f"Sync thread {self._ThreadID} {remaining_tasks} tasks discarded.")


class _ProcessObject:
    """
    进程对象类，用于管理和封装进程级别的操作和属性。

    属性:
        - _Logger: 日志记录器，用于记录进程和任务的执行信息。
        - _ProcessID: 进程的唯一标识。
        - _ProcessType: 进程类型，可以是'Core'或'Expand'。
        - _ProcessPID: 进程的操作系统PID。
        - _TaskThreshold: 任务阈值，用于控制任务的加载和分配。
        - _CallbackQueue: 回调队列，用于存放任务执行后的回调函数。
        - _TaskLock: 任务执行的锁。
        - _TaskQueue: 多进程安全队列，用于存放待执行的任务。
        - _Process: 代表该对象的多进程处理器。
        - _CloseEvent: 用于通知进程关闭的事件。
        - _AsyncThread: 处理异步任务的线程对象。
        - _SyncThread: 处理同步任务的线程对象。
    """

    def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], ProcessID: int, ProcessType: Literal["Core", "Expand"], TaskThreshold: int, CallbackQueue: multiprocessing.Queue, TaskLock: multiprocessing.Lock):
        """
        初始化进程对象。

        创建并配置进程、异步线程、同步线程和任务队列等。
        """
        self._Logger = Logger
        self._ProcessID = ProcessID
        self._ProcessType = ProcessType
        self._ProcessPID: Union[None, int] = None
        self._TaskThreshold = TaskThreshold
        self._CallbackQueue = CallbackQueue
        self._TaskLock = TaskLock
        self._TaskQueue = multiprocessing.Queue()
        self._Process = multiprocessing.Process(target=self._run)
        self._CloseEvent = multiprocessing.Event()
        self._AsyncThread = None
        self._SyncThread = None

    def startProcess(self):
        """
        启动进程。

        进程开始执行_run方法。
        """
        self._Process.start()
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._Process.pid}) has been started.")

    def closeProcess(self):
        """
        关闭进程。

        设置关闭事件，等待进程结束，然后删除进程对象。
        """
        self._CloseEvent.set()
        if self._Process.is_alive():
            self._Process.join()
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} has been closed.")
        del self

    def addProcessTask(self, priority, task_object):
        """
        向进程的任务队列添加一个任务。

        任务被封装为一个元组，包含任务的优先级和任务对象本身。
        """
        task_data = (priority, task_object)
        self._TaskQueue.put(task_data)

    def getProcessTaskCount(self) -> int:
        """获取任务队列中的任务数量。"""
        return self._TaskQueue.qsize()

    def getCurrentProcessLoad(self):
        """
        计算当前进程的负载。

        使用psutil库来获取CPU和内存使用率，并计算加权负载。
        """
        psutil_object = psutil.Process(self._Process.pid)
        cpu_usage = psutil_object.cpu_percent(interval=0.1) / psutil.cpu_count(logical=False)
        memory_usage = psutil_object.memory_percent()
        weighted_load = (cpu_usage * 5) + (memory_usage * 5)
        return min(max(weighted_load, 0), 100)

    def processID(self):
        """返回进程的唯一标识。"""
        return self._ProcessID

    def _startThread(self):
        """启动处理异步和同步任务的线程。"""
        self._AsyncThread = _AsyncThreadObject(self._Logger, 0, self._CallbackQueue, self._TaskLock)
        self._SyncThread = _SyncThreadObject(self._Logger, 0, self._CallbackQueue, self._TaskLock)
        self._AsyncThread.startThread()
        self._SyncThread.startThread()
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._Process.pid}) async thread has been started.")
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._Process.pid}) sync thread has been started.")

    def _closeThread(self):
        """关闭异步和同步处理线程。"""
        self._AsyncThread.closeThread()
        self._SyncThread.closeThread()

    def _run(self):
        """
        进程的主执行逻辑。

        处理任务的调度和线程的管理，确保在接收到关闭事件时正确地清理和关闭资源。
        """
        self._ProcessPID = self._Process.pid
        self._startThread()
        try:
            while not self._CloseEvent.is_set():
                gc.collect()
                try:
                    item: tuple[int, _AsyncTaskObject | _SyncTaskObject] = self._TaskQueue.get(block=True, timeout=0.5)
                except queue.Empty:
                    continue
                priority, task_object = item
                task_type = "Async" if asyncio.iscoroutinefunction(task_object.execute) else "Sync"
                if task_type == "Async":
                    if self._AsyncThread.getThreadTaskCount() < int(self._TaskThreshold // 2):
                        self._AsyncThread.addThreadTask(priority, task_object)
                        continue
                    self.addProcessTask(priority, task_object)
                    continue
                if task_type == "Sync":
                    if self._SyncThread.getThreadTaskCount() < int(self._TaskThreshold // 2):
                        self._SyncThread.addThreadTask(priority, task_object)
                        continue
                    self.addProcessTask(priority, task_object)
                    continue
        except (KeyboardInterrupt, SystemExit):
            self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} received shutdown signal (Ctrl+C).")
        finally:
            self._cleanUp()

    def _cleanUp(self):
        """
        清理进程资源。

        关闭线程，并处理任何剩余的任务，确保所有资源被正确释放。
        """
        self._closeThread()
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._ProcessPID}) async thread has been closed.")
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._ProcessPID}) sync thread has been closed.")
        remaining_tasks = self._TaskQueue.qsize()
        while not self._TaskQueue.empty():
            remaining_task = self._TaskQueue.get()
            self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._ProcessPID}) discarded remaining task: {remaining_task}")
            del remaining_task
        self._Logger.debug(f"{self._ProcessType}Process {self._ProcessID} - ({self._ProcessPID}) {remaining_tasks} tasks discarded.")


class TheSeedCoreConcurrencySystem:
    """
    TheSeedCore 并发系统，负责配置和管理多进程及多线程任务的执行。

    提供动态的资源管理，包括进程和线程的扩展与收缩，以及任务的优先级管理和拒绝策略。
    """
    _INSTANCE: TheSeedCoreConcurrencySystem = None
    _INITIALIZED: bool = False

    class _SetupConfig:
        """
        初始化并设置基本配置，包括进程数、线程数等。

        参数:
            - Logger: 日志记录器。
            - BaseConfig: 并发系统的基本配置。
        """

        def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], BaseConfig: ConcurrencySystemConfig):
            self.Logger = Logger
            self.CoreProcessCount = self.setCoreProcessCount(BaseConfig.CoreProcessCount)
            self.CoreThreadCount = self.setCoreThreadCount(BaseConfig.CoreThreadCount)
            self.MaximumProcessCount = self.setMaximumProcessCount(BaseConfig.MaximumProcessCount)
            self.MaximumThreadCount = self.setMaximumThreadCount(BaseConfig.MaximumThreadCount)
            self.TaskThreshold = self.setTaskThreshold(BaseConfig.TaskThreshold)
            self.GlobalTaskThreshold = self.setGlobalTaskThreshold(BaseConfig.GlobalTaskThreshold)
            self.TaskRejectionPolicy = self.setTaskRejectionPolicy(BaseConfig.TaskRejectionPolicy)
            self.RejectionPolicyTimeout = self.setRejectionPolicyTimeout(BaseConfig.RejectionPolicyTimeout)
            self.ExpandPolicy = self.setExpandPolicy(BaseConfig.ExpandPolicy)
            self.ShrinkagePolicy = self.setShrinkagePolicy(BaseConfig.ShrinkagePolicy)
            self.ShrinkagePolicyTimeout = self.setShrinkagePolicyTimeout(BaseConfig.ShrinkagePolicyTimeout)

        def setCoreProcessCount(self, core_process_count: int):
            """
            验证并设置核心进程数。

            参数:
                - core_process_count: 指定的核心进程数。
            返回:
                - 设置后的核心进程数。

            1. 如果指定的核心进程数为 None 或非整数，使用默认值 2。
            2. 如果指定的核心进程数超过物理 CPU 核心数，同样使用默认值。
            3. 如果指定的核心进程数有效且不超过 CPU 核心数，使用指定值。
            """
            default_value = 2
            if core_process_count is not None:
                if not isinstance(core_process_count, int):
                    self.Logger.warning(f"Core process count must be an integer, using default value {default_value}.\n")
                    return default_value
                if core_process_count > psutil.cpu_count(logical=False):
                    self.Logger.warning(f"Core process count must be less than or equal to the number of physical CPU cores, using default value {default_value}.")
                    return default_value
                if core_process_count > default_value:
                    return core_process_count
                if core_process_count < default_value:
                    return default_value
            self.Logger.warning(f"Core process count not set, using default value {default_value}.")
            return default_value

        def setCoreThreadCount(self, core_thread_count: int):
            """
            验证并设置核心线程数。

            参数:
                - core_thread_count: 指定的核心线程数。
            返回:
                - 设置后的核心线程数。

            1. 如果指定的核心线程数为 None 或非整数，使用默认值 4。
            2. 如果指定的核心线程数超过物理 CPU 核心数的两倍，同样使用默认值。
            3. 如果指定的核心线程数有效且不超过 CPU 核心数的两倍，使用指定值。
            """
            default_value = int(self.CoreProcessCount * 2)
            if core_thread_count is not None:
                if not isinstance(core_thread_count, int):
                    self.Logger.warning(f"Core thread count must be an integer, using default value {default_value}.")
                    return default_value
                if core_thread_count >= default_value:
                    if core_thread_count % 2 == 0:
                        return core_thread_count
                    return core_thread_count - 1
                return default_value
            self.Logger.warning(f"Core thread count not set, using default value {default_value}.")
            return default_value

        def setMaximumProcessCount(self, maximum_process_count: int):
            """
            设置最大进程数。验证数值是否合法，若不合法使用默认值。

            参数:
                - maximum_process_count: 指定的最大进程数。
            返回:
                - 整数，最大进程数。

            1. 如果指定的最大进程数为 None 或非整数，使用默认值 4。
            2. 如果指定的最大进程数超过物理 CPU 核心数，同样使用默认值。
            3. 如果指定的最大进程数有效且不超过 CPU 核心数，使用指定值。
            """
            default_value = int(self.CoreProcessCount * 2)
            if maximum_process_count is not None:
                if not isinstance(maximum_process_count, int):
                    self.Logger.warning(f"Maximum process count must be an integer, using default value: {default_value}.")
                    return default_value
                if maximum_process_count > psutil.cpu_count(logical=False):
                    self.Logger.warning(f"Maximum process count must be less than or equal to the number of physical CPU cores, using default value: {default_value}.")
                    return default_value
                return maximum_process_count
            self.Logger.warning(f"Maximum process count not set, using default value: {default_value}.")
            return default_value

        def setMaximumThreadCount(self, maximum_thread_count: int):
            """
            设置最大线程数。验证数值是否合法，若不合法使用默认值。

            参数:
                - maximum_thread_count: 指定的最大线程数。
            返回:
                - 整数，最大线程数。

            1. 如果指定的最大线程数为 None 或非整数，使用默认值 4。
            2. 如果指定的最大线程数超过核心线程数的两倍，同样使用默认值。
            3. 如果指定的最大线程数有效且不超过核心线程数的两倍，使用指定值。
            """
            default_value = int(self.CoreThreadCount * 2)
            if maximum_thread_count is not None:
                if not isinstance(maximum_thread_count, int):
                    self.Logger.warning(f"Maximum thread count must be an integer, using default value: {default_value}.")
                    return default_value
                if maximum_thread_count >= default_value:
                    if maximum_thread_count % 2 == 0:
                        return maximum_thread_count
                    return maximum_thread_count - 1
                return default_value
            self.Logger.warning(f"Maximum thread count not set, using default value: {default_value}.")
            return default_value

        def setTaskThreshold(self, task_threshold: int):
            """
            设置任务阈值。验证数值是否合法，若不合法使用默认值。

            参数:
                - task_threshold: 指定的任务阈值。
            返回:
                - 整数，任务阈值。

            1. 如果指定的任务阈值为 None 或非整数将根据系统硬件配置动态设置任务阈值。
            2. 如果指定的任务阈值有效，使用指定值。
            """
            default_value = self.calculateTaskThreshold()
            if task_threshold is not None:
                if not isinstance(task_threshold, int):
                    self.Logger.warning(f"Task threshold must be an integer, using default value: {default_value}.")
                    return default_value
                return task_threshold
            self.Logger.warning(f"Task threshold not set, using default value: {default_value}.")
            return default_value

        def setGlobalTaskThreshold(self, global_task_threshold: int):
            """
            设置全局任务阈值。验证数值是否合法，若不合法使用默认值。

            参数:
                - global_task_threshold: 指定的全局任务阈值。
            返回:
                - 整数，全局任务阈值。

            1. 如果指定的全局任务阈值为 None 或非整数，将根据系统硬件配置动态设置全局任务阈值。
            2. 如果指定的全局任务阈值有效，使用指定值。
            """
            default_value = int((self.CoreProcessCount + self.CoreThreadCount) * self.TaskThreshold)
            if global_task_threshold is not None:
                if not isinstance(global_task_threshold, int):
                    self.Logger.warning(f"Global task threshold must be an integer, using default value: {default_value}.")
                    return default_value
                return global_task_threshold
            self.Logger.warning(f"Global task threshold not set, using default value: {default_value}.")
            return default_value

        def setTaskRejectionPolicy(self, task_rejection_policy: Literal[None, "Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]) -> Literal["Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]:
            """
            设置任务拒绝策略。验证策略是否合法，若不合法使用默认策略。

            参数:
                - task_rejection_policy: 指定的任务拒绝策略。
            返回:
                - 字符串，任务拒绝策略。

            1. 如果指定的任务拒绝策略为 None 或不在合法范围内，使用默认策略: Abandonment。
            2. 如果指定的任务拒绝策略有效，使用指定策略。
            """
            if task_rejection_policy is None:
                self.Logger.warning("Task rejection policy not set, using default policy: Abandon.")
                return "Abandonment"
            if task_rejection_policy not in ["Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]:
                self.Logger.warning("Unknown task rejection policy, using default policy: Abandon.")
                return "Abandonment"
            return task_rejection_policy

        def setRejectionPolicyTimeout(self, rejection_policy_timeout: int):
            """
            设置任务拒绝策略的超时时间。验证数值是否合法，若不合法使用默认值。

            参数:
                - rejection_policy_timeout: 指定的任务拒绝策略超时时间。
            返回:
                - 整数，任务拒绝策略超时时间。

            1. 如果指定的任务拒绝策略超时时间为 None 或非整数，使用默认超时时间: 3秒。
            2. 如果指定的任务拒绝策略超时时间有效，使用指定超时时间。
            """
            if rejection_policy_timeout is None:
                self.Logger.warning("Rejection policy timeout not set, using default timeout: 3 seconds.")
                return 3
            if not isinstance(rejection_policy_timeout, int):
                self.Logger.warning("Rejection policy timeout must be an integer, using default timeout: 3 seconds.")
                return 3
            return rejection_policy_timeout

        def setExpandPolicy(self, expand_policy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"]) -> Literal["NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"]:
            """
            设置扩展策略。验证策略是否合法，若不合法使用默认策略。

            参数:
                - expand_policy: 指定的扩展策略。
            返回:
                - 字符串，扩展策略。

            1. 如果指定的扩展策略为 None 或不在合法范围内，使用默认策略: AutoExpand。
            2. 如果指定的扩展策略有效，使用指定策略。
            """
            if expand_policy is None:
                self.Logger.warning("Expand policy is not set, using default policy: AutoExpand.")
                return "AutoExpand"
            if expand_policy not in ["NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"]:
                self.Logger.warning("Unknown expand policy, using default policy: AutoExpand.")
                return "AutoExpand"
            return expand_policy

        def setShrinkagePolicy(self, shrinkage_policy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"]) -> Literal["NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"]:
            """
            设置收缩策略。验证策略是否合法，若不合法使用默认策略。

            参数:
                - shrinkage_policy: 指定的收缩策略。
            返回:
                - 字符串，收缩策略。

            1. 如果指定的收缩策略为 None 或不在合法范围内，使用默认策略: AutoShrink。
            2. 如果指定的收缩策略有效，使用指定策略。
            """
            if shrinkage_policy is None:
                self.Logger.warning("Shrinkage policy not set, using default policy: AutoShrink.")
                return "AutoShrink"
            if shrinkage_policy not in ["NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"]:
                self.Logger.warning("Unknown shrinkage policy, using default policy: AutoShrink.")
                return "AutoShrink"
            return shrinkage_policy

        def setShrinkagePolicyTimeout(self, shrinkage_policy_timeout: Union[None, int]):
            """
            设置收缩策略的超时时间。验证数值是否合法，若不合法使用默认值。

            参数:
                - shrinkage_policy_timeout: 指定的收缩策略超时时间。
            返回:
                - 整数，收缩策略超时时间。

            1. 如果指定的收缩策略超时时间为 None 或非整数，使用默认超时时间: 3秒。
            2. 如果指定的收缩策略超时时间有效，使用指定超时时间。
            """
            if shrinkage_policy_timeout is None:
                self.Logger.warning("Shrinkage policy timeout not set, using default timeout: 3 seconds.")
                return 3
            if not isinstance(shrinkage_policy_timeout, int):
                self.Logger.warning("Shrinkage policy timeout must be an integer, using default timeout: 3 seconds.")
                return 3
            return shrinkage_policy_timeout

        @staticmethod
        def calculateTaskThreshold():
            """
            计算任务阈值。

            根据系统的 CPU 核心数和内存大小计算任务阈值，用于控制任务的处理和调度。
            1. 如果物理 CPU 核心数小于 128，使用公式 (physical_cores / 128) + (total_memory / 3072) / 2 计算平衡分数。
            2. 根据平衡分数和阈值设置，返回任务阈值。
            """
            physical_cores = psutil.cpu_count(logical=False)
            total_memory = psutil.virtual_memory().total / (1024 ** 3)
            balanced_score = ((physical_cores / 128) + (total_memory / 3072)) / 2

            balanced_score_thresholds = [0.2, 0.4, 0.6, 0.8]
            task_thresholds = [20, 40, 60, 80, 90]
            for score_threshold, threshold in zip(balanced_score_thresholds, task_thresholds):
                if balanced_score <= score_threshold:
                    return threshold
            return task_thresholds[-1]

    def __new__(cls, Config: ConcurrencySystemConfig, *args, **kwargs):
        """
        实现单例模式确保并发系统全局只有一个实例。

        参数:
            - Logger: 日志记录器。
            - Config: 并发系统配置对象。
            - args, kwargs: 其他参数。
        返回:
            - 类实例。

        1. 检查是否已经存在实例，如果不存在，创建新实例。
        """
        if cls._INSTANCE is None:
            cls._INSTANCE = super(TheSeedCoreConcurrencySystem, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Config: ConcurrencySystemConfig):
        """
        初始化并发系统，设置日志、配置，并初始化管理器和队列。

        参数:
            - Logger: 日志记录器。
            - Config: 并发系统配置。

        1. 如果系统未初始化，设置系统的日志记录器和配置。
        2. 初始化共享管理器和任务队列。
        3. 启动负载均衡线程。
        4. 标记系统为已初始化。
        """
        if not self._INITIALIZED:
            self._Logger = self._setConcurrencySystemLogger(Config.DebugMode)
            self._Config = TheSeedCoreConcurrencySystem._SetupConfig(self._Logger, Config)
            self._SharedManager = multiprocessing.Manager()
            self.CallbackQueue = self._SharedManager.Queue()
            self._TaskLock = self._SharedManager.Lock()
            self._GlobalTaskQueue = queue.Queue()
            self._LoadBalancerThread = threading.Thread(target=self._loadBalancer, daemon=True)
            self._LoadBalancerThreadEvent = threading.Event()
            self._CoreProcess = {}
            self._ExpandProcess = {}
            self._ExpandProcessKeepAlive = {}
            self._AsyncCoreThread = {}
            self._SyncCoreThread = {}
            self._AsyncExpandThread = {}
            self._AsyncExpandThreadKeepAlive = {}
            self._SyncExpandThread = {}
            self._SyncExpandThreadKeepAlive = {}
            self._initConcurrencySystem()
            TheSeedCoreConcurrencySystem._INITIALIZED = True

    def submitProcessTask(self, task: callable, priority: int = 0, *args, **kwargs):
        """
        提交一个处理任务到进程队列。

        参数:
            - task: 可调用的任务。
            - priority: 任务的优先级，默认为 0。
            - args: 任务函数的位置参数。
            - kwargs: 任务函数的关键字参数。

        1. 使用 _taskParamsProcess 方法处理任务参数并创建任务对象。
        2. 调用 _taskSubmitProcess 方法将任务对象提交到全局队列。
        """
        task_object = self._taskParamsProcess(task, *args, **kwargs)
        self._taskSubmitProcess("Process", priority, task_object)

    def submitThreadTask(self, task: callable, priority: int = 0, *args, **kwargs):
        """
        提交一个处理任务到线程队列。

        参数:
            - task: 可调用的任务。
            - priority: 任务的优先级，默认为 0。
            - args: 任务函数的位置参数。
            - kwargs: 任务函数的关键字参数。

        1. 使用 _taskParamsProcess 方法处理任务参数并创建任务对象。
        2. 调用 _taskSubmitProcess 方法将任务对象提交到全局队列。
        """
        task_object = self._taskParamsProcess(task, *args, **kwargs)
        self._taskSubmitProcess("Thread", priority, task_object)

    @staticmethod
    def _taskParamsProcess(task: callable, *args, **kwargs):
        """
        处理任务参数，创建任务对象。

        参数:
            - task: 可调用的任务函数。
            - args: 任务函数的位置参数。
            - kwargs: 任务函数的关键字参数。
        返回:
            - 返回创建的任务对象，可以是 _AsyncTaskObject 或 _SyncTaskObject。

        1. 设置默认参数。
        2. 将传入的参数与默认参数合并。
        3. 根据任务函数类型（异步或同步）创建相应的任务对象。
        """
        default_values = {
            "Callback": None,
            "Lock": False,
            "MaximumLockHoldingTime": 3,
            "GpuBoost": False,
            "ReTry": False,
            "MaxRetries": 3
        }

        params_names = ["Callback", "Lock", "MaximumLockHoldingTime", "GpuBoost", "ReTry", "MaxRetries"]

        num_defined_params = min(len(args), len(params_names))
        for params in range(num_defined_params):
            default_values[params_names[params]] = args[params]

        task_args = args[num_defined_params:]

        default_values.update(kwargs)

        if asyncio.iscoroutinefunction(task):
            task_object = _AsyncTaskObject(task, *task_args, **default_values)
        else:
            task_object = _SyncTaskObject(task, *task_args, **default_values)
        return task_object

    def _taskSubmitProcess(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        将任务对象提交到全局任务队列。

        参数:
            - submit_type: 提交类型，'Process' 或 'Thread'。
            - priority: 任务的优先级。
            - task_object: 创建的任务对象。

        1. 检查全局任务队列的大小是否低于全局任务阈值。
        2. 如果低于阈值，将任务添加到队列。
        3. 如果超出阈值，调用 _executionRejectTask 方法处理任务拒绝策略。
        """
        if self._GlobalTaskQueue.qsize() < self._Config.GlobalTaskThreshold:
            self._GlobalTaskQueue.put((submit_type, priority, task_object))
            return
        self._executionRejectTask(submit_type, priority, task_object)

    def _executionRejectTask(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        执行任务拒绝策略。

        参数:
            - submit_type: 提交类型，'Process' 或 'Thread'，指示任务是进程任务还是线程任务。
            - priority: 任务的优先级。
            - task_object: 要提交的任务对象，可能是异步任务对象或同步任务对象。

        1. 根据配置中设定的拒绝策略，从 policy_method 字典中选择相应的方法。
        2. 调用选定的拒绝方法，传入提交类型、优先级和任务对象。
        3. 这些方法处理任务队列已满的情况，按照预设策略处理无法加入队列的任务。
        """
        policy_method = {
            "Abandonment": self._abandonment,
            "ExceptionAbandonment": self._exceptionAbandonment,
            "EarliestAbandonment": self._earliestAbandonment,
            "CallerExecution": self._callerExecution,
            "TimeoutAbandonment": self._timeoutAbandonment
        }
        rejection_method = policy_method[self._Config.TaskRejectionPolicy]
        rejection_method(submit_type, priority, task_object)

    def _abandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        直接放弃任务执行。

        参数:
            - submit_type: 提交类型。
            - priority: 任务优先级。
            - task_object: 任务对象。

        1. 简单记录一条日志，表明任务被放弃。
        """
        self._Logger.debug(f"The global task queue is full, abandon the {submit_type} task: {task_object.taskName()}")
        _ = priority
        del submit_type
        del priority
        del task_object

    def _exceptionAbandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        放弃任务并抛出异常。

        参数:
            - submit_type: 提交类型。
            - priority: 任务优先级。
            - task_object: 任务对象。

        1. 记录日志，并抛出异常通知调用者任务无法被执行。
        """
        msg = f"The global task queue is full, abandon the {submit_type} task: {task_object.taskName()}"
        self._Logger.debug(msg)
        _ = priority
        del priority
        raise Exception(msg)

    def _earliestAbandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: _AsyncTaskObject | _SyncTaskObject):
        """
        放弃队列中最早的任务，以便为当前任务腾出空间。

        参数:
            - submit_type: 提交类型。
            - priority: 任务优先级。
            - task_object: 任务对象。

        1. 从全局任务队列中移除最早的任务。
        2. 将当前任务添加到队列中。
        """
        self._Logger.debug(f"The global task queue is full, abandon the {submit_type} task: {task_object.taskName()}")
        self._GlobalTaskQueue.get()
        self._GlobalTaskQueue.put((submit_type, priority, task_object))

    def _callerExecution(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        当任务队列已满时，让调用者直接执行任务。

        参数:
            - submit_type: 提交类型，表示任务是进程任务还是线程任务。
            - priority: 任务的优先级。
            - task_object: 任务对象。

        1. 记录一条日志，说明任务队列已满且任务将由调用者执行。
        2. 将任务标记为“被放弃”，并放入回调队列，实际上这里的“放弃”是让调用者处理。
        3. 清理传入的优先级参数，虽然这不是必需的，但作为示例清理无用参数。
        """
        self._Logger.debug(f"The global task queue is full, caller execute the {submit_type} task: {task_object.taskName()}")
        self.CallbackQueue.put(("Rejected", task_object, None))
        _ = priority
        del priority

    def _timeoutAbandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        基于超时的任务放弃策略。如果在指定的超时期间队列空间未释放，任务将被放弃。

        参数:
            - submit_type: 提交类型，表示任务是进程任务还是线程任务。
            - priority: 任务的优先级。
            - task_object: 任务对象。

        1. 睡眠一段时间，等待超时（超时时间由配置决定）。
        2. 超时后检查全局任务队列是否有空间：
            2.1 如果有空间，将任务重新放入队列。
            2.2 如果没有空间，记录一条日志并放弃任务，清理相关参数。
        """
        time.sleep(self._Config.RejectionPolicyTimeout)
        if self._GlobalTaskQueue.qsize() < self._Config.GlobalTaskThreshold:
            self._GlobalTaskQueue.put((submit_type, priority, task_object))
        else:
            self._Logger.debug(f"The global task queue is full, abandon the {submit_type} task: {task_object.taskName()}")
            del submit_type
            del priority
            del task_object

    def _initConcurrencySystem(self):
        """
        初始化并发系统的核心组件。


        1. 使用线程池来并发地启动所有配置中指定的核心进程和一半的核心线程。
        2. 核心进程和核心线程的数量由配置对象 (_Config) 提供。
        3. 启动一个负载均衡器线程，该线程负责监视和调整任务分配，确保系统运行效率。
        """
        with ThreadPoolExecutor(max_workers=self._Config.CoreProcessCount + self._Config.CoreThreadCount) as executor:
            for process_id in range(self._Config.CoreProcessCount):
                executor.submit(self._startProcess, process_id)
            for thread_id in range(self._Config.CoreThreadCount // 2):
                executor.submit(self._startThread, thread_id)
        self._LoadBalancerThread.start()

    def _startProcess(self, process_id: int):
        """
        启动一个核心进程。

        参数:
            - process_id: 进程的标识符，用于跟踪和管理进程。

        1. 创建一个进程对象，配置其日志、进程ID、任务阈值、回调队列和任务锁。
        2. 启动进程。
        3. 将启动的进程存储在核心进程字典中，以便于管理和监控。
        """
        process = _ProcessObject(self._Logger, process_id, "Core", self._Config.TaskThreshold, self.CallbackQueue, self._TaskLock)
        process.startProcess()
        self._CoreProcess[process_id] = process

    def _startThread(self, thread_id: int):
        """
        同时启动一个异步线程和一个同步线程。

        参数:
            - thread_id: 线程的标识符，用于跟踪和管理线程。

        1. 创建一个异步线程对象和一个同步线程对象，配置它们的日志、线程ID、回调队列和任务锁。
        2. 启动这两个线程。
        3. 将启动的线程分别存储在异步和同步核心线程字典中，以便于管理和监控。
        4. 记录日志信息，确认线程已成功启动。
        """
        async_thread = _AsyncThreadObject(self._Logger, thread_id, self.CallbackQueue, self._TaskLock)
        sync_thread = _SyncThreadObject(self._Logger, thread_id, self.CallbackQueue, self._TaskLock)
        async_thread.startThread()
        sync_thread.startThread()
        self._AsyncCoreThread[thread_id] = async_thread
        self._SyncCoreThread[thread_id] = sync_thread
        self._Logger.debug(f"CoreAsyncThread {thread_id} has been started.")
        self._Logger.debug(f"CoreSyncThread {thread_id} has been started.")

    def closeConcurrencySystem(self):
        """
        关闭并发系统，确保所有资源被适当地清理。

        1. 触发负载均衡器线程的结束事件。
        2. 等待负载均衡器线程结束。
        3. 使用线程池并发关闭所有核心和扩展的进程及线程。
        4. 对每个关闭的线程记录日志，确认它们已经被关闭。
        """
        self._LoadBalancerThreadEvent.set()
        if self._LoadBalancerThread.is_alive():
            self._LoadBalancerThread.join()
        with ThreadPoolExecutor() as executor:
            for process in self._CoreProcess.values():
                executor.submit(self._closeProcesses, process)
            for process in self._ExpandProcess.values():
                executor.submit(self._closeProcesses, process)
            for thread in self._AsyncCoreThread.values():
                executor.submit(self._closeThreads, thread)
                self._Logger.debug(f"CoreAsyncThread {thread.threadID()} has been closed.")
            for thread in self._AsyncExpandThread.values():
                executor.submit(self._closeThreads, thread)
                self._Logger.debug(f"ExpandAsyncThread {thread.threadID()} has been closed.")
            for thread in self._SyncCoreThread.values():
                executor.submit(self._closeThreads, thread)
                self._Logger.debug(f"CoreSyncThread {thread.threadID()} has been closed.")
            for thread in self._SyncExpandThread.values():
                executor.submit(self._closeThreads, thread)
                self._Logger.debug(f"ExpandSyncThread {thread.threadID()} has been closed.")

    @staticmethod
    def _closeProcesses(process: _ProcessObject):
        """
        关闭单个进程。

        参数:
            - process: 要关闭的进程对象。

        1. 调用进程的关闭方法，确保进程资源被适当释放。
        """
        process.closeProcess()

    @staticmethod
    def _closeThreads(thread: Union[_AsyncThreadObject, _SyncThreadObject]):
        """
        关闭单个线程。

        参数:
            - thread: 要关闭的线程对象。

        1. 调用线程的关闭方法，确保线程安全地停止并释放资源。
        """
        thread.closeThread()

    @staticmethod
    def _setConcurrencySystemLogger(debug_mode: bool = False) -> logging.Logger:
        logger = logging.getLogger('TheSeedCoreConcurrencySystem')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if debug_mode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        return logger

    def _loadBalancer(self):
        """
        负责系统中的负载均衡，动态调整资源分配。

        1. 持续监听负载均衡线程事件，直至设置为关闭。
        2. 执行资源扩展策略。
        3. 执行资源收缩策略。
        4. 清理垃圾，释放未被引用的内存。
        5. 尝试从全局任务队列中获取任务，如果超时则继续。
        6. 根据任务类型分配任务到相应的处理队列。
        """
        while not self._LoadBalancerThreadEvent.is_set():
            gc.collect()
            self._executionExpandPolicy()
            self._executionShrinkagePolicy()
            try:
                item: tuple[Literal["Process", "Thread"], int, _AsyncTaskObject | _SyncTaskObject] = self._GlobalTaskQueue.get(block=True, timeout=0.1)
            except queue.Empty:
                continue
            submit_type, priority, task_object = item
            if submit_type == "Process":
                self._processTaskAllocation(priority, task_object)
                continue
            if submit_type == "Thread":
                self._threadTaskAllocation(priority, task_object)
                continue

    def _executionExpandPolicy(self):
        """
        执行资源扩展策略。

        1. 根据配置选择适当地扩展策略。
        2. 调用选定的策略方法来增加进程或线程资源。
        """
        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self._Config.ExpandPolicy]
        expand_method()

    def _noExpand(self):
        pass

    def _autoExpand(self):
        """
        根据系统当前负载自动扩展资源。

        1. 计算核心进程和线程的平均负载。
        2. 如果平均负载超过预设阈值（80%），检查是否允许扩展。
        3. 若允许，则进行相应的进程或线程扩展。
        """
        core_process_obj = [obj for index, obj in self._CoreProcess.items()]
        core_async_threads_obj = [obj for index, obj in self._AsyncCoreThread.items()]
        core_sync_threads_obj = [obj for index, obj in self._SyncCoreThread.items()]

        current_core_process_total_load = sum([obj.getCurrentProcessLoad() for obj in core_process_obj])
        current_core_async_thread_total_load = sum([obj.getThreadTaskCount() for obj in core_async_threads_obj])
        current_core_sync_thread_total_load = sum([obj.getThreadTaskCount() for obj in core_sync_threads_obj])

        process_average_load = current_core_process_total_load / len(core_process_obj) if core_process_obj else 0
        async_thread_average_load = current_core_async_thread_total_load / len(core_async_threads_obj) if core_async_threads_obj else 0
        sync_thread_average_load = current_core_sync_thread_total_load / len(core_sync_threads_obj) if core_sync_threads_obj else 0

        ideal_load_per_process = 100 * 0.8
        ideal_load_per_thread = 100 * 0.8
        if process_average_load > ideal_load_per_process:
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more process")

        if async_thread_average_load > ideal_load_per_thread:
            if self._isExpansionAllowed("Thread"):
                self._expandThread("Async")
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more async thread")

        if sync_thread_average_load > ideal_load_per_thread:
            if self._isExpansionAllowed("Thread"):
                self._expandThread("Sync")
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more sync thread")

    def _beforehandExpand(self):
        """
        如果全局任务队列的大小达到阈值的80%，提前扩展资源。

        1. 检查全局任务队列的大小是否达到设置的阈值的80%。
        2. 如果达到，首先检查是否允许扩展进程。
        3. 如果允许扩展进程，则执行进程扩展。
        4. 同理，检查并执行线程的扩展。
        5. 如果不允许扩展，记录日志。
        """
        if self._GlobalTaskQueue.qsize() >= int(self._Config.GlobalTaskThreshold * 0.8):
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more process")
            if self._isExpansionAllowed("Thread"):
                self._expandThread("Async")
                self._expandThread("Sync")
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more thread")

    def _isExpansionAllowed(self, expand_type: Literal["Process", "Thread"]):
        """
        根据当前进程或线程的数量判断是否允许扩展。

        1. 根据传入的类型（进程或线程）进行判断。
        2. 如果当前活跃的进程或线程数已达到配置的最大值，不允许扩展。
        3. 返回是否允许扩展的布尔值。
        """
        match expand_type:
            case "Process":
                if (len(self._CoreProcess) + len(self._ExpandProcess)) >= self._Config.MaximumProcessCount:
                    return False
                return True
            case "Thread":
                if (len(self._AsyncCoreThread) + len(self._AsyncExpandThread) + len(self._SyncCoreThread) + len(self._SyncExpandThread)) - self._Config.MaximumThreadCount == 2:
                    return False
                return True

    def _expandProcess(self):
        """
        扩展一个新的进程。

        1. 生成一个新的进程ID。
        2. 创建并启动一个新的进程对象。
        3. 将新进程记录在扩展进程的字典中，包括其活跃时间。
        """
        current_time = time.time()
        process_id = self._generateExpandID("Process")
        process = _ProcessObject(self._Logger, process_id, "Expand", self._Config.TaskThreshold, self.CallbackQueue, self._TaskLock)
        process.startProcess()
        self._ExpandProcess[process_id] = process
        self._ExpandProcessKeepAlive[process] = current_time

    def _expandThread(self, thread_type: Literal["Async", "Sync"]):
        """
        扩展一个新的线程，可以是异步或同步类型。

        1. 生成一个新的线程ID。
        2. 根据指定的类型创建并启动线程。
        3. 将新线程记录在扩展线程的字典中，包括其活跃时间。
        """
        current_time = time.time()
        thread_id = self._generateExpandID(thread_type)
        if thread_type == "Async":
            thread = _AsyncThreadObject(self._Logger, thread_id, self.CallbackQueue, self._TaskLock)
            thread.startThread()
            self._AsyncExpandThread[thread_id] = thread
            self._AsyncExpandThreadKeepAlive[thread] = current_time
            return
        if thread_type == "Sync":
            thread = _SyncThreadObject(self._Logger, thread_id, self.CallbackQueue, self._TaskLock)
            thread.startThread()
            self._SyncExpandThread[thread_id] = thread
            self._SyncExpandThreadKeepAlive[thread] = current_time
            return

    def _generateExpandID(self, expand_type: Literal["Process", "Async", "Sync"]):
        """
        生成一个独特的扩展ID，避免冲突。

        1. 检查给定类型的当前ID映射。
        2. 循环直到找到一个未使用的ID。
        3. 返回新的ID。
        """
        expand_type_mapping = {
            "Process": self._ExpandProcess,
            "Async": self._AsyncExpandThread,
            "Sync": self._SyncExpandThread
        }
        basic_id = 0
        while True:
            if basic_id not in expand_type_mapping[expand_type]:
                return basic_id
            basic_id += 1

    def _executionShrinkagePolicy(self):
        """
        根据配置的收缩政策执行资源收缩。

        1. 根据配置选择适当的资源收缩策略。
        2. 调用选定的策略方法进行资源收缩。
        """
        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self._Config.ShrinkagePolicy]
        shrink_method()

    def _noShrink(self):
        pass

    def _autoShrink(self):
        """
        自动收缩未使用的资源。

        1. 遍历所有扩展的进程和线程。
        2. 检查是否有闲置的资源（没有正在处理的任务）。
        3. 如果这些资源已经超过了设定的超时时间，进行关闭并从系统中移除。
        """
        expand_process_obj = [obj for index, obj in self._ExpandProcess.items()]
        expand_async_threads_obj = [obj for index, obj in self._AsyncExpandThread.items()]
        expand_sync_threads_obj = [obj for index, obj in self._SyncExpandThread.items()]

        idle_process = [obj for obj in expand_process_obj if obj.getProcessTaskCount() == 0]
        idle_async_threads = [obj for obj in expand_async_threads_obj if obj.getThreadTaskCount() == 0]
        idle_sync_threads = [obj for obj in expand_sync_threads_obj if obj.getThreadTaskCount() == 0]

        allow_closed_processes = [obj for obj in self._ExpandProcessKeepAlive if time.time() - self._ExpandProcessKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]
        allow_closed_async_threads = [obj for obj in self._AsyncExpandThreadKeepAlive if time.time() - self._AsyncExpandThreadKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]
        allow_closed_sync_threads = [obj for obj in self._SyncExpandThreadKeepAlive if time.time() - self._SyncExpandThreadKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]

        if idle_process:
            for process in idle_process:
                if process in allow_closed_processes:
                    process.closeProcess()
                    del self._ExpandProcess[process.processID()]
                    del self._ExpandProcessKeepAlive[process]

        if idle_async_threads:
            for thread in idle_async_threads:
                if thread in allow_closed_async_threads:
                    thread.closeThread()
                    del self._AsyncExpandThread[thread.threadID()]
                    del self._AsyncExpandThreadKeepAlive[thread]

        if idle_sync_threads:
            for thread in idle_sync_threads:
                if thread in allow_closed_sync_threads:
                    thread.closeThread()
                    del self._SyncExpandThread[thread.threadID()]
                    del self._SyncExpandThreadKeepAlive[thread]

    def _timeoutShrink(self):
        """
        根据超时设置收缩资源。

        1. 检查所有扩展的进程和线程，确定它们是否已经达到了超时阈值。
        2. 对于超时的资源，进行关闭并从系统中移除。
        """
        expand_process_obj = [obj for obj, keep_alive in self._ExpandProcessKeepAlive.items() if time.time() - keep_alive >= self._Config.ShrinkagePolicyTimeout]
        expand_async_threads_obj = [obj for obj, keep_alive in self._AsyncExpandThreadKeepAlive.items() if time.time() - keep_alive >= self._Config.ShrinkagePolicyTimeout]
        expand_sync_threads_obj = [obj for obj, keep_alive in self._SyncExpandThreadKeepAlive.items() if time.time() - keep_alive >= self._Config.ShrinkagePolicyTimeout]

        if expand_process_obj:
            for process in expand_process_obj:
                process.closeProcess()
                del self._ExpandProcess[process.processID()]
                del self._ExpandProcessKeepAlive[process]

        if expand_async_threads_obj:
            for thread in expand_async_threads_obj:
                thread.closeThread()
                del self._AsyncExpandThread[thread.threadID()]
                del self._AsyncExpandThreadKeepAlive[thread]

        if expand_sync_threads_obj:
            for thread in expand_sync_threads_obj:
                thread.closeThread()
                del self._SyncExpandThread[thread.threadID()]
                del self._SyncExpandThreadKeepAlive[thread]

    def _processTaskAllocation(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        分配任务到进程。

        1. 首先检查核心进程是否有空闲。
        2. 如果没有空闲的核心进程，检查扩展进程。
        3. 如果扩展进程也满载，将任务放回全局任务队列。
        4. 在空闲的进程中，选择负载最低的进程分配任务。
        """
        idle_core_process = [obj for index, obj in self._CoreProcess.items() if obj.getProcessTaskCount() != self._Config.TaskThreshold]
        if not idle_core_process:
            if self._ExpandProcess:
                idle_expand_process = [obj for index, obj in self._ExpandProcess.items() if obj.getProcessTaskCount() != self._Config.TaskThreshold]
                if not idle_expand_process:
                    self._GlobalTaskQueue.put(("Process", priority, task_object))
                    return
                if len(idle_expand_process) > 1:
                    minimum_load_expand_process = min(idle_expand_process, key=lambda x: x.getCurrentProcessLoad())
                    minimum_load_expand_process.addProcessTask(priority, task_object)
                    return
                idle_expand_process[0].addProcessTask(priority, task_object)
                return
            self._GlobalTaskQueue.put(("Process", priority, task_object))
            return
        if len(idle_core_process) > 1:
            minimum_load_core_process = min(idle_core_process, key=lambda x: x.getCurrentProcessLoad())
            minimum_load_core_process.addProcessTask(priority, task_object)
            return
        idle_core_process[0].addProcessTask(priority, task_object)
        return

    def _threadTaskAllocation(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        分配任务到线程。

        1. 确定任务类型（异步或同步）并选择相应的线程池。
        2. 检查核心线程是否有空闲。
        3. 如果核心线程满载，检查扩展线程。
        4. 如果扩展线程也满载，将任务放回全局任务队列。
        5. 在空闲的线程中，选择负载最低的线程分配任务。
        """
        task_type = "Async" if asyncio.iscoroutinefunction(task_object.execute) else "Sync"
        core_thread_pool = self._AsyncCoreThread if task_type == "Async" else self._SyncCoreThread
        idle_core_thread = [obj for index, obj in core_thread_pool.items() if obj.getThreadTaskCount() != self._Config.TaskThreshold]
        if not idle_core_thread:
            expand_thread_pool = self._AsyncExpandThread if task_type == "Async" else self._SyncExpandThread
            if expand_thread_pool:
                idle_expand_thread = [obj for index, obj in expand_thread_pool.items() if obj.getThreadTaskCount() != self._Config.TaskThreshold]
                if not idle_expand_thread:
                    self._GlobalTaskQueue.put(("Thread", priority, task_object))
                    return
                if len(idle_expand_thread) > 1:
                    minimum_load_expand_thread = min(idle_expand_thread, key=lambda x: x.getThreadTaskCount())
                    minimum_load_expand_thread.addThreadTask(priority, task_object)
                    return
                idle_expand_thread[0].addThreadTask(priority, task_object)
                return
            self._GlobalTaskQueue.put(("Thread", priority, task_object))
            return
        if len(idle_core_thread) > 1:
            minimum_load_core_thread = min(idle_core_thread, key=lambda x: x.getThreadTaskCount())
            minimum_load_core_thread.addThreadTask(priority, task_object)
            return
        idle_core_thread[0].addThreadTask(priority, task_object)
        return
