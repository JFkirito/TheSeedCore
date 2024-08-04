# -*- coding: utf-8 -*-
"""
TheSeedCore Concurrent System Module

Module Description:
This module implements a concurrent system for executing asynchronous and synchronous tasks in a multiprocess and multithreaded environment.
The system provides efficient task management and execution capabilities by dynamically adjusting the number of processes and threads, as well as task priority and scheduling policies.
The module supports retry mechanisms for asynchronous tasks and integrates GPU acceleration features.

Main Components:
1. Dependency Check and Import: Checks and imports necessary modules and libraries such as PyTorch, Qt, etc.
2. Callback Executor: Implements a callback executor based on the Qt event loop to handle task results and invoke corresponding callback functions.
3. Task Objects: Defines the basic structure of asynchronous and synchronous tasks, including task execution and result handling logic.
4. Thread Objects: Implements task processing logic for asynchronous and synchronous threads, including task queue management and task execution.
5. Process Objects: Manages task scheduling and execution in a multiprocess environment, including process start, shutdown, priority setting, and memory cleanup.
6. Concurrent System Configuration: Defines configuration parameters for the concurrent system, including the number of processes, threads, task thresholds, and priorities.
7. Core Concurrent System: Implements the core logic of the concurrent system, including initialization, configuration loading, and task management.

Module Functionality Overview:
- Dynamically adjusts the number of processes and threads to accommodate varying task loads.
- Supports retry mechanisms for asynchronous tasks, ensuring tasks can be re-executed upon failure.
- Integrates GPU acceleration to improve task execution efficiency.
- Provides detailed logging and error handling mechanisms for debugging and maintenance.
- Supports various task scheduling strategies and priority settings to optimize task management and resource utilization.

Key Classes and Methods:
- _checkDependencies(): Checks and imports module dependencies.
- _CallbackExecutorBase: Base class for a Qt event loop-based callback executor.
- _CoreCallbackExecutor: Core callback executor that manages asynchronous task execution and callbacks.
- _BaseTaskObject: Base class defining the basic structure of asynchronous and synchronous tasks.
- _AsyncTaskObject: Asynchronous task object, includes execution and retry logic for asynchronous tasks.
- _SyncTaskObject: Synchronous task object, includes execution and retry logic for synchronous tasks.
- _BaseThreadObject: Base class implementing task processing logic for asynchronous and synchronous threads.
- _AsyncThreadObject: Asynchronous thread object responsible for processing and executing asynchronous tasks.
- _SyncThreadObject: Synchronous thread object responsible for processing and executing synchronous tasks.
- _ProcessObject: Process object that manages task scheduling and execution in a multiprocess environment.
- ConcurrentSystemConfig: Data class for configuring concurrent system parameters.
- TheSeedCoreConcurrentSystem: Core of the concurrent system, includes initialization, configuration loading, and task management.

Notes:
- Various task scheduling and resource management strategies are used in the module. Adjust configurations according to the actual application scenario.
- To ensure the proper functioning of the module, avoid starting multiple instances of the concurrent system in the same environment.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import multiprocessing
import pickle
import queue
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import count
from typing import TYPE_CHECKING, Union, Any, Literal

import psutil
from colorama import init

from . import MainEventLoop, _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

_PyTorchSupport: bool = False
_AvailableCUDADevicesID: list = []
_PySide6Support: bool = False
_PyQt6Support: bool = False
_PyQt5Support: bool = False


def _checkDependencies():
    """
    检查并导入模块依赖项

    参数:
        :param 无
    返回:
        :return: 无返回值
    执行过程:
        1. 检查PyTorch库是否可用，如果可用则检查CUDA设备是否可用
        2. 检查PySide6库是否可用
    """
    global _PyTorchSupport, _AvailableCUDADevicesID, _PySide6Support, _PyQt6Support, _PyQt5Support
    try:
        # noinspection PyUnresolvedReferences
        import torch

        if torch.cuda.is_available():
            _AvailableCUDADevicesID = [cuda_device_id for cuda_device_id in range(torch.cuda.device_count())]
            _PyTorchSupport = True
        else:
            _AvailableCUDADevicesID = []
            _PyTorchSupport = False
    except ImportError as _:
        _AvailableCUDADevicesID = []
        _PyTorchSupport = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PySide6.QtWidgets import QApplication

        _PySide6Support = True
    except ImportError as _:
        _PySide6Support = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt6.QtWidgets import QApplication
        _PyQt6Support = True
    except ImportError as _:
        _PyQt6Support = False

    try:
        # noinspection PyUnresolvedReferences
        import qasync
        # noinspection PyUnresolvedReferences
        from PyQt5.QtWidgets import QApplication
        _PyQt5Support = True
    except ImportError as _:
        _PyQt5Support = False


_checkDependencies()

if _PyTorchSupport:
    # noinspection PyUnresolvedReferences
    import torch
if _PySide6Support:
    # noinspection PyUnresolvedReferences
    from PySide6.QtCore import QObject, Signal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PySide6.QtWidgets import QApplication
elif _PyQt6Support:
    # noinspection PyUnresolvedReferences
    from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PyQt6.QtWidgets import QApplication
elif _PyQt5Support:
    # noinspection PyUnresolvedReferences
    from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
    # noinspection PyUnresolvedReferences
    from PyQt5.QtWidgets import QApplication
else:
    QThread = None
    QApplication = None
if QThread and QApplication:
    # noinspection PyUnresolvedReferences
    import qasync


    class _CallbackExecutorBase(QThread):
        def __init__(self, TaskResultQueue: multiprocessing.Queue, parent=None):
            super().__init__(parent)
            self.TaskResultQueue = TaskResultQueue
            self.CallbackFunctionDict = {}
            self.CloseEvent = threading.Event()

        def startExecutor(self):
            """启动回调执行器"""
            self.start()

        def closeExecutor(self):
            """关闭回调执行器"""
            self.CloseEvent.set()
            self.wait()

        def addCallbackFunction(self, task_id: str, callback: callable):
            """
            为指定的任务ID添加回调函数

            参数:
                :param task_id: 任务的唯一标识符
                :param callback: 在任务完成后要执行的回调函数
            返回:
                :return: 无返回值
            执行过程:
                1. 将回调函数与任务ID关联，并存储在CallbackFunctionDict字典中
            """
            self.CallbackFunctionDict[task_id] = callback

        @qasync.asyncSlot(tuple)
        async def callbackExecutor(self, callback_data: tuple):
            """
            异步槽函数，用于处理任务结果并调用相应的回调函数

            参数:
                :param callback_data: 包含回调对象和任务结果的元组
            返回:
                :return: 无返回值
            执行过程:
                1. 从callback_data中解包回调对象和任务结果
                2. 检查回调对象是否为异步函数
                3. 如果是异步函数，则使用await调用回调，并传递任务结果
                4. 如果不是异步函数，则直接调用回调函数并传递任务结果
            """
            callback_object, task_result = callback_data
            if asyncio.iscoroutinefunction(callback_object):
                await callback_object(task_result)
                return
            callback_object(task_result)

        def run(self):
            """
            执行回调处理任务的主循环

            参数:
                :param 无
            返回:
                :return: 无返回值
            执行过程:
                1. 检查关闭事件标志是否已设置，如果未设置则继续处理
                2. 初始化空任务列表和开始时间
                3. 在0.5秒内尝试从任务结果队列中获取任务结果和任务ID
                4. 如果队列为空，等待短时间后继续尝试获取
                5. 收集到任务结果后，从回调字典中获取对应的回调函数
                6. 通过信号触发方式执行回调函数并传递任务结果
                7. 删除已执行回调的任务ID对应的回调函数
            """
            while not self.CloseEvent.is_set():
                tasks = []
                start_time = time.time()
                while (time.time() - start_time) < 0.5:
                    try:
                        callback_data = self.TaskResultQueue.get_nowait()
                        task_result, task_id = callback_data
                        tasks.append((task_result, task_id))
                    except queue.Empty:
                        time.sleep(0.005)
                        continue
                for task_result, task_id in tasks:
                    callback_object = self.CallbackFunctionDict[task_id]
                    # noinspection PyUnresolvedReferences
                    self.ExecuteSignal.emit((callback_object, task_result))
                    del self.CallbackFunctionDict[task_id]


    if _PySide6Support:
        class _PySide6CallbackExecutor(_CallbackExecutorBase):
            ExecuteSignal = Signal(tuple)

            def __init__(self, TaskResultQueue: multiprocessing.Queue, parent=None):
                super().__init__(TaskResultQueue, parent)
                self.ExecuteSignal.connect(self.callbackExecutor)

    if _PyQt6Support:
        class _PyQt6CallbackExecutor(_CallbackExecutorBase):
            ExecuteSignal = pyqtSignal(tuple)

            def __init__(self, TaskResultQueue: multiprocessing.Queue, parent=None):
                super().__init__(TaskResultQueue, parent)
                # noinspection PyUnresolvedReferences
                self.ExecuteSignal.connect(self.callbackExecutor)

    if _PyQt5Support:
        class _PyQt5CallbackExecutor(_CallbackExecutorBase):
            ExecuteSignal = pyqtSignal(tuple)

            def __init__(self, TaskResultQueue: multiprocessing.Queue, parent=None):
                super().__init__(TaskResultQueue, parent)
                # noinspection PyUnresolvedReferences
                self.ExecuteSignal.connect(self.callbackExecutor)


class _CoreCallbackExecutor:
    def __init__(self, TaskResultQueue: multiprocessing.Queue):
        self.TaskResultQueue = TaskResultQueue
        self.CallbackFunctionDict = {}
        self.CloseEvent = threading.Event()
        self.AllowExit = False
        self.PhysicalCpuCore = psutil.cpu_count(logical=True)
        self.ConcurrentExecutor = ThreadPoolExecutor(int(self.PhysicalCpuCore // 4))

    def startExecutor(self):
        MainEventLoop.create_task(self.callbackExecutor())

    def closeExecutor(self):
        """
        关闭当前线程及其相关资源

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 设置关闭事件标志，通知线程应关闭
            2. 等待线程完全终止
            2. 关闭并终止所有在并发执行器中运行的线程
        """
        self.CloseEvent.set()
        while self.AllowExit:
            break
        self.ConcurrentExecutor.shutdown()

    def addCallbackFunction(self, task_id: str, callback: callable):
        """
        为指定的任务ID添加回调函数

        参数:
            :param task_id: 任务的唯一标识符
            :param callback: 在任务完成后要执行的回调函数
        返回:
            :return: 无返回值
        执行过程:
            1. 检查回调函数是否可调用，如果不可调用则抛出异常
            2. 将回调函数与任务ID关联，并存储在CallbackFunctionDict字典中
        """
        if not callable(callback):
            raise ValueError(f"The callback for task_id {task_id} is not callable.")
        self.CallbackFunctionDict[task_id] = callback

    async def callbackExecutor(self):
        """
        异步回调执行器，用于处理任务结果并调用相应的回调函数

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 检查关闭事件标志是否已设置，如果未设置则继续处理
            2. 初始化空任务列表和开始时间
            3. 在0.5秒内尝试从任务结果队列中获取任务结果和任务ID
            4. 如果队列为空，等待短时间后继续尝试获取
            5. 收集到任务结果后，使用异步方式调用对应的回调函数执行任务
        """
        while not self.CloseEvent.is_set():
            tasks = []
            start_time = time.time()
            while (time.time() - start_time) < 0.5:
                try:
                    callback_data = self.TaskResultQueue.get_nowait()
                    task_result, task_id = callback_data
                    tasks.append((task_result, task_id))
                except queue.Empty:
                    await asyncio.sleep(0.005)
                    continue
            if tasks:
                await asyncio.gather(*[self._executeCallback(task_id, task_result) for task_result, task_id in tasks])
        self.AllowExit = True

    async def _executeCallback(self, task_id: str, task_result: Any):
        """
        执行指定任务ID的回调函数

        参数:
            :param task_id: 任务的唯一标识符
            :param task_result: 任务执行的结果数据
        返回:
            :return: 无返回值
        执行过程:
            1. 根据任务ID从CallbackFunctionDict中获取回调对象
            2. 如果未找到对应的回调对象，则直接返回
            3. 检查回调对象是否为异步函数
            4. 如果是异步函数，则使用await调用回调
            5. 如果是同步函数，则获取当前运行的事件循环，在并发执行器中执行回调
        """
        callback_object = self.CallbackFunctionDict.get(task_id)
        if callback_object is None:
            return
        if asyncio.iscoroutinefunction(callback_object):
            MainEventLoop.create_task(callback_object(task_result))
        else:
            await MainEventLoop.run_in_executor(self.ConcurrentExecutor, callback_object, task_result)


class TaskSerializationProcessor:
    def __init__(self):
        self._UnserializableAttrs = {}

    def getState(self, obj):
        state = obj.__dict__.copy()
        self._UnserializableAttrs = {}
        for key, value in state.items():
            try:
                pickle.dumps(value)
            except Exception as _:  # noqa
                self._UnserializableAttrs[key] = type(value).__name__
                state[key] = f"<Unserializable: {type(value).__name__}>"
            state['_UnserializableAttrs'] = self._UnserializableAttrs
            return state

    def setState(self, obj, state):
        obj.__dict__.update(state)
        self._UnserializableAttrs = state.get('_UnserializableAttrs', {})
        for key, type_name in self._UnserializableAttrs.items():
            obj.__dict__[key] = self.restoreUnserializableAttr(key, type_name)

    def restoreUnserializableAttr(self, key, type_name):
        raise NotImplementedError("This method must be implemented be subclasses.")


class _BaseTaskObject:
    def __init__(self, Task: callable, TaskID: str, SerializationProcessor: TaskSerializationProcessor = None, IsCallback: bool = False, IsLock: bool = False, LockHoldingTime: int = 3, IsGpuBoost: bool = False, GpuID: int = 0, IsReTry: bool = False, MaxRetries: int = 3, *args, **kwargs):
        self.Task = Task
        self.TaskID = TaskID
        self.SerializationProcessor = SerializationProcessor
        self.IsCallback = IsCallback
        self.IsLock = IsLock
        self.LockHoldingTime = LockHoldingTime
        self.IsGpuBoost = IsGpuBoost
        self.GpuID = GpuID
        self.IsReTry = IsReTry
        self.MaxRetries = MaxRetries
        self.Args = args
        self.Kwargs = kwargs
        self.Retries = 0
        self.adjustGpuBoostParams()

    def __getstate__(self):
        if self.SerializationProcessor:
            return self.SerializationProcessor.getState(self)
        else:
            state = self.__dict__.copy()
            return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if "_UnserializableAttrs" in state:
            if self.SerializationProcessor:
                self.SerializationProcessor.setState(self, state)
        self.adjustGpuBoostParams()

    def adjustGpuBoostParams(self):
        """
        调整GPU加速参数

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 检查是否启用了GPU加速功能
            2. 如果启用了GPU加速，并且PyTorch支持，则进一步检查GPU设备ID是否在可用设备列表中
            3. 如果GPU设备ID无效，则将其重置为0
            4. 准备GPU加速所需的参数
            5. 如果未启用PyTorch支持，禁用GPU加速功能
        """
        if self.IsGpuBoost:
            if _PyTorchSupport:
                if self.GpuID not in _AvailableCUDADevicesID:
                    self.GpuID = 0
                self.Args, self.Kwargs = self.prepareGpuBoostParams()
            else:
                self.IsGpuBoost = False

    def prepareGpuBoostParams(self):
        """
        准备用于GPU加速的参数

        参数:
            :param 无
        返回:
            :return: 返回处理后的args和kwargs，适用于指定的GPU设备
        执行过程:
            1. 创建指定GPU设备的torch.device对象
            2. 递归检查并转换args中的所有参数，使其适用于GPU设备
            3. 递归检查并转换kwargs中的所有参数，使其适用于GPU设备
            4. 返回转换后的args和kwargs
        """
        device = torch.device(f"cuda:{self.GpuID}")
        args = [self.recursivelyCheckGpuBoostParams(arg, device) for arg in self.Args]
        kwargs = {key: self.recursivelyCheckGpuBoostParams(value, device) for key, value in self.Kwargs.items()}
        return args, kwargs

    def recursivelyCheckGpuBoostParams(self, obj, device):
        """
        递归地检查并转换对象以支持GPU加速

        参数:
            :param obj: 要检查和转换的对象，可以是Tensor、Module、dict、list、tuple等
            :param device: 目标GPU设备的torch.device对象
        返回:
            :return: 转换后的对象，使其适用于指定的GPU设备
        执行过程:
            1. 如果对象是torch.Tensor类型，将其转移到指定的GPU设备
            2. 如果对象是torch.nn.Module类型，将其转移到指定的GPU设备
            3. 如果对象是字典，递归检查字典中的每个值
            4. 如果对象是列表，递归检查列表中的每个元素
            5. 如果对象是元组，递归检查元组中的每个元素
            6. 如果对象不是以上类型，直接返回对象本身
        """
        if isinstance(obj, torch.Tensor):
            return obj.to(device)
        if isinstance(obj, torch.nn.Module):
            return obj.to(device)
        if isinstance(obj, dict):
            return {key: self.recursivelyCheckGpuBoostParams(value, device) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self.recursivelyCheckGpuBoostParams(value, device) for value in obj]
        if isinstance(obj, tuple):
            return (self.recursivelyCheckGpuBoostParams(value, device) for value in obj)
        return obj

    @staticmethod
    def cleanupGpuResources():
        """
        清理GPU资源

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 调用torch.cuda.synchronize()确保所有GPU任务完成
            2. 调用torch.cuda.empty_cache()释放未使用的GPU内存
        """
        torch.cuda.synchronize()
        torch.cuda.empty_cache()

    def taskExecute(self):
        """任务执行方法，必须由子类实现"""
        raise NotImplementedError(f"This method must be implemented by subclasses.")

    def processResult(self, task_result):
        """
        处理任务结果，特别是处理GPU加速情况下的结果数据

        参数:
            :param task_result: 任务执行的结果数据
        返回:
            :return: 如果使用了GPU加速，将结果转换为CPU格式后返回；否则直接返回原结果
        执行过程:
            1. 检查是否启用了GPU加速，并且任务结果是否为torch.Tensor或torch.nn.Module类型
            2. 如果满足条件，克隆并分离任务结果，将其转换为CPU格式
            3. 删除原始的GPU结果以释放内存
            4. 清理GPU资源
            5. 返回转换后的CPU结果
            6. 如果未使用GPU加速，直接返回原始任务结果
        """
        if self.IsGpuBoost and isinstance(task_result, (torch.Tensor, torch.nn.Module)):
            cpu_result = task_result.clone().detach().cpu()
            del task_result
            self.cleanupGpuResources()
            return cpu_result
        return task_result

    async def asyncRetryExecution(self):
        """
        异步任务的重试执行逻辑

        参数:
            :param 无
        返回:
            :return: 成功执行任务后返回任务结果
        执行过程:
            1. 初始化回退时间为0.1秒
            2. 循环尝试执行任务，直到重试次数达到最大重试次数
                a. 尝试执行任务，如果成功则处理并返回任务结果
                b. 如果任务执行失败，增加重试次数
                c. 等待一段时间后再重试，等待时间逐渐增加
                d. 如果达到最大重试次数，抛出异常并记录错误信息
        """
        backoff_time = 0.1
        while self.Retries < self.MaxRetries:
            try:
                task_result = await self.Task(*self.Args, **self.Kwargs)
                return self.processResult(task_result)
            except Exception as e:
                self.Retries += 1
                await asyncio.sleep(backoff_time)
                backoff_time *= 2
                if self.Retries >= self.MaxRetries:
                    raise Exception(f"Failed to execute async task {self.Task.__name__} after {self.MaxRetries} attempts due to {str(e)}\n\n{traceback.format_exc()}.")

    def syncRetryExecution(self):
        """
        同步任务的重试执行逻辑

        参数:
            :param 无
        返回:
            :return: 成功执行任务后返回任务结果
        执行过程:
            1. 初始化回退时间为0.1秒
            2. 循环尝试执行任务，直到重试次数达到最大重试次数
                a. 尝试执行任务，如果成功则处理并返回任务结果
                b. 如果任务执行失败，增加重试次数
                c. 等待一段时间后再重试，等待时间逐渐增加
                d. 如果达到最大重试次数，抛出异常并记录错误信息
        """
        backoff_time = 0.1
        while self.Retries < self.MaxRetries:
            try:
                task_result = self.Task(*self.Args, **self.Kwargs)
                return self.processResult(task_result)
            except Exception as e:
                self.Retries += 1
                time.sleep(backoff_time)
                backoff_time *= 2
                if self.Retries >= self.MaxRetries:
                    raise Exception(f"Failed to execute sync task {self.Task.__name__} after {self.MaxRetries} attempts due to {str(e)}\n\n{traceback.format_exc()}.")


class _AsyncTaskObject(_BaseTaskObject):

    async def taskExecute(self):
        """
        执行异步任务，并处理任务结果

        参数:
            :param 无
        返回:
            :return: 处理后的任务结果
        执行过程:
            1. 尝试执行异步任务
                a. 获取任务结果并处理
            2. 如果任务执行过程中发生异常
                a. 检查是否启用重试机制
                b. 如果启用，则调用异步重试执行方法
                c. 如果未启用重试机制，抛出异常并记录错误信息
            3. 在任务执行完成后（无论成功与否），如果启用了GPU加速，则清理GPU资源
        """
        try:
            task_result = await self.Task(*self.Args, **self.Kwargs)
            return self.processResult(task_result)
        except Exception as e:
            if self.IsReTry:
                return await self.asyncRetryExecution()
            raise Exception(f"Failed to execute async task {self.Task.__name__} due to {str(e)}\n\n{traceback.format_exc()}.")
        finally:
            if self.IsGpuBoost:
                self.cleanupGpuResources()


class _SyncTaskObject(_BaseTaskObject):
    def taskExecute(self):
        """
        执行同步任务，并处理任务结果

        参数:
            :param 无
        返回:
            :return: 处理后的任务结果
        执行过程:
            1. 尝试执行同步任务
                a. 获取任务结果并处理
            2. 如果任务执行过程中发生异常
                a. 检查是否启用重试机制
                b. 如果启用，则调用同步重试执行方法
                c. 如果未启用重试机制，抛出异常并记录错误信息
            3. 在任务执行完成后（无论成功与否），如果启用了GPU加速，则清理GPU资源
        """
        try:
            task_result = self.Task(*self.Args, **self.Kwargs)
            return self.processResult(task_result)
        except Exception as e:
            if self.IsReTry:
                return self.syncRetryExecution()
            raise Exception(f"Failed to execute sync task {self.Task.__name__} due to {str(e)}\n\n{traceback.format_exc()}.")
        finally:
            if self.IsGpuBoost:
                self.cleanupGpuResources()


class _BaseThreadObject:
    def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], ThreadID: int, TaskResultQueue: multiprocessing.Queue, TaskLock: multiprocessing.Lock):
        self.Logger = Logger
        self.ThreadID = ThreadID
        self.TaskResultQueue = TaskResultQueue
        self.TaskLock = TaskLock
        self.ProcessWorkingEvent = None
        self.ThreadWorkingEvent = multiprocessing.Event()
        self.ThreadTaskQueue = queue.PriorityQueue()
        self.ThreadTaskQueueUniqueID = count()
        self.Thread = threading.Thread(target=self._run, daemon=True)
        self.CloseEvent = threading.Event()
        self.Condition = threading.Condition()

    def startThread(self):
        """启动线程"""
        self.Thread.start()

    def closeThread(self):
        """
        关闭线程及其相关资源

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 设置关闭事件标志，通知线程应关闭
            2. 使用条件变量通知所有等待的线程，继续执行以完成关闭过程
            3. 如果线程仍然存活，等待其完全终止
            4. 删除线程对象以释放资源
        """
        self.CloseEvent.set()
        with self.Condition:
            self.Condition.notify_all()
        if self.Thread.is_alive():
            self.Thread.join()
        del self

    def setProcessWorkingEvent(self, event: multiprocessing.Event):
        """设置进程工作事件"""
        self.ProcessWorkingEvent = event

    def addThreadTask(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        向线程任务队列中添加新的任务

        参数:
            :param priority: 任务的优先级
            :param task_object: 要添加的任务对象，可以是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 使用优先级和任务对象创建任务数据
            2. 在条件变量的上下文中，将任务数据加入到线程任务队列中
            3. 通知等待的线程有新任务可以处理
        """
        task_data = (priority, next(self.ThreadTaskQueueUniqueID), task_object)
        with self.Condition:
            self.ThreadTaskQueue.put_nowait(task_data)
            self.Condition.notify()

    def getThreadTaskCount(self):
        """获取当前线程任务队列中的任务数量"""
        return self.ThreadTaskQueue.qsize()

    def _run(self):
        """线程执行方法，必须由子类实现"""
        raise NotImplementedError("This method must be implemented by subclasses.")

    def _taskResultCallbackProcess(self, task_result: Any, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        处理任务结果并执行回调函数

        参数:
            :param task_result: 任务的执行结果
            :param task_object: 任务对象，包括异步和同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 检查任务对象是否有回调函数
            2. 如果有，将任务结果和任务ID放入任务结果队列中，供回调函数处理
            3. 删除任务对象和任务结果以释放内存
        """
        if task_object.IsCallback:
            self.TaskResultQueue.put_nowait((task_result, task_object.TaskID))
        del task_object
        del task_result

    def _cleanup(self, mode: str):
        """
        清理线程任务队列中的剩余任务，并记录日志

        参数:
            :param mode: 当前线程模式的描述字符串，用于日志记录
        返回:
            :return: 无返回值
        执行过程:
            1. 初始化剩余任务计数器
            2. 检查线程任务队列是否为空
                a. 如果不为空，从队列中获取任务并增加剩余任务计数器
                b. 如果队列为空，跳出循环
            3. 记录日志，显示当前线程模式和线程ID以及被丢弃的任务数量
        """
        remaining_tasks = 0
        while not self.ThreadTaskQueue.empty():
            try:
                _, _, task_object = self.ThreadTaskQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        self.Logger.debug(f"{mode} thread [{self.ThreadID}] discarded {remaining_tasks} tasks.")


class _AsyncThreadObject(_BaseThreadObject):

    def _run(self):
        """
        运行异步任务处理器的主线程

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 创建一个新的异步事件循环
            2. 将新的事件循环设置为当前线程的事件循环
            3. 尝试运行事件循环，直到任务处理器完成所有任务
            4. 在完成后，关闭事件循环
        """
        thread_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_event_loop)
        try:
            thread_event_loop.run_until_complete(self._taskProcessor())
        finally:
            thread_event_loop.close()

    async def _taskProcessor(self):
        """
        异步任务处理器，负责从任务队列中提取任务并执行

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 循环检查关闭事件标志是否设置
            2. 使用条件变量等待新任务到达或关闭事件设置
            3. 如果关闭事件已设置，跳出循环
            4. 从任务队列中获取任务数据
            5. 检查任务是否需要锁定资源
                a. 如果需要锁定，尝试获取锁定并执行任务，完成后释放锁定
                b. 如果获取锁定失败，等待一段时间后重试将任务放回队列
            6. 如果任务不需要锁定资源，直接执行任务
            7. 在退出循环前进行清理操作，记录被丢弃的任务数量
        """
        while not self.CloseEvent.is_set():
            with self.Condition:
                while self.ThreadTaskQueue.empty() and not self.CloseEvent.is_set():
                    self.Condition.wait()
                if self.CloseEvent.is_set():
                    break
                task_data: tuple[int, int, _AsyncTaskObject] = self.ThreadTaskQueue.get_nowait()

            priority, uniqueid, task_object = task_data
            if task_object.IsLock:
                if self.TaskLock.acquire(timeout=task_object.LockHoldingTime):
                    try:
                        await self._executeAsyncTask(task_object)
                    finally:
                        self.TaskLock.release()
                else:
                    await asyncio.sleep(min(0.1 * (2 ** task_object.MaxRetries), 10))
                    self.ThreadTaskQueue.put_nowait(task_data)
            else:
                await self._executeAsyncTask(task_object)
        self._cleanup("Async")

    async def _executeAsyncTask(self, task_object: _AsyncTaskObject):
        """
        执行异步任务并处理结果

        参数:
            :param task_object: 异步任务对象
        返回:
            :return: 无返回值
        执行过程:
            1. 调用任务对象的taskExecute方法执行异步任务，并等待结果
            2. 调用_taskResultCallbackProcess方法处理任务结果并执行回调
            3. 清除线程的工作状态标志
            4. 如果存在进程工作状态标志，清除该标志
        """
        task_result = await task_object.taskExecute()
        self._taskResultCallbackProcess(task_result, task_object)
        self.ThreadWorkingEvent.clear()
        if self.ProcessWorkingEvent:
            self.ProcessWorkingEvent.clear()


class _SyncThreadObject(_BaseThreadObject):

    def _run(self):
        """
        运行同步任务处理器的主线程

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 循环检查关闭事件标志是否设置
                a. 如果未设置，则调用_taskProcessor方法处理任务
            2. 如果关闭事件已设置，调用_cleanup方法清理任务队列
        """
        while not self.CloseEvent.is_set():
            self._taskProcessor()
        self._cleanup("Sync")

    def _taskProcessor(self):
        """
        同步任务处理器，负责从任务队列中提取任务并执行

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 使用条件变量等待新任务到达或关闭事件设置
            2. 如果关闭事件已设置，退出处理器
            3. 从任务队列中获取任务数据
                a. 如果队列为空，返回退出
            4. 检查任务是否需要锁定资源
                a. 如果需要锁定，尝试获取锁定并执行任务，完成后释放锁定
                b. 如果获取锁定失败，等待一段时间后重试将任务放回队列
            5. 如果任务不需要锁定资源，直接执行任务
        """
        with self.Condition:
            while self.ThreadTaskQueue.empty() and not self.CloseEvent.is_set():
                self.Condition.wait()
            if self.CloseEvent.is_set():
                return
            try:
                task_data: tuple[int, int, _SyncTaskObject] = self.ThreadTaskQueue.get_nowait()
            except queue.Empty:
                return

        priority, uniqueid, task_object = task_data
        if task_object.IsLock:
            if self.TaskLock.acquire(timeout=task_object.LockHoldingTime):
                try:
                    self._executeSyncTask(task_object)
                finally:
                    self.TaskLock.release()
            else:
                time.sleep(min(0.1 * (2 ** task_object.MaxRetries), 10))
                self.ThreadTaskQueue.put_nowait(task_data)
        else:
            self._executeSyncTask(task_object)

    def _executeSyncTask(self, task_object: _SyncTaskObject):
        """
        执行同步任务并处理结果

        参数:
            :param task_object: 同步任务对象
        返回:
            :return: 无返回值
        执行过程:
            1. 调用任务对象的taskExecute方法执行同步任务，并获取结果
            2. 调用_taskResultCallbackProcess方法处理任务结果并执行回调
            3. 清除线程的工作状态标志
            4. 如果存在进程工作状态标志，清除该标志
        """
        task_result = task_object.taskExecute()
        self._taskResultCallbackProcess(task_result, task_object)
        self.ThreadWorkingEvent.clear()
        if self.ProcessWorkingEvent:
            self.ProcessWorkingEvent.clear()


class _ProcessObject:
    def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], ProcessID: int, ProcessType: Literal["Core", "Expand"], TaskThreshold: int, TaskResultQueue: multiprocessing.Queue, TaskLock: multiprocessing.Lock, IdleCleanupThreshold: int, ProcessPriority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]):
        self.Logger = Logger
        self.ProcessID = ProcessID
        self.ProcessType = ProcessType
        self.TaskThreshold = TaskThreshold
        self.TaskResultQueue = TaskResultQueue
        self.TaskLock = TaskLock
        self.IdleCleanupThreshold = IdleCleanupThreshold
        self.ProcessPriority = ProcessPriority
        self.ProcessTaskQueue = multiprocessing.Queue()
        self.Process = multiprocessing.Process(target=self._run, daemon=True)
        self.ProcessWorkingEvent = multiprocessing.Event()
        self.CloseEvent = multiprocessing.Event()
        self.PsutilObject: Union[psutil.Process, None] = None
        self.AsyncThread: Union[_AsyncThreadObject, None] = None
        self.SyncThread: Union[_SyncThreadObject, None] = None

    def startProcess(self):
        """
        启动进程并记录日志

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 尝试启动进程
                a. 如果启动过程中发生异常，记录错误日志并返回
            2. 使用进程PID创建psutil对象，用于监控进程状态
            3. 记录日志，指示进程已启动，包括进程类型、进程ID和进程PID
        """
        try:
            self.Process.start()
        except Exception as e:
            self.Logger.error(f"Error occurred in {self.ProcessType}Process [{self.ProcessID}] due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        self.PsutilObject = psutil.Process(self.Process.pid)
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} has been started.")

    def closeProcess(self):
        """
        关闭进程并记录日志

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 设置关闭事件标志，通知进程应关闭
            2. 如果进程仍然存活，等待其完全终止
            3. 记录日志，指示进程已关闭，包括进程类型、进程ID和进程PID
        """
        self.CloseEvent.set()
        if self.Process.is_alive():
            self.Process.join()
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} has been closed.")

    def addProcessTask(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        向进程任务队列中添加新的任务

        参数:
            :param priority: 任务的优先级
            :param task_object: 要添加的任务对象，可以是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 创建包含优先级和任务对象的任务数据元组
            2. 将任务数据放入进程任务队列中
        """
        task_data = (priority, task_object)
        self.ProcessTaskQueue.put_nowait(task_data)

    def getProcessTaskCount(self):
        """获取当前进程任务队列中的任务数量"""
        return self.ProcessTaskQueue.qsize()

    def getProcessLoad(self):
        """
        获取当前进程的负载情况，包括CPU和内存使用率

        参数:
            :param 无
        返回:
            :return: 进程的加权负载百分比，范围为0到100
        执行过程:
            1. 尝试获取进程的CPU使用率，如果进程不存在则将CPU使用率设置为0
            2. 获取进程的内存使用率
            3. 计算加权负载：CPU和内存使用率各占50%的权重
            4. 返回加权负载的值，确保返回值在0到100之间
        """
        try:
            cpu_usage = self.PsutilObject.cpu_percent(0.015) / psutil.cpu_count(False)
        except psutil.NoSuchProcess:
            cpu_usage = 0
        memory_usage = self.PsutilObject.memory_percent()
        weighted_load = (cpu_usage * 5) + (memory_usage * 5)
        return min(max(weighted_load, 0), 100)

    def _startThread(self):
        """
        启动异步和同步线程，并记录日志

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 创建异步线程对象，并传入日志记录器、任务结果队列和任务锁
            2. 创建同步线程对象，并传入日志记录器、任务结果队列和任务锁
            3. 设置异步线程和同步线程的进程工作事件
            4. 启动异步线程
            5. 启动同步线程
            6. 记录日志，指示异步线程已启动
            7. 记录日志，指示同步线程已启动
        """
        self.AsyncThread = _AsyncThreadObject(self.Logger, 0, self.TaskResultQueue, self.TaskLock)
        self.SyncThread = _SyncThreadObject(self.Logger, 0, self.TaskResultQueue, self.TaskLock)
        self.AsyncThread.setProcessWorkingEvent(self.ProcessWorkingEvent)
        self.SyncThread.setProcessWorkingEvent(self.ProcessWorkingEvent)
        self.AsyncThread.startThread()
        self.SyncThread.startThread()
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} async threads has been started.")
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} sync threads has been started.")

    def _closeThread(self):
        """
        关闭异步和同步线程，并记录日志

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 调用AsyncThread的closeThread方法，关闭异步线程
            2. 调用SyncThread的closeThread方法，关闭同步线程
            3. 记录日志，指示异步线程已关闭
            4. 记录日志，指示同步线程已关闭
        """
        self.AsyncThread.closeThread()
        self.SyncThread.closeThread()
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} async threads has been closed.")
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} sync threads has been closed.")

    def _run(self):
        """
        运行方法，处理进程任务队列中的任务

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 初始化空闲时间计数器 `idle_times`，并启动线程、设置进程优先级、清理进程内存。
            2. 在关闭事件未设置时循环：
                a. 尝试从 `ProcessTaskQueue` 中获取任务数据 `task_data`，包括优先级和任务对象 `task_object`。
                b. 如果任务队列为空，休眠 0.005 秒。如果空闲时间小于 `IdleCleanupThreshold`，则增加空闲时间并继续循环。
                c. 如果 `ProcessWorkingEvent` 被设置，则继续循环。
                d. 调用 `_cleanupProcessMemory` 方法清理进程内存，并重置空闲时间。
            3. 根据任务对象的类型（异步或同步）选择相应的线程处理任务：
                a. 如果任务类型为异步且异步线程任务数未达到阈值的一半，将任务添加到异步线程。
                b. 如果异步线程任务数已达阈值，将任务重新添加到 `ProcessTaskQueue`。
                c. 如果任务类型为同步且同步线程任务数未达到阈值的一半，将任务添加到同步线程。
                d. 如果同步线程任务数已达阈值，将任务重新添加到 `ProcessTaskQueue`。
            4. 捕获处理过程中的任何异常，并记录错误日志。
            5. 捕获 `KeyboardInterrupt` 或 `SystemExit` 异常，并记录调试日志。
            6. 最后调用 `_cleanup` 方法进行清理操作。
        """
        idle_times = 0
        self._startThread()
        self._setProcessPriority()
        self._cleanupProcessMemory()
        try:
            while not self.CloseEvent.is_set():
                try:
                    task_data: tuple[int, _AsyncTaskObject | _SyncTaskObject] = self.ProcessTaskQueue.get_nowait()
                    priority, task_object = task_data
                except queue.Empty:
                    time.sleep(0.005)
                    if idle_times < self.IdleCleanupThreshold:
                        idle_times += 0.005
                        continue
                    if self.ProcessWorkingEvent.is_set():
                        continue
                    self._cleanupProcessMemory()
                    idle_times = 0
                    continue
                task_type = "Async" if asyncio.iscoroutinefunction(task_object.taskExecute) else "Sync"
                if task_type == "Async":
                    if self.AsyncThread.getThreadTaskCount() < int(self.TaskThreshold // 2):
                        self.AsyncThread.addThreadTask(priority, task_object)
                        continue
                    self.addProcessTask(priority, task_object)
                    continue
                if task_type == "Sync":
                    if self.SyncThread.getThreadTaskCount() < int(self.TaskThreshold // 2):
                        self.SyncThread.addThreadTask(priority, task_object)
                        continue
                    self.addProcessTask(priority, task_object)
                    continue
        except Exception as e:
            self.Logger.error(f"Error occurred in {self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} due to {str(e)}\n\n{traceback.format_exc()}.")
        except (KeyboardInterrupt, SystemExit):
            self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} has been terminated.")
        finally:
            self._cleanup()

    def _setProcessPriority(self):
        """
        设置进程优先级的方法

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 定义优先级映射 `priority_mapping`，将优先级字符串映射为对应的常量值。
            2. 尝试使用 `OpenProcess` 函数获取进程的句柄 `handle`，权限为 `0x1F0FFF`。
                a. 如果获取句柄失败，记录错误日志并返回。
            3. 检查 `handle` 是否有效。
                a. 如果无效，记录错误日志并返回。
            4. 使用 `SetPriorityClass` 函数设置进程的优先级，优先级值从 `priority_mapping` 获取。
                a. 如果设置优先级失败，调用 `GetLastError` 函数获取错误代码并记录错误日志。
            5. 调用 `CloseHandle` 函数关闭句柄 `handle`。
        """

        priority_mapping = {
            "IDLE": 0x00000040,
            "BELOW_NORMAL": 0x00004000,
            "NORMAL": 0x00000020,
            "ABOVE_NORMAL": 0x00008000,
            "HIGH": 0x00000080,
            "REALTIME": 0x00000100
        }
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.Process.pid)
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
        except Exception as e:
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} set priority failed due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        if not handle:
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} failed to obtain a valid process handle.")
            return
        result = ctypes.windll.kernel32.SetPriorityClass(handle, priority_mapping[self.ProcessPriority])
        if result == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} set priority failed with error code {error_code}.")
        ctypes.windll.kernel32.CloseHandle(handle)

    def _cleanupProcessMemory(self):
        """
        清理进程内存的方法

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 尝试使用 `OpenProcess` 函数获取进程的句柄 `handle`，权限为 `0x1F0FFF`。
                a. 如果获取句柄失败，抛出异常并记录错误日志，返回。
            2. 检查 `handle` 是否有效。
                a. 如果无效，记录错误日志并返回。
            3. 使用 `EmptyWorkingSet` 函数清理进程的工作集内存。
                a. 如果清理失败，调用 `GetLastError` 函数获取错误代码并记录错误日志。
            4. 调用 `CloseHandle` 函数关闭句柄 `handle`。
        """
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, self.Process.pid)
            if handle == 0:
                raise ValueError("Failed to obtain a valid handle")
        except Exception as e:
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} memory cleanup failed due to {str(e)}\n\n{traceback.format_exc()}.")
            return
        if not handle:
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} failed to obtain a valid process handle.")
            return
        result = ctypes.windll.psapi.EmptyWorkingSet(handle)
        if result == 0:
            error_code = ctypes.windll.kernel32.GetLastError()
            self.Logger.error(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} memory cleanup failed with error code {error_code}.")
        ctypes.windll.kernel32.CloseHandle(handle)

    def _cleanup(self):
        """
        清理进程任务队列中的剩余任务并记录日志

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 调用_closeThread方法关闭相关线程
            2. 初始化剩余任务计数器
            3. 检查进程任务队列是否为空
                a. 如果不为空，从队列中获取任务并增加剩余任务计数器
                b. 如果队列为空，跳出循环
            4. 记录日志，显示当前进程类型、进程ID以及被丢弃的任务数量
        """
        self._closeThread()
        remaining_tasks = 0
        while not self.ProcessTaskQueue.empty():
            try:
                _, task_object = self.ProcessTaskQueue.get_nowait()
                remaining_tasks += 1
            except queue.Empty:
                break
        self.Logger.debug(f"{self.ProcessType}Process [{self.ProcessID}]{self.Process.pid} discarded {remaining_tasks} tasks.")


