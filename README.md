# TheSeedCore

## 简介

TheSeedCore 是一个高度模块化和可扩展的框架，旨在为开发复杂的应用程序提供一个坚实的基础。框架集成了多个核心模块，包括并发处理、配置管理、数据库操作、加密功能、外部服务集成、日志记录、网络服务以及初始化启动流程，使其成为构建高效、安全和可维护应用程序的理想选择。

## 主要特性

每个模块都被设计为低耦合和高内聚，可以独立于其他模块工作，同时提供接口与其他模块交互，以完成复杂的业务场景。

### 模块化架构

- **高度可扩展**：TheSeedCore 设计为高度模块化的框架，可以轻松集成到各种软件架构中，支持独立或协同工作。


- **组件化设计**：通过独立且互联的模块实现功能，涵盖并发系统、配置管理、数据库操作、加密服务、外部服务集成、日志记录以及网络服务。


- **模块交互与扩展**：模块之间通过接口交互，支持业务逻辑实现；同时提供模块的扩展和定制，满足不同需求。

### 强大的并发系统

- **多进程与多线程**：支持并发处理以及并行计算，提高系统性能和资源利用率。


- **负载均衡与任务优先级管理**：根据框架的资源使用率以及任务数量，实现负载均衡，优化资源分配；根据任务重要性调整执行优先级。

### 数据库管理

- **支持多种数据库**：支持 SQLite 和 Redis 数据库以及对应的事务管理，提供灵活的数据存储和查询选项。


- **数据安全与完整性**：提供数据加密和事务管理，确保数据安全性和一致性。

### 安全和数据保护

- **全面的加密解决方案与密钥管理**：提供先进的数据加密和解密功能，支持AES和RSA加密；提供密钥的生成、管理和使用功能。

### 配置和服务管理

- **动态配置与外部服务集成**：支持运行时配置更新；简化Node.js等第三方服务的集成。


- **服务控制**：无缝启动和停止外部服务。

### 网络通信能力

- **HTTP与WebSocket支持**：提供高性能HTTP服务器和实时WebSocket服务。


- **扩展性与实时互动**：轻松添加新路由和处理程序；支持构建实时通信应用。

### 日志记录

- **颜色编码与文件轮换**：不同日志级别以不同颜色显示，提升可读性；自动按天轮换日志文件。


- **调试模式**：轻松开启或关闭调试模式，便于开发过程中的详细日志查看。

### 易用性和维护性

- **清晰的API设计**：提供直观的API，简化开发过程，减少学习曲线。


- **详细的错误处理和反馈**：系统自动记录错误信息并提供反馈，帮助开发者快速定位和解决问题。

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

├── ConcurrencySystemModule.py

├── ConfigModule.py

├── DatabaseModule.py

├── EncryptionModule.py

├── ExternalServicesModule.py

├── LoggerModule.py

└── NetworkModule.py

## 环境要求

- 系统环境：Windows


- Python 3.11 或更高版本


- Node.js


- 相关 Python 库：aiohttp, asyncio, websockets,requests, redis, rsa, Crypto

## 使用说明

### 启动

必须在程序入口使用 TheSeedCore 的 `linkStart` 方法启动，并将应用作为参数传入，TheSeedCore 会自动管理并实例应用。

### 关闭

在应用退出时，进行自定义的清理后，请调用 TheSeedCore 的 `linkStop` 方法关闭 TheSeedCore， 此方法会关闭和清理由 TheSeedCore 创建的所有资源。

### 模块调用

TheSeedCore 的模块都是独立的，可以单独调用或与其他模块组合使用。

### linkStart参数

- **`application`**：应用实例，必须是一个可调用的类对象。


- **`basic_system_path`**：基础系统路径，默认为 `None`。
    - 为None时，TheSeedCore会在当前目录下创建TheSeedData文件夹，用于存放日志文件、数据库文件等数据文件。


- **`concurrency_system_config`**：并发系统配置，默认为 `None`。
    - 可以实例`ConfigModule`模块的`ConcurrencySystemConfig`数据类自定义并发系统的配置以及性能。
    - 为None时，TheSeedCore会根据系统的硬件配置自动设置合适的配置值。


- **`banner_mode`**：Banner的颜色显示模式，默认为`Solid`。
    - 只接受 `Solid` 和 `Gradient`。


- **`debug`**：是否启用调试模式，默认为 False。
    - 开启调试模式会将日志记录输出到控制台中。

### 目录

- **以下目录会在TheSeedCore启动时自动生成**：
    - **`ExternalLibrary`**：外部库文件夹。
    - **`TheSeedData`**：用于存放日志文件、数据库文件等数据文件。


- **开发环境**: 目录会生成在和TheSeedCore同级的目录下。


- **生产环境**: 目录会生成在和应用程序同级的目录下。

### 加密

- **AES**：TheSeedCore 的加密器被设计为启动时使用 设备编码 + 自定义key 来生成Keyring的唯一标识符并使用该标识符存储AES秘钥。如果分发时携带了使用 `aesEncryptData` 或 `aesEncrypt` 方法加密的数据，或数据库使用了数据加密，分发的应用将无法解密数据


