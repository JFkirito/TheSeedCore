# TheSeedCoreInterface

## 公共变量

**`SystemType`**：系统类型，取值为`"Windows"`、`"Linux"`或`"Darwin"`。

**`DevelopmentEnv`**：是否为开发环境，取值为`True`或`False`，如果程序被打包，则为`False`。

**`RootDirectoryPath`**：程序根目录路径, 如果程序被打包，则目录指向exe可执行程序的同级目录，否则指向TheSeedCore包的所在目录。

**`ExternalLibraryDirectoryPath`**：外部库目录路径，如果程序被打包，则目录指向exe可执行程序的同级目录，否则指向TheSeedCore包的所在目录。

**`ExternalServiceDirectoryPath`**：外部服务目录路径，如果程序被打包，则目录指向exe可执行程序的同级目录，否则指向TheSeedCore包的所在目录。

**`DataDirectoryPath`**：数据目录路径，指向`RootDirectoryPath`/`TheSeedCoreData`。

**`DatabaseDirectoryPath`**：数据库目录路径，指向`DataDirectoryPath`/`Database`。

**`FlaskDataDirectoryPath`**：Flask数据目录路径，指向`DataDirectoryPath`/`Flask`。

**`FlaskStaticFolderPath`**：Flask静态文件目录路径，指向`FlaskDataDirectoryPath`/`Static`。

**`FlaskTemplateFolderPath`**：Flask模板文件目录路径，指向`FlaskDataDirectoryPath`/`Template`。

**`FlaskInstanceFolderPath`**：Flask实例文件目录路径，指向`FlaskDataDirectoryPath`/`Instance`。

**`FlaskRootFolderPath`**：Flask根目录路径，指向`RootDirectoryPath`/`Root`。

**`LogsDirectoryPath`**：日志目录路径，指向`DataDirectoryPath`/`Logs`。

## 配置/枚举

**`Priority`**：进程优先级，取值为`Priority.IDLE`、`Priority.BELOW_NORMAL`、`Priority.NORMAL`、`Priority.ABOVE_NORMAL`、`Priority.HIGH`、`Priority.REALTIME`。

**`ExpandPolicy`**：扩展策略，取值为`ExpandPolicy.NoExpand`、`ExpandPolicy.AutoExpand`、`ExpandPolicy.BeforehandExpand`。

**`ShrinkagePolicy`**：收缩策略，取值为`ShrinkagePolicy.NoShrink`、`ShrinkagePolicy.AutoShrink`、`ShrinkagePolicy.TimeoutShrink`。

## 启动和关闭

**`ConnectTheSeedCore`**：连接TheSeedCore，初始化事件循环。

- **`check_env`**：是否检查环境依赖，默认为`True`。
- **`quit_qapp`**：异步事件循环退出时是否退出Qt应用程序，PySide6版本小于6.7.0时该值不生效，默认为`True`。
- **`handle_sigint`**：是否处理SIGINT信号，PySide6版本小于6.7.0时该值不生效，默认为`False`。
- **`MainPriority`**：主进程优先级，可选，默认为`Priority.NORMAL`。
- **`CoreProcessCount`**：核心进程数，框架会自动检测最大值，为`0`时进程池将不可用，为`None`时自动设置，默认为`None`。
- **`CoreThreadCount`**：核心线程数，框架会自动检测最大值，为`0`时线程池将不可用，为`None`时自动设置，默认为`None`。
- **`MaximumProcessCount`**：最大进程数，框架会自动检测最大值，为`None`时自动设置，默认为`None`。
- **`MaximumThreadCount`**：最大线程数，框架会自动检测最大值，为`None`时自动设置，默认为`None`。
- **`IdleCleanupThreshold`**：进程内存空闲清理阈值，为`None`时自动设置，默认为`None`。
- **`TaskThreshold`**：每个进程和线程的任务数量阈值，为`None`时自动设置，默认为`None`。
- **`GlobalTaskThreshold`**：全局任务队列阈值，为`None`时自动设置，默认为`None`。
- **`ExpandPolicy`**：扩展策略，默认为`ExpandPolicy.AutoExpand`。
- **`ShrinkagePolicy`**：收缩策略，默认为`ShrinkagePolicy.AutoShrink`。
- **`ShrinkagePolicyTimeout`**：收缩策略超时时间，默认为`5`秒。
- **`PerformanceReport`**：性能报告，为`True`时启用，默认为`True`。

**`LinkStart`**：启动事件循环。

**`MainEventLoop`**：获取主事件循环，必须在`ConnectTheSeedCore`之后才能调用，否则将抛出`RuntimeError`异常。