@dataclass
class ConcurrentSystemConfig:
    """
    数据类：用于配置并发系统的参数。

    属性:
        - CoreProcessCount: 核心进程数。
        - CoreThreadCount: 核心线程数。
        - MaximumProcessCount: 最大进程数。
        - MaximumThreadCount: 最大线程数。
        - IdleCleanupThreshold: 空闲清理阈值，用于控制系统资源的释放，单位为毫秒。
        - ProcessPriority: 进程优先级，用于控制进程的调度。
        - TaskThreshold: 任务阈值，用于控制任务的处理和调度。
        - GlobalTaskThreshold: 全局任务阈值，用于整个系统的任务管理。
        - TaskRejectionPolicy: 任务拒绝策略，定义当任务超出处理能力时的行为。
        - RejectionPolicyTimeout: 任务拒绝策略的超时设置，用于某些拒绝策略的时间控制。
        - ExpandPolicy: 扩展策略，定义系统如何增加资源以处理更多任务。
        - ShrinkagePolicy: 收缩策略，定义系统如何减少资源以适应较低的任务负载。
        - ShrinkagePolicyTimeout: 收缩策略的超时设置，用于控制资源减少的时机。
    """
    CoreProcessCount: Union[None, int] = None,
    CoreThreadCount: Union[None, int] = None,
    MaximumProcessCount: Union[None, int] = None,
    MaximumThreadCount: Union[None, int] = None,
    IdleCleanupThreshold: Union[None, int] = None,
    ProcessPriority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"] = "NORMAL",
    TaskThreshold: Union[None, int] = None,
    GlobalTaskThreshold: Union[None, int] = None,
    TaskRejectionPolicy: Literal[None, "Abandonment", "EarliestAbandonment", "TimeoutAbandonment"] = None,
    RejectionPolicyTimeout: Union[None, int] = None,
    ExpandPolicy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand"] = None,
    ShrinkagePolicy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink"] = None,
    ShrinkagePolicyTimeout: Union[None, int] = None


