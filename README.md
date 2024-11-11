# TheSeedCore

## 简介

TheSeedCore 是一个综合性的模块化框架，旨在满足现代应用开发的多样化需求。无论是构建高性能、可扩展的应用程序，还是集成复杂的系统，TheSeedCore 都提供了强大的基础，涵盖广泛的功能。凭借其模块化、安全性和灵活性的设计，TheSeedCore 能够帮助开发者创建可靠且易于维护的解决方案

## 主要特性

### 全面的并发支持

- 提供了对并发任务的配置与管理支持，能够有效处理多线程与多进程任务，确保系统的高效运行和资源的最佳利用。

### 多功能数据库集成

- TheSeedCore 提供与多种数据库（包括 SQLite、MySQL）的无缝集成。通过统一的数据库操作接口，开发者可以轻松切换不同数据库，而无需修改代码。

### PyQt/PySide 支持

- 集成对 Qt 的支持，特别是在回调执行和界面操作方面。通过 PyQt/PySide 事件循环管理回调和异步任务，确保图形界面应用的流畅性和响应性。

### 高级加密功能

- TheSeedCore 提供先进的数据加密和解密功能，支持AES和RSA加密，提供密钥的生成、管理和使用功能。配备密钥管理和安全数据处理，确保您的数据始终受到保护。

### 先进的网络服务

- 网络模块包括 HTTP 服务器和 WebSocket 服务器/客户端功能，支持异步操作和安全连接，并且消息处理可定制，适用于实时通信和高效的网络操作。

### 灵活的日志系统

- TheSeedCore 提供先进的日志模块，支持颜色格式化的控制台输出和文件日志记录，并支持日志轮换。可配置的日志级别和调试模式确保您能够详细了解应用程序的操作和错误。

### 可扩展性与可配置性

- TheSeedCore 设计高度可定制和扩展。其模块化方法允许开发者轻松添加新功能并与其他系统集成，确保框架能够随应用需求的增长而扩展。

### 详细的错误处理和日志记录

- TheSeedCore 的每个模块都配备了完善的错误处理和详细的日志记录功能，确保能够及时识别和解决任何问题，便于调试和维护应用的稳定性。

## 使用场景

TheSeedCore 框架适用于需要高并发处理、安全数据操作、实时通讯和复杂日志管理的各种应用程序，例如：

- **企业级后端服务及应用**
    - **企业资源规划 (ERP) 系统**：整合财务、采购、人力资源等业务流程。
    - **客户关系管理 (CRM) 系统**：管理客户信息，提升客户服务和销售效率。
    - **供应链管理 (SCM) 系统**：自动化库存跟踪和管理，实时更新库存状态，预测需求，优化库存水平。集成供应商数据，自动化采购订单处理，评估和管理供应商绩效。
    - **人力资源管理 (HRM) 系统**：允许员工自行管理个人信息、请假、报销等。自动化招聘流程，从简历筛选到面试安排，以及员工绩效跟踪和发展规划。
    - **商务智能 (BI) 系统**：提供强大的数据分析工具，帮助企业从大量数据中提取有价值的业务洞察。定制化仪表板展示关键性能指标(KPI)，助力决策者快速做出决策。


- **云计算和微服务**
    - **容器化和微服务架构**：为各种微服务提供日志记录、配置管理和数据库支持。
    - **云资源管理**：动态管理计算资源，如自动扩展、负载均衡和资源监控。


- **数据处理和分析**
    - **大数据处理**：处理和分析海量数据，支持数据仓库和数据湖的建设。
    - **实时数据流分析**：对来自IoT设备或在线服务的数据进行实时分析和反馈。
    - **人工智能和机器学习**：支持模型训练、数据预处理和模型部署。


- **安全和合规**
    - **数据加密和安全**：确保传输和存储中的数据安全，支持多种加密标准。
    - **合规性监控**：自动检测系统运行和数据处理是否符合法规要求。


- **网络通信**
    - **实时通信服务**：支持IM、实时视频会议等应用的后端服务。
    - **API管理和微服务通信**：管理API网关，提供服务间通信的安全和效率。


- **高性能计算 (HPC) 应用**
    - **科学模拟和计算**：用于复杂的科学计算和模拟，如气候模型、物理仿真等。
    - **金融建模**：进行高速的金融市场模拟和风险分析。


- **智能城市和IoT**
    - **智能交通系统**：实时分析交通数据，优化交通流和信号控制。
    - **智能监控系统**：处理和分析从各种传感器和摄像头收集的大量数据，提高城市管理效率和安全。