**`LinkStop`**：安全地清理资源并停止事件循环，QT模式下`QApplication`的`aboutToQuit`信号会自动连接至此方法。

**_非QT模式_**

```python
import asyncio

import TheSeedCore as TSC


async def main():
    for i in range(10):
        await asyncio.sleep(1)
        print("System shutdown countdown:", 10 - i)
    print("System shutdown")
    TSC.LinkStop()


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(
        check_env=True,
        quit_qapp=False,
        handle_sigint=False,
        MainPriority=TSC.Priority.NORMAL,
        CoreProcessCount=0,  # 不使用进程池
        CoreThreadCount=0,  # 不使用线程池
        MaximumProcessCount=None,
        MaximumThreadCount=None,
        IdleCleanupThreshold=None,
        TaskThreshold=None,
        GlobalTaskThreshold=None,
        ExpandPolicy=TSC.ExpandPolicy.AutoExpand,
        ShrinkagePolicy=TSC.ShrinkagePolicy.AutoShrink,
        ShrinkagePolicyTimeout=None,
        PerformanceReport=True
    )
    main_loop = TSC.MainEventLoop()
    main_loop.create_task(main())
    TSC.LinkStart()
```

**_QT模式_**

```python
import asyncio
import sys
import time

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

import TheSeedCore as TSC


class Example(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.button = QPushButton(self)
        self.button.setText("Start test")
        self.current_time_label = QLabel(self)
        self.main_layout.addWidget(self.current_time_label)
        self.main_layout.addWidget(self.button)
        self.button.clicked.connect(self.clicked_function)
        TSC.MainEventLoop().create_task(self.update_current_time())

    # QT 信号连接的是异步函数时必须使用装饰器
    @TSC.AsyncTask
    async def clicked_function(self):
        for i in range(10):
            await asyncio.sleep(1)
            self.button.setText(f"Countdown: {10 - i}")
        self.button.setText("Start test")

    # 非 QT 信号连接的异步函数可以用 MainEventLoop() 来创建任务
    async def update_current_time(self):
        for i in range(60):
            await asyncio.sleep(1)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.current_time_label.setText(f"Current Time: {current_time}")
        self.current_time_label.setText(f"Current Time: ")


if __name__ == "__main__":
    qt = QApplication(sys.argv)  # 必须先实例 QApplication
    TSC.ConnectTheSeedCore(
        check_env=True,
        quit_qapp=True,
        handle_sigint=True,
        MainPriority=TSC.Priority.NORMAL,
        CoreProcessCount=0,  # 不使用进程池
        CoreThreadCount=0,  # 不使用线程池
        MaximumProcessCount=None,
        MaximumThreadCount=None,
        IdleCleanupThreshold=None,
        TaskThreshold=None,
        GlobalTaskThreshold=None,
        ExpandPolicy=TSC.ExpandPolicy.AutoExpand,
        ShrinkagePolicy=TSC.ShrinkagePolicy.AutoShrink,
        ShrinkagePolicyTimeout=None,
        PerformanceReport=True
    )
    w = Example()
    w.show()
    TSC.LinkStart()  # 实例应用后调用 LinkStart
```

## 并发

_以下接口仅在使用进程池或线程池时可用，如果不使用进程池或线程池，调用这些方法系统会提示异常。_

**`submitAsyncTask`**：向主事件循环提交异步任务。

- **`task`**：必须是可调用的异步任务。
- **`*args`**：可选，任务参数。
- **`**kwargs`**：可选，任务关键字参数。
- **`return`**：返回`asyncio.Future`对象。

```python
import asyncio

import TheSeedCore as TSC


async def test_async_task(index: int):
    await asyncio.sleep(1)
    print(f"Async task {index} done")
    if index == 9:
        await asyncio.sleep(1)
        print("All tasks done, system shutdown")
        TSC.LinkStop()


async def main():
    for i in range(10):
        future = TSC.submitAsyncTask(test_async_task, index=i)


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreProcessCount=0)
    TSC.MainEventLoop().create_task(main())
    TSC.LinkStart()
```

**`submitProcessTask`**：向进程池提交任务。

