# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QTextEdit
from qasync import asyncSlot

import TheSeedCore as TSC

if TYPE_CHECKING:
    pass


class TestWidget(QWidget):
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
        TSC.submitSystemThreadTask(TSC.submitProcessTask, 1000, self.process_test_function, callback=self.process_test_callback, start_time=start_time)
        TSC.submitSystemThreadTask(TSC.submitThreadTask, 1000, self.thread_test_function, callback=self.thread_test_callback, start_time=start_time)

    @asyncSlot()
    async def _start_process_test(self):
        start_time = time.time()
        for i in range(100):
            TSC.submitProcessTask(self.process_test_function, callback=self.process_test_callback, start_time=start_time)

    @asyncSlot()
    async def _start_thread_test(self):
        start_time = time.time()
        for i in range(100):
            TSC.submitThreadTask(self.thread_test_function, callback=self.thread_test_callback, start_time=start_time)

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
        # time.sleep(2)
        await asyncio.sleep(2)
        execution_time = time.time() - current_time
        return current_time - start_time, start_time, execution_time

    # noinspection PyUnresolvedReferences
    @staticmethod
    def process_gpu_test_function(start_time: float):
        current_time = time.time()
        x = torch.randn(3000, 3000).cuda()
        y = torch.randn(3000, 3000).cuda()
        result = torch.matmul(x, y)
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
    TSC.ConnectTheSeedCore(check_env=True, MainPriority=TSC.Priority.HIGH, CoreProcessCount=4, CoreThreadCount=4, ExpandPolicy=TSC.ExpandPolicy.AutoExpand, ShrinkagePolicy=TSC.ShrinkagePolicy.AutoShrink)
    w = TestWidget()
    w.show()
    TSC.LinkStart()