## 框架结构

/TheSeedCore

│

├── init.py

├── Concurrent.py

├── Database.py

├── InstanceManager.py

├── LoggerModule.py

├── Network.py

└── Security.py

## 环境要求

- 系统环境：Windows, Linux, macOS


- Python 3.11 或更高版本

## 使用说明

### 模块依赖

1. `ConnectTheSeedCore` 方法在启动时会检查各个模块的依赖，如果某个模块缺少依赖，TheSeedCore会提示应该安装哪些依赖库以支持该模块的使用。

2. 如果在缺少依赖的情况下仍然使用该模块的功能，将会抛出 `ModuleNotFoundError` 异常。

3. 如果不希望看到依赖检查信息，可以在调用 `ConnectTheSeedCore` 时传递 `check_env=False`，依赖检查信息将不会显示在控制台中。

```python
import TheSeedCore as TSC

if __name__ == "__main__":
    # 传递check_env=False将不会显示依赖检查信息
    TSC.ConnectTheSeedCore(check_env=False)
    TSC.LinkStart()
```

### 启动和关闭

1. 在程序入口处必须先调用 `ConnectTheSeedCore` 方法来初始化TheSeedCore，该方法会检查相关组件和依赖的完整性以及启动一些必要的服务。该方法接受以下参数：
    - **`check_env`**：是否检查环境依赖，默认为`True`。
    - **`quit_qapp`**：异步事件循环退出时是否退出Qt应用程序，PySide6版本小于6.7.0时该值不生效，默认为`True`。
    - **`handle_sigint`**：是否处理SIGINT信号，PySide6版本小于6.7.0时该值不生效，默认为`False`。
    - **`MainPriority`**：主进程优先级，可选，默认为`Priority.NORMAL`。
    - **`CoreProcessCount`**：核心进程数，框架会自动检测最大值，为`None`时进程池将不可用，默认为`None`。
    - **`CoreThreadCount`**：核心线程数，框架会自动检测最大值，为`None`时自动设置，默认为`None`。
    - **`MaximumProcessCount`**：最大进程数，框架会自动检测最大值，为`None`时自动设置，默认为`None`。
    - **`MaximumThreadCount`**：最大线程数，框架会自动检测最大值，为`None`时自动设置，默认为`None`。
    - **`IdleCleanupThreshold`**：进程内存空闲清理阈值，为`None`时自动设置，默认为`None`。
    - **`TaskThreshold`**：每个进程和线程的任务数量阈值，为`None`时自动设置，默认为`None`。
    - **`GlobalTaskThreshold`**：全局任务队列阈值，为`None`时自动设置，默认为`None`。
    - **`ExpandPolicy`**：扩展策略，默认为`ExpandPolicy.AutoExpand`。
    - **`ShrinkagePolicy`**：收缩策略，默认为`ShrinkagePolicy.AutoShrink`。
    - **`ShrinkagePolicyTimeout`**：收缩策略超时时间，默认为`15`。
    - **`PerformanceReport`**：性能报告，为`True`时启用，默认为`True`。
2. `ConnectTheSeedCore`会自动创建主事件循环，您可以调用 `MainEventLoop()` 来获取主事件循环并进行操作。
3. 退出应用时请调用 `LinkStop` 方法，该方法会清理所有由TheSeedCore创建的所有资源后关闭主事件循环并退出应用程序。

```python
import asyncio
import time

import TheSeedCore as TSC

task_total_count = 0
execution_count = 10


async def shutdown_system():
    for i in range(10):
        await asyncio.sleep(1)
        print("System shutdown countdown:", 10 - i)
    print("System shutdown")
    TSC.LinkStop()


async def example_function(start_time: float):
    current_time = time.time()
    await asyncio.sleep(2)
    execution_time = time.time() - current_time
    return start_time, current_time - start_time, execution_time


async def example_function_callback(result: tuple[float, float, float]):
    callback_time = time.time() - result[0]
    arrival_time = result[1]
    execution_time = result[2]
    global task_total_count, execution_count
    task_total_count += 1
    print(f"Task{task_total_count}. Callback time: {callback_time:.3f}, Arrival time: {arrival_time:.3f}, Execution time: {execution_time:.3f}")
    if task_total_count == execution_count:
        print("All example functions have been completed.")
        await shutdown_system()


async def countdown():
    for i in range(2):
        await asyncio.sleep(1)
        print(f"The example will complete in {2 - i} seconds.")
    print("Example completed")


async def main_function():
    global execution_count
    start_time = time.time()
    print("Start example function")
    for i in range(execution_count):
        TSC.submitThreadTask(example_function, callback=example_function_callback, start_time=start_time)


if __name__ == "__main__":
    TSC.ConnectTheSeedCore()
    TSC.MainEventLoop().create_task(main_function())
    TSC.MainEventLoop().create_task(countdown())
    TSC.LinkStart()

```