- **`task`**：必须是可调用的同步或异步函数。
- **`priority`**：可选，任务优先级，范围 0-10，值越低优先级越高，默认为`0`。
- **`callback`**：可选，任务完成后的回调函数，可以是同步或异步函数。
- **`future`**：可选，提交任务后返回的Future对象，默认为`TaskFuture`类实例对象，可以传入继承了`TaskFuture`类的实例对象。
- **`lock`**：可选，是否为任务加锁，默认为`False`。
- **`lock_timeout`**：可选，任务锁超时时间，默认为`3`秒。
- **`timeout`**：可选，任务超时时间，为`None`时不会检测超时，默认为`None`。
- **`gpu_boost`**：可选，是否使用GPU加速，默认为`False`。
- **`gpu_id`**：可选，GPU设备ID，默认为`0`。
- **`retry`**：可选，任务失败时是否重试，默认为`False`。
- **`max_retries`**：可选，任务失败时最大重试次数，默认为`3`。
- **`return`**：返回`TaskFuture`类实例对象。

```python
import asyncio
import time

import TheSeedCore as TSC


def test_process_task(index: int):
    current_time = time.time()
    result = 0
    for i in range(10 ** 7):
        result += i ** 2
    execution_time = time.time() - current_time
    print(f"Process task {index}, time consuming {execution_time:.3f}")
    return index


async def test_callback(result):
    if result == 3:
        print("All tasks done, system shutdown")
        await asyncio.sleep(1)
        TSC.LinkStop()


async def main():
    await asyncio.sleep(1)
    for i in range(4):
        TSC.submitProcessTask(test_process_task, callback=test_callback, index=i)


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreProcessCount=4)
    TSC.MainEventLoop().create_task(main())
    TSC.LinkStart()
```

**`submitThreadTask`**：向线程池提交任务。

- **`task`**：必须是可调用的同步或异步函数。
- **`priority`**：可选，任务优先级，范围 0-10，值越低优先级越高，默认为`0`。
- **`callback`**：可选，任务完成后的回调函数，可以是同步或异步函数。
- **`future`**：可选，提交任务后返回的Future对象，默认为`TaskFuture`类实例对象，可以传入继承了`TaskFuture`类的实例对象。
- **`lock`**：可选，是否为任务加锁，默认为`False`。
- **`lock_timeout`**：可选，任务锁超时时间，默认为`3`秒。
- **`timeout`**：可选，任务超时时间，为`None`时不会检测超时，默认为`None`。
- **`gpu_boost`**：可选，是否使用GPU加速，默认为`False`。
- **`gpu_id`**：可选，GPU设备ID，默认为`0`。
- **`retry`**：可选，任务失败时是否重试，默认为`False`。
- **`max_retries`**：可选，任务失败时最大重试次数，默认为`3`。
- **`return`**：返回`TaskFuture`类实例对象。

```python
import asyncio
import time

import TheSeedCore as TSC


def test_thread_task(index: int):
    time.sleep(1)
    print(f"Thread task {index} done\n")
    return index


async def test_callback(result):
    if result == 3:
        print("All tasks done, system shutdown")
        await asyncio.sleep(1)
        TSC.LinkStop()


async def main():
    await asyncio.sleep(1)
    for i in range(4):
        TSC.submitThreadTask(test_thread_task, callback=test_callback, index=i)


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreThreadCount=4)
    TSC.MainEventLoop().create_task(main())
    TSC.LinkStart()
```

**`submitSystemProcessTask`**：向系统进程池提交任务, 不支持异步函数。

- **`task`**：必须是可调用的同步函数。
- **`count`**：可选，任务数量，大于`1`时批量创建任务，默认为`1`。
- **`*args`**：可选，任务参数。
- **`**kwargs`**：可选，任务关键字参数。
- **`return`**：返回单个`concurrent.futures.Future`对象或包含`concurrent.futures.Future`对象的列表。

```python
import asyncio
import time

import TheSeedCore as TSC


def test_process_task():
    current_time = time.time()
    result = 0
    for i in range(10 ** 7):
        result += i ** 2
    execution_time = time.time() - current_time
    print(f"Process task, time consuming {execution_time:.3f}")
    return f"{execution_time:.3f}"


async def main():
    futures = TSC.submitSystemProcessTask(test_process_task, count=4)
    count = 0
    while count < 4:
        done_count = sum([1 for future in futures if future.done()])
        if done_count > count:
            count = done_count
        await asyncio.sleep(0.1)
    print("All tasks done, system shutdown")
    await asyncio.sleep(1)
    TSC.LinkStop()


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreProcessCount=4)
    TSC.MainEventLoop().create_task(main())
    TSC.LinkStart()
```

**`submitSystemThreadTask`**：向系统进程池提交任务, 不支持异步函数。

- **`task`**：必须是可调用的同步函数。
- **`count`**：可选，任务数量，大于`1`时批量创建任务，默认为`1`。
- **`*args`**：可选，任务参数。
- **`**kwargs`**：可选，任务关键字参数。
- **`return`**：返回单个`concurrent.futures.Future`对象或包含`concurrent.futures.Future`对象的列表。

