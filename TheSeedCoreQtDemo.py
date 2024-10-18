# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
from qasync import asyncSlot

from TheSeedCore import *

if TYPE_CHECKING:
    pass


class CustomTaskFuture(TaskFuture):
    def execute(self):
        """ 你可以在这里自定义对任务结果的处理，也可以把它当成回调函数使用"""
        result = self.result()
        return result

    def asyncExecute(self):
        """ 你可以在这里自定义对任务结果的异步处理"""
        result = self.result()
        return result


class View(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_layout = QVBoxLayout(self)
        self._sub_layout = QHBoxLayout()
        self._v_layout1 = QVBoxLayout()
        self._v_layout2 = QVBoxLayout()

        self._current_time_label = QLabel(self)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_current_time)
        self._timer.start(1000)
        self._batch_test_button = QPushButton("Batch Test", self)

        self._process_total_time_label = QLabel(self)
        self._process_result_text_edit = QTextEdit(self)
        self._start_process_test_button = QPushButton("Start Process Test", self)

        self._thread_total_time_label = QLabel(self)
        self._thread_result_text_edit = QTextEdit(self)
        self._start_thread_test_button = QPushButton("Start Thread Test", self)

        self._main_layout.addWidget(self._current_time_label)
        self._main_layout.addWidget(self._batch_test_button)
        self._main_layout.addLayout(self._sub_layout)
        self._sub_layout.addLayout(self._v_layout1)
        self._sub_layout.addLayout(self._v_layout2)

        self._v_layout1.addWidget(self._process_total_time_label)
        self._v_layout1.addWidget(self._start_process_test_button)
        self._v_layout1.addWidget(self._process_result_text_edit)

        self._v_layout2.addWidget(self._thread_total_time_label)
        self._v_layout2.addWidget(self._start_thread_test_button)
        self._v_layout2.addWidget(self._thread_result_text_edit)

        self._batch_test_button.clicked.connect(self._start_batch_test)
        self._start_process_test_button.clicked.connect(self._start_process_test)
        self._start_thread_test_button.clicked.connect(self._start_thread_test)
        self.setMinimumHeight(600)

        self._process_total_time = 0
        self._process_task_total_count = 0
        self._thread_total_time = 0
        self._thread_task_total_count = 0

    def _start_batch_test(self):
        start_time = time.time()
        ConcurrentSystem.submitSystemThreadTask(ConcurrentSystem.submitProcessTask, 500, self.process_test_function, callback=self.process_test_callback, start_time=start_time)
        ConcurrentSystem.submitSystemThreadTask(ConcurrentSystem.submitThreadTask, 500, self.thread_test_function, callback=self.thread_test_callback, start_time=start_time)

    @asyncSlot()
    async def _start_process_test(self):
        # 方法1：调用 ConcurrentSystem.submitProcessTask 方法，使用回调函数来处理任务执行结果
        """
        1.1 将测试函数 process_test_function 作为参数传入，同时传入回调函数 process_test_callback
        1.2 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        1.3 任务执行完毕后，会调用回调函数 process_test_callback 来处理任务执行的结果
        1.4 如果定义了回调函数，该回调函数必须且只能接受一个参数来接收结果，请自行在回调函数中解包结果

            start_time = time.time()
            ConcurrentSystem.submitProcessTask(self.process_test_function, callback=self.process_test_callback, start_time=start_time)
        """
        # 方法2：调用 ConcurrentSystem.submitProcessTask 方法，使用 TaskFuture.result() 来获取任务执行结果
        """
        2.1 将测试函数 process_test_function 作为参数传入
        2.2 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        2.3 提交任务后不会立即返回结果，但是会返回一个 TaskFuture 实例对象，可以通过调用 TaskFuture 实例对象的 result() 方法来获取任务执行结果
        2.4 TaskFuture 实例对象的 result() 方法会阻塞当前线程，直到任务执行完毕并返回结果，你可以传递一个 timeout 参数来设置超时时间
        2.5 如果超时后未获取到任务结果将会抛出异常
        2.6 你可以继承 TaskFuture 类并重写 execute 和 asyncExecute 方法来实现对任务结果的处理逻辑
        2.7 如果你需要使用自定义的 TaskFuture 类，你可以在 ConcurrentSystem.submitProcessTask 方法中传入 future=CustomTaskFuture 参数来指定自定义的 TaskFuture 类
            
            # 默认的future
            start_time = time.time()
            future = ConcurrentSystem.submitProcessTask(self.process_test_function, start_time=start_time)
            result = future.result()
            self.process_test_callback(result)
            
            # 自定义的future
            start_time = time.time()
            future = ConcurrentSystem.submitProcessTask(self.process_test_function, future=CustomTaskFuture, start_time=start_time)
            execute_result = future.execute()
            self.process_test_callback(execute_result)
        """
        # 方法3：调用 ConcurrentSystem.submitSystemProcessTask 方法，使用 future 来获取任务执行结果
        """
        3.1 将测试函数 process_test_function 作为参数传入
        3.2 该方法支持批量提交相同的任务，可以指定 count 参数来设置任务数量
        3.3 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        3.4 该方法不支持回调函数，但是会返回一个 future 对象，可以通过调用 future.result() 方法来获取任务执行结果
        3.5 如果是批量提交，那么该方法将会返回一个列表， 里面包含了所有被提交的任务的 future 对象
        
            # 单次提交
            start_time = time.time()
            future = ConcurrentSystem.submitSystemProcessTask(self.process_test_function, start_time=start_time)
            result = future.result()
            self.process_test_callback(result)
            
            # 批量提交
            start_time = time.time()
            future = ConcurrentSystem.submitSystemProcessTask(self.process_test_function, count=4, start_time=start_time)
            for i in future:
                result = i.result()
                self.process_test_callback(result)
        """
        # 注意事项
        """
        1. 提交任务时请确保被提交的任务可以被序列化，否则该任务将会被直接抛弃，回调函数因为是在主进程执行，所以不受此限制
        2. 同时指定 callback 和 future 参数时，callback 参数指定的回调函数会被优先执行，而 future.result() 则是在其之后执行
        """
        start_time = time.time()
        for i in range(10):
            ConcurrentSystem.submitSystemThreadTask(
                ConcurrentSystem.submitProcessTask, 100, self.process_test_function,
                callback=self.process_test_callback,
                timeout=None,
                lock=False,
                lock_timeout=3,
                start_time=start_time,
            )

    @asyncSlot()
    async def _start_thread_test(self):
        # 方法1：调用 ConcurrentSystem.submitThreadTask 方法，使用回调函数来处理任务执行结果
        """
        1.1 将测试函数 thread_test_function 作为参数传入，同时传入回调函数 thread_test_callback
        1.2 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        1.3 任务执行完毕后，会调用回调函数 thread_test_callback 来处理任务执行的结果
        1.4 如果定义了回调函数，该回调函数必须且只能接受一个参数来接收结果，请自行在回调函数中解包结果

            start_time = time.time()
            ConcurrentSystem.submitThreadTask(self.thread_test_function, callback=self.thread_test_callback, start_time=start_time)
        """
        # 方法2：调用 ConcurrentSystem.submitThreadTask 方法，使用 TaskFuture.result() 来获取任务执行结果
        """
        2.1 将测试函数 thread_test_function 作为参数传入
        2.2 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        2.3 提交任务后不会立即返回结果，但是会返回一个 TaskFuture 实例对象，可以通过调用 TaskFuture 实例对象的 result() 方法来获取任务执行结果
        2.4 TaskFuture 实例对象的 result() 方法会阻塞当前线程，直到任务执行完毕并返回结果，你可以传递一个 timeout 参数来设置超时时间
        2.5 如果超时后未获取到任务结果将会抛出异常
        2.6 你可以继承 TaskFuture 类并重写 execute 和 asyncExecute 方法来实现对任务结果的处理逻辑
        2.7 如果你需要使用自定义的 TaskFuture 类，你可以在 ConcurrentSystem.submitThreadTask 方法中传入 future=CustomTaskFuture 参数来指定自定义的 TaskFuture 类

            # 默认的future
            start_time = time.time()
            future = ConcurrentSystem.submitThreadTask(self.thread_test_function, start_time=start_time)
            result = future.result()
            self.thread_test_callback(result)

            # 自定义的future
            start_time = time.time()
            future = ConcurrentSystem.submitThreadTask(self.thread_test_function, future=CustomTaskFuture, start_time=start_time)
            execute_result = future.execute()
            self.thread_test_callback(execute_result)
        """
        # 方法3：调用 ConcurrentSystem.submitSystemThreadTask 方法，使用 future 来获取任务执行结果
        """
        3.1 将测试函数 thread_test_function 作为参数传入
        3.2 该方法支持批量提交相同的任务，可以指定 count 参数来设置任务数量
        3.3 start_time参数为测试任务所需参数，你也可以指定更多任务参数，但是这些参数必须与被执行任务参数一一对应
        3.4 该方法不支持回调函数，但是会返回一个 future 对象，可以通过调用 future.result() 方法来获取任务执行结果
        3.5 如果是批量提交，那么该方法将会返回一个列表， 里面包含了所有被提交的任务的 future 对象

            # 单次提交
            start_time = time.time()
            future = ConcurrentSystem.submitSystemThreadTask(self.thread_test_function, start_time=start_time)
            result = future.result()
            self.thread_test_callback(result)

            # 批量提交
            start_time = time.time()
            future = ConcurrentSystem.submitSystemThreadTask(self.thread_test_function, count=4, start_time=start_time)
            for i in future:
                result = i.result()
                self.thread_test_callback(result)
        """
        # 注意事项
        """
        1. 同时指定 callback 和 future 参数时，callback 参数指定的回调函数会被优先执行，而 future.result() 则是在其之后执行
        2. 可以使用 submitSystemThreadTask 方法批量提交 submitThreadTask 和 submitProcessTask 方法
            在套嵌提交的情况下，submitSystemThreadTask 返回的future在调用result()时，返回的将会是 submitThreadTask 或 submitProcessTask 的future对象
            你可以通过 future.result().result() 来获取 submitThreadTask 或 submitProcessTask 的执行结果
            
            # 批量提交 submitThreadTask 或 submitProcessTask
            start_time = time.time()
            sys_future = ConcurrentSystem.submitSystemThreadTask(ConcurrentSystem.submitProcessTask, 4, self.process_test_function, start_time=start_time)
            for i in sys_future:
                result = i.result().result()
                self.thread_test_callback(result)
        """
        start_time = time.time()
        for i in range(10):
            ConcurrentSystem.submitSystemThreadTask(
                ConcurrentSystem.submitThreadTask, 100, self.thread_test_function,
                callback=self.thread_test_callback,
                timeout=None,
                lock=False,
                lock_timeout=3,
                start_time=start_time
            )

    @staticmethod
    def process_test_function(start_time: float):
        """ 测试方法，可以是异步任务也可以是同步任 """
        current_time = time.time()
        result = 0
        for i in range(10 ** 7):
            result += i ** 2
        execution_time = time.time() - current_time
        return current_time - start_time, start_time, execution_time

    @staticmethod
    async def thread_test_function(start_time: float):
        """ 测试方法，可以是异步任务也可以是同步任务 """
        current_time = time.time()
        await asyncio.sleep(2)
        execution_time = time.time() - current_time
        return current_time - start_time, start_time, execution_time

    def process_test_callback(self, result):
        """测试回调函数，必须接受一个参数来接收任务执行结果"""
        self._process_task_total_count += 1
        current_time = time.time()
        self._process_total_time += result[2]
        self._process_total_time_label.setText(f"Process Total Time: {self._process_total_time:.3f}")
        self._process_result_text_edit.append(f"[Process] {self._process_task_total_count}.arrivals time: {result[0]:.3f}")
        self._process_result_text_edit.append(f"[Process] {self._process_task_total_count}.execution time: {result[2]:.3f}")
        self._process_result_text_edit.append(f"[Process] {self._process_task_total_count}.callback time: {current_time - result[1]:.3f}")

    def thread_test_callback(self, result):
        """测试回调函数，必须接受一个参数来接收任务执行结果"""
        self._thread_task_total_count += 1
        current_time = time.time()
        self._thread_total_time += result[2]
        self._thread_total_time_label.setText(f"Thread Total Time: {self._thread_total_time:.3f}")
        self._thread_result_text_edit.append(f"[Thread] {self._thread_task_total_count}.arrivals time: {result[0]:.3f}")
        self._thread_result_text_edit.append(f"[Thread] {self._thread_task_total_count}.execution time: {result[2]:.3f}")
        self._thread_result_text_edit.append(f"[Thread] {self._thread_task_total_count}.callback time: {current_time - result[1]:.3f}")

    def _update_current_time(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self._current_time_label.setText(f"Current Time: {current_time}")


if __name__ == "__main__":
    qt = QApplication(sys.argv)
    ConnectNERvGear(Priority="HIGH", CoreProcessCount=4, MaximumProcessCount=8, CoreThreadCount=16, MaximumThreadCount=32, ExpandPolicy="AutoExpand", ShrinkagePolicy="AutoShrink")
    v = View()
    v.show()
    LinkStart()
