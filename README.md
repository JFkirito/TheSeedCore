# TheSeedCore

## 简介

TheSeedCore 是一个综合性的模块化框架，旨在满足现代应用开发的多样化需求。无论是构建高性能、可扩展的应用程序，还是集成复杂的系统，TheSeedCore 都提供了强大的基础，涵盖广泛的功能。凭借其模块化、安全性和灵活性的设计，TheSeedCore 能够帮助开发者创建可靠且易于维护的解决方案

## 主要特性

### 模块化架构

- TheSeedCore 的模块化架构允许轻松定制和扩展。每个模块都专为处理特定任务而设计，确保了关注点的分离，便于维护和扩展

### 全面的并发支持

- 框架包含强大的并发模块，支持多线程和多进程，提高系统性能和资源利用率。这使得任务管理和执行更加高效，适用于高性能应用。

### PyQt/PySide 支持

- TheSeedCore 集成了对 Qt 的支持，特别是在回调执行和界面操作方面。通过 PyQt/PySide 事件循环管理回调和异步任务，确保图形界面应用的流畅性和响应性。

### Kafka 支持

- TheSeedCore 的 Kafka 服务模块提供了管理 Apache Kafka 集群的全面支持。包括集群配置、生产者和消费者管理以及主题处理，适用于分布式消息系统。

### 多功能数据库集成

- TheSeedCore 提供与多种数据库（包括 SQLite、MySQL 和 Redis）的无缝集成。通过统一的数据库操作接口，开发者可以轻松切换不同数据库，而无需修改代码。

### 高级加密功能

- TheSeedCore 提供先进的数据加密和解密功能，支持AES和RSA加密，提供密钥的生成、管理和使用功能。配备密钥管理和安全数据处理，确保您的数据始终受到保护。

### 外部服务管理

- 框架包含一个外部服务模块，支持 Node.js 包的安装和管理。这使得集成外部服务和扩展应用功能变得简单。

### 先进的网络服务

- 网络模块包括 HTTP 服务器和 WebSocket 服务器/客户端功能，支持异步操作和安全连接，并且消息处理可定制，适用于实时通信和高效的网络操作。

### 灵活的日志系统

- TheSeedCore 提供先进的日志模块，支持颜色格式化的控制台输出和文件日志记录，并支持日志轮换。可配置的日志级别和调试模式确保您能够详细了解应用程序的操作和错误。

### 高度的可定制性和扩展性

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

├── ConcurrentSystemModule.py

├── DatabaseModule.py

├── EncryptionModule.py

├── ExternalServicesModule.py

├── KafkaServiceModule.py

├── LoggerModule.py

└── NetworkModule.py

## 环境要求

- 系统环境：Windows


- Python 3.11 或更高版本

## 使用说明

### 模块依赖

1. TheSeedCore除了并发系统模块 `ConcurrentSystemModule` 和日志模块 `LoggerModule` 外，其他模块都需要一定的依赖库支持。

2. `linkStart` 方法在启动时会检查各个模块的依赖，如果某个模块缺少依赖，TheSeedCore会提示应该安装哪些依赖库以支持该模块的使用。

3. 如果在缺少依赖的情况下仍然导入该模块的类，系统将会抛出 `ModuleNotFoundError` 异常。

4. 如果不希望看到依赖检查信息，可以在调用 `linkStart` 时传递`False`，依赖检查信息将不会打印到控制台。

```
from TheSeedCore import *

if __name__ == "__main__":
    # 传递False将不会显示依赖检查信息
    linkStart()
```

### 启动和关闭

1. **_启动_**
    1. 在程序入口处必须调用 `linkStart` 方法来启动TheSeedCore，该方法会启动主事件循环并初始化TheSeedCore执行您的应用程序。

2. **_主事件循环_**
    1. TheSeedCore会自动获取当前异步事件循环来作为回调执行的主事件循环。
    2. 如果导入TheSeedCore之前没有创建事件循环，TheSeedCore会立即创建一个并存储在 `MainEventLoop` 中，后续您可以调用 `MainEventLoop` 来获取主事件循环。

3. **_关闭_**
    1. 退出应用时请调用 `linkStop` 方法，该方法会清理所有由TheSeedCore创建的所有资源后关闭主事件循环并退出应用程序。

```
import asyncio
from TheSeedCore import *

class MyApplication:
    def __init__(self, some_value):
        self.value = some_value
        self._initApplication()
        
    def _initApplication(self):
        # 在这里用主事件循环创建一个异步任务
        MainEventLoop.create_task(self.printValue())
        
    async def printValue(self):
        await asyncio.sleep(1)
        print(self.value)
        # 在这里调用linkStop关闭应用
        linkStop()
    
if __name__ == "__main__":
    app = MyApplication("This is TheSeeCore. Welcome home sir")
    linkStart()
```

### Qt模式

1. Qt模式依赖 `qasync` 库来管理Qt事件循环，集成 `PyQt` / `PySide` 时，请确保安装了 `qasync` 库，以确保异步任务和回调的正确执行。