```python
import asyncio
import time

import TheSeedCore as TSC


def test_thread_task():
    current_time = time.time()
    time.sleep(1)
    execution_time = time.time() - current_time
    print(f"Thread task done in {execution_time:.3f}\n")


async def main():
    futures = TSC.submitSystemThreadTask(test_thread_task, count=4)
    count = 0
    while count < 4:
        done_count = sum([1 for future in futures if future.done()])
        if done_count > count:
            count = done_count
        await asyncio.sleep(0.1)
    print("All tasks done, system shutdown")
    await asyncio.sleep(1)
    TSC.LinkStop()


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(CoreThreadCount=4)
    TSC.MainEventLoop().create_task(main())
    TSC.LinkStart()
```

## 数据库

### `SQLiteDatabase`：SQLite数据库操作类

**`实例参数`**：

- **`name`**：数据库名称，不需要包含后缀，必填。
- **`path`**：数据库路径，不填写时默认为`DatabaseDirectoryPath`，可选。
- **`stay_connected`**：是否保持连接，为`True`时数据库连接不会关闭，为`False`时数据库连接会在每次操作后关闭，默认为`False`。
- **`encryptor`**：数据库加密器，必须为`Security`模块的`AESEncryptor`实例，不指定则无法使用数据加密，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
# 执行完毕后可以在TheSeedCoreData/Database目录下看到TestDB.db文件
```

### `MySQLDatabase`：MySQL数据库操作类

- **`name`**：数据库名称，必填。
- **`host`**：数据库主机地址，必填。
- **`user`**：数据库用户名，必填。
- **`password`**：数据库密码，必填。
- **`stay_connected`：是否保持连接，为`True`时数据库连接不会关闭，为`False`时数据库连接会在每次操作后关闭，默认为`False`。
- **`encryptor`**：数据库加密器，必须为`Security`模块的`AESEncryptor`实例，不指定则无法使用数据加密，默认为`None`。

### 实例接口（`MySQLDatabase`和`SQLiteDatabase`的实例接口一致）

- **`deleteDatabase`**：删除数据库文件。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
test_db.deleteDatabase()
# 执行完毕后可以在TheSeedCoreData/Database目录下看到TestDB.db文件被删除
```

- **`checkExistedTable`**：检查表是否存在。
    - **`table_name`**：表名。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
is_exited = test_db.checkExistedTable("test_table")
print(is_exited)
# 输出 False
```

- **`getExistedTables`**：获取所有存在的表。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
all_existed_tables = test_db.getExistedTables()
print(all_existed_tables)
# 输出 []
```