class TheSeedCoreConcurrentSystem:
    INSTANCE: TheSeedCoreConcurrentSystem = None
    _INITIALIZED: bool = False

    class _SetupConfig:
        def __init__(self, Logger: Union[TheSeedCoreLogger, logging.Logger], BaseConfig: ConcurrentSystemConfig = None):
            self.PhysicalCores = psutil.cpu_count(logical=False)
            self.Logger = Logger
            self.BaseConfig = self._setBaseConfig(BaseConfig)
            self.CoreProcessCount = self.setCoreProcessCount(self.BaseConfig.CoreProcessCount)
            self.CoreThreadCount = self.setCoreThreadCount(self.BaseConfig.CoreThreadCount)
            self.MaximumProcessCount = self.setMaximumProcessCount(self.BaseConfig.MaximumProcessCount)
            self.MaximumThreadCount = self.setMaximumThreadCount(self.BaseConfig.MaximumThreadCount)
            self.IdleCleanupThreshold = self.setIdleCleanupThreshold(self.BaseConfig.IdleCleanupThreshold)
            self.ProcessPriority = self.setProcessPriority(self.BaseConfig.ProcessPriority)
            self.TaskThreshold = self.setTaskThreshold(self.BaseConfig.TaskThreshold)
            self.GlobalTaskThreshold = self.setGlobalTaskThreshold(self.BaseConfig.GlobalTaskThreshold)
            self.TaskRejectionPolicy = self.setTaskRejectionPolicy(self.BaseConfig.TaskRejectionPolicy)
            self.RejectionPolicyTimeout = self.setRejectionPolicyTimeout(self.BaseConfig.RejectionPolicyTimeout)
            self.ExpandPolicy = self.setExpandPolicy(self.BaseConfig.ExpandPolicy)
            self.ShrinkagePolicy = self.setShrinkagePolicy(self.BaseConfig.ShrinkagePolicy)
            self.ShrinkagePolicyTimeout = self.setShrinkagePolicyTimeout(self.BaseConfig.ShrinkagePolicyTimeout)

        def _setBaseConfig(self, base_config: Union[None, ConcurrentSystemConfig]):
            if base_config is None:
                self.Logger.warning("Configuration not set, using default configuration.")
                config = ConcurrentSystemConfig(None, None, None, None, None, "NORMAL", None, None, None, None, None, None, None)
                return config
            return base_config

        def setCoreProcessCount(self, core_process_count: int, adjust_mode: bool = False):
            """
            设置核心进程数，确保在有效范围内，并记录日志

            参数:
                :param core_process_count: 要设置的核心进程数
                :param adjust_mode: 布尔值，指示是否在内部调整和设置核心进程数
            返回:
                :return: 最终确定的核心进程数
            执行过程:
                1. 定义默认核心进程数为CPU物理核心数的一半
                2. 检查core_process_count是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                    b. 如果adjust_mode为True，将CoreProcessCount设置为默认值
                3. 检查core_process_count是否在有效范围内（默认值到CPU物理核心数之间）
                    a. 如果不在范围内，记录警告日志，并使用默认值
                    b. 如果adjust_mode为True，将CoreProcessCount设置为默认值
                4. 如果core_process_count有效且adjust_mode为True，设置CoreProcessCount为core_process_count
                5. 返回最终确定的核心进程数
            """
            default_value = self.PhysicalCores // 2
            if core_process_count is None:
                self.Logger.warning(f"Core process count not set, using default value {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if not isinstance(core_process_count, int):
                self.Logger.warning(f"Invalid type for core process count '{core_process_count}'. Must be an integer; using default value {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if not (default_value <= core_process_count <= self.PhysicalCores):
                self.Logger.warning(f"Core process count {core_process_count} is out of valid range ({default_value} to {self.PhysicalCores}); using default value {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if adjust_mode:
                self.CoreProcessCount = core_process_count
            return core_process_count

        def setCoreThreadCount(self, core_thread_count: int, adjust_mode: bool = False):
            """
            设置核心线程数，确保在有效范围内，并记录日志

            参数:
                :param core_thread_count: 要设置的核心线程数
                :param adjust_mode: 布尔值，指示是否在内部调整和设置核心线程数
            返回:
                :return: 最终确定的核心线程数
            执行过程:
                1. 定义默认核心线程数为核心进程数的两倍
                2. 检查core_thread_count是否为None
                    a. 如果为None，记录警告日志，并使用默认值
                    b. 如果adjust_mode为True，将CoreThreadCount设置为默认值
                3. 检查core_thread_count是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                    b. 如果adjust_mode为True，将CoreThreadCount设置为默认值
                4. 检查core_thread_count是否在有效范围内（默认值到CPU物理核心数的两倍之间）
                    a. 如果不在范围内，记录警告日志，并使用默认值
                    b. 如果adjust_mode为True，将CoreThreadCount设置为默认值
                5. 如果core_thread_count有效且adjust_mode为True，设置CoreThreadCount为core_thread_count
                6. 返回最终确定的核心线程数
            """
            default_value = int(self.CoreProcessCount * 2)
            if core_thread_count is None:
                self.Logger.warning(f"Core thread count not set, using default value {default_value}.")
                if adjust_mode:
                    self.CoreThreadCount = default_value
                return default_value

            if not isinstance(core_thread_count, int):
                self.Logger.warning(f"Core thread count must be an integer; received type {type(core_thread_count).__name__}. Using default value {default_value}.")
                if adjust_mode:
                    self.CoreThreadCount = default_value
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

            if adjust_mode:
                self.CoreThreadCount = adjusted_count
            return adjusted_count

        def setMaximumProcessCount(self, maximum_process_count: int, adjust_mode: bool = False):
            """
            设置最大进程数，确保在有效范围内，并记录日志

            参数:
                :param maximum_process_count: 要设置的最大进程数
                :param adjust_mode: 布尔值，指示是否在内部调整和设置最大进程数
            返回:
                :return: 最终确定的最大进程数
            执行过程:
                1. 定义默认最大进程数为CPU物理核心数
                2. 检查maximum_process_count是否为None
                    a. 如果为None，记录警告日志，并使用默认值
                3. 检查maximum_process_count是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                4. 检查maximum_process_count是否小于默认值
                    a. 如果小于默认值，记录警告日志，并使用默认值
                5. 检查maximum_process_count是否小于核心进程数
                    a. 如果小于核心进程数，记录警告日志，并使用默认值
                6. 如果maximum_process_count有效且adjust_mode为True，设置MaximumProcessCount为maximum_process_count
                7. 返回最终确定的最大进程数
            """
            default_value = self.PhysicalCores
            if maximum_process_count is None:
                self.Logger.warning(f"Maximum process count not set, using default value: {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if not isinstance(maximum_process_count, int):
                self.Logger.warning(f"Maximum process count must be an integer; received '{maximum_process_count}'. Using default value: {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if maximum_process_count > self.PhysicalCores:
                self.Logger.warning(f"Maximum process count {maximum_process_count} exceeds the number of physical CPU cores ({self.PhysicalCores}). Using default value: {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if maximum_process_count < self.CoreProcessCount:
                self.Logger.warning(f"Maximum process count {maximum_process_count} is less than the core process count ({self.CoreProcessCount}). Using default value: {default_value}.")
                if adjust_mode:
                    self.CoreProcessCount = default_value
                return default_value

            if adjust_mode:
                self.CoreProcessCount = maximum_process_count
            return maximum_process_count

        def setMaximumThreadCount(self, maximum_thread_count: int, adjust_mode: bool = False):
            """
            设置最大线程数，确保在有效范围内，并记录日志

            参数:
                :param maximum_thread_count: 要设置的最大线程数
                :param adjust_mode: 布尔值，指示是否在内部调整和设置最大线程数
            返回:
                :return: 最终确定的最大线程数
            执行过程:
                1. 定义默认最大线程数为CPU物理核心数的两倍
                2. 检查maximum_thread_count是否为None
                    a. 如果为None，记录警告日志，并使用默认值
                3. 检查maximum_thread_count是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                4. 检查maximum_thread_count是否小于核心线程数
                    a. 如果小于核心线程数，记录警告日志，并使用默认值
                5. 检查maximum_thread_count是否大于默认值
                    a. 如果大于默认值，记录警告日志，并使用默认值
                6. 检查maximum_thread_count是否为偶数
                    a. 如果不是偶数，将最大线程数调整为偶数，并记录警告日志
                7. 如果maximum_thread_count有效且adjust_mode为True，设置MaximumThreadCount为maximum_thread_count
                8. 返回最终确定的最大线程数
            """
            default_value = int(self.PhysicalCores * 2)
            if maximum_thread_count is None:
                self.Logger.warning(f"Maximum thread count not set, using default value: {default_value}.")
                if adjust_mode:
                    self.MaximumThreadCount = default_value
                return default_value

            if not isinstance(maximum_thread_count, int):
                self.Logger.warning(f"Received non-integer type for maximum thread count; using default value: {default_value}.")
                if adjust_mode:
                    self.MaximumThreadCount = default_value
                return default_value

            if maximum_thread_count < self.CoreThreadCount:
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

            if adjust_mode:
                self.MaximumThreadCount = adjusted_count
            return adjusted_count

        def setIdleCleanupThreshold(self, idle_cleanup_threshold: int):
            """
            设置空闲清理阈值，确保在有效范围内，并记录日志

            参数:
                :param idle_cleanup_threshold: 要设置的空闲清理阈值
            返回:
                :return: 最终确定的空闲清理阈值
            执行过程:
                1. 定义默认空闲清理阈值为300(5分钟)
                2. 检查idle_cleanup_threshold是否为None
                    a. 如果为None，记录警告日志，并使用默认值
                3. 检查idle_cleanup_threshold是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                4. 返回最终确定的空闲清理阈值
            """
            default_value = 300
            if idle_cleanup_threshold is None:
                self.Logger.warning(f"Idle cleanup threshold not set, using default value: {default_value}.")
                return default_value

            if not isinstance(idle_cleanup_threshold, int):
                self.Logger.warning(f"Received non-integer type for idle cleanup threshold; using default value: {default_value}.")
                return default_value

            return idle_cleanup_threshold

        def setProcessPriority(self, process_priority: Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]) -> Literal["IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
            """
            设置进程优先级，确保优先级合法并记录日志

            参数:
                :param process_priority: 要设置的进程优先级
            返回:
                :return: 最终确定的进程优先级
            执行过程:
                1. 检查process_priority是否在已知的优先级列表中
                    a. 如果不在列表中，记录警告日志，并使用默认值“NORMAL”
                2. 检查process_priority是否为None
                    a. 如果为None，记录警告日志，并使用默认值“NORMAL”
                3. 检查核心进程数是否等于物理核心数且process_priority为“HIGH”或“REALTIME”
                    a. 如果是，记录警告日志，并使用默认值“ABOVE_NORMAL”
                4. 返回最终确定的进程优先级
            """
            if process_priority not in [None, "IDLE", "BELOW_NORMAL", "NORMAL", "ABOVE_NORMAL", "HIGH", "REALTIME"]:
                self.Logger.warning(f"Invalid process priority '{process_priority}'. Using default value: NORMAL.")
                return "NORMAL"

            if process_priority is None:
                self.Logger.warning("Process priority not set, using default value: NORMAL.")
                return "NORMAL"

            if self.CoreProcessCount == self.PhysicalCores and process_priority in ["HIGH", "REALTIME"]:
                self.Logger.warning(f"Process priority {process_priority} is not recommended for all physical cores; using default value: NORMAL.")
                return "ABOVE_NORMAL"
            return process_priority

        def setTaskThreshold(self, task_threshold: int, adjust_mode: bool = False):
            """
            设置任务阈值，确保在有效范围内，并记录日志

            参数:
                :param task_threshold: 要设置的任务阈值
                :param adjust_mode: 布尔值，指示是否在内部调整和设置任务阈值
            返回:
                :return: 最终确定的任务阈值
            执行过程:
                1. 计算默认任务阈值
                2. 检查task_threshold是否为None
                    a. 如果为None，记录警告日志，并使用默认值
                3. 检查task_threshold是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                4. 如果adjust_mode为True，设置TaskThreshold为task_threshold
                5. 返回最终确定的任务阈值
            """
            default_value = self.calculateTaskThreshold()
            if task_threshold is None:
                self.Logger.warning(f"Task threshold not set, using default value: {default_value}.")
                if adjust_mode:
                    self.TaskThreshold = default_value
                return default_value

            if not isinstance(task_threshold, int):
                self.Logger.warning(f"Received non-integer type for task threshold; using default value: {default_value}.")
                if adjust_mode:
                    self.TaskThreshold = default_value
                return default_value

            if adjust_mode:
                self.TaskThreshold = task_threshold
            return task_threshold

        def setGlobalTaskThreshold(self, global_task_threshold: int, adjust_mode: bool = False):
            """
            设置全局任务阈值，并确保其为整数类型

            参数:
                :param global_task_threshold: 要设置的全局任务阈值
                :param adjust_mode: 布尔值，指示是否在内部调整和设置全局任务阈值
            返回:
                :return: 最终确定的全局任务阈值
            执行过程:
                1. 计算默认全局任务阈值
                2. 检查global_task_threshold是否为None
                    a. 如果是None，记录警告日志，并使用默认值
                3. 检查global_task_threshold是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认值
                4. 如果adjust_mode为True，设置GlobalTaskThreshold为global_task_threshold
                5. 返回最终确定的全局任务阈值
            """
            default_value = int((self.CoreProcessCount + self.CoreThreadCount) * self.TaskThreshold)
            if global_task_threshold is None:
                self.Logger.warning(f"Global task threshold not set, using default value: {default_value}.")
                if adjust_mode:
                    self.GlobalTaskThreshold = default_value
                return default_value

            if not isinstance(global_task_threshold, int):
                self.Logger.warning(f"Global task threshold must be an integer, using default value: {default_value}. Received type: {type(global_task_threshold).__name__}")
                if adjust_mode:
                    self.GlobalTaskThreshold = default_value
                return default_value

            if adjust_mode:
                self.GlobalTaskThreshold = global_task_threshold
            return global_task_threshold

        def setTaskRejectionPolicy(self, task_rejection_policy: Literal[None, "Abandonment", "EarliestAbandonment", "TimeoutAbandonment"], adjust_mode: bool = False) -> Literal["Abandonment", "EarliestAbandonment", "TimeoutAbandonment"]:
            """
            设置任务拒绝策略，确保策略合法并记录日志

            参数:
                :param task_rejection_policy: 要设置的任务拒绝策略
                :param adjust_mode: 布尔值，指示是否在内部调整和设置任务拒绝策略
            返回:
                :return: 最终确定的任务拒绝策略
            执行过程:
                1. 检查task_rejection_policy是否为None
                    a. 如果是None，记录警告日志，并使用默认策略“Abandonment”
                    b. 如果adjust_mode为True，将TaskRejectionPolicy设置为默认策略
                2. 检查task_rejection_policy是否在已知的策略列表中
                    a. 如果不在列表中，记录警告日志，并使用默认策略“Abandonment”
                    b. 如果adjust_mode为True，将TaskRejectionPolicy设置为默认策略
                3. 如果task_rejection_policy合法且adjust_mode为True，设置TaskRejectionPolicy为task_rejection_policy
                4. 返回最终确定的任务拒绝策略
            """
            if task_rejection_policy is None:
                self.Logger.warning("Task rejection policy not set, using default policy: Abandon.")
                if adjust_mode:
                    self.TaskRejectionPolicy = "Abandonment"
                return "Abandonment"

            if task_rejection_policy not in ["Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]:
                self.Logger.warning("Unknown task rejection policy, using default policy: Abandon.")
                if adjust_mode:
                    self.TaskRejectionPolicy = "Abandonment"
                return "Abandonment"

            if adjust_mode:
                self.TaskRejectionPolicy = task_rejection_policy
            return task_rejection_policy

        def setRejectionPolicyTimeout(self, rejection_policy_timeout: int, adjust_mode: bool = False):
            """
            设置任务拒绝策略的超时时间，确保其为整数类型，并记录日志

            参数:
                :param rejection_policy_timeout: 要设置的超时时间（秒）
                :param adjust_mode: 布尔值，指示是否在内部调整和设置超时时间
            返回:
                :return: 最终确定的超时时间
            执行过程:
                1. 检查rejection_policy_timeout是否为None
                    a. 如果是None，记录警告日志，并使用默认超时时间3秒
                    b. 如果adjust_mode为True，将RejectionPolicyTimeout设置为默认超时时间
                2. 检查rejection_policy_timeout是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认超时时间3秒
                    b. 如果adjust_mode为True，将RejectionPolicyTimeout设置为默认超时时间
                3. 如果rejection_policy_timeout有效且adjust_mode为True，设置RejectionPolicyTimeout为rejection_policy_timeout
                4. 返回最终确定的超时时间
            """
            if rejection_policy_timeout is None:
                self.Logger.warning("Rejection policy timeout not set, using default timeout: 3 seconds.")
                if adjust_mode:
                    self.RejectionPolicyTimeout = 3
                return 3

            if not isinstance(rejection_policy_timeout, int):
                self.Logger.warning("Rejection policy timeout must be an integer, using default timeout: 3 seconds.")
                if adjust_mode:
                    self.RejectionPolicyTimeout = 3
                return 3

            if adjust_mode:
                self.RejectionPolicyTimeout = rejection_policy_timeout
            return rejection_policy_timeout

        def setExpandPolicy(self, expand_policy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"], adjust_mode: bool = False) -> Literal["NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"]:
            """
            设置扩展策略，确保策略合法并记录日志

            参数:
                :param expand_policy: 要设置的扩展策略
                :param adjust_mode: 布尔值，指示是否在内部调整和设置扩展策略
            返回:
                :return: 最终确定的扩展策略
            执行过程:
                1. 检查expand_policy是否为None
                    a. 如果是None，记录警告日志，并使用默认策略“AutoExpand”
                    b. 如果adjust_mode为True，将ExpandPolicy设置为默认策略
                2. 检查expand_policy是否在已知的策略列表中
                    a. 如果不在列表中，记录警告日志，并使用默认策略“AutoExpand”
                    b. 如果adjust_mode为True，将ExpandPolicy设置为默认策略
                3. 如果expand_policy合法且adjust_mode为True，设置ExpandPolicy为expand_policy
                4. 返回最终确定的扩展策略
            """
            if expand_policy is None:
                self.Logger.warning("Expand policy not set, using default policy: AutoExpand.")
                if adjust_mode:
                    self.ExpandPolicy = "AutoExpand"
                return "AutoExpand"

            if expand_policy not in ["NoExpand", "AutoExpand", "BeforehandExpand", "FullLoadExpand"]:
                self.Logger.warning("Unknown expand policy, using default policy: AutoExpand.")
                if adjust_mode:
                    self.ExpandPolicy = "AutoExpand"
                return "AutoExpand"

            if adjust_mode:
                self.ExpandPolicy = expand_policy
            return expand_policy

        def setShrinkagePolicy(self, shrinkage_policy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"], adjust_mode: bool = False) -> Literal["NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"]:
            """
            设置缩减策略，确保策略合法并记录日志

            参数:
                :param shrinkage_policy: 要设置的缩减策略
                :param adjust_mode: 布尔值，指示是否在内部调整和设置缩减策略
            返回:
                :return: 最终确定的缩减策略
            执行过程:
                1. 检查shrinkage_policy是否为None
                    a. 如果是None，记录警告日志，并使用默认策略“AutoShrink”
                    b. 如果adjust_mode为True，将ShrinkagePolicy设置为默认策略
                2. 检查shrinkage_policy是否在已知的策略列表中
                    a. 如果不在列表中，记录警告日志，并使用默认策略“AutoShrink”
                    b. 如果adjust_mode为True，将ShrinkagePolicy设置为默认策略
                3. 如果shrinkage_policy合法且adjust_mode为True，设置ShrinkagePolicy为shrinkage_policy
                4. 返回最终确定的缩减策略
            """
            if shrinkage_policy is None:
                self.Logger.warning("Shrinkage policy not set, using default policy: AutoShrink.")
                if adjust_mode:
                    self.ShrinkagePolicy = "AutoShrink"
                return "AutoShrink"

            if shrinkage_policy not in ["NoShrink", "AutoShrink", "TimeoutShrink", "LowLoadShrink"]:
                self.Logger.warning("Unknown shrinkage policy, using default policy: AutoShrink.")
                if adjust_mode:
                    self.ShrinkagePolicy = "AutoShrink"
                return "AutoShrink"

            if adjust_mode:
                self.ShrinkagePolicy = shrinkage_policy
            return shrinkage_policy

        def setShrinkagePolicyTimeout(self, shrinkage_policy_timeout: Union[None, int], adjust_mode: bool = False):
            """
            设置缩减策略的超时时间，确保其为整数类型，并记录日志

            参数:
                :param shrinkage_policy_timeout: 要设置的超时时间（秒）
                :param adjust_mode: 布尔值，指示是否在内部调整和设置超时时间
            返回:
                :return: 最终确定的超时时间
            执行过程:
                1. 检查shrinkage_policy_timeout是否为None
                    a. 如果是None，记录警告日志，并使用默认超时时间3秒
                    b. 如果adjust_mode为True，将ShrinkagePolicyTimeout设置为默认超时时间
                2. 检查shrinkage_policy_timeout是否为整数类型
                    a. 如果不是整数，记录警告日志，并使用默认超时时间3秒
                    b. 如果adjust_mode为True，将ShrinkagePolicyTimeout设置为默认超时时间
                3. 如果shrinkage_policy_timeout有效且adjust_mode为True，设置ShrinkagePolicyTimeout为shrinkage_policy_timeout
                4. 返回最终确定的超时时间
            """
            if shrinkage_policy_timeout is None:
                self.Logger.warning("Shrinkage policy timeout not set, using default timeout: 3 seconds.")
                if adjust_mode:
                    self.ShrinkagePolicyTimeout = 15
                return 15

            if not isinstance(shrinkage_policy_timeout, int):
                self.Logger.warning("Shrinkage policy timeout must be an integer, using default timeout: 3 seconds.")
                if adjust_mode:
                    self.ShrinkagePolicyTimeout = 15
                return 15

            if adjust_mode:
                self.ShrinkagePolicyTimeout = shrinkage_policy_timeout
            return shrinkage_policy_timeout

        @staticmethod
        def calculateTaskThreshold():
            """
            计算任务阈值，基于物理核心数量和总内存容量

            参数:
                :param 无
            返回:
                :return: 计算出的任务阈值
            执行过程:
                1. 获取物理核心的数量
                2. 获取总内存容量，并将其转换为GB
                3. 计算平衡得分，平衡核心数和内存容量的比例
                4. 根据平衡得分和预设的得分阈值列表，确定相应的任务阈值
                5. 如果平衡得分高于所有预设得分阈值，返回最大的任务阈值
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

    def __new__(cls, Config: ConcurrentSystemConfig = None, DebugMode: bool = False, *args, **kwargs):
        if cls.INSTANCE is None:
            cls.INSTANCE = super(TheSeedCoreConcurrentSystem, cls).__new__(cls)
        return cls.INSTANCE

    def __init__(self, Config: ConcurrentSystemConfig = None, DebugMode: bool = False, ):
        if not self._INITIALIZED:
            self._Logger = self._setConcurrentSystemLogger(DebugMode)
            self._Config = TheSeedCoreConcurrentSystem._SetupConfig(self._Logger, Config)
            self._TaskResultQueue = multiprocessing.Queue()
            self._TaskLock = multiprocessing.Lock()
            self._ProcessTaskQueue = queue.Queue()
            self._ThreadTaskQueue = queue.Queue()
            self._LoadBalancerThread = threading.Thread(target=self._loadBalancer, daemon=True)
            self._LoadBalancerThreadEvent = threading.Event()
            self._ProcessTaskAllocationThread = threading.Thread(target=self._ProcessTaskAllocator, daemon=True)
            self._ProcessTaskAllocationThreadEvent = threading.Event()
            self._ThreadTaskAllocationThread = threading.Thread(target=self._ThreadTaskAllocator, daemon=True)
            self._ThreadTaskAllocationThreadEvent = threading.Event()
            self._ThreadWorkingEvent = multiprocessing.Event()
            self._CoreProcess = {}
            self._ExpandProcess = {}
            self._ExpandProcessKeepAlive = {}
            self._AsyncCoreThread = {}
            self._SyncCoreThread = {}
            self._AsyncExpandThread = {}
            self._AsyncExpandThreadKeepAlive = {}
            self._SyncExpandThread = {}
            self._SyncExpandThreadKeepAlive = {}
            self._CallbackProcessor = self._setCallbackExecutor()

    def startSystem(self):
        self._CallbackProcessor.startExecutor()
        self._initSystem()
        TheSeedCoreConcurrentSystem._INITIALIZED = True

    def closeSystem(self):
        """
        关闭并发系统，确保所有进程和线程资源被适当地清理

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 设置LoadBalancerThreadEvent，指示负载均衡线程应停止
            2. 检查负载均衡线程是否仍在运行，如果是，等待线程结束
            3. 创建一个任务列表，用于存储关闭进程和线程的任务
            4. 使用ThreadPoolExecutor并行执行以下操作：
                a. 遍历所有核心进程，提交关闭每个进程的任务
                b. 遍历所有扩展进程，提交关闭每个进程的任务
                c. 遍历所有核心异步线程，提交关闭每个线程的任务
                d. 遍历所有扩展异步线程，提交关闭每个线程的任务
                e. 遍历所有核心同步线程，提交关闭每个线程的任务
                f. 遍历所有扩展同步线程，提交关闭每个线程的任务
            5. 等待所有提交的任务完成
            6. 关闭CallbackProcessor的执行器
            7. 记录日志，指示所有进程和线程已关闭
        """
        self._LoadBalancerThreadEvent.set()
        if self._LoadBalancerThread.is_alive():
            self._LoadBalancerThread.join()

        self._ProcessTaskAllocationThreadEvent.set()
        if self._ProcessTaskAllocationThread.is_alive():
            self._ProcessTaskAllocationThread.join()

        self._ThreadTaskAllocationThreadEvent.set()
        if self._ThreadTaskAllocationThread.is_alive():
            self._ThreadTaskAllocationThread.join()

        tasks = []

        with ThreadPoolExecutor(max_workers=(len(self._CoreProcess) + len(self._ExpandProcess))) as executor:
            for process in self._CoreProcess.values():
                tasks.append(executor.submit(self._closeProcesses, process))
            for process in self._ExpandProcess.values():
                tasks.append(executor.submit(self._closeProcesses, process))
            for thread in self._AsyncCoreThread.values():
                tasks.append(executor.submit(self._closeThreads, thread))
            for thread in self._AsyncExpandThread.values():
                tasks.append(executor.submit(self._closeThreads, thread))
            for thread in self._SyncCoreThread.values():
                tasks.append(executor.submit(self._closeThreads, thread))
            for thread in self._SyncExpandThread.values():
                tasks.append(executor.submit(self._closeThreads, thread))

            for future in tasks:
                future.result()
        self._CallbackProcessor.closeExecutor()
        self._Logger.debug(f"All processes and threads has been closed.")

    def submitProcessTask(self, task: callable, priority: int = 0, callback: callable = None, serialization_processor: TaskSerializationProcessor = None, is_lock: bool = False, lock_holding_time: int = 3, is_gpu_boost: bool = False, gpu_id: int = 0, is_retry: bool = False, max_retries: int = 3, *args, **kwargs):
        """
        提交一个进程任务进行处理

        参数:
            :param task: 可调用的任务函数
            :param priority: 任务的优先级，默认值为0
            :param callback: 可选的回调函数，在任务完成后调用
            :param serialization_processor: 可选的序列化处理器，用于序列化任务
            :param is_lock: 布尔值，指示任务是否需要锁定资源
            :param lock_holding_time: 锁定资源的最大时间（秒），默认值为3秒
            :param is_gpu_boost: 布尔值，指示是否启用GPU加速
            :param gpu_id: 指定用于加速的GPU ID
            :param is_retry: 布尔值，指示是否启用任务重试
            :param max_retries: 任务重试的最大次数，默认值为3次
            :param args: 传递给任务的其他位置参数
            :param kwargs: 传递给任务的其他关键字参数
        返回:
            :return: 无返回值
        执行过程:
            1. 调用_taskParamsProcess方法创建任务对象
            2. 调用_taskSubmitProcess方法提交任务对象进行处理
        """
        task_object = self._taskParamsProcess(task, callback, serialization_processor, is_lock, lock_holding_time, is_gpu_boost, gpu_id, is_retry, max_retries, *args, **kwargs)
        self._taskSubmitProcess("Process", priority, task_object)

    def submitThreadTask(self, task: callable, priority: int = 0, callback: callable = None, serialization_processor: TaskSerializationProcessor = None, is_lock: bool = False, lock_holding_time: int = 3, is_gpu_boost: bool = False, gpu_id: int = 0, is_retry: bool = False, max_retries: int = 3, *args, **kwargs):
        """
        提交一个线程任务进行处理

        参数:
            :param task: 可调用的任务函数
            :param priority: 任务的优先级，默认值为0
            :param callback: 可选的回调函数，在任务完成后调用
            :param serialization_processor: 可选的序列化处理器，用于序列化任务
            :param is_lock: 布尔值，指示任务是否需要锁定资源
            :param lock_holding_time: 锁定资源的最大时间（秒），默认值为3秒
            :param is_gpu_boost: 布尔值，指示是否启用GPU加速
            :param gpu_id: 指定用于加速的GPU ID
            :param is_retry: 布尔值，指示是否启用任务重试
            :param max_retries: 任务重试的最大次数，默认值为3次
            :param args: 传递给任务的其他位置参数
            :param kwargs: 传递给任务的其他关键字参数
        返回:
            :return: 无返回值
        执行过程:
            1. 调用_taskParamsProcess方法创建任务对象
            2. 调用_taskSubmitProcess方法提交任务对象进行处理
        """
        task_object = self._taskParamsProcess(task, callback, serialization_processor, is_lock, lock_holding_time, is_gpu_boost, gpu_id, is_retry, max_retries, *args, **kwargs)
        self._taskSubmitProcess("Thread", priority, task_object)

    def _taskParamsProcess(self, task: callable, callback: callable = None, serialization_processor: TaskSerializationProcessor = None, is_lock: bool = False, lock_holding_time: int = 3, is_gpu_boost: bool = False, gpu_id: int = 0, is_retry: bool = False, max_retries: int = 3, *args, **kwargs):
        """
        创建任务对象，包含任务的详细参数

        参数:
            :param task: 可调用的任务函数
            :param callback: 可选的回调函数，在任务完成后调用
            :param serialization_processor: 可选的序列化处理器，用于序列化任务
            :param is_lock: 布尔值，指示任务是否需要锁定资源
            :param lock_holding_time: 锁定资源的最大时间（秒），默认值为3秒
            :param is_gpu_boost: 布尔值，指示是否启用GPU加速
            :param gpu_id: 指定用于加速的GPU ID
            :param is_retry: 布尔值，指示是否启用任务重试
            :param max_retries: 任务重试的最大次数，默认值为3次
            :param args: 传递给任务的其他位置参数
            :param kwargs: 传递给任务的其他关键字参数
        返回:
            :return: 创建的任务对象，包括所有指定的参数
        执行过程:
            1. 生成唯一任务ID
            2. 检查是否提供了回调函数
                a. 如果提供了回调函数，添加到回调处理器中，并设置is_callback为True
                b. 如果未提供回调函数，设置is_callback为False
            3. 检查任务是否为异步函数
                a. 如果是异步函数，创建异步任务对象
                b. 如果是同步函数，创建同步任务对象
            4. 返回创建的任务对象
        """
        task_id = f"{uuid.uuid4()}"
        if callback is not None:
            self._CallbackProcessor.addCallbackFunction(task_id, callback)
            is_callback = True
        else:
            is_callback = False
        if asyncio.iscoroutinefunction(task):
            task_object = _AsyncTaskObject(task, task_id, serialization_processor, is_callback, is_lock, lock_holding_time, is_gpu_boost, gpu_id, is_retry, max_retries, *args, **kwargs)
        else:
            task_object = _SyncTaskObject(task, task_id, serialization_processor, is_callback, is_lock, lock_holding_time, is_gpu_boost, gpu_id, is_retry, max_retries, *args, **kwargs)
        return task_object

    def _taskSubmitProcess(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        提交任务对象到全局任务队列或拒绝任务

        参数:
            :param submit_type: 提交的类型，可以是"Process"或"Thread"
            :param priority: 任务的优先级
            :param task_object: 提交的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 检查全局任务队列的大小是否小于配置的全局任务阈值
                a. 如果小于阈值，将任务对象放入全局任务队列中
                b. 如果等于或超过阈值，调用_executionRejectTask方法拒绝任务
        """
        task_threshold = self._Config.GlobalTaskThreshold
        try:
            pickle.dumps(task_object)
        except Exception as e:
            self._Logger.error(f"Task [{task_object.Task.__name__}] cannot be pickled the task has been abandoned\n{str(e)}\n\n{traceback.format_exc()}.")
            del task_object
            return
        if submit_type == "Process":
            if self._ProcessTaskQueue.qsize() < task_threshold:
                self._ProcessTaskQueue.put_nowait((priority, task_object))
                return
        if submit_type == "Thread":
            if self._ThreadTaskQueue.qsize() < task_threshold:
                self._ThreadTaskQueue.put_nowait((priority, task_object))
                return
        self._executionRejectTask(submit_type, priority, task_object)

    def _executionRejectTask(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        根据配置的任务拒绝策略执行任务拒绝

        参数:
            :param submit_type: 提交的类型，可以是"Process"或"Thread"
            :param priority: 任务的优先级
            :param task_object: 被拒绝的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 根据当前的TaskRejectionPolicy选择相应的拒绝方法
            2. 调用选择的拒绝方法处理任务对象
        """
        policy_method = {
            "Abandonment": self._abandonment,
            "EarliestAbandonment": self._earliestAbandonment,
            "TimeoutAbandonment": self._timeoutAbandonment
        }
        rejection_method = policy_method[self._Config.TaskRejectionPolicy]
        rejection_method(submit_type, priority, task_object)

    def _abandonment(self, _, __, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        根据"Abandonment"策略处理任务对象，将其丢弃

        参数:
            :param _: 提交的类型（未使用）
            :param __: 任务的优先级（未使用）
            :param task_object: 被丢弃的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 记录警告日志，指示任务因全局任务队列超载而被丢弃
            2. 删除任务对象以释放资源
        """
        self._Logger.warning(f"Task [{task_object.Task.__name__}] has been abandoned due to global task queue overload.")
        del task_object

    def _earliestAbandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: _AsyncTaskObject | _SyncTaskObject):
        """
        根据"最早丢弃"策略处理任务对象，丢弃队列中最早的任务，并将新任务添加到队列中

        参数:
            :param submit_type: 提交的类型，可以是"Process"或"Thread"
            :param priority: 新任务的优先级
            :param task_object: 新的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 记录警告日志，指示新的任务因全局任务队列超载而被处理
            2. 从全局任务队列中移除最早的任务
            3. 将新的任务对象放入全局任务队列中
        """
        self._Logger.warning(f"Task [{task_object.Task.__name__}] has been abandoned due to global task queue overload.")
        task_queue = self._ProcessTaskQueue if submit_type == "Process" else self._ThreadTaskQueue
        task_queue.get_nowait()
        task_queue.put_nowait((priority, task_object))

    def _timeoutAbandonment(self, submit_type: Literal["Process", "Thread"], priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        根据"超时丢弃"策略处理任务对象，在超时后尝试重新提交任务

        参数:
            :param submit_type: 提交的类型，可以是"Process"或"Thread"
            :param priority: 任务的优先级
            :param task_object: 被处理的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 等待配置的拒绝策略超时时间
            2. 检查全局任务队列的大小是否小于全局任务阈值
                a. 如果小于阈值，将任务对象放入全局任务队列中
                b. 如果等于或超过阈值，记录警告日志，指示任务因全局任务队列超载而被丢弃
            3. 删除任务对象和相关参数以释放资源
        """
        time.sleep(self._Config.RejectionPolicyTimeout)
        task_queue = self._ProcessTaskQueue if submit_type == "Process" else self._ThreadTaskQueue
        if task_queue.qsize() < self._Config.GlobalTaskThreshold // 2:
            task_queue.put_nowait((submit_type, priority, task_object))
            return
        self._Logger.warning(f"Task [{task_object.Task.__name__}] has been abandoned due to global task queue overload.")
        del submit_type
        del priority
        del task_object

    def _setCallbackExecutor(self):
        """
        根据Qt模式设置回调执行器

        参数:
            :param 无
        返回:
            :return: 回调执行器对象
        执行过程:
            1. 检查当前是否为Qt模式
                a. 如果是Qt模式，根据Qt版本选择相应的回调执行器
                b. 如果不是Qt模式，使用默认的回调执行器
            2. 返回回调执行器对象
        """
        global _PySide6Support, _PyQt6Support, _PyQt5Support
        # noinspection PyUnresolvedReferences
        if QApplication and QApplication.instance():
            if _PyQt5Support:
                return _PyQt5CallbackExecutor(self._TaskResultQueue)
            if _PyQt6Support:
                return _PyQt6CallbackExecutor(self._TaskResultQueue)
            if _PySide6Support:
                return _PySide6CallbackExecutor(self._TaskResultQueue)
        return _CoreCallbackExecutor(self._TaskResultQueue)

    def _initSystem(self):
        """
        初始化并发系统，包括启动进程和线程

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 使用ThreadPoolExecutor根据配置的核心进程数和核心线程数创建并发执行器
            2. 提交启动核心进程和线程的任务
                a. 根据核心进程数，提交启动每个进程的任务
                b. 根据核心线程数，提交启动每个线程的任务
            3. 等待所有提交的任务完成
            4. 启动负载均衡线程
            5. 捕获并处理初始化过程中可能发生的异常，记录错误日志
        """
        try:
            with ThreadPoolExecutor(max_workers=self._Config.CoreProcessCount + self._Config.CoreThreadCount) as executor:
                futures = []
                for process_id in range(self._Config.CoreProcessCount):
                    futures.append(executor.submit(self._startProcess, process_id))
                for thread_id in range(self._Config.CoreThreadCount // 2):
                    futures.append(executor.submit(self._startThread, thread_id))
                for future in as_completed(futures):
                    future.result()
            self._LoadBalancerThread.start()
            self._ProcessTaskAllocationThread.start()
            self._ThreadTaskAllocationThread.start()
        except Exception as e:
            self._Logger.error(f"Error occurred during concurrent task system initialization due to {str(e)}\n\n{traceback.format_exc()}.")

    def _startProcess(self, process_id: int):
        """
        启动指定的核心进程并将其存储在核心进程字典中

        参数:
            :param process_id: 要启动的进程的唯一标识符
        返回:
            :return: 无返回值
        执行过程:
            1. 创建_ProcessObject实例，初始化核心进程对象
            2. 调用进程对象的startProcess方法启动进程
            3. 将启动的进程对象存储在_CoreProcess字典中，以process_id为键
        """
        process = _ProcessObject(self._Logger, process_id, "Core", self._Config.TaskThreshold, self._TaskResultQueue, self._TaskLock, self._Config.IdleCleanupThreshold, self._Config.ProcessPriority)
        process.startProcess()
        self._CoreProcess[process_id] = process

    def _startThread(self, thread_id: int):
        """
        启动指定的核心异步和同步线程并将其存储在相应的字典中

        参数:
            :param thread_id: 要启动的线程的唯一标识符
        返回:
            :return: 无返回值
        执行过程:
            1. 创建_AsyncThreadObject实例，初始化异步线程对象
            2. 创建_SyncThreadObject实例，初始化同步线程对象
            3. 启动异步线程
            4. 启动同步线程
            5. 将启动的异步线程对象存储在_AsyncCoreThread字典中，以thread_id为键
            6. 将启动的同步线程对象存储在_SyncCoreThread字典中，以thread_id为键
            7. 记录日志，指示核心异步和同步线程已启动
        """
        async_thread = _AsyncThreadObject(self._Logger, thread_id, self._TaskResultQueue, self._TaskLock)
        sync_thread = _SyncThreadObject(self._Logger, thread_id, self._TaskResultQueue, self._TaskLock)
        async_thread.startThread()
        sync_thread.startThread()
        self._AsyncCoreThread[thread_id] = async_thread
        self._SyncCoreThread[thread_id] = sync_thread
        self._Logger.debug(f"CoreAsyncThread [{thread_id}] has been started.")
        self._Logger.debug(f"CoreSyncThread [{thread_id}] has been started.")

    @staticmethod
    def _closeProcesses(process: _ProcessObject):
        """
        关闭指定的进程对象

        参数:
            :param process: 要关闭的_ProcessObject实例
        返回:
            :return: 无返回值
        执行过程:
            1. 调用_ProcessObject实例的closeProcess方法，关闭指定的进程
        """
        process.closeProcess()

    @staticmethod
    def _closeThreads(thread: Union[_AsyncThreadObject, _SyncThreadObject]):
        """
        关闭指定的线程对象

        参数:
            :param thread: 要关闭的线程对象，可以是 _AsyncThreadObject 或 _SyncThreadObject 的实例
        返回:
            :return: 无返回值
        执行过程:
            1. 调用线程对象的 closeThread 方法，关闭指定的线程
        """
        thread.closeThread()

    @staticmethod
    def _setConcurrentSystemLogger(debug_mode: bool = False) -> logging.Logger:
        """
        设置并发系统的日志记录器，根据调试模式配置日志级别

        参数:
            :param debug_mode: 布尔值，指示是否启用调试模式
        返回:
            :return: 配置完成的 logging.Logger 实例
        执行过程:
            1. 获取名为'TheSeedConcurrentTaskSystem'的日志记录器
            2. 设置日志记录器的日志级别为 DEBUG
            3. 创建一个控制台处理器
                a. 如果启用调试模式，设置处理器级别为 DEBUG
                b. 否则，设置处理器级别为 WARNING（取 DEBUG 和 WARNING 的最大值）
            4. 设置日志格式，包括时间戳、日志记录器名称、日志级别和消息
            5. 将格式应用于控制台处理器
            6. 将控制台处理器添加到日志记录器中
            7. 返回配置完成的日志记录器
        """
        # Initialize colorama
        init(autoreset=True)

        logger = logging.getLogger('TheSeedCore - ConcurrentSystem')
        logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        if debug_mode:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(max(logging.DEBUG, logging.WARNING))

        formatter = _ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        return logger

    def _loadBalancer(self):
        """
        负载均衡器，负责根据任务队列中的任务情况扩展或缩减资源

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 循环运行，直到LoadBalancerThreadEvent设置为停止
                a. 执行资源扩展策略
                b. 执行资源缩减策略
                c. 尝试从全局任务队列中获取任务
                    i. 如果队列为空，等待一小段时间后继续
                d. 获取任务后，根据任务的提交类型（Process或Thread）进行任务分配
                    i. 如果是进程任务，调用_processTaskAllocation方法分配任务
                    ii. 如果是线程任务，调用_threadTaskAllocation方法分配任务
        """
        while not self._LoadBalancerThreadEvent.is_set():
            self._executionExpandPolicy()
            self._executionShrinkagePolicy()

    def _ProcessTaskAllocator(self):
        while not self._ProcessTaskAllocationThreadEvent.is_set():
            tasks = []
            start_time = time.time()
            while (time.time() - start_time) < 0.1:
                try:
                    item: tuple[int, _AsyncTaskObject | _SyncTaskObject] = self._ProcessTaskQueue.get_nowait()
                    priority, task_object = item
                    tasks.append((priority, task_object))
                except queue.Empty:
                    time.sleep(0.015)
                    continue
            if tasks:
                for priority, task_object in tasks:
                    self._processTaskAllocation(priority, task_object)

    def _ThreadTaskAllocator(self):
        while not self._ThreadTaskAllocationThreadEvent.is_set():
            tasks = []
            start_time = time.time()
            while (time.time() - start_time) < 0.1:
                try:
                    item: tuple[int, _AsyncTaskObject | _SyncTaskObject] = self._ThreadTaskQueue.get_nowait()
                    priority, task_object = item
                    tasks.append((priority, task_object))
                except queue.Empty:
                    time.sleep(0.0001)
                    continue
            if tasks:
                for priority, task_object in tasks:
                    self._threadTaskAllocation(priority, task_object)

    def _processTaskAllocation(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        根据当前核心和扩展进程的负载情况分配进程任务

        参数:
            :param priority: 任务的优先级
            :param task_object: 要分配的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 检查当前非满载的核心进程
            2. 检查当前非工作的核心进程
            3. 如果没有非工作的核心进程
                a. 如果没有非满载的核心进程
                    i. 检查是否存在扩展进程
                    ii. 检查当前非满载的扩展进程
                    iii. 检查当前非工作的扩展进程
                    iv. 如果没有非工作的扩展进程
                        - 如果没有非满载的扩展进程，将任务重新放入全局任务队列
                    v. 否则，将任务分配给任务负载最小的非满载扩展进程
                b. 如果存在非满载的核心进程，将任务分配给任务负载最小的非满载核心进程
            4. 如果存在非工作的核心进程，将任务分配给负载最小的非工作核心进程，并设置其工作事件
        """
        not_full_core_processes = self._checkNotFullProcess("Core")
        not_working_core_processes = self._checkNotWorkingProcess("Core")

        if not not_working_core_processes:
            if not not_full_core_processes:
                if self._ExpandProcess:
                    non_full_expand_processes = self._checkNotFullProcess("Expand")
                    non_working_expand_processes = self._checkNotWorkingProcess("Expand")
                    if not non_working_expand_processes:
                        if not non_full_expand_processes:
                            self._ProcessTaskQueue.put_nowait((priority, task_object))
                            return
                        minimum_task_load_expand_process = self._checkMinimumTaskLoadProcess(non_full_expand_processes)
                        minimum_task_load_expand_process.addProcessTask(priority, task_object)
                        return
                    minimum_load_expand_process = self._checkMinimumLoadProcess(non_working_expand_processes)
                    minimum_load_expand_process.addProcessTask(priority, task_object)
                    minimum_load_expand_process.ProcessWorkingEvent.set()
                self._ProcessTaskQueue.put_nowait((priority, task_object))
                return
            minimum_task_load_core_process = self._checkMinimumTaskLoadProcess(not_full_core_processes)
            minimum_task_load_core_process.addProcessTask(priority, task_object)
            return
        minimum_load_core_process = self._checkMinimumLoadProcess(not_working_core_processes)
        minimum_load_core_process.addProcessTask(priority, task_object)
        minimum_load_core_process.ProcessWorkingEvent.set()

    def _checkNotFullProcess(self, process_type: Literal["Core", "Expand"]):
        """
        检查并返回非满载的进程对象列表

        参数:
            :param process_type: 进程类型，可以是 "Core" 或 "Expand"
        返回:
            :return: 非满载的进程对象列表
        执行过程:
            1. 根据 process_type 获取相应的进程池
            2. 遍历进程池中的所有进程对象
            3. 返回任务计数未达到配置任务阈值的进程对象列表
        """
        process_pool = self._CoreProcess if process_type == "Core" else self._ExpandProcess
        not_full_processes = [obj for index, obj in process_pool.items() if obj.getProcessTaskCount() < self._Config.TaskThreshold]
        return not_full_processes

    def _checkNotWorkingProcess(self, process_type: Literal["Core", "Expand"]):
        """
        检查并返回非工作状态的进程对象列表

        参数:
            :param process_type: 进程类型，可以是 "Core" 或 "Expand"
        返回:
            :return: 非工作状态的进程对象列表
        执行过程:
            1. 根据 process_type 获取相应的进程池
            2. 遍历进程池中的所有进程对象
            3. 返回 ProcessWorkingEvent 未设置的进程对象列表（即非工作状态）
        """
        process_pool = self._CoreProcess if process_type == "Core" else self._ExpandProcess
        not_working_processes = [obj for index, obj in process_pool.items() if not obj.ProcessWorkingEvent.is_set()]
        return not_working_processes

    @staticmethod
    def _checkMinimumTaskLoadProcess(non_full_processes):
        """
        查找并返回任务负载最小的非满载进程对象

        参数:
            :param non_full_processes: 非满载的进程对象列表
        返回:
            :return: 任务负载最小的进程对象
        执行过程:
            1. 遍历 non_full_processes 列表，获取每个进程对象的任务计数
            2. 返回任务计数最小的进程对象
        """
        return min(non_full_processes, key=lambda x: x.getProcessTaskCount())

    @staticmethod
    def _checkMinimumLoadProcess(not_working_processes):
        """
        查找并返回负载最小的非工作进程对象

        参数:
            :param not_working_processes: 非工作状态的进程对象列表
        返回:
            :return: 负载最小的进程对象
        执行过程:
            1. 尝试遍历 non_working_processes 列表，获取每个进程对象的当前负载
            2. 返回负载最小的进程对象
            3. 如果出现 psutil.NoSuchProcess 异常，返回非工作进程列表中的第一个进程对象
        """
        try:
            return min(not_working_processes, key=lambda x: x.getProcessLoad())
        except psutil.NoSuchProcess:
            return not_working_processes[0]

    def _threadTaskAllocation(self, priority: int, task_object: Union[_AsyncTaskObject, _SyncTaskObject]):
        """
        根据当前核心和扩展线程的负载情况分配线程任务

        参数:
            :param priority: 任务的优先级
            :param task_object: 要分配的任务对象，可能是异步或同步任务
        返回:
            :return: 无返回值
        执行过程:
            1. 根据任务对象的类型确定任务类型（异步或同步）
            2. 获取对应任务类型的核心线程池和扩展线程池
            3. 检查当前非满载的核心线程
                a. 如果没有非满载的核心线程
                    i. 检查是否存在扩展线程池
                    ii. 检查当前非满载的扩展线程
                    iii. 如果没有非满载的扩展线程，将任务重新放入全局任务队列
                    iv. 否则，将任务分配给任务负载最小的非满载扩展线程
                b. 如果存在非满载的核心线程，将任务分配给任务负载最小的非满载核心线程
            4. 设置线程的工作事件
        """
        task_type = "Async" if asyncio.iscoroutinefunction(task_object.taskExecute) else "Sync"
        core_thread_pool = self._AsyncCoreThread if task_type == "Async" else self._SyncCoreThread
        expand_thread_pool = self._AsyncExpandThread if task_type == "Async" else self._SyncExpandThread
        non_full_core_threads = self._checkNonFullThread(core_thread_pool)
        if not non_full_core_threads:
            if expand_thread_pool:
                non_full_expand_threads = self._checkNonFullThread(expand_thread_pool)
                if not non_full_expand_threads:
                    self._ThreadTaskQueue.put((priority, task_object))
                    return
                minimum_load_expand_thread = self._checkMinimumTaskLoadThread(non_full_expand_threads)
                minimum_load_expand_thread.addThreadTask(priority, task_object)
                minimum_load_expand_thread.ThreadWorkingEvent.set()
                return
            self._ThreadTaskQueue.put((priority, task_object))
            return
        minimum_load_core_thread = self._checkMinimumTaskLoadThread(non_full_core_threads)
        minimum_load_core_thread.addThreadTask(priority, task_object)
        minimum_load_core_thread.ThreadWorkingEvent.set()
        return

    def _checkNonFullThread(self, thread_pool: dict):
        """
        检查并返回非满载的线程对象列表

        参数:
            :param thread_pool: 线程池字典，包含所有线程对象
        返回:
            :return: 非满载的线程对象列表
        执行过程:
            1. 遍历线程池中的所有线程对象
            2. 返回任务计数未达到配置任务阈值的线程对象列表
        """
        return [obj for index, obj in thread_pool.items() if obj.getThreadTaskCount() != self._Config.TaskThreshold]

    @staticmethod
    def _checkMinimumTaskLoadThread(thread_pool):
        """
        查找并返回任务负载最小的线程对象

        参数:
            :param thread_pool: 线程池列表，包含所有线程对象
        返回:
            :return: 任务负载最小的线程对象
        执行过程:
            1. 遍历 thread_pool 列表，获取每个线程对象的任务计数
            2. 返回任务计数最小的线程对象
        """
        return min(thread_pool, key=lambda x: x.getThreadTaskCount())

    def _executionExpandPolicy(self):
        """
        执行资源扩展策略，根据当前配置选择合适的扩展方法

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 根据当前配置的 ExpandPolicy 选择相应的扩展方法
            2. 调用选择的扩展方法进行资源扩展
        """
        policy_method = {
            "NoExpand": self._noExpand,
            "AutoExpand": self._autoExpand,
            "BeforehandExpand": self._beforehandExpand,
        }
        expand_method = policy_method[self._Config.ExpandPolicy]
        expand_method()

    def _noExpand(self):
        """
        "NoExpand"策略的实现，表示不执行任何资源扩展操作

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 不执行任何操作，方法主体为空
        """
        pass

    def _autoExpand(self):
        """
        "AutoExpand"策略的实现，根据当前负载自动扩展资源

        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 获取所有核心进程和线程对象
            2. 计算当前所有核心进程和线程的总负载
            3. 计算核心进程和线程的平均负载
            4. 根据负载情况判断是否需要扩展资源
                a. 如果核心进程的平均负载超过理想负载，则尝试扩展核心进程
                b. 如果异步线程的平均负载超过理想负载，则尝试扩展异步线程
                c. 如果同步线程的平均负载超过理想负载，则尝试扩展同步线程
        异常处理:
            - 捕获psutil.NoSuchProcess异常，并将负载值设置为0
        """
        core_process_obj = [obj for index, obj in self._CoreProcess.items()]
        core_async_threads_obj = [obj for index, obj in self._AsyncCoreThread.items()]
        core_sync_threads_obj = [obj for index, obj in self._SyncCoreThread.items()]

        try:
            current_core_process_total_load = sum([obj.getProcessLoad() for obj in core_process_obj])
            current_core_async_thread_total_load = sum([obj.getThreadTaskCount() for obj in core_async_threads_obj])
            current_core_sync_thread_total_load = sum([obj.getThreadTaskCount() for obj in core_sync_threads_obj])
        except psutil.NoSuchProcess:
            current_core_process_total_load = 0
            current_core_async_thread_total_load = 0
            current_core_sync_thread_total_load = 0

        process_average_load = current_core_process_total_load / len(core_process_obj) if core_process_obj else 0
        async_thread_average_load = current_core_async_thread_total_load / len(core_async_threads_obj) if core_async_threads_obj else 0
        sync_thread_average_load = current_core_sync_thread_total_load / len(core_sync_threads_obj) if core_sync_threads_obj else 0

        ideal_load_per_process = 100 * 0.8 / (len(self._CoreProcess) + len(self._ExpandProcess))
        ideal_load_per_thread = 100 * 0.8
        if process_average_load > ideal_load_per_process:
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self._Logger.debug(f"Load reaches {int(ideal_load_per_process)}%, but unable to expand more process")

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
        "BeforehandExpand" 策略的实现，根据全局任务队列的负载提前扩展资源
        参数:
            :param 无
        返回:
            :return: 无返回值
        执行过程:
            1. 检查全局任务队列的大小是否达到全局阈值的80%
            2. 如果达到80%负载，并且允许扩展进程，则扩展核心进程
            3. 如果达到80%负载，并且允许扩展线程，则同时扩展异步线程和同步线程
        异常处理:
            - 如果无法扩展进程或线程，记录相应的调试日志
        """
        if (self._ProcessTaskQueue.qsize() + self._ThreadTaskQueue.qsize()) >= int(self._Config.GlobalTaskThreshold * 0.8):
            if self._isExpansionAllowed("Process"):
                self._expandProcess()
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more process")
            if self._isExpansionAllowed("Thread"):
                self._expandThread("Async")
                self._expandThread("Sync")
            else:
                self._Logger.debug("Load reaches 80%, but unable to expand more thread")

    def _isExpansionAllowed(self, expand_type: Literal["Process", "Thread"]) -> bool:
        """
        检查是否允许扩展指定类型的资源（进程或线程）。

        参数:
            :param expand_type: 资源类型，可以是 "Process" 或 "Thread"
        返回:
            :return: 如果允许扩展则返回 True，否则返回 False
        执行过程:
            1. 如果扩展类型是 "Process"，检查当前核心进程和扩展进程的数量是否超过最大进程数量
            2. 如果扩展类型是 "Thread"，检查当前所有线程的数量是否超过最大线程数量的限制
            3. 根据检查结果返回是否允许扩展
        """
        match expand_type:
            case "Process":
                if (len(self._CoreProcess) + len(self._ExpandProcess)) >= self._Config.MaximumProcessCount:
                    return False
                return True
            case "Thread":
                if (len(self._AsyncCoreThread) + len(self._AsyncExpandThread) + len(self._SyncCoreThread) + len(self._SyncExpandThread)) >= self._Config.MaximumThreadCount:
                    return False
                return True

    def _expandProcess(self):
        """
        扩展进程池，增加一个新的扩展进程。

        执行过程:
            1. 获取当前时间，用于记录扩展进程的存活时间
            2. 生成新的进程 ID
            3. 创建一个新的 `_ProcessObject` 实例，设置为扩展类型
            4. 启动新创建的进程
            5. 将新进程加入扩展进程池
            6. 记录新进程的存活时间，用于后续的管理和检查
        """
        current_time = time.time()
        process_id = self._generateExpandID("Process")
        process = _ProcessObject(self._Logger, process_id, "Expand", self._Config.TaskThreshold, self._TaskResultQueue, self._TaskLock, self._Config.IdleCleanupThreshold, self._Config.ProcessPriority)
        process.startProcess()
        self._ExpandProcess[process_id] = process
        self._ExpandProcessKeepAlive[process] = current_time

    def _expandThread(self, thread_type: Literal["Async", "Sync"]):
        """
        扩展线程池，增加一个新的扩展线程。

        参数:
            :param thread_type : 要扩展的线程类型，"Async" 表示异步线程，"Sync" 表示同步线程

        执行过程:
            1. 获取当前时间，用于记录扩展线程的存活时间
            2. 生成新的线程 ID
            3. 根据线程类型创建相应的线程对象
                a. 如果线程类型为 "Async"，则创建 `_AsyncThreadObject` 实例并启动线程
                b. 如果线程类型为 "Sync"，则创建 `_SyncThreadObject` 实例并启动线程
            4. 将新创建的线程加入扩展线程池
            5. 记录新线程的存活时间，用于后续的管理和检查
        """
        current_time = time.time()
        thread_id = self._generateExpandID(thread_type)
        if thread_type == "Async":
            thread = _AsyncThreadObject(self._Logger, thread_id, self._TaskResultQueue, self._TaskLock)
            thread.startThread()
            self._AsyncExpandThread[thread_id] = thread
            self._AsyncExpandThreadKeepAlive[thread] = current_time
            return
        if thread_type == "Sync":
            thread = _SyncThreadObject(self._Logger, thread_id, self._TaskResultQueue, self._TaskLock)
            thread.startThread()
            self._SyncExpandThread[thread_id] = thread
            self._SyncExpandThreadKeepAlive[thread] = current_time
            return

    def _generateExpandID(self, expand_type: Literal["Process", "Async", "Sync"]):
        """
        生成一个唯一的扩展 ID，确保该 ID 不与当前已有的扩展对象冲突。

        参数:
            :param expand_type : 扩展对象的类型，"Process" 表示进程，"Async" 表示异步线程，"Sync" 表示同步线程

        返回:
            int: 生成的唯一扩展 ID

        执行过程:
            1. 根据扩展类型选择相应的扩展对象池。
            2. 初始化基本 ID 为 0。
            3. 循环检查生成的 ID 是否已经存在于扩展对象池中。
                a. 如果基本 ID 不在扩展对象池中，则返回该 ID。
                b. 如果基本 ID 已经存在，则增加基本 ID 并继续检查，直到找到一个唯一的 ID。
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
        执行收缩策略，根据配置的策略类型来调整系统资源（进程或线程）的数量。

        根据当前配置的收缩策略 (`ShrinkagePolicy`)，调用相应的收缩方法来处理系统资源的减少。
        收缩策略包括：
            - "NoShrink"：不进行任何收缩操作
            - "AutoShrink"：根据负载自动收缩资源
            - "TimeoutShrink"：根据超时收缩资源

        执行过程:
            1. 获取当前配置的收缩策略。
            2. 根据收缩策略调用相应的收缩方法。
        """
        policy_method = {
            "NoShrink": self._noShrink,
            "AutoShrink": self._autoShrink,
            "TimeoutShrink": self._timeoutShrink,
        }
        shrink_method = policy_method[self._Config.ShrinkagePolicy]
        shrink_method()

    def _noShrink(self):
        """
        不进行任何收缩操作。

        该方法表示当前配置的收缩策略为 "NoShrink"，在这种情况下，系统不会对进程或线程进行任何收缩操作。
        """
        pass

    def _autoShrink(self):
        """
        自动收缩进程和线程资源。

        参数:
            :param 无

        返回:
            :return: 无返回值。

        执行过程:
            1. 从扩展的进程和线程中筛选出空闲的资源（即没有任务的进程和线程）。
                a. 获取所有扩展的进程，并筛选出任务计数为0的进程。
                b. 获取所有扩展的异步线程，并筛选出任务计数为0的线程。
                c. 获取所有扩展的同步线程，并筛选出任务计数为0的线程。
            2. 从记录中筛选出符合收缩超时条件的资源（即超过收缩策略超时时间的进程和线程）。
                a. 获取符合超时条件的空闲进程。
                b. 获取符合超时条件的空闲异步线程。
                c. 获取符合超时条件的空闲同步线程。
            3. 对于符合条件的空闲进程和线程，执行收缩操作。
                a. 关闭符合条件的空闲进程，并从 `self._ExpandProcess` 和 `self._ExpandProcessKeepAlive` 中删除。
                b. 关闭符合条件的空闲异步线程，并从 `self._AsyncExpandThread` 和 `self._AsyncExpandThreadKeepAlive` 中删除。
                c. 关闭符合条件的空闲同步线程，并从 `self._SyncExpandThread` 和 `self._SyncExpandThreadKeepAlive` 中删除。
        """
        expand_process_obj = [obj for index, obj in self._ExpandProcess.items()]
        expand_async_threads_obj = [obj for index, obj in self._AsyncExpandThread.items()]
        expand_sync_threads_obj = [obj for index, obj in self._SyncExpandThread.items()]

        try:
            idle_process = [obj for obj in expand_process_obj if obj.getProcessTaskCount() == 0]
            idle_async_threads = [obj for obj in expand_async_threads_obj if obj.getThreadTaskCount() == 0]
            idle_sync_threads = [obj for obj in expand_sync_threads_obj if obj.getThreadTaskCount() == 0]
        except psutil.NoSuchProcess:
            idle_process = []
            idle_async_threads = []
            idle_sync_threads = []

        allow_closed_processes = [obj for obj in self._ExpandProcessKeepAlive if time.time() - self._ExpandProcessKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]
        allow_closed_async_threads = [obj for obj in self._AsyncExpandThreadKeepAlive if time.time() - self._AsyncExpandThreadKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]
        allow_closed_sync_threads = [obj for obj in self._SyncExpandThreadKeepAlive if time.time() - self._SyncExpandThreadKeepAlive[obj] >= self._Config.ShrinkagePolicyTimeout]

        if idle_process:
            for process in idle_process:
                if process in allow_closed_processes:
                    process.closeProcess()
                    del self._ExpandProcess[process.ProcessID]
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
        基于超时策略收缩进程和线程资源。

        参数:
            :param 无

        返回:
            :return: 无返回值。

        执行过程:
            1. 从扩展的进程和线程中筛选出超时的资源（即超过收缩策略超时时间的资源）。
                a. 获取所有扩展的进程，并筛选出超过超时时间的进程。
                b. 获取所有扩展的异步线程，并筛选出超过超时时间的线程。
                c. 获取所有扩展的同步线程，并筛选出超过超时时间的线程。
            2. 对于符合超时条件的进程和线程，执行收缩操作。
                a. 关闭符合超时条件的进程，并从 `self._ExpandProcess` 和 `self._ExpandProcessKeepAlive` 中删除。
                b. 关闭符合超时条件的异步线程，并从 `self._AsyncExpandThread` 和 `self._AsyncExpandThreadKeepAlive` 中删除。
                c. 关闭符合超时条件的同步线程，并从 `self._SyncExpandThread` 和 `self._SyncExpandThreadKeepAlive` 中删除。
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