### Qt模式

1. Qt模式依赖 `qasync` 库来管理Qt事件循环，集成 `PyQt` / `PySide` 时，请确保安装了 `qasync` 库，以确保异步任务和回调的正确执行。

2. 如果使用的是 `PySide6.7.0` 及以上版本可以不依赖 `qasync` 库。

3. 在Qt模式下请确保在程序入口处实例 `QApplication` 后再调用 `ConnectTheSeedCore` 方法，否则即使安装了Qt库也无法正确执行异步任务和回调，并可能会导致UI未响应。

4. TheSeedCore会自动将 `QApplication` 实例的 `aboutToQuit` 信号连接到 `LinkStop` 方法，以确保在退出应用时正确关闭TheSeedCore。

5. 如果要兼容PyQt或PySide，请确保 `ConnectTheSeedCore` 的调用在实例化 `QApplication` 之后，并且实例您的应用程序后调用 `LinkStart` 方法启动TheSeedCore。

```python

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QTextEdit

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

    @TSC.AsyncTask()
    async def _start_process_test(self):
        start_time = time.time()
        for i in range(1000):
            TSC.submitProcessTask(self.process_test_function, callback=self.process_test_callback, start_time=start_time)

    @TSC.AsyncTask()
    async def _start_thread_test(self):
        start_time = time.time()
        for i in range(1000):
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
    TSC.ConnectTheSeedCore()
    w = TestWidget()
    w.show()
    TSC.LinkStart()

```

### 并发

- **装饰器**：
    - **`@AsyncTask`**：异步任务装饰器，用于将异步函数提交到主事件循环执行。
    - **`@ProcessTask`**：进程任务装饰器，用于将进程任务提交到进程池执行。
    - **`@ThreadTask`**：线程任务装饰器，用于将线程任务提交到线程池执行。
- **任务参数**：
    - **`task`**：任务函数。
    - **`priority`**：任务优先级，可选，范围0-10，值越低优先级越高，默认为0。
    - **`callback`**：任务回调函数，可选。
    - **`future`**：提交任务后立即返回的任务的Future对象，可选, 默认为TaskFuture类的实例对象。
    - **`lock`**：任务锁，可选。
    - **`lock_timeout`**：任务锁超时时间，可选。
    - **`timeout`**：任务超时时间，可选。
    - **`gpu_boost`**：GPU加速，可选，默认为False。
    - **`gpu_id`**：GPU设备ID，可选，默认为0。
    - **`retry`**：任务是否重试，可选，默认为True。
    - **`max_retries`**：最大重试次数，可选，默认为3。
- **任务提交**：
    - **`submitAsyncTask`**：提交一个异步任务到主事件循环。
    - **`submitProcessTask`**：提交一个进程任务。
    - **`submitThreadTask`**：提交一个线程任务。
    - **`submitSystemProcessTask`**：提交一个系统进程任务。
    - **`submitSystemThreadTask`**：提交一个系统线程任务。

### 目录

- **以下文件夹根据不同环境会存放在不同目录**
    1. 开发环境：目录会生成在和TheSeedCore同级的目录下。
    2. 生产环境：目录会生成在和应用程序同级的目录下。

- **_TheSeedCoreData_**
    1. `Database` ： 数据库文件夹。
    2. `Logs` ： 日志文件夹。
- **_TheSeedCoreExternalService_**: 外部服务文件夹
- **_TheSeedCoreExternalLibrary_**: 外部库文件夹

### 加密

1. TheSeedCore 的加密器被设计为启动时使用 _设备编码_ + _自定义key_ 来生成 `Keyring` 的唯一标识符并使用该标识符存储AES秘钥。
2. 如果分发时携带了加密的数据，或数据库使用了数据加密，被分发的应用将无法解密数据

## 接口文档

- 接口文档详见[TheSeedCoreInterface](TheSeedCoreInterface.md)。

## 许可证

此项目在 MIT许可下发布，您可以自由使用，复制，修改，分发本项目。
请查阅 [LICENSE](LICENSE) 文件获取更多信息。