- **`createTable`**：创建表。
    - **`table_name`**：表名。
    - **`table_sql`**：表结构SQL语句。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
);
"""
test_db.createTable(table_name, table_sql)
# 用 checkExistedTable 检查是否创建成功
is_exited = test_db.checkExistedTable(table_name)
print(is_exited)
# 输出True
```

- **`createTables`**：批量创建表。
    - **`tables_dict`**：表结构字典，键为表名，值为表结构SQL语句。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
tables_dict = {
    "test_table1": f"""
    CREATE TABLE test_table1 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    """,
    "test_table2": f"""
    CREATE TABLE test_table2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL
    );
    """
}
test_db.createTables(tables_dict)
# 用 getExistedTables 检查是否创建成功
all_existed_tables = test_db.getExistedTables()
print(all_existed_tables)
# 输出的列表将包含 'test_table1', 'test_table2'
```

- **`deleteTable`**：删除表。
    - **`table_name`**：表名。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
table_name = "test_table"
test_db.deleteTable(table_name)
# 如果之前没有创建过 test_table，控制台会打印 SQLite database [TestDB] table test_table not exists.
# 用 checkExistedTable 检查是否删除成功
is_exited = test_db.checkExistedTable(table_name)
print(is_exited)
# 输出 False
```

- **`deleteTables`**：批量删除表。
    - **`tables`**：表名列表。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
tables = ["test_table1", "test_table2"]
test_db.deleteTables(tables)
# 如果之前没有创建过 test_table1 和 test_table2，控制台会打印
# SQLite database [TestDB] table test_table1 not exists.
# SQLite database [TestDB] table test_table2 not exists.
# 用 getExistedTables 检查是否删除成功
all_existed_tables = test_db.getExistedTables()
print(all_existed_tables)
# 输出 ['sqlite_sequence']
```

- **`insertData`**：插入数据。
    - **`table_name`**：表名。
    - **`data`**：数据字典。
    - **`encrypt_columns`**：加密列名列表，不指定列名或加密器为指定则不加密，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data = {
    "name": "Kirito",
    "age": 16
}
test_db.insertData(table_name, data)
# 用 selectData 检查是否插入成功
result = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result)
# 输出 [{'id': 1, 'name': 'Kirito', 'age': 16}]
```

- **`insertDatas`**：批量插入数据。
    - **`table_name`**：表名。
    - **`datas`**：数据列表,每个元素为一个数据字典。
    - **`encrypt_columns`**：加密列名列表，不指定列名或加密器为指定则不加密，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data1 = {
    "name": "Kirito",
    "age": 16
}
data2 = {
    "name": "Asuna",
    "age": 18
}
data_list = [data1, data2]
test_db.insertDatas(table_name, data_list)
# 用 selectData 检查是否插入成功
result = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result)
# 输出 [{'id': 1, 'name': 'Kirito', 'age': 16}, {'id': 2, 'name': 'Asuna', 'age': 18}]
```

- **`updateData`**：更新数据。
    - **`table_name`**：表名。
    - **`data`**：要更新的数据字典。
    - **`condition`**：条件字符串。
    - **`encrypt_columns`**：加密列名列表，不指定列名或加密器为指定则不加密，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
test_db.deleteTable("test_table")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data = {
    "name": "Kirito",
    "age": 16
}
test_db.insertData(table_name, data)
update_data = {
    "name": "Kirito",
    "age": 18
}
test_db.updateData(table_name, update_data, "name='Kirito'")
# 用 selectData 检查是否更新成功
result = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result)
# 输出 [{'id': 1, 'name': 'Kirito', 'age': 18}]
```

- **`updateDatas`**：批量更新数据。
    - **`table_name`**：表名。
    - **`datas`**：要更新的数据列表,每个元素为一个数据字典。
    - **`condition`**：条件字符串。
    - **`encrypt_columns`**：加密列名列表，不指定列名或加密器为指定则不加密，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
test_db.deleteTable("test_table")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data1 = {
    "name": "Kirito",
    "age": 16
}
data2 = {
    "name": "Asuna",
    "age": 18
}
data_list = [data1, data2]
test_db.insertDatas(table_name, data_list)
update_data1 = {
    "age": 18
}
update_data2 = {
    "age": 20
}
update_data_list = [update_data1, update_data2]
# noinspection PyTypeChecker
test_db.updateDatas(table_name, update_data_list, f"age < 20")
# 用 selectData 检查是否更新成功
result = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result)
# 输出 [{'id': 1, 'name': 'Kirito', 'age': 20}, {'id': 2, 'name': 'Asuna', 'age': 20}]
```

- **`selectData`**：查询数据。
    - **`table_name`**：表名。
    - **`columns`**：列名列表，默认为`*`。
    - **`condition`**：条件字符串，默认为`None`。
    - **`dencrypt_columns`**：解密列名列表，不指定列名或加密器为指定则不解密，默认为`None`。
    - **`order_by`**：排序字符串，默认为`None`。
    - **`limit`**：限制返回数量，默认为`None`。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
test_db.deleteTable("test_table")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data = {
    "name": "Kirito",
    "age": 16
}
test_db.insertData(table_name, data)
result = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result)
# 输出 [{'id': 1, 'name': 'Kirito', 'age': 16}]
```

- **`deleteData`**：删除数据。
    - **`table_name`**：表名。
    - **`condition`**：条件字符串。
    - **`condition_params`**：条件参数列表，默认为空元组。

```python
import TheSeedCore as TSC

test_db = TSC.SQLiteDatabase("TestDB")
test_db.deleteTable("test_table")
table_name = "test_table"
table_sql = f"""
CREATE TABLE {table_name}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
"""
test_db.createTable(table_name, table_sql)
data = {
    "name": "Kirito",
    "age": 16
}
test_db.insertData(table_name, data)
result1 = test_db.selectData(table_name, columns=["id", "name", "age"])
test_db.deleteData(table_name, "name='Kirito'")
result2 = test_db.selectData(table_name, columns=["id", "name", "age"])
print(result2)
# 输出 []
```

## 日志

### `TheSeedCoreLogger`：继承自logging.Logger的日志类

**`实例参数`**：

- **`name`**：日志名称，必填。
- **`path`**：日志文件路径，不填写时默认为`LogsDirectoryPath`，可选。
- **`backup_count`**：日志备份天数，默认为`7`天。
- **`level`**：日志级别，默认为`logging.DEBUG`。
- **`debug`**：是否输出调试信息，默认为`DevelopmentEnv`。

```python
import TheSeedCore as TSC

logger = TSC.TheSeedCoreLogger("TestLogger")
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
```