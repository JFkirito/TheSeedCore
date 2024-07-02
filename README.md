# TheSeedCore

## 简介

TheSeedCore 框架是一个高度模块化且可扩展的系统，旨在提供强大的支持，以便轻松构建复杂的应用程序。TheSeedCore 注重灵活性、高并发和安全性，提供了全面的工具和组件，满足各种开发需求。

## 主要特性

### 模块化架构 ：TheSeedCore 设计为高度模块化的框架，可以轻松集成到各种软件架构中，支持独立或协同工作。


- **模块独立**：每个模块都是独立的，可以单独使用或与其他模块组合使用。


- **模块交互**：模块之间提供接口，以便实现复杂的业务逻辑。


- **模块扩展**：支持模块的扩展和定制，以满足不同的需求。

### 命令行交互 ：支持命令行操作和自定义命令，可自由拓展命令和操作。

### 数据库管理 ：支持 SQLite 和 Redis 数据库，以及对应的事务管理，提供灵活且安全的数据管理解决方案。


- **多样性**：支持多种数据库以满足不同的数据存储需求。


- **加密**：内置数据加密功能，确保存储和传输的安全性。


- **日志记录**：详细的操作日志，便于跟踪和审核。


- **数据完整性**：支持事务管理，确保数据的完整性和一致性。

### 加密管理 ：提供先进的数据加密和解密功能，确保数据安全。


- **AES 和 RSA**：支持 AES 和 RSA 加密算法。


- **密钥管理**：提供密钥管理功能，支持密钥的生成、导入和导出，方便密钥的管理和使用。


- **日志记录**：全面记录所有加密和解密过程。

### 外部服务管理 ：管理和操作 Node.js 等相关的包和服务，支持与 Node.js 环境的无缝集成。


- **Node.js 管理**：安装和管理 Node.js 包和应用程序。


- **服务控制**：无缝启动和停止 Node.js 服务。


- **日志记录**：自动记录所有操作，便于监控和调试。

### 网络服务管理 ：实现 HTTP 和 WebSocket 服务器及客户端，支持实时数据交换和网络通信。


- **HTTP 服务器**：基于 aiohttp，支持路由管理和动态内容响应。


- **WebSocket 服务器和客户端**：实现 WebSocket 协议的实时通信。


- **扩展性**：轻松添加新的路由和处理程序，扩展功能。

### 线程池管理 ：提供高度可配置的系统，用于管理同步和异步任务，优化资源使用和性能。


- **任务管理**：高效执行同步和异步任务。


- **动态调整**：根据当前负载自动调整线程数量。


- **负载均衡**：均衡分配任务到各个线程，实现最佳性能。


- **性能监控**：监控系统性能，优化资源利用。

### 任务调度 ：集成了同步和异步任务管理，优化了任务执行效率，支持高并发处理。


- **指定线程**：通过线程池管理模块，支持任务的线程控制，提高任务处理效率。


- **同步与异步任务执行**：支持同步任务和基于 asyncio 的异步任务，允许高效的任务处理。


- **线程安全**：确保任务的线程安全性，避免资源竞争和死锁。


- **数据共享安全**：提供数据共享和传递的安全机制，避免数据泄露和损坏。

### 日志记录 ：提供丰富的日志记录功能，支持颜色编码、文件保存和调试模式切换。


- **颜色编码**：不同日志级别以不同颜色显示，提升可读性。


- **文件轮换**：按天自动轮换日志文件，并保留可配置数量的备份。


- **调试模式**：轻松开启或关闭调试模式，便于开发过程中的详细日志查看。

## 模块交互

每个模块都被设计为低耦合和高内聚，可以独立于其他模块工作，同时提供接口与其他模块交互，以完成复杂的业务场景。

## 框架结构

/TheSeedCore

│

├── init.py

├── DatabaseModule.py

├── EncryptionModule.py

├── ExternalServicesModule.py

├── LoggerModule.py

├── NetworkModule.py

└── ThreadPoolModule.py

## 环境要求

- 系统环境：Windows


- Python 3.11 或更高版本


- Node.js


- 相关 Python 库：aiohttp, asyncio, websockets,requests, redis, rsa, Crypto

## 使用说明

### 启动 ：必须在程序入口使用 TheSeedCore 的 `linkStart` 方法启动，并将应用作为参数传入，TheSeedCore 会自动管理并实例应用。


### 关闭 ：在应用退出时，进行自定义的清理后，请调用 TheSeedCore 的 `linkStop` 方法关闭 TheSeedCore， 此方法会关闭和清理由 TheSeedCore 创建的所有资源。


### 模块调用 ：TheSeedCore 的模块都是独立的，可以单独调用或与其他模块组合使用。


### linkStart参数 ：

- **`application`**：应用实例，必须是一个可调用的类对象。


- **`total_thread_count`**：线程池中线程数的总量。默认为 `None`。
    - 为None时自动根据CPU的线程数动态调整。