2. 在程序入口处实例 `QApplication` 后，TheSeedCore会自动识别 `QApplication` 实例并使用 `qasync` 库来管理Qt事件循环。

3. 在Qt模式下请确保在程序入口处实例 `QApplication` 后再调用 `linkStart` 方法，否则即使安装了Qt库也无法正确执行异步任务和回调，并可能会导致UI未响应。

4. TheSeedCore会自动将 `QApplication` 实例的 `aboutToQuit` 信号连接到 `linkStop` 方法，以确保在退出应用时正确关闭TheSeedCore。

```
import sys

# 这里替换为PyQt或PySide
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication

from TheSeedCore import linkStart


class MyApplication:
    def __init__(self):
        self.widget = QWidget()
        self.widget.setWindowTitle("TheSeedCoreQtMode")
        self.widget.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self.widget)
        self.label = QLabel("TheSeedCore")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.widget.show()


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    window = MyApplication()
    linkStart()

```

### 模块调用

1. **TheSeedCore 的模块都是独立的，在依赖允许的情况下可以单独调用或与其他模块组合使用。**
2. **可以使用 `from TheSeedCore import *` 导入所有可用类**
3. **在调用模块之前请确保已经安装了该模块所需的依赖。**

### 目录

- **以下文件夹根据不同环境会存放在不同目录**
    1. 开发环境：目录会生成在和TheSeedCore同级的目录下。
    2. 生产环境：目录会生成在和应用程序同级的目录下。

- **_TheSeedCoreData_**
    1. `Database` ： 数据库文件夹。
    2. `ExternalServices` ： 外部服务文件夹。
    3. `Logs` ： 日志文件夹。

- **_ExternalLibrary_**
    1. 外部库文件夹。

### 加密

- **_AES_**
    1. TheSeedCore 的加密器被设计为启动时使用 _设备编码_ + _自定义key_ 来生成 `Keyring` 的唯一标识符并使用该标识符存储AES秘钥。
    2. 如果分发时携带了使用 `aesEncryptData` 或 `aesEncrypt` 方法加密的数据，或数据库使用了数据加密，分发的应用将无法解密数据

- **_RSA_**
    1. `generateRSAKeys`方法会立即返回未加密的公私钥对
    2. 如果指定了存储路径和 `store_locally` 参数，TheSeedCore 会使用该加密器实例的AES将私钥加密后存储在指定的路径

- **如果分发时必须携带加密数据，可以采用以下方案**。
    1. 使用 `generateRSAKeys` 方法不指定存储路径生成公私钥对
    2. 使用 `generateRSAKeys` 方法返回的公钥加密数据，然后将私钥手动保存或将私钥不加密存储进数据库中，分发时携带私钥
    3. 运行时使用私钥解密数据后在客户端再次将数据加密存储，随后删除私钥。

### 并发系统

- **_队列和模式_**
  - 系统使用生产者-消费者模式，并使用非阻塞队列进行IPC(Inter-Process Communication)
      1. 全局任务队列：由全局线程任务队列和全局进程任务队列组成。
      2. 进程任务队列：每个进程都有自己的任务队列，进程之间的任务不会相互干扰。
      3. 线程任务队列：每个线程都有自己的任务队列，包括进程中的线程，线程的任务队列为优先级队列。

- **_延迟_**
  - 由于队列的特性，IPC会有一定的延迟，下面是8个进程100次网络请求任务的单任务延迟和多任务延迟的测试结果。
      1. 单任务到达时间
          1. 最小时间：约 0.1313 秒
          2. 平均时间：约 0.1851 秒
          3. 最大时间：约 0.2491 秒
      2. 多任务到达时间
          1. 最小时间：约 0.1965 秒
          2. 平均时间：约 6.8159 秒
          3. 最大时间：约 13.9273 秒
      3. 实际的延迟可能会受到以下因素的影响
          1. 系统负载
          2. 数据量和复杂性
          3. 网络和硬件环境

- **_线程_**
  - 系统线程
    1. 负载均衡线程：轮询检查进程和线程的负载情况并根据配置的负载均衡策略来扩展和收缩线程和进程。
    2. 进程任务分配线程：轮询从全局进程任务队列中获取任务并根据所有进程的负载情况分配任务。
    3. 线程任务分配线程：轮询从全局线程任务队列中获取任务并根据所有线程的负载情况分配任务。
  - 核心线程/扩展线程
    1. 核心线程和扩展线程主要运行在主进程中，适合处理一些IO密集型任务。
    2. 核心线程会在系统启动时创建并一直运行，扩展线程会根据负载均衡策略自动创建和销毁。
    3. 线程分为同步线程和异步线程，系统启动和负载均衡时时会根据核心线程数和最大线程数对等创建和收缩同步线程和异步线程。

- **_进程_**
  - 进程线程
    1. 每个进程都有一组同步线程和异步线程，进程会根据任务类型自动分配任务给同步线程或异步线程。
    2. 进程线程数是固定的，不会根据负载均衡策略自动创建和销毁。
  - 核心进程/扩展进程
    1. 系统会根据配置创建一定数量的进程，如果没有指定则根据物理CPU核心数动态创建并设置最大进程数。
    2. 核心进程会在系统启动时创建并一直运行，扩展进程会根据负载均衡策略自动创建和销毁。