- **RSA**：`generateRSAKeys`方法会立即返回未加密的公私钥对，如果指定了存储路径和  `store_locally`参数，TheSeedCore 会使用该加密器实例的AES将私钥加密后存储在指定的路径


- **如果分发时必须携带加密数据，可以采用以下方案**。
    - **使用 `generateRSAKeys` 方法不指定存储路径生成公私钥对，用 `generateRSAKeys` 方法返回的公钥加密数据，然后将私钥手动保存或将私钥不加密存储进数据库中，分发时携带私钥，运行时使用私钥解密数据后在客户端再次将数据加密存储，随后删除私钥**。

### 并发系统

- **内部工作原理**
    - **GPU支持检测与利用**
        - 系统在启动时检测PyTorch及CUDA的可用性，对GPU资源进行动态配置，以支持并加速任务执行。
    - **任务对象管理**
        - 定义了基础任务对象`_BaseTaskObject`，包括任务执行所需的所有参数和方法，支持同步与异步任务。
        - 任务可以配置是否使用GPU、是否需要锁定、重试策略等。
    - **异步和同步任务的执行**
        - 为异步任务和同步任务分别定义了执行方法，包括错误处理和重试逻辑。
        - 在执行过程中，如果启用了GPU加速，则会将数据传输到GPU进行处理，并在处理完成后清理GPU资源。
    - **线程与进程的管理**
        - 使用线程和进程对象封装复杂的并发行为，包括任务的分配、执行和线程/进程的生命周期管理。
        - 每个进程或线程可以独立管理其任务队列和执行逻辑，提高任务处理的灵活性和效率。


- **性能优化策略**
    - **资源利用与负载均衡**
        - 实现动态资源管理，根据系统负载动态调整线程和进程的数量，优化资源利用率。
        - 通过负载均衡策略，确保各处理单元负载均匀，避免某些节点过载而其他节点空闲。
    - **任务调度优化**
        - 优化任务调度策略，通过优先级队列和任务类型管理，确保高优先级任务优先执行，同时根据任务类型（CPU密集型或I/O密集型）智能调度到最适合的处理单元。
        - 引入任务拒绝策略，对于超出处理能力的任务，可以选择合理的拒绝策略以保证系统稳定性和响应性。
    - **错误处理与重试机制**
        - 增强错误处理能力，对于可能因外部因素导致失败的任务，提供自动重试机制。
        - 通过配置最大重试次数和重试策略，避免系统资源被无效任务长时间占用。
    - **GPU资源管理**
        - 对于支持GPU的任务，优化GPU资源的分配和管理，确保GPU资源的高效利用。
        - 在任务执行完毕后，及时清理GPU资源，避免内存泄漏。

- **配置和性能调整**
    - **并发系统配置**：通过实例化ConfigModule模块的ConcurrencySystemConfig数据类，可以自定义并发系统的配置，涵盖进程数、线程数、任务阈值、负载平衡策略等，使得并发系统能够根据不同的硬件环境和应用需求进行优化。


- **线程管理策略**
    - **线程使用**： 并发系统采用了多线程策略，核心线程池（Core）和扩展线程池（Expand）均运行在主进程上，专门用于处理I/O密集型任务和轻量级并发任务。核心线程池提供持续服务，而扩展线程池根据实时负载动态调整，以适应突发的任务高峰。
    - **任务类型管理**：系统将异步和同步任务分开管理，通过独立的队列分配给专门的线程，优化执行效率和响应时间。确保任务按需分配到最适合的处理资源上。


- **进程与线程的关系**
    - **进程结构**：并发系统中的进程分为核心（Core）进程和扩展（Expand）进程。每个核心进程和扩展进程内部都维护着自己的一组线程（同步和异步线程），这些线程专门处理该进程分配的任务。核心进程负责处理常规且关键的任务，而扩展进程在系统负载高时被动态创建，以增强处理能力。

    - **进程中的线程**：核心线程和扩展线程虽然在主进程中运行，但每个独立的核心进程和扩展进程都有自己的线程组，这些线程负责执行进程级的任务，利用多线程的优势来提高任务处理速度和效率。


- **资源动态调整与扩展**
    - **自适应负载管理**：系统能够监控实时的负载情况，并根据需要自动调整进程和线程的数量。帮助系统在保持高性能的同时，优化资源使用和成本。
    - **进程和线程的动态扩展**：在需要处理更多任务时，系统可以动态启动更多的扩展进程和线程，而在负载减少时相应地减少这些资源，确保系统资源的有效利用。

## 快速开始

```
pip install requirements.txt
```

```
from TheSeedCore import *

class Test(TheSeed):
    def __init__(self):
        ...


if __name__ == "__main__":
    linkStart(Test, debug_mode=True)

```

## 接口文档

- 大部分快速接口都封装在了TheSeed类中，可以通过直接调用TheSeed类或继承TheSeed类调用。


- 接口文档详见[TheSeedCoreInterface](TheSeedCoreInterface.md)。

## 许可证

此项目在 Apache License 2.0 下发布。该许可证允许他人对项目进行商业或非商业的使用、修改和再分配，同时要求在修改后的文件中必须声明改动，并提供对原作者的必要归属。此外，Apache License 2.0 还提供了对专利的明确保护。
请查阅 [LICENSE](LICENSE) 文件获取更多信息。