- **`sync_thread_labels`**：同步线程的标签列表，默认为 `None`。
    - 添加同步任务时可以指定线程的标签，以便线程池管理模块对线程进行管理。


- **`async_thread_labels`**：异步线程的标签列表，默认为 `None`。
    - 添加异步任务时可以指定线程的标签，以便线程池管理模块对线程进行管理。


- **`task_threshold`**：任务数量阈值，默认为`10`。
    - 当线程池中的任务数量平均值超过阈值时，TheSeedCore会自动增加线程数量，但是线程数不会超过总量的50%。


- **`load_balancing`**：是否启用负载均衡，默认为 `True`。
    - 开启负载均衡后，TheSeedCore会根据任务数量自动调整线程的数量，支持运行时动态调整。


- **`logger_backup_count`**：日志备份数量，默认为`30`。
    - 日志文件会按天自动备份，备份文件数量不会超过指定数量。


- **`banner_color_mode`**：Banner的颜色显示模式，默认为`Solid`。
    - 只接受 `Solid` 和 `Gradient`。


- **`debug`**：是否启用调试模式，默认为 False。
    - 开启调试模式会将日志记录输出到控制台中。

### 目录 ：


- **以下目录会在TheSeedCore启动时自动生成**：
  - **`ExternalLibrary`**：外部库文件夹。
  - **`TheSeedData`**：用于存放日志文件、数据库文件等数据文件。


- **开发环境**: 目录会生成在和TheSeedCore同级的目录下。


- **生产环境**: 目录会生成在和应用程序同级的目录下。

### 加密 ：


- **AES**：TheSeedCore 的加密器被设计为启动时使用 设备编码 + 自定义key 来生成Keyring的唯一标识符并使用该标识符存储AES秘钥。如果分发时携带了使用 `aesEncryptData` 或 `aesEncrypt` 方法加密的数据，或数据库使用了数据加密，分发的应用将无法解密数据


- **RSA**：`generateRSAKeys`方法会立即返回未加密的公私钥对，如果指定了存储路径和  `store_locally`参数，TheSeedCore 会使用该加密器实例的AES将私钥加密后存储在指定的路径


- **如果分发时必须携带加密数据，可以采用以下方案**。
  -**使用 `generateRSAKeys` 方法不指定存储路径生成公私钥对，用 `generateRSAKeys` 方法返回的公钥加密数据，然后将私钥手动保存或将私钥不加密存储进数据库中，分发时携带私钥，运行时使用私钥解密数据后在客户端再次将数据加密存储，随后删除私钥**。

### 任务调度和线程池 ：


- **添加任务**：通过调用 `TheSeed` 的 `addSyncTask` 或 `addAsyncTask` 方法，可以将要执行的函数放到后台线程中。
  - **`callback`**：任务执行完毕后的回调函数，可以在回调函数中处理任务的结果。
  - **`thread_label`**：指定任务应该放入哪个线程，前提是在 `linkStart` 调用时指定了线程标签，如果未指定 `sync_thread_labels` 或 `async_thread_labels` ，则 TheSeedCore 会选择一条任务最少的线程执行任务。
  - **`lock`**：是否为任务加锁，默认为 `False`。


- **线程池**：TheSeedCore 会自动管理线程，如果需要手动控制线程的数量，可以在 `linkStart` 方法中指定 `total_thread_count` 参数，TheSeedCore 会将指定的线程数平均分配同步线程和异步线程。
  - **未指定线程数量**：如果未指定`total_thread_count` 参数，TheSeedCore 会通过性能模式根据 CPU 的最大线程动态调整线程池中线程的数量。


- **事件循环**：TheSeedCore 会自动管理异步线程的事件循环，不需要在应用中手动创建事件循环。


- **创建线程**：通过调用 `TheSeed` 的 `createSyncThread` 或 `createAsyncThread` 方法，可以创建一个新的线程。


- **性能模式**：具体调用请参阅[TheSeedCoreInterface](TheSeedCoreInterface.md)。该方法可以调整 TheSeedCore 的性能模式，可以选择性能模式为lowPerformance、Balance、HighestPerformance，TheSeedCore 会根据CPU的最大线程动态调整线程池中线程的数量，重启 TheSeedCore 生效。


- **负载均衡**：TheSeedCore 会根据任务数量和线程的数量自动调整线程的数量，支持运行时动态调整。

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


- 大部分快速接口都封装在了TheSeed类中，可以通过TheSeed类的实例或继承TheSeed调用。


- 接口文档详见[TheSeedCoreInterface](TheSeedCoreInterface.md)。

## 许可证

此项目在 Apache License 2.0 下发布。该许可证允许他人对项目进行商业或非商业的使用、修改和再分配，同时要求在修改后的文件中必须声明改动，并提供对原作者的必要归属。此外，Apache License 2.0 还提供了对专利的明确保护。
请查阅 [LICENSE](LICENSE) 文件获取更多信息。