- **_任务序列化处理器_**
  - 由于整个系统使用非阻塞队列进行IPC，在传递任务时可能会遇到无法序列化的情况，为此系统提供了任务序列化处理器。
  - 可以继承 `TaskSerializationProcessor` 类并实现 `restoreUnserializableAttr` 方法来处理无法序列化的属性。

- **_配置_**
  - `ConcurrentSystemConfig`
    - **`CoreProcessCount`**：核心进程数，默认为None，系统会根据物理CPU核心数动态设置。
    - **`CoreThreadCount`**：核心线程数，默认为None，系统会根据核心进程数动态设置。
    - **`MaximumProcessCount`**：最大进程数，默认为None，系统会根据CPU核心数动态设置。
    - **`MaximumThreadCount`**：最大线程数，默认为None，系统会根据最大进程数动态设置。
    - **`IdleCleanupThreshold`**：进程内存空闲清理阈值，默认为None，系统会根据负载均衡策略自动清理进程内存。
    - **`ProcessPriority`**：进程优先级，默认为NORMAL。
    - **`TaskThreshold`**：任务阈值，默认为None，系统会根据物理CPU核心数和物理内存自动计算阈值。
    - **`GlobalTaskThreshold`**：全局任务队列阈值，默认为None，系统会根据物理CPU核心数和物理内存总量自动计算阈值。
    - **`TaskRejectionPolicy`**：任务拒绝策略，默认为 `Abandonment` 。
    - **`RejectionPolicyTimeout`**：超时拒绝策略的超时时间，默认为3秒。
    - **`ExpandPolicy`**：扩展策略，默认为 `AutoExpand` 。
    - **`ShrinkagePolicy`**：收缩策略，默认为 `AutoShrink` 。
    - **`ShrinkagePolicyTimeout`**：可以理解为KeepAlive的时间，默认15秒。如果收缩策略为 `AutoShrink` 扩展线程/进程在没有工作和任务时超过这个时间将会被销毁。
    ```
    from TheSeedCore import *

    config = ConcurrentSystemConfig(
        CoreProcessCount=2,
        CoreThreadCount=6,
        MaximumProcessCount=8,
        MaximumThreadCount=12,
        IdleCleanupThreshold=10,
        ProcessPriority="NORMAL",
        TaskThreshold=100,
        GlobalTaskThreshold=1000,
        TaskRejectionPolicy="Abandonment",
        RejectionPolicyTimeout=5,
        ExpandPolicy="AutoExpand",
        ShrinkagePolicy="AutoShrink",
        ShrinkagePolicyTimeout=30
    )

    if __name__ == "__main__":
        concurrent_system = TheSeedCoreConcurrentSystem(config)
        concurrent_system.startSystem()
        linkStart()
    ```

- **_提交任务_**
  - `submitProcessTask` 和 `submitThreadTask` 方法用于提交进程任务和线程任务，参数是一致的。
    - **task**：任务函数。
    - **priority**：任务优先级，默认为0。
    - **callback**：任务完成后的回调函数，默认为None。
    - **serialization_processor**：任务序列化处理器，默认为None。
    - **is_lock**：是否锁定任务，默认为False。
    - **lock_holding_time**：锁定任务的时间，默认为3。
    - **is_gpu_boost**：是否使用GPU加速，默认为False。
    - **gpu_id**：GPU ID，默认为0。
    - **is_retry**：是否重试，默认为False。
    - **max_retries**：最大重试次数，默认为3。
    - ***args**：任务函数的参数。
    - ****kwargs**：任务函数的关键字参数。
    ```
    import time
    from TheSeedCore import *
    
    def testIOBound():
        start_time = time.time()
        time.sleep(1)  # 模拟IO操作
        result = time.time() - start_time
        return f"{result:.4f}\n"
    
    def testCallback(result):
        print(result)
    
    if __name__ == "__main__":
        concurrent_system = TheSeedCoreConcurrentSystem()
        concurrent_system.startSystem()
        for i in range(10):
            concurrent_system.submitProcessTask(testIOBound, callback=testCallback)
        linkStart()
    ```

## 快速开始

```
pip install requirements.txt
```

```
import asyncio
from TheSeedCore import *

async def testFunction():
    print("This is TheSeedCore. Welcome home sir")
    for i in range(10):
        await asyncio.sleep(1)
        print("System shutdown countdown:", 10 - i)
    print("System shutdown")
    linkStop()
    
if __name__ == "__main__":
    MainEventLoop.create_task(testFunction())
    linkStart()
```

## 接口文档
- 接口文档详见[TheSeedCoreInterface](TheSeedCoreInterface.md)。

## 许可证

此项目在 MIT许可下发布，您可以自由使用，复制，修改，分发本项目。
请查阅 [LICENSE](LICENSE) 文件获取更多信息。
