# -*- coding: utf-8 -*-
"""
TheSeedCore DatabaseModule

######################################################################################################################################
# This module provides configurations and management utilities for interacting with different types of databases,
# including SQLite, MySQL, and Redis. It is designed to handle database connections, perform CRUD operations,
# and manage configurations for various databases with support for logging and optional encryption.

# Main functionalities:
# 1. Manage configurations for SQLite, MySQL, and Redis databases.
# 2. Provide basic and extended CRUD operations for each database type.
# 3. Support optional data encryption and decryption for secure data storage.
# 4. Integrate logging utilities to monitor database activities and errors.
# 5. Manage database connections, including connection persistence and resource cleanup.

# Main components:
# 1. SQLiteDatabaseConfig, MySQLDatabaseConfig, RedisDatabaseConfig - Configuration classes for each database type.
# 2. BasicSQLiteDatabase, BasicMySQLDatabase, BasicRedisDatabase - Base classes for basic database operations.
# 3. ExpandSQLiteDatabase - Extends BasicSQLiteDatabase with additional functionality for table and data management.
# 4. TheSeedCoreSQLiteDatabase - A specialized SQLite database for managing TheSeedCore application data.
# 5. SQLiteDatabaseManager - A manager class that handles multiple SQLite database instances.
# 6. MySQLDatabaseManager, RedisDatabaseManager - Manager classes for MySQL and Redis databases.

# Design thoughts:
# 1. Modular design:
#    a. The module is structured to separate configuration management, basic operations, and extended functionalities.
#    b. Each class is responsible for a specific aspect of database management, promoting modularity and ease of maintenance.
#
# 2. Support for multiple database types:
#    a. The module provides configurations and utilities for SQLite, MySQL, and Redis, making it versatile and adaptable
#       to different database environments.
#    b. MySQL and Redis support is optional and can be enabled based on the availability of the corresponding libraries.
#
# 3. Logging and debugging:
#    a. The module integrates logging at various levels to monitor database operations and track errors, aiding in
#       debugging and maintenance.
#    b. The defaultLogger function sets up a logger with configurable debug mode, which can be adjusted based on the
#       application's requirements.
#
# 4. Encryption support:
#    a. The module includes optional encryption for sensitive data, using an Encryptor class to secure data before storage.
#    b. Encryption and decryption are integrated into the CRUD operations, ensuring that data is always handled securely.
#
# 5. Error handling and resource management:
#    a. The module provides robust error handling across all database operations, including connection management,
#       query execution, and transaction handling.
#    b. Resource cleanup is built into the classes to ensure that database connections are properly closed and resources
#       are released after use.

# Required dependencies:
# 1. Python libraries: logging, sqlite3, traceback, dataclasses, typing, os.
# 2. Optional libraries for extended functionality: pymysql (for MySQL support), redis (for Redis support).
######################################################################################################################################
"""

from __future__ import annotations

__all__ = [
    "SQLiteDatabaseConfig",
    "MySQLDatabaseConfig",
    "RedisDatabaseConfig",
    "TheSeedCoreSQLiteDatabase",
    "BasicSQLiteDatabase",
    "BasicMySQLDatabase",
    "BasicRedisDatabase",
    "SQLiteDatabaseManager",
    "MySQLDatabaseManager",
    "RedisDatabaseManager",
    "MySQLSupport",
    "RedisSupport"
]

import logging
import os
import sqlite3
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, Literal

from . import _ColoredFormatter

if TYPE_CHECKING:
    from TheSeedCore import TheSeedCoreLogger

MySQLSupport: bool = False
RedisSupport: bool = False


def defaultLogger(database_type: Literal["SQLite", "Redis", "MySQL"], debug_mode: bool = False) -> logging.Logger:
    """
    创建并返回一个用于指定数据库类型的日志记录器。

    参数：
        :param database_type: 字符串，指定数据库类型，可以是 "SQLite"、"Redis" 或 "MySQL"。
        :param debug_mode: 布尔值，指示是否启用调试模式。默认为 `False`。

    返回：
        :return - logger : 配置好的日志记录器对象

    执行过程：
        1. 使用指定的 `database_type` 创建一个日志记录器实例，并设置日志级别为 `DEBUG`。
        2. 创建一个 `StreamHandler`，用于将日志输出到控制台。
        3. 根据 `debug_mode` 参数设置控制台处理器的日志级别：
            a. 如果 `debug_mode` 为 `True`，则设置级别为 `DEBUG`。
            b. 否则，设置级别为 `DEBUG` 和 `WARNING` 之间的最大值。
        4. 创建一个 `_ColoredFormatter` 对象，用于格式化日志消息。
        5. 将格式化器应用到控制台处理器上。
        6. 将控制台处理器添加到日志记录器中。

    异常：
        无
    """

    logger = logging.getLogger(f'TheSeedCore - {database_type}Database')
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


@dataclass
class SQLiteDatabaseConfig:
    """
    该类用于配置SQLite数据库的相关参数，包括数据库ID、路径、加密器和连接保持状态。

    参数：
        :param - DatabaseID：数据库的唯一标识符
        :param - DatabasePath：数据库文件的路径
        :param - Encryptor：用于加密数据库的加密器实例，如果没有加密则为None
        :param - StayConnected：是否保持与数据库的连接

    属性：
        - DatabaseID：数据库的唯一标识符
        - DatabasePath：数据库文件的路径
        - Encryptor：用于加密数据库的加密器实例
        - StayConnected：是否保持与数据库的连接状态

    设计思路：
        1. 初始化数据库配置参数
            a. 验证数据库ID和路径的类型
            b. 验证加密器的类型，如果存在的话
            c. 验证连接保持标志的类型
    """

    DatabaseID: str
    DatabasePath: str
    Encryptor: Union[None, Encryptor]
    StayConnected: bool

    def __post_init__(self):
        if not isinstance(self.DatabaseID, str):
            raise ValueError("The sqlite database ID must be a string.")
        if not isinstance(self.DatabasePath, str):
            raise ValueError("The sqlite database path must be a string.")
        if not isinstance(self.StayConnected, bool):
            raise ValueError("The sqlite database stay connected flag must be a boolean.")


@dataclass
class MySQLDatabaseConfig:
    """
    该类用于配置MySQL数据库的连接参数，包括主机、端口、用户、密码和数据库名称。

    参数：
        :param - Host：MySQL数据库的主机地址
        :param - Port：MySQL数据库的端口号
        :param - User：用于连接数据库的用户名
        :param - Password：连接数据库的密码
        :param - Database：要连接的数据库名称

    属性：
        - Host：MySQL数据库的主机地址
        - Port：MySQL数据库的端口号
        - User：用于连接数据库的用户名
        - Password：连接数据库的密码
        - Database：要连接的数据库名称

    设计思路：
        1. 初始化MySQL数据库配置参数
            a. 验证主机地址的类型
            b. 验证端口号的类型
            c. 验证用户名的类型
            d. 验证密码的类型
            e. 验证数据库名称的类型
    """

    Host: str
    Port: int
    User: str
    Password: str
    Database: str

    def __post_init__(self):
        if not isinstance(self.Host, str):
            raise ValueError("The mysql database host must be a string.")
        if not isinstance(self.Port, int):
            raise ValueError("The mysql database port must be an integer.")
        if not isinstance(self.User, str):
            raise ValueError("The mysql database user must be a string.")
        if not isinstance(self.Password, str):
            raise ValueError("The mysql database password must be a string.")
        if not isinstance(self.Database, str):
            raise ValueError("The mysql database name must be a string.")


@dataclass
class RedisDatabaseConfig:
    """
    该类用于配置Redis数据库的连接参数，包括主机、端口、密码、数据库编号和加密器。

    参数：
        :param - Host：Redis数据库的主机地址
        :param - Port：Redis数据库的端口号
        :param - Password：连接Redis数据库的密码
        :param - Num：Redis数据库的编号
        :param - Encryptor：用于Redis数据库连接的加密器

    属性：
        - Host：Redis数据库的主机地址
        - Port：Redis数据库的端口号
        - Password：连接Redis数据库的密码
        - Num：Redis数据库的编号
        - Encryptor：用于Redis数据库连接的加密器

    设计思路：
        1. 初始化Redis数据库配置参数
            a. 验证主机地址的类型
            b. 验证端口号的类型
            c. 验证密码的类型
            d. 验证数据库编号的类型
            e. 加密器作为属性存储，用于提供连接的加密功能
    """

    Host: str
    Port: int
    Password: str
    Num: int
    Encryptor: Encryptor

    def __post_init__(self):
        if not isinstance(self.Host, str):
            raise ValueError("The redis database host must be a string.")
        if not isinstance(self.Port, int):
            raise ValueError("The redis database port must be an integer.")
        if not isinstance(self.Password, str):
            raise ValueError("The redis database password must be a string.")
        if not isinstance(self.Num, int):
            raise ValueError("The redis database number must be an integer.")


class BasicSQLiteDatabase:
    """
    SQLite数据库基类，包括连接、断开、创建、删除、插入、更新、查询等功能。

    参数：
        :param - Config：SQLite数据库配置对象，类型为SQLiteDatabaseConfig。
        :param - Logger：日志记录器，可以是TheSeedCoreLogger或Python的标准logging.Logger。
        :param - DebugMode：调试模式标志，默认为False。

    属性：
        - _DatabaseID：数据库的唯一标识符
        - _DatabasePath：数据库文件路径
        - _Database：数据库文件的完整路径
        - _Logger：日志记录器
        - _Encryptor：加密器对象
        - _StayConnected：是否保持连接标志
        - _ConnectedDatabase：数据库连接对象

    设计思路：
        1. 初始化数据库配置参数
            a. 验证并设置数据库ID、路径、加密器和连接保持标志
            b. 创建数据库文件路径
            c. 设置日志记录器和调试模式
        2. 提供数据库的基本操作方法
            a. 连接和断开数据库
            b. 创建、删除数据库及表
            c. 插入、删除、更新和查询数据
            d. 支持数据加密和解密功能
    """

    def __init__(self, Config: SQLiteDatabaseConfig, Logger: Union[TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        self._configParamsValidation(Config)
        self._DatabaseID = Config.DatabaseID
        self._DatabasePath = Config.DatabasePath
        self._Database = os.path.join(self._DatabasePath, f"{self._DatabaseID}.db")
        self._Logger = defaultLogger("SQLite", DebugMode) if Logger is None else Logger
        self._Encryptor = Config.Encryptor
        self._StayConnected = Config.StayConnected if Config.StayConnected is not None else False
        self._ConnectedDatabase = None

    @staticmethod
    def _configParamsValidation(config: SQLiteDatabaseConfig):
        """
        验证 SQLite 数据库配置的各个参数的有效性。

        参数：
            :param config: `SQLiteDatabaseConfig` 类型，包含 SQLite 数据库的配置参数。

        执行过程：
            1. 检查 `DatabaseID` 是否为 `None`，如果是，则引发 `ValueError`。
            2. 检查 `DatabaseID` 是否为字符串类型，如果不是，则引发 `ValueError`。
            3. 检查 `DatabasePath` 是否为 `None`，如果是，则引发 `ValueError`。
            4. 检查 `DatabasePath` 是否为字符串类型，如果不是，则引发 `ValueError`。
            5. 检查 `StayConnected` 是否为布尔值或 `None`，如果不是，则引发 `ValueError`。

        异常：
            1. ValueError: 如果 `DatabaseID` 为 `None` 或不是字符串类型。
            2. ValueError: 如果 `DatabasePath` 为 `None` 或不是字符串类型。
            3. ValueError: 如果 `StayConnected` 既不是布尔值也不是 `None`。
        """

        if config.DatabaseID is None:
            raise ValueError("DatabaseID cannot be None.")
        if not isinstance(config.DatabaseID, str):
            raise ValueError("DatabaseID must be a string.")
        if config.DatabasePath is None:
            raise ValueError("DatabasePath cannot be None.")
        if not isinstance(config.DatabasePath, str):
            raise ValueError("DatabasePath must be a string.")
        if not (isinstance(config.StayConnected, bool) or config.StayConnected is None):
            raise ValueError("StayConnected must be a boolean or None.")

    def _connect(self) -> bool:
        """
        连接到 SQLite 数据库并进行异常处理。

        返回：
            :return - bool : 如果成功连接数据库，则返回 `True`；否则返回 `False`。

        执行过程：
            1. 检查 `_ConnectedDatabase` 是否已连接，如果没有连接则继续。
            2. 检查数据库文件是否存在，如果不存在，则创建一个空文件。
            3. 尝试使用 `sqlite3.connect` 连接到数据库。
            4. 如果连接成功，记录调试日志并返回 `True`。
            5. 如果连接失败，记录错误日志并返回 `False`。

        异常：
            1. sqlite3.Error: 处理数据库连接过程中出现的错误。
        """

        try:
            if not self._ConnectedDatabase:
                if not os.path.exists(self._Database):
                    open(self._Database, "a").close()
                self._ConnectedDatabase = sqlite3.connect(self._Database)
                self._Logger.debug(f"Database {self._DatabaseID} connection completed")
                return True
        except sqlite3.Error as e:
            self._Logger.error(f"Database {self._DatabaseID} connection error : {e}\n\n{traceback.format_exc()}")
            return False

    def _disconnect(self) -> bool:
        """
        断开与 SQLite 数据库的连接并进行异常处理。

        返回：
            :return - bool : 如果成功断开数据库连接，则返回 `True`；否则返回 `False`。

        执行过程：
            1. 检查 `_ConnectedDatabase` 是否已连接且 `_StayConnected` 为 `False`，如果满足条件则继续。
            2. 尝试关闭数据库连接并将 `_ConnectedDatabase` 设置为 `None`。
            3. 如果断开成功，记录调试日志并返回 `True`。
            4. 如果断开失败，记录错误日志并返回 `False`。

        异常：
            1. Exception: 处理断开数据库连接过程中出现的错误。
        """

        try:
            if self._ConnectedDatabase and not self._StayConnected:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.debug(f"Database {self._DatabaseID} disconnection completed")
                return True
        except Exception as e:
            self._Logger.error(f"Database {self._DatabaseID} disconnect error : {e}\n\n{traceback.format_exc()}")
            return False

    def basicCreateDatabase(self, tables_dict: dict) -> bool:
        """
        创建 SQLite 数据库及其表格，处理异常并进行日志记录。

        参数：
            :param - tables_dict: 表名与创建表 SQL 语句的字典，其中键为表名，值为创建表的 SQL 语句。

        返回：
            :return - bool : 如果成功创建数据库及其表格，则返回 `True`；否则返回 `False`。

        执行过程：
            1. 检查 `tables_dict` 是否为字典类型；如果不是，记录错误日志并返回 `False`。
            2. 尝试连接到数据库。
            3. 如果 `tables_dict` 不为空：
                a. 获取数据库游标。
                b. 遍历 `tables_dict` 中的每个表名和 SQL 语句。
                c. 检查表是否已存在；如果不存在，则执行创建表的 SQL 语句，并将表名添加到 `created_tables` 列表。
                d. 提交事务。
                e. 返回 `True`。
            4. 如果 `tables_dict` 为空，记录错误日志并返回 `False`。
            5. 如果出现 `sqlite3.Error` 异常，回滚事务，记录调试日志并返回 `False`。
            6. 无论是否成功，最终都调用 `_disconnect` 方法断开数据库连接。

        异常：
            1. sqlite3.Error: 处理创建数据库表过程中出现的 SQL 错误。
        """

        if not isinstance(tables_dict, dict):
            self._Logger.error(f"Database {self._DatabaseID} create database parameter error : tables_dict must be a dictionary.")
            return False
        created_tables = []
        try:
            self._connect()
            if tables_dict:
                cursor = self._ConnectedDatabase.cursor()
                for table_name, table_sql in tables_dict.items():
                    # noinspection SqlResolve
                    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute(table_sql)
                        created_tables.append(table_name)
                self._ConnectedDatabase.commit()
                return True
            self._Logger.error(f"Database {self._DatabaseID} create database error : tables_dict is empty.")
            return False
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.debug(f"Database {self._DatabaseID} create database error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicDeleteDatabase(self) -> bool:
        """
        删除 SQLite 数据库文件，处理异常并进行日志记录。

        参数：
            无

        返回：
            :return - bool : 如果成功删除数据库，则返回 `True`；否则返回 `False`。

        执行过程：
            1. 将 `_StayConnected` 设置为 `False`。
            2. 调用 `_disconnect` 方法断开数据库连接。
            3. 删除数据库文件。
            4. 记录调试日志，指示数据库已被删除。
            5. 返回 `True`。

        异常：
            1. OSError: 处理删除数据库文件过程中出现的错误，如文件不存在或权限问题。
        """

        try:
            self._StayConnected = False
            self._disconnect()
            os.remove(self._Database)
            self._Logger.debug(f"Database {self._DatabaseID} deleted")
            return True
        except OSError as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} delete database error : {e}\n\n{traceback.format_exc()}")
            return False

    def basicGetExistingTables(self) -> list:
        """
        获取 SQLite 数据库中现有的所有表名，并进行日志记录。

        参数：
            无

        返回：
            :return - list : 包含所有现有表名的列表。如果发生错误，则返回空列表。

        执行过程：
            1. 连接到数据库。
            2. 使用 SQL 查询获取所有表的名称。
            3. 记录调试日志，列出现有的表名。
            4. 返回现有表名的列表。

        异常：
            1. sqlite3.Error: 在查询数据库过程中发生的错误，如 SQL 执行错误或数据库连接问题。
        """

        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [table[0] for table in cursor.fetchall()]
            self._Logger.debug(f"Database {self._DatabaseID} existing tables : {', '.join(existing_tables)}")
            return existing_tables
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} get existing tables error : {e}\n\n{traceback.format_exc()}")
            return []
        finally:
            self._disconnect()

    def basicCheckExistingTables(self, table_name: str) -> bool:
        """
        检查指定的表是否存在于 SQLite 数据库中，并记录相关日志。

        参数：
            :param - table_name: 要检查的表名，必须是字符串类型。

        返回：
            :return - bool : 如果表存在，则返回 True；否则返回 False。如果发生错误，也返回 False。

        执行过程：
            1. 检查 `table_name` 是否为字符串类型。
            2. 连接到数据库。
            3. 使用 SQL 查询检查表是否存在。
            4. 记录调试日志，表存在或不存在。
            5. 返回表是否存在的布尔值。

        异常：
            1. sqlite3.Error: 在查询数据库过程中发生的错误，如 SQL 执行错误或数据库连接问题。
        """

        if not isinstance(table_name, str):
            self._Logger.error(f"Database {self._DatabaseID} check existing tables parameter error : table_name must be a string.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone()[0] == 1
            if exists:
                self._Logger.debug(f"Database {self._DatabaseID} table {table_name} exists")
                return exists
            self._Logger.debug(f"Database {self._DatabaseID} table {table_name} not exists")
            return exists
        except sqlite3.Error as e:
            self._Logger.error(f"Database {self._DatabaseID} check table exists error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicCreateTable(self, table_name, table_sql) -> bool:
        """
        创建一个新表到 SQLite 数据库中，如果表已存在则不进行操作，并记录相关日志。

        参数：
            :param - table_name: 要创建的表名，必须是字符串类型。
            :param - table_sql: 创建表的 SQL 语句，必须是字符串类型。

        返回：
            :return - bool : 如果表成功创建，则返回 True；如果表已经存在，则返回 False。如果发生错误，也返回 False。

        执行过程：
            1. 连接到数据库。
            2. 检查表是否已经存在。
            3. 如果表不存在，则执行创建表的 SQL 语句。
            4. 提交事务。
            5. 记录表创建成功的日志或表已存在的日志。
            6. 返回表创建的结果。

        异常：
            1. sqlite3.Error: 在执行创建表 SQL 时发生的错误，如 SQL 执行错误或数据库连接问题。
        """

        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(table_sql)
                self._ConnectedDatabase.commit()
                self._Logger.debug(f"Database {self._DatabaseID} created table {table_name}")
                return True
            self._Logger.debug(f"Database {self._DatabaseID} table {table_name} already exists")
            return False
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} create table error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicDeleteTable(self, table_name: str) -> bool:
        """
        从 SQLite 数据库中删除指定的表。如果表不存在，则不会引发错误，并记录相关日志。

        参数：
            :param - table_name: 要删除的表名，必须是字符串类型。

        返回：
            :return - bool : 如果表成功删除，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 连接到数据库。
            2. 执行删除表的 SQL 语句，如果表不存在不会引发错误。
            3. 提交事务。
            4. 记录表删除成功的日志。
            5. 返回表删除的结果。

        异常：
            1. sqlite3.Error: 在执行删除表 SQL 时发生的错误，如 SQL 执行错误或数据库连接问题。
        """

        if not isinstance(table_name, str):
            self._Logger.error(f"Database {self._DatabaseID} delete table parameter error : table_name must be a string.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} table {table_name} deleted")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} delete table error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicInsertData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        插入数据。如果启用了加密，将对指定的列进行加密处理。

        参数：
            :param - query: 插入数据的 SQL 查询语句，必须是字符串类型。
            :param - data: 要插入的数据，可以是元组、列表或字典类型。
            :param - encrypt: 是否对数据进行加密，布尔值。
            :param - encrypt_column: 需要加密的列的索引列表，仅在 encrypt 为 True 时有效。

        返回：
            :return - bool : 如果数据成功插入，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 验证参数类型，确保 query 是字符串，data 是 tuple、list 或 dict，encrypt 是布尔值。
            2. 连接到数据库。
            3. 如果启用了加密且提供了加密列的索引，则对数据进行加密处理。
            4. 执行插入数据的 SQL 语句。
            5. 提交事务。
            6. 记录数据插入成功的日志。
            7. 返回数据插入的结果。

        异常：
            1. sqlite3.Error: 在执行插入数据的 SQL 语句时发生的错误，如 SQL 执行错误或数据库连接问题。
        """

        if not isinstance(query, str):
            self._Logger.error(f"Database {self._DatabaseID} insert data parameter error : query must be a string.")
            return False
        if not isinstance(data, (tuple, list, dict)):
            self._Logger.error(f"Database {self._DatabaseID} insert data parameter error : data must be a tuple or list or dict.")
            return False
        if not isinstance(encrypt, bool):
            self._Logger.error(f"Database {self._DatabaseID} insert data parameter error : encrypt must be a boolean.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            if encrypt and encrypt_column is not None and self._Encryptor is not None:
                data = [
                    self._Encryptor.aesEncrypt(data[i])
                    if i in encrypt_column and isinstance(data[i], str)
                    else data[i]
                    for i in range(len(data))
                ]
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} insert data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} insert data error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicInsertDatas(self, query: str, data_list: list, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        插入多条数据。如果启用了加密，将对指定的列进行加密处理。

        参数：
            :param - query: 插入数据的 SQL 查询语句，必须是字符串类型。
            :param - data_list: 包含要插入的数据的列表，每项数据可以是元组、列表或字典类型。
            :param - encrypt: 是否对数据进行加密，布尔值。
            :param - encrypt_column: 需要加密的列的索引列表，仅在 encrypt 为 True 时有效。

        返回：
            :return - bool : 如果所有数据成功插入，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 验证参数类型，确保 query 是字符串，data_list 是 list，encrypt 是布尔值。
            2. 连接到数据库。
            3. 对于 data_list 中的每一项数据，如果启用了加密且提供了加密列的索引，则对数据进行加密处理。
            4. 执行插入数据的 SQL 语句。
            5. 提交事务。
            6. 记录数据插入成功的日志。
            7. 返回数据插入的结果。

        异常：
            1. Exception: 在执行插入数据的 SQL 语句时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(query, str):
            self._Logger.error(f"Database {self._DatabaseID} insert datas parameter error : query must be a string.")
            return False
        if not isinstance(data_list, (tuple, list, dict)):
            self._Logger.error(f"Database {self._DatabaseID} insert datas parameter error : data_list must be a tuple or list or dict.")
            return False
        if not isinstance(encrypt, bool):
            self._Logger.error(f"Database {self._DatabaseID} insert datas parameter error : encrypt must be a boolean.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            for data in data_list:
                if encrypt and encrypt_column is not None and self._Encryptor is not None:
                    data = [
                        self._Encryptor.aesEncrypt(data[i])
                        if i in encrypt_column and isinstance(data[i], str)
                        else data[i]
                        for i in range(len(data))
                    ]
                cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} insert datas completed")
            return True
        except Exception as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} insert datas error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicDeleteData(self, query: str, data: tuple | list | dict | str) -> bool:
        """
        从数据库中删除数据。

        参数：
            :param - query: 删除数据的 SQL 查询语句，必须是字符串类型。
            :param - data: 要删除的数据，可以是元组、列表、字典或字符串类型，用于匹配 SQL 查询条件。

        返回：
            :return - bool : 如果数据成功删除，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 验证参数类型，确保 query 是字符串，data 是元组、列表、字典或字符串。
            2. 连接到数据库。
            3. 执行删除数据的 SQL 语句。
            4. 提交事务。
            5. 记录数据删除成功的日志。
            6. 返回数据删除的结果。

        异常：
            1. sqlite3.Error: 在执行删除数据的 SQL 语句时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(query, str):
            self._Logger.error(f"Database {self._DatabaseID} delete data parameter error : query must be a string.")
            return False
        if not isinstance(data, (tuple, list, dict, str)):
            self._Logger.error(f"Database {self._DatabaseID} delete data parameter error : data must be a tuple or list or dict or str.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} delete data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} delete data error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicDeleteAllData(self, table_name: str) -> bool:
        """
        从指定的表中删除所有数据。

        参数：
            :param - table_name: 要删除数据的表名，必须是字符串类型。

        返回：
            :return - bool : 如果所有数据成功删除，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 验证参数类型，确保 table_name 是字符串。
            2. 连接到数据库。
            3. 执行删除所有数据的 SQL 语句。
            4. 提交事务。
            5. 记录数据删除成功的日志。
            6. 返回数据删除的结果。

        异常：
            1. sqlite3.Error: 在执行删除数据的 SQL 语句时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(table_name, str):
            self._Logger.error(f"Database {self._DatabaseID} delete all data parameter error : table_name must be a string.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlWithoutWhere
            query = f"DELETE FROM {table_name}"
            cursor.execute(query)
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} delete all data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} delete all data error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicUpdateData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        更新数据库中指定表的数据。

        参数：
            :param - query: 执行更新操作的 SQL 查询语句，必须是字符串类型。
            :param - data: 更新的数据，可以是元组、列表或字典类型。
            :param - encrypt: 是否对数据进行加密，默认为 False。
            :param - encrypt_column: 需要加密的列的索引列表，仅在 encrypt 为 True 时有效。

        返回：
            :return - bool : 如果数据成功更新，则返回 True；如果发生错误，则返回 False。

        执行过程：
            1. 验证参数类型，确保 query 是字符串，data 是元组、列表或字典，encrypt 是布尔值。
            2. 连接到数据库。
            3. 如果需要加密且提供了加密器，使用加密器对指定的列进行加密。
            4. 执行更新操作的 SQL 语句。
            5. 提交事务。
            6. 记录更新操作成功的日志。
            7. 返回数据更新的结果。

        异常：
            1. sqlite3.Error: 在执行更新数据的 SQL 语句时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(query, str):
            self._Logger.error(f"Database {self._DatabaseID} update data parameter error : query must be a string.")
            return False
        if not isinstance(data, (tuple, list, dict)):
            self._Logger.error(f"Database {self._DatabaseID} update data parameter error : data must be a tuple or list or dict.")
            return False
        if not isinstance(encrypt, bool):
            self._Logger.error(f"Database {self._DatabaseID} update data parameter error : encrypt must be a boolean.")
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            if encrypt and encrypt_column is not None and self._Encryptor is not None:
                data = [
                    self._Encryptor.aesEncrypt(data[i])
                    if i in encrypt_column and isinstance(data[i], str)
                    else data[i]
                    for i in range(len(data))
                ]
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} update data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            self._Logger.error(f"Database {self._DatabaseID} update data error : {e}\n\n{traceback.format_exc()}")
            return False
        finally:
            self._disconnect()

    def basicSearchData(self, table_name: str, unique_id: str, unique_id_row: str, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        在指定表中根据唯一标识符查找数据，并根据需要进行解密。

        参数：
            :param - table_name: 要查询的表名，必须是字符串类型。
            :param - unique_id: 唯一标识符，用于定位数据，必须是字符串类型。
            :param - unique_id_row: 存储唯一标识符的列名，必须是字符串类型。
            :param - decrypt: 是否对数据进行解密，默认为 False。
            :param - decrypt_column: 需要解密的列的索引列表，仅在 decrypt 为 True 时有效。

        返回：
            :return - list : 查找到的行数据，如果没有找到数据或发生错误，则返回空列表。

        执行过程：
            1. 验证参数类型，确保 table_name、unique_id、unique_id_row 都是字符串类型，decrypt 是布尔值。
            2. 连接到数据库。
            3. 执行 SQL 查询以查找数据。
            4. 如果找到数据且需要解密，则对指定的列进行解密。
            5. 记录查询操作的成功日志。
            6. 返回查找到的行数据。

        异常：
            1. sqlite3.Error: 在执行查询操作时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(table_name, str):
            self._Logger.error(f"Database {self._DatabaseID} search data parameter error : table_name must be a string.")
            return []
        if not isinstance(unique_id, str):
            self._Logger.error(f"Database {self._DatabaseID} search data parameter error : unique_id must be a string.")
            return []
        if not isinstance(unique_id_row, str):
            self._Logger.error(f"Database {self._DatabaseID} search data parameter error : unique_id_row must be a string.")
            return []
        if not isinstance(decrypt, bool):
            self._Logger.error(f"Database {self._DatabaseID} search data parameter error : decrypt must be a boolean.")
            return []
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            query = f"SELECT * FROM {table_name} WHERE {unique_id_row} = ?"
            cursor.execute(query, (unique_id,))
            row = cursor.fetchone()
            if row is None:
                self._Logger.info(f"Database {self._DatabaseID} No data found for ID {unique_id}")
                return []
            if decrypt and decrypt_column is not None and row and self._Encryptor is not None:
                row = [self._Encryptor.aesDecrypt(row[i])
                       if i in decrypt_column and isinstance(row[i], str)
                       else row[i] for i in range(len(row))
                       ]
            self._Logger.debug(f"Database {self._DatabaseID} search data completed")
            return row
        except sqlite3.Error as e:
            self._Logger.error(f"Database {self._DatabaseID} search data error : {e}\n\n{traceback.format_exc()}")
            return []
        finally:
            self._disconnect()

    def basicSearchDatas(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        在指定表中查找所有数据，并根据需要进行解密和排序。

        参数：
            :param - table_name: 要查询的表名，必须是字符串类型。
            :param - sort_by_column: 可选的排序列索引，如果不为空，则按此列排序，必须是整数类型。
            :param - decrypt: 是否对数据进行解密，默认为 False。
            :param - decrypt_column: 需要解密的列的索引列表，仅在 decrypt 为 True 时有效。

        返回：
            :return - list : 查找到的所有行数据。如果没有找到数据或发生错误，则返回空列表。

        执行过程：
            1. 验证参数类型，确保 table_name 是字符串，sort_by_column 是整数（如果提供），decrypt 是布尔值。
            2. 连接到数据库。
            3. 构造 SQL 查询语句，根据是否提供排序列进行排序。
            4. 执行 SQL 查询并获取所有数据行。
            5. 如果需要解密，并且存在需要解密的列，则对这些列进行解密。
            6. 记录查询操作的成功日志。
            7. 返回查找到的数据行列表。

        异常：
            1. sqlite3.Error: 在执行查询操作时发生的错误，如 SQL 执行错误、数据处理错误或数据库连接问题。
        """

        if not isinstance(table_name, str):
            self._Logger.error(f"Database {self._DatabaseID} search datas parameter error : table_name must be a string.")
            return []
        if sort_by_column is not None and not isinstance(sort_by_column, int):
            self._Logger.error(f"Database {self._DatabaseID} search datas parameter error : sort_by_column must be an integer.")
            return []
        if not isinstance(decrypt, bool):
            self._Logger.error(f"Database {self._DatabaseID} search datas parameter error : decrypt must be a boolean.")
            return []
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            query = f"SELECT * FROM {table_name}"
            if sort_by_column:
                query += f" ORDER BY {sort_by_column}"
            cursor.execute(query)
            rows = cursor.fetchall()
            if decrypt and decrypt_column is not None and rows and self._Encryptor is not None:
                decrypted_rows = []
                for row in rows:
                    decrypted_row = [
                        self._Encryptor.aesDecrypt(row[i])
                        if i in decrypt_column and isinstance(row[i], str)
                        else row[i] for i in range(len(row))
                    ]
                    decrypted_rows.append(decrypted_row)
                self._Logger.info(f"Database {self._DatabaseID} search datas completed")
                return decrypted_rows
            self._Logger.debug(f"Database {self._DatabaseID} search datas completed")
            return rows
        except sqlite3.Error as e:
            self._Logger.error(f"Database {self._DatabaseID} search datas error : {e}\n\n{traceback.format_exc()}")
            return []
        finally:
            self._disconnect()

    def basicCloseDatabase(self) -> bool:
        """
        关闭当前数据库连接。

        返回：
            :return - bool : 如果成功关闭连接，返回 True；否则返回 False。

        执行过程：
            1. 检查是否存在连接到数据库。
            2. 如果存在连接，则关闭数据库连接，并将连接对象设置为 None。
            3. 记录成功关闭连接的日志。
            4. 返回成功关闭连接的标志。

        异常：
            1. Exception: 在关闭数据库连接时发生的任何异常，如无法关闭连接的错误。
        """

        try:
            if self._ConnectedDatabase:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.debug(f"Database {self._DatabaseID} connection closed")
                return True
        except Exception as e:
            self._Logger.error(f"Database {self._DatabaseID} close database error : {e}\n\n{traceback.format_exc()}")
            return False


class ExpandSQLiteDatabase(BasicSQLiteDatabase):
    """
    BasicSQLiteDatabase扩展类，提供了对SQLite数据库表的更多操作功能，包括表创建、数据插入、更新、查询和删除。

    参数：
        :param - TablesDict：包含表结构的字典，用于在初始化时创建数据库。
        :param - Config：SQLite数据库配置对象，类型为SQLiteDatabaseConfig。
        :param - Logger：日志记录器，可以是TheSeedCoreLogger或Python的标准logging.Logger。
        :param - DebugMode：调试模式标志，默认为False。

    属性：
        - 继承自BasicSQLiteDatabase：
        - _DatabaseID：数据库的唯一标识符
        - _DatabasePath：数据库文件路径
        - _Database：数据库文件的完整路径
        - _Logger：日志记录器
        - _Encryptor：加密器对象
        - _StayConnected：是否保持连接标志
        - _ConnectedDatabase：数据库连接对象

    设计思路：
        1. 扩展数据库的基本操作功能
            a. 在初始化时根据TablesDict创建数据库
            b. 提供创建表、插入数据、更新数据、查询数据和删除数据的功能
            c. 支持数据的加密和解密
        2. 针对不同操作提供了灵活的实现
            a. 表结构创建
            b. 单条数据和多条数据的插入、更新、查询和删除
    """

    def __init__(self, TablesDict: dict, Config: SQLiteDatabaseConfig, Logger: Union[TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        super().__init__(Config, Logger, DebugMode)
        self.basicCreateDatabase(TablesDict)

    def expandCreateTable(self, table_name, tables_structured: dict):
        """
        创建一个新的表，如果表不存在的话。

        参数：
            :param - table_name: 表名。
            :param - tables_structured: 包含表结构的字典。字典应包含两个键：
                - "primary_key": 主键的名称和类型。
                - "columns": 列的名称和类型的字典。

        返回：
            :return - bool : 如果表创建成功，返回 True；否则返回 False。

        执行过程：
            1. 从 `tables_structured` 中提取主键名称和类型。
            2. 构建列定义的 SQL 语句。
            3. 构建完整的 CREATE TABLE SQL 语句，确保表不存在时才创建。
            4. 调用 `basicCreateTable` 方法执行创建表操作。

        异常：
            1. 无
        """

        pk_name, pk_type = tables_structured["primary_key"]
        columns_sql = ", ".join([f"{item_name} {item_type}" for item_name, item_type in tables_structured["columns"].items()])
        table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({pk_name} {pk_type}, {columns_sql})"
        create_result = self.basicCreateTable(table_name, table_sql)
        return create_result

    def expandUpsertItem(self, table_name: str, item_data: dict, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        在指定的表中插入或更新一条记录。如果记录已经存在，则更新该记录；如果不存在，则插入一条新记录。

        参数：
            :param - table_name: 表名。
            :param - item_data: 要插入或更新的记录数据，字典格式，其中键为列名，值为列值。
            :param - encrypt: 是否对指定的列进行加密。默认为 False。
            :param - encrypt_columns: 需要加密的列名列表。如果 `encrypt` 为 True，指定哪些列需要加密。

        返回：
            :return - bool : 如果操作成功，返回 True；否则返回 False。

        执行过程：
            1. 从 `item_data` 中提取列名和对应的值，构建 INSERT OR REPLACE SQL 语句。
            2. 如果 `encrypt` 为 True 且 `encrypt_columns` 不为 None，使用 `_Encryptor` 对指定的列进行加密。
            3. 调用 `basicInsertData` 方法执行插入或更新操作。

        异常：
            1. 无
        """

        columns = ", ".join(item_data.keys())
        placeholders = ", ".join(["?"] * len(item_data))
        query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        data = tuple(item_data.values())
        if encrypt and encrypt_columns is not None and self._Encryptor is not None:
            columns_list = list(item_data.keys())
            encrypt_column_indices = [columns_list.index(col) for col in encrypt_columns if col in columns_list]
            encrypted_data = []
            for index, value in enumerate(data):
                if index in encrypt_column_indices:
                    encrypted_data.append(self._Encryptor.aesEncrypt(value))
                else:
                    encrypted_data.append(value)
            data = tuple(encrypted_data)
        else:
            data = tuple(data)
        return self.basicInsertData(query, data, encrypt=False)

    def expandUpsertItems(self, table_name: str, items_data: list[dict], encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        在指定的表中批量插入或更新记录。如果记录已经存在，则更新该记录；如果不存在，则插入新记录。

        参数：
            :param - table_name: 表名。
            :param - items_data: 要插入或更新的记录数据，字典格式的列表，其中每个字典代表一条记录。
            :param - encrypt: 是否对指定的列进行加密。默认为 False。
            :param - encrypt_columns: 需要加密的列名列表。如果 `encrypt` 为 True，指定哪些列需要加密。

        返回：
            :return - bool : 如果操作成功，返回 True；否则返回 False。

        执行过程：
            1. 从 `items_data` 中提取列名和对应的值，构建 INSERT OR REPLACE SQL 语句。
            2. 遍历 `items_data`，将每条记录的数据提取并处理。
            3. 如果 `encrypt` 为 True 且 `encrypt_columns` 不为 None，使用 `_Encryptor` 对指定的列进行加密。
            4. 调用 `basicInsertDatas` 方法执行批量插入或更新操作。

        异常：
            1. 无
        """

        columns = ", ".join(items_data[0].keys())
        placeholders = ", ".join(["?"] * len(items_data[0]))
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        data_list = []
        for item in items_data:
            data = tuple(item.values())
            if encrypt and encrypt_columns is not None and self._Encryptor is not None:
                columns_list = list(item.keys())
                encrypt_column_indices = [columns_list.index(col) for col in encrypt_columns if col in columns_list]
                encrypted_data = []
                for index, value in enumerate(data):
                    if index in encrypt_column_indices:
                        encrypted_data.append(self._Encryptor.aesEncrypt(value) if isinstance(value, str) else value)
                    else:
                        encrypted_data.append(value)
                data = tuple(encrypted_data)
            data_list.append(data)
        return self.basicInsertDatas(sql, data_list, encrypt=False)

    def expandUpdateItem(self, table_name: str, update_data: dict, where_clause: str, where_args: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        更新指定表中的记录，根据给定的条件和数据进行更新。如果指定了需要加密的列，则对这些列的数据进行加密。

        参数：
            :param - table_name: 表名。
            :param - update_data: 要更新的数据，字典格式，其中键为列名，值为更新后的值。
            :param - where_clause: 更新条件的 SQL 片段，例如 "id = ?"。
            :param - where_args: 更新条件的参数列表，与 `where_clause` 对应。
            :param - encrypt: 是否对指定的列进行加密。默认为 False。
            :param - encrypt_columns: 需要加密的列名列表。如果 `encrypt` 为 True，指定哪些列需要加密。

        返回：
            :return - bool : 如果操作成功，返回 True；否则返回 False。

        执行过程：
            1. 根据 `update_data` 构建 SET 子句。
            2. 合成完整的 UPDATE SQL 语句。
            3. 合并更新数据和条件参数。
            4. 如果 `encrypt` 为 True 且 `encrypt_columns` 不为 None，计算需要加密的列索引并对数据进行加密。
            5. 调用 `basicUpdateData` 方法执行更新操作。

        异常：
            1. 无
        """

        set_parts = [f"{key} = ?" for key in update_data.keys()]
        set_clause = ", ".join(set_parts)
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

        data = list(update_data.values()) + list(where_args)

        if encrypt and encrypt_columns is not None and self._Encryptor is not None:
            encrypt_column_indices = [list(update_data.keys()).index(col) for col in encrypt_columns if col in update_data]
        else:
            encrypt_column_indices = None
        return self.basicUpdateData(sql, data, encrypt=encrypt, encrypt_column=encrypt_column_indices)

    def expandSearchItem(self, table_name: str, unique_id: str, unique_id_column: str, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        通过指定的唯一标识符在指定表中搜索单条记录。如果指定了需要解密的列，则对这些列的数据进行解密。

        参数：
            :param - table_name: 表名。
            :param - unique_id: 唯一标识符，用于在表中查找记录。
            :param - unique_id_column: 唯一标识符所在的列名。
            :param - decrypt: 是否对指定的列进行解密。默认为 False。
            :param - decrypt_columns: 需要解密的列名列表。如果 `decrypt` 为 True，指定哪些列需要解密。

        返回：
            :return - list : 如果找到数据，返回包含记录的列表；否则返回空列表。

        执行过程：
            1. 调用 `basicSearchData` 方法，传入指定的表名、唯一标识符、唯一标识符列名、解密标志和解密列名列表。
            2. 返回查询结果。

        异常：
            1. 无
        """

        return self.basicSearchData(table_name, unique_id, unique_id_column, decrypt, decrypt_columns)

    def expandSearchItems(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        在指定表中搜索所有记录，并可以选择对结果进行排序和解密处理。

        参数：
            :param - table_name: 表名。
            :param - sort_by_column: 用于排序的列索引。如果不指定，则不进行排序。
            :param - decrypt: 是否对指定的列进行解密。默认为 False。
            :param - decrypt_columns: 需要解密的列名列表。如果 `decrypt` 为 True，指定哪些列需要解密。

        返回：
            :return - list : 返回包含所有记录的列表。根据是否需要排序，记录会按指定列排序；如果需要解密，数据会经过解密处理。

        执行过程：
            1. 调用 `basicSearchDatas` 方法，传入指定的表名、排序列索引、解密标志和解密列名列表。
            2. 返回查询结果。

        异常：
            1. 无
        """

        return self.basicSearchDatas(table_name, sort_by_column, decrypt, decrypt_columns)

    def expandDeleteItem(self, table_name: str, where_clause: str, where_args: list) -> bool:
        """
        在指定表中删除符合条件的记录。

        参数：
            :param - table_name: 表名。
            :param - where_clause: 用于筛选记录的条件子句。
            :param - where_args: 用于条件子句的参数列表。

        返回：
            :return - bool : 如果删除操作成功，则返回 True；否则返回 False。

        执行过程：
            1. 构造删除记录的 SQL 查询语句。
            2. 调用 `basicDeleteData` 方法，传入构造的查询语句和条件参数列表。
            3. 返回删除操作的结果。

        异常：
            1. 无
        """

        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        return self.basicDeleteData(query, where_args)

    def expandDeleteItems(self, table_name: str, where_clause: str = None, where_args: list = None) -> bool:
        """
        在指定表中删除符合条件的记录，或删除表中的所有记录。

        参数：
            :param - table_name: 表名。
            :param - where_clause: 用于筛选记录的条件子句（可选）。
            :param - where_args: 用于条件子句的参数列表（可选）。

        返回：
            :return - bool : 如果删除操作成功，则返回 True；否则返回 False。

        执行过程：
            1. 如果提供了 `where_clause`：
                a. 构造删除记录的 SQL 查询语句。
                b. 调用 `basicDeleteData` 方法，传入构造的查询语句和条件参数列表。
            2. 如果未提供 `where_clause`：
                a. 调用 `basicDeleteAllData` 方法删除表中的所有记录。
                b. 记录删除所有项的日志信息。
            3. 返回删除操作的结果。

        异常：
            1. 无
        """

        if where_clause:
            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            result = self.basicDeleteData(query, where_args)
        else:
            result = self.basicDeleteAllData(table_name)
            self._Logger.debug(f"All items deleted from {table_name}.")
        return result


class TheSeedCoreSQLiteDatabase(BasicSQLiteDatabase):
    """
    TheSeedCore SQLite 数据库，用于管理 `TheSeedCore` 表的 CRUD 操作。

    参数：
        :param - Config: 数据库配置，类型为 `SQLiteDatabaseConfig`。
        :param - Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`。
        :param - DebugMode: 调试模式开关，类型为布尔值。

    属性：
        - _INSTANCE: 类级别的唯一实例，类型为 `TheSeedCoreSQLiteDatabase`。

    设计思路：
        1. 使用单例模式确保数据库连接在应用生命周期内唯一。
        2. 在初始化时创建 `TheSeedCore` 表。
        3. 提供基本的 CRUD 操作方法来管理 `TheSeedCore` 表中的记录。
        4. 支持记录的插入、更新、查询和删除操作，同时支持数据加密和解密。

    """
    _INSTANCE: TheSeedCoreSQLiteDatabase = None

    def __new__(cls, Config: SQLiteDatabaseConfig, Logger: Union[TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(TheSeedCoreSQLiteDatabase, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Config: SQLiteDatabaseConfig, Logger: Union[TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        super().__init__(Config, Logger, DebugMode)
        _tables_dict = {
            "TheSeedCore": """
                    CREATE TABLE IF NOT EXISTS TheSeedCore (
                            ItemID TEXT PRIMARY KEY,
                            ItemValue TEXT NOT NULL
                        )
            """
        }
        self.basicCreateDatabase(_tables_dict)

    def initTheSeedDatabase(self):
        """
        初始化 TheSeed 数据库，插入初始数据项。

        参数：
            :param - 无

        返回：
            :return - 无

        执行过程：
            1. 定义一个包含初始数据项的列表，每个数据项包含 `ItemID` 和 `ItemValue`。
            2. 调用 `upsertItems` 方法，将初始数据项插入到数据库中。
            3. 如果操作中发生异常，记录错误日志并输出异常详细信息。

        异常：
            1. 记录 `TheSeedCore` 数据库初始化时发生的异常信息。
        """

        try:
            item_list = [
                {"ItemID": "FirstRun", "ItemValue": "0"},
                {"ItemID": "StartTime", "ItemValue": "0"},
                {"ItemID": "CloseTime", "ItemValue": "0"},
            ]
            self.upsertItems(item_list)
        except Exception as e:
            self._Logger.error(f"TheSeedDatabaseManager init TheSeedCore database error : {e}\n\n{traceback.format_exc()}")

    def upsertItem(self, item_id: str, item_value: str, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        插入或更新 `TheSeedCore` 表中的一项数据。

        参数：
            :param - item_id: 要插入或更新的项的标识符。
            :param - item_value: 要插入或更新的项的值。
            :param - encrypt: 是否对数据进行加密。默认为 `False`。
            :param - encrypt_column: 需要加密的列名列表。仅在 `encrypt` 为 `True` 时有效。

        返回：
            :return - 成功返回 `True`，失败返回 `False`。

        执行过程：
            1. 构建 SQL 查询语句，使用 `INSERT OR REPLACE` 语法插入或更新数据。
            2. 将 `item_id` 和 `item_value` 作为参数传递给查询语句。
            3. 调用 `basicInsertData` 方法执行插入或更新操作，依据 `encrypt` 参数决定是否加密数据。

        异常：
            1. 处理 `basicInsertData` 方法中的异常情况。
        """

        query = "INSERT OR REPLACE INTO TheSeedCore (ItemID, ItemValue) VALUES (?, ?)"
        data = (item_id, item_value)
        return self.basicInsertData(query, data, encrypt, encrypt_column if encrypt else None)

    def updateItem(self, item_id: str, item_value: str, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        更新 `TheSeedCore` 表中指定项的 `ItemValue`。

        参数：
            :param - item_id: 要更新的项的 ID。
            :param - item_value: 要更新的项的值。
            :param - encrypt: 是否对数据进行加密。默认为 `False`。
            :param - encrypt_column: 需要加密的列名列表。如果 `encrypt` 为 `True`，`ItemValue` 可以在此列表中进行加密。

        返回：
            :return - 成功返回 `True`，失败返回 `False`。

        执行过程：
            1. 构建 SQL 查询语句，使用 `UPDATE` 语法更新指定 `ItemID` 的 `ItemValue`。
            2. 构建数据元组，将 `item_value` 和 `item_id` 传递给 SQL 查询。
            3. 如果 `encrypt` 为 `True` 且 `encrypt_column` 包含 `ItemValue`，则对 `item_value` 进行加密。
            4. 调用 `basicUpdateData` 方法执行更新操作。

        异常：
            1. 处理 `basicUpdateData` 方法中的异常情况。
        """

        # noinspection SqlResolve
        query = "UPDATE TheSeedCore SET ItemValue = ? WHERE ItemID = ?"
        data = (item_value, item_id)
        return self.basicUpdateData(query, data, encrypt, encrypt_column if encrypt else None)

    def upsertItems(self, items_data: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        批量插入或更新 `TheSeedCore` 表中的数据项。

        参数：
            :param - items_data: 包含要插入或更新的项数据的字典列表，每个字典包括 `ItemID` 和 `ItemValue`。
            :param - encrypt: 是否对数据进行加密。默认为 `False`。
            :param - encrypt_columns: 需要加密的列名列表。如果 `encrypt` 为 `True`，`ItemValue` 可以在此列表中进行加密。

        返回：
            :return - 成功返回 `True`，失败返回 `False`。

        执行过程：
            1. 构建 SQL 查询语句，使用 `INSERT OR REPLACE` 语法插入或更新数据。
            2. 遍历 `items_data` 列表，为每个项构建数据元组。
            3. 如果 `encrypt` 为 `True` 且 `encrypt_columns` 包含 `ItemValue`，则对 `ItemValue` 进行加密。
            4. 将数据元组添加到 `data_list` 中。
            5. 调用 `basicInsertDatas` 方法执行批量插入或更新操作。

        异常：
            1. 处理 `basicInsertDatas` 方法中的异常情况。
        """

        query = "INSERT OR REPLACE INTO TheSeedCore (ItemID, ItemValue) VALUES (?, ?)"
        data_list = []
        for item in items_data:
            item_id = item['ItemID']
            item_value = item['ItemValue']
            data_tuple = (item_id, item_value)
            if encrypt and encrypt_columns:
                if 'ItemValue' in encrypt_columns:
                    item_value = self._Encryptor.aesEncrypt(item_value)
                data_tuple = (item_id, item_value)
            data_list.append(data_tuple)
        return self.basicInsertDatas(query, data_list, encrypt=False)

    def searchItem(self, item_id, decrypt=False, decrypt_column=None) -> list:
        """
        从 `TheSeedCore` 表中根据指定的 `ItemID` 查询项的详细信息。

        参数：
            :param - item_id: 要查询的项的 ID。
            :param - decrypt: 是否对查询结果进行解密。默认为 `False`。
            :param - decrypt_column: 需要解密的列名列表。如果 `decrypt` 为 `True`，`ItemValue` 可以在此列表中进行解密。

        返回：
            :return - 查找到的项的详细信息。如果没有找到，返回空列表。

        执行过程：
            1. 调用 `basicSearchData` 方法，指定表名为 `TheSeedCore`，查询条件为 `ItemID`。
            2. 根据 `decrypt` 和 `decrypt_column` 参数决定是否对查询结果进行解密。

        异常：
            1. 处理 `basicSearchData` 方法中的异常情况。
        """

        return self.basicSearchData("TheSeedCore", item_id, "ItemID", decrypt, decrypt_column)

    def searchItems(self, order_by_column=None, decrypt=False, decrypt_column=None) -> list:
        """
        从 `TheSeedCore` 表中查询所有项，并根据指定列排序（可选）。支持对结果进行解密。

        参数：
            :param - order_by_column: 根据指定列排序。如果为 `None`，则不排序。
            :param - decrypt: 是否对查询结果进行解密。默认为 `False`。
            :param - decrypt_column: 需要解密的列名列表。如果 `decrypt` 为 `True`，则这些列会被解密。

        返回：
            :return - 查询到的所有项的详细信息列表。如果没有找到任何项，返回空列表。

        执行过程：
            1. 调用 `basicSearchDatas` 方法，指定表名为 `TheSeedCore`，并传递排序列、解密标志和解密列列表。

        异常：
            1. 处理 `basicSearchDatas` 方法中的异常情况。
        """

        return self.basicSearchDatas("TheSeedCore", order_by_column, decrypt, decrypt_column)

    def deleteItem(self, item_id: str) -> bool:
        """
        从 `TheSeedCore` 表中删除指定的项。

        参数：
            :param - item_id: 要删除项的 ID。

        返回：
            :return - 删除操作是否成功。如果成功返回 `True`，否则返回 `False`。

        执行过程：
            1. 构造删除查询语句，指定要删除的项 ID。
            2. 调用 `basicDeleteData` 方法执行删除操作。

        异常：
            1. 处理 `basicDeleteData` 方法中的异常情况。
        """

        # noinspection SqlResolve
        query = "DELETE FROM TheSeedCore WHERE ItemID = ?"
        return self.basicDeleteData(query, item_id)

    def deleteAllItems(self) -> bool:
        """
        从 `TheSeedCore` 表中删除所有项。

        返回：
            :return - 删除所有项操作是否成功。如果成功返回 `True`，否则返回 `False`。

        执行过程：
            1. 调用 `basicDeleteAllData` 方法，删除 `TheSeedCore` 表中的所有项。

        异常：
            1. 处理 `basicDeleteAllData` 方法中的异常情况。
        """

        return self.basicDeleteAllData("TheSeedCore")

    def closeDatabase(self):
        """
        关闭数据库连接。

        返回：
            :return - 无返回值。

        执行过程：
            1. 调用 `basicCloseDatabase` 方法，关闭当前数据库连接。

        异常：
            1. 处理 `basicCloseDatabase` 方法中的异常情况。
        """

        self.basicCloseDatabase()


class SQLiteDatabaseManager:
    """
    SQLite数据库管理器，管理多个 `ExpandSQLiteDatabase` 实例，并提供对 SQLite 数据库的操作接口，包括创建、获取、更新、查询和删除数据库及其表格。

    参数：
        :param - Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`，默认为 `None`。
        :param - DebugMode: 调试模式开关，类型为布尔值，默认为 `False`。

    属性：
        - INSTANCE: 类级别的唯一实例，类型为 `SQLiteDatabaseManager`。
        - _INITIALIZED: 初始化标志，类型为布尔值。

    设计思路：
        1. 使用单例模式确保 `SQLiteDatabaseManager` 的唯一实例。
        2. 提供方法创建和管理多个 `ExpandSQLiteDatabase` 实例。
        3. 提供 CRUD 操作的接口方法，允许对数据库中的表格进行各种操作。
        4. 支持数据的插入、更新、查询和删除操作，同时支持数据的加密和解密。
        5. 提供关闭单个数据库实例和所有数据库实例的方法。
    """

    INSTANCE: SQLiteDatabaseManager = None
    _INITIALIZED: bool = False

    def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        if cls.INSTANCE is None:
            cls.INSTANCE = super(SQLiteDatabaseManager, cls).__new__(cls)
        return cls.INSTANCE

    def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        if not self._INITIALIZED:
            self._Logger = defaultLogger("SQLite", DebugMode) if Logger is None else Logger
            self._SQLiteDatabase: dict = {}
            self.IsClosed = False
            SQLiteDatabaseManager._INITIALIZED = True

    def createSQLiteDatabase(self, tables_structured: dict, config: SQLiteDatabaseConfig, expand_database=ExpandSQLiteDatabase, logger: Union[TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False) -> bool:
        """
        创建一个扩展的 SQLite 数据库实例，并创建所需的表。

        参数：
            :param - tables_structured: 包含表结构信息的字典，其中每个表的结构包含主键和列信息。
            :param - config: `SQLiteDatabaseConfig` 对象，包含数据库配置。
            :param - expand_database: 用于扩展数据库功能的类或函数。
            :param - logger: 可选的日志记录器对象，支持 `TheSeedCoreLogger` 或 `logging.Logger`。
            :param - debug_mode: 是否启用调试模式。

        返回：
            :return - True: 数据库创建成功。
            :return - False: 数据库创建失败。

        执行过程：
            1. 遍历 `tables_structured` 字典，生成每个表的 SQL 创建语句。
            2. 使用 `expand_database` 参数创建自定义的数据库实例。
            3. 将新创建的数据库实例存储在 `_SQLiteDatabase` 字典中。
            4. 记录数据库创建成功的信息。

        异常：
            1. 处理数据库创建过程中的所有异常情况。
        """

        try:
            tables_dict = {}
            for table_name, structure in tables_structured.items():
                pk_name, pk_type = structure["primary_key"]
                columns_sql = ", ".join([f"{item_name} {item_type}" for item_name, item_type in structure["columns"].items()])
                table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({pk_name} {pk_type}, {columns_sql})"
                tables_dict[table_name] = table_sql
            custom_database = expand_database(tables_dict, config, logger, debug_mode)
            self._SQLiteDatabase[config.DatabaseID] = custom_database
            self._Logger.debug(f"SQLiteDatabaseManager create expand database '{config.DatabaseID}' completed")
            return True
        except Exception as e:
            self._Logger.error(f"SQLiteDatabaseManager create expand database error : {e}\n\n{traceback.format_exc()}")
            return False

    def getDatabase(self, database_id: str) -> ExpandSQLiteDatabase:
        """
        根据数据库 ID 获取扩展的 SQLite 数据库实例。

        参数：
            :param - database_id: 数据库的唯一标识符。

        返回：
            :return - ExpandSQLiteDatabase: 对应的扩展 SQLite 数据库实例。如果找不到对应的数据库，则返回 `None`。

        执行过程：
            1. 使用 `database_id` 从 `_SQLiteDatabase` 字典中获取数据库实例。

        异常：
            1. 无
        """

        return self._SQLiteDatabase.get(database_id)

    def getExistingTables(self, database_id) -> list:
        """
        获取指定数据库实例中存在的所有表名。

        参数：
            :param - database_id: 数据库的唯一标识符。

        返回：
            :return - list: 数据库中存在的表名列表。如果数据库未找到，则返回空列表。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `basicGetExistingTables` 方法。
            3. 如果存在，调用 `basicGetExistingTables` 方法获取表名。
            4. 如果实例不存在或没有该方法，记录错误日志并返回空列表。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicGetExistingTables"):
            return database_instance.basicGetExistingTables()
        else:
            self._Logger.error(f"SQLiteDatabaseManager get existing tables error : Database '{database_id}' not found.")
            return []

    def checkExistingTables(self, database_id, table_name) -> bool:
        """
        检查指定数据库中是否存在给定名称的表。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要检查的表名。

        返回：
            :return - bool: 如果表存在，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `basicCheckExistingTables` 方法。
            3. 如果存在，调用 `basicCheckExistingTables` 方法检查表是否存在。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicCheckExistingTables"):
            return database_instance.basicCheckExistingTables(table_name)
        else:
            self._Logger.error(f"DatabaseManager check existing tables error : Database '{database_id}' not found.")
            return False

    def createTable(self, database_id: str, table_name: str, tables_structured: dict) -> bool:
        """
        在指定的数据库中创建表。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要创建的表名。
            :param - tables_structured: 表的结构定义，包括主键和列的信息。

        返回：
            :return - bool: 如果表创建成功，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `expandCreateTable` 方法。
            3. 如果存在，调用 `expandCreateTable` 方法创建表。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "expandCreateTable"):
            result = database_instance.expandCreateTable(table_name, tables_structured)
            return result
        else:
            self._Logger.error(f"DatabaseManager create table error : Database '{database_id}' not found.")
            return False

    def deleteTable(self, database_id: str, table_name: str) -> bool:
        """
        在指定的数据库中删除表。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要删除的表名。

        返回：
            :return - bool: 如果表删除成功，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `basicDeleteTable` 方法。
            3. 如果存在，调用 `basicDeleteTable` 方法删除表。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicDeleteTable"):
            result = database_instance.basicDeleteTable(table_name)
            return result
        else:
            self._Logger.error(f"DatabaseManager delete table error : Database '{database_id}' not found.")
            return False

    def upsertData(self, database_id: str, table_name: str, update_data: dict, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        在指定的数据库表中插入或更新数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要插入或更新数据的表名。
            :param - update_data: 要插入或更新的数据字典。
            :param - encrypt: 是否对数据进行加密（默认 False）。
            :param - encrypt_columns: 需要加密的列名列表（如果 `encrypt` 为 True，则此参数必需）。

        返回：
            :return - bool: 如果数据插入或更新成功，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customUpsertItem` 方法。
            3. 如果存在，调用 `expandUpsertItem` 方法插入或更新数据。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpsertItem"):
            result = database_instance.expandUpsertItem(table_name, update_data, encrypt, encrypt_columns)
            return result
        else:
            self._Logger.error(f"DatabaseManager upsert data error : database '{database_id}' not found.")
            return False

    def upsertDatas(self, database_id: str, table_name: str, update_data: list, encrypt: bool = False, encrypt_columns: list = None):
        """
        在指定的数据库表中批量插入或更新数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要插入或更新数据的表名。
            :param - update_data: 要插入或更新的数据列表，每个数据项是一个字典。
            :param - encrypt: 是否对数据进行加密（默认 False）。
            :param - encrypt_columns: 需要加密的列名列表（如果 `encrypt` 为 True，则此参数必需）。

        返回：
            :return - bool: 如果数据插入或更新成功，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customUpsertItems` 方法。
            3. 如果存在，调用 `expandUpsertItems` 方法批量插入或更新数据。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpsertItems"):
            result = database_instance.expandUpsertItems(table_name, update_data, encrypt, encrypt_columns)
            return result
        else:
            self._Logger.error(f"DatabaseManager upsert datas error : database '{database_id}' not found.")
            return False

    def updateData(self, database_id: str, table_name: str, update_data: dict, where_clause: str, where_args: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        在指定的数据库表中根据条件更新数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要更新数据的表名。
            :param - update_data: 要更新的数据字典，其中键为列名，值为新值。
            :param - where_clause: 更新条件的 SQL 语句的 WHERE 部分。
            :param - where_args: 与 WHERE 子句相关联的参数列表。
            :param - encrypt: 是否对数据进行加密（默认 False）。
            :param - encrypt_columns: 需要加密的列名列表（如果 `encrypt` 为 True，则此参数必需）。

        返回：
            :return - bool: 如果数据更新成功，则返回 True；否则返回 False。如果数据库未找到，则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customUpdateItem` 方法。
            3. 如果存在，调用 `expandUpdateItem` 方法根据条件更新数据。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpdateItem"):
            result = database_instance.expandUpdateItem(table_name, update_data, where_clause, where_args, encrypt, encrypt_columns)
            return result
        else:
            self._Logger.error(f"DatabaseManager update data error : database '{database_id}' not found.")
            return False

    def searchData(self, database_id: str, table_name: str, unique_id: str, unique_id_column: str, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        在指定的数据库表中根据唯一标识符搜索数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要搜索数据的表名。
            :param - unique_id: 用于搜索的唯一标识符值。
            :param - unique_id_column: 用于搜索的唯一标识符列名。
            :param - decrypt: 是否对数据进行解密（默认 False）。
            :param - decrypt_columns: 需要解密的列名列表（如果 `decrypt` 为 True，则此参数必需）。

        返回：
            :return - list: 如果数据找到，则返回包含数据的列表；否则返回空列表。如果数据库未找到，则返回空列表。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customSearchItem` 方法。
            3. 如果存在，调用 `expandSearchItem` 方法进行数据搜索。
            4. 如果实例不存在或没有该方法，记录错误日志并返回空列表。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customSearchItem"):
            row = database_instance.expandSearchItem(table_name, unique_id, unique_id_column, decrypt, decrypt_columns)
            return row
        else:
            self._Logger.error(f"DatabaseManager search data error : database '{database_id}' not found.")
            return []

    def searchDatas(self, database_id: str, table_name: str, sort_by_column=None, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        在指定的数据库表中搜索数据，并可选地按列排序和解密数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要搜索数据的表名。
            :param - sort_by_column: 用于排序的列索引（默认为 None，不排序）。
            :param - decrypt: 是否对数据进行解密（默认 False）。
            :param - decrypt_columns: 需要解密的列名列表（如果 `decrypt` 为 True，则此参数必需）。

        返回：
            :return - list: 返回包含数据的列表；如果数据库未找到，则返回空列表。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customSearchItems` 方法。
            3. 如果存在，调用 `expandSearchItems` 方法进行数据搜索。
            4. 如果实例不存在或没有该方法，记录错误日志并返回空列表。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customSearchItems"):
            rows = database_instance.expandSearchItems(table_name, sort_by_column, decrypt, decrypt_columns)
            return rows
        else:
            self._Logger.error(f"DatabaseManager search datas error : database '{database_id}' not found.")
            return []

    def deleteData(self, database_id: str, table_name: str, where_clause: str, where_args: list) -> bool:
        """
        在指定的数据库表中删除数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要删除数据的表名。
            :param - where_clause: 用于筛选要删除记录的 SQL 条件子句。
            :param - where_args: 用于替换 SQL 条件子句中的占位符的参数列表。

        返回：
            :return - bool: 如果成功删除数据则返回 True；否则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customDeleteItem` 方法。
            3. 如果存在，调用 `expandDeleteItem` 方法执行删除操作。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customDeleteItem"):
            result = database_instance.expandDeleteItem(table_name, where_clause, where_args)
            return result
        else:
            self._Logger.error(f"DatabaseManager delete data error : database '{database_id}' not found.")
            return False

    def deleteDatas(self, database_id: str, table_name: str, where_clause: str = None, where_args: list = None) -> bool:
        """
        在指定的数据库表中删除数据。可以根据条件删除特定的数据，也可以删除表中的所有数据。

        参数：
            :param - database_id: 数据库的唯一标识符。
            :param - table_name: 要删除数据的表名。
            :param - where_clause: 用于筛选要删除记录的 SQL 条件子句。如果为 None，则删除表中的所有数据。
            :param - where_args: 用于替换 SQL 条件子句中的占位符的参数列表，仅在 `where_clause` 不为 None 时使用。

        返回：
            :return - bool: 如果成功删除数据则返回 True；否则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `customDeleteItems` 方法。
            3. 如果存在，调用 `expandDeleteItems` 方法执行删除操作。
            4. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customDeleteItems"):
            result = database_instance.expandDeleteItems(table_name, where_clause, where_args)
            return result
        else:
            self._Logger.error(f"DatabaseManager delete datas error : database '{database_id}' not found.")
            return False

    def closeDatabase(self, database_id: str) -> bool:
        """
        关闭指定的数据库连接，并从管理的数据库列表中移除该数据库实例。

        参数：
            :param - database_id: 要关闭的数据库的唯一标识符。

        返回：
            :return - bool: 如果成功关闭数据库则返回 True；否则返回 False。

        执行过程：
            1. 调用 `getDatabase` 方法获取数据库实例。
            2. 检查获取的实例是否存在 `basicCloseDatabase` 方法。
            3. 如果存在，调用 `basicCloseDatabase` 方法关闭数据库连接。
            4. 如果成功关闭数据库，移除数据库实例。
            5. 如果实例不存在或没有该方法，记录错误日志并返回 False。

        异常：
            1. 无
        """

        database_instance = self.getDatabase(database_id)
        if database_instance is not None and hasattr(database_instance, "basicCloseDatabase"):
            result = database_instance.basicCloseDatabase()
            if result:
                self._SQLiteDatabase.pop(database_id)
            return result
        else:
            self._Logger.error(f"DatabaseManager close database error : database '{database_id}' not found.")
            return False

    def closeAllDatabase(self) -> bool:
        """
        关闭所有已管理的 SQLite 数据库连接，并标记为已关闭。

        参数：
            无

        返回：
            :return - bool: 如果成功关闭所有数据库则返回 True。

        执行过程：
            1. 检查 `_SQLiteDatabase` 是否有数据库实例。
            2. 遍历所有数据库实例的唯一标识符。
            3. 调用 `closeDatabase` 方法关闭每个数据库连接。
            4. 设置 `IsClosed` 标志为 True。
            5. 记录调试日志，表示所有数据库连接已关闭。

        异常：
            1. 无
        """

        if self._SQLiteDatabase:
            for database_id in list(self._SQLiteDatabase.keys()):
                self.closeDatabase(database_id)
        self.IsClosed = True
        self._Logger.debug("All sqlite databases closed.")
        return True


# Try defining the MySQL database class
try:
    # noinspection PyUnresolvedReferences
    import mysql.connector
    # noinspection PyUnresolvedReferences
    from mysql.connector import errorcode
except ImportError:
    class BasicMySQLDatabase:
        # noinspection PyUnusedLocal
        def __init__(self, Config: MySQLDatabaseConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The mysql connector is not installed. Please install it using 'pip install mysql-connector-python'.")


    class MySQLDatabaseManager:
        INSTANCE: MySQLDatabaseManager = None

        # noinspection PyUnusedLocal
        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The mysql connector is not installed. Please install it using 'pip install mysql-connector-python'.")
else:
    MySQLSupport = True


    class BasicMySQLDatabase:
        """
        MySQL 数据库基类，提供基本的操作功能，包括连接、断开连接、执行查询、获取查询结果、创建和删除表格等。

        参数：
            :param - Config: MySQL 数据库配置，类型为 `MySQLDatabaseConfig`。
            :param - Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`，默认为 `None`。
            :param - DebugMode: 调试模式开关，类型为布尔值，默认为 `False`。

        属性：
            - _Config: 数据库配置，类型为 `MySQLDatabaseConfig`。
            - _Connection: 数据库连接对象，类型为 `mysql.connector.connection.MySQLConnection` 或 `None`。
            - _Cursor: 数据库游标对象，类型为 `mysql.connector.cursor.MySQLCursor` 或 `None`。
            - _Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`。
            - _StayConnected: 是否保持连接，类型为布尔值。

        设计思路：
            1. 提供数据库连接和断开连接的功能，并根据配置进行操作。
            2. 提供方法执行 SQL 查询，包括创建表格、插入数据、删除表格等。
            3. 支持提交和回滚事务，以确保数据库操作的原子性。
            4. 在操作过程中记录日志，以便调试和错误排查。
        """

        def __init__(self, Config: MySQLDatabaseConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._Config = Config
            self._Connection = None
            self._Cursor = None
            self._Logger = defaultLogger("MySQL", DebugMode) if Logger is None else Logger
            self._StayConnected = False

        def _connect(self):
            """
            建立与 MySQL 数据库的连接，并初始化数据库游标。

            参数：
                无

            返回：
                无

            执行过程：
                1. 检查是否已有连接存在且是否需要保持连接。
                2. 如果没有连接或需要重新连接，创建新的数据库连接。
                3. 使用连接创建一个新的游标。
                4. 记录调试日志，表示数据库连接已成功建立。

            异常：
                1. mysql.connector.Error: 处理 MySQL 连接错误。
                    - `ER_ACCESS_DENIED_ERROR`: 用户名或密码错误。
                    - `ER_BAD_DB_ERROR`: 数据库不存在。
                    - 其他 MySQL 错误: 记录详细错误信息及堆栈跟踪。
            """

            try:
                if not self._Connection or not self._StayConnected:
                    self._Connection = mysql.connector.connect(
                        host=self._Config.Host,
                        port=self._Config.Port,
                        user=self._Config.User,
                        password=self._Config.Password,
                        database=self._Config.Database,
                    )
                    self._Cursor = self._Connection.cursor()
                    self._Logger.debug(f"Database {self._Config.Database} connection completed")
            except mysql.connector.Error as e:
                if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                    self._Logger.error("Something is wrong with your user name or password")
                elif e.errno == errorcode.ER_BAD_DB_ERROR:
                    self._Logger.error("Database does not exist")
                else:
                    self._Logger.error(f"Database connection error : {e}\n\n{traceback.format_exc()}")

        def _disconnect(self):
            """
            断开与 MySQL 数据库的连接，并清理相关资源。

            参数：
                无

            返回：
                无

            执行过程：
                1. 检查是否存在连接，并且是否需要断开连接。
                2. 如果满足条件，关闭连接并清理游标和连接对象。
                3. 记录调试日志，表示数据库连接已成功断开。

            异常：
                无
            """

            if self._Connection and not self._StayConnected:
                self._Connection.close()
                self._Connection = None
                self._Cursor = None
                self._Logger.debug(f"Disconnected from database {self._Config.Database}")

        def executeQuery(self, query: str, params=None):
            """
            执行给定的 SQL 查询，并处理事务的提交和回滚。

            参数：
                :param - query: 要执行的 SQL 查询语句。
                :param - params: list or None，可选的查询参数。如果有参数，请提供一个与查询语句匹配的元组或列表。

            返回：
                无

            执行过程：
                1. 连接到数据库。
                2. 执行给定的查询，并提供参数（如果有的话）。
                3. 提交事务以保存更改。
                4. 记录调试日志，表示查询执行成功。
                5. 处理可能发生的异常，回滚事务并记录错误日志。
                6. 断开数据库连接。

            异常：
                1. mysql.connector.Error: 处理数据库操作时发生的异常。
            """

            try:
                self._connect()
                self._Cursor.execute(query, params)
                self._Connection.commit()
                self._Logger.debug(f"Database {self._Config.Database} query executed")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} executing query error : {e}\n\n{traceback.format_exc()}")
            finally:
                self._disconnect()

        def fetchQuery(self, query: str, params=None):
            """
            执行给定的 SQL 查询，并返回所有结果。

            参数：
                :param - query: 要执行的 SQL 查询语句。
                :param - params:  list or None，可选的查询参数。如果有参数，请提供一个与查询语句匹配的元组或列表。

            返回：
                :return - list: 查询结果的列表。如果查询失败或没有结果，返回空列表。

            执行过程：
                1. 连接到数据库。
                2. 执行给定的查询，并提供参数（如果有的话）。
                3. 获取并返回所有查询结果。
                4. 记录调试日志，表示查询成功。
                5. 处理可能发生的异常，回滚事务并记录错误日志。
                6. 断开数据库连接。

            异常：
                1. mysql.connector.Error: 处理数据库操作时发生的异常。
            """

            try:
                self._connect()
                self._Cursor.execute(query, params)
                result = self._Cursor.fetchall()
                self._Logger.debug(f"Database {self._Config.Database} query fetched : {query}")
                return result
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} fetching query error : {e}\n\n{traceback.format_exc()}")
                return []
            finally:
                self._disconnect()

        def createTable(self, table_name: str, table_structure: str):
            """
            创建一个新的表，如果表已经存在则不会重新创建。

            参数：
                :param - table_name: 要创建的表的名称。
                :param - table_structure: 表的结构定义，包括列名和数据类型。

            返回：
                :return - None: 无返回值。

            执行过程：
                1. 使用提供的表名和结构定义执行创建表的 SQL 查询。
                2. 记录调试日志，表示表已成功创建。
                3. 处理可能发生的异常，回滚事务并记录错误日志。

            异常：
                1. mysql.connector.Error: 处理数据库操作时发生的异常。
            """

            try:
                self.executeQuery(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_structure})")
                self._Logger.debug(f"Database {self._Config.Database} table created.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} creating table error : {e}\n\n{traceback.format_exc()}")

        def insertData(self, query: str, data: tuple):
            """
            插入数据到数据库表中。

            参数：
                :param - query: 插入数据的 SQL 查询语句。
                :param - data : 要插入的数据。

            返回：
                :return - None: 无返回值。

            执行过程：
                1. 执行插入数据的 SQL 查询。
                2. 记录调试日志，表示数据已成功插入。
                3. 处理可能发生的异常，回滚事务并记录错误日志。

            异常：
                1. mysql.connector.Error: 处理数据库操作时发生的异常。
            """

            try:
                self.executeQuery(query, data)
                self._Logger.debug(f"Database {self._Config.Database} data inserted.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} inserting data error : {e}\n\n{traceback.format_exc()}")

        def deleteTable(self, table_name: str):
            """
            删除指定的数据库表。

            参数：
                :param - table_name: 要删除的表名。

            返回：
                :return - None: 无返回值。

            执行过程：
                1. 执行删除表的 SQL 查询。
                2. 记录调试日志，表示表已成功删除。
                3. 处理可能发生的异常，回滚事务并记录错误日志。

            异常：
                1. mysql.connector.Error: 处理数据库操作时发生的异常。
            """

            try:
                self.executeQuery(f"DROP TABLE IF EXISTS {table_name}")
                self._Logger.debug(f"Database {self._Config.Database} table {table_name} deleted.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} deleting table error : {e}\n\n{traceback.format_exc()}")

        def closeDatabase(self):
            """
            关闭与数据库的连接。

            参数：
                无

            返回：
               无

            执行过程：
                1. 调用 `_disconnect` 方法来关闭数据库连接。

            异常：
                1. 无特殊异常处理。
            """

            self._disconnect()


    class MySQLDatabaseManager:
        """
        MySQL数据库管理器，管理 MySQL 数据库实例，包括创建、获取、执行查询、插入数据、创建和删除表格等功能。

        参数：
            :param - Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`，默认为 `None`。
            :param - DebugMode: 调试模式开关，类型为布尔值，默认为 `False`。

        属性：
            - _Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`。
            - _MySQLDatabase: 存储 MySQL 数据库实例的字典，键为数据库名称，值为 `BasicMySQLDatabase` 实例。

        设计思路：
            1. 单例模式：确保 `MySQLDatabaseManager` 类只有一个实例。
            2. 提供数据库实例的创建和管理功能，并支持基本的数据库操作，如执行查询、插入数据、创建和删除表格。
            3. 记录操作日志，以便于调试和错误排查。
            4. 通过数据库名称获取和操作相应的 `BasicMySQLDatabase` 实例。
        """

        INSTANCE: MySQLDatabaseManager = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, *args, **kwargs):
            if not cls.INSTANCE:
                # noinspection PySuperArguments
                cls.INSTANCE = super(MySQLDatabaseManager, cls).__new__(cls)
            return cls.INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if not self._INITIALIZED:
                self._Logger = defaultLogger("MySQL", DebugMode) if Logger is None else Logger
                self._MySQLDatabase = {}
                MySQLDatabaseManager._INITIALIZED = True

        def createMySQLDatabase(self, config: MySQLDatabaseConfig, logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False):
            """
            创建一个 MySQL 数据库实例，并将其添加到 `_MySQLDatabase` 字典中。

            参数：
                :param config: 数据库配置对象，包含数据库连接的详细信息。
                :param logger: 可选的日志记录器实例，用于记录日志信息。
                :param debug_mode: 可选的布尔值，指示是否启用调试模式。

            返回：
                :return - None: 无返回值。

            执行过程：
                1. 检查 `config.Database` 是否已存在于 `_MySQLDatabase` 字典中。
                2. 如果不存在，则创建一个新的 `BasicMySQLDatabase` 实例，并将其添加到 `_MySQLDatabase` 字典中。
                3. 记录数据库创建成功的日志。

            异常：
                1. 无特殊异常处理。
            """

            if config.Database not in self._MySQLDatabase:
                self._MySQLDatabase[config.Database] = BasicMySQLDatabase(config, logger, debug_mode)
                self._Logger.debug(f"Database {config.Database} created.")

        def getDatabase(self, database_name: str) -> BasicMySQLDatabase:
            """
            根据数据库名称从 `_MySQLDatabase` 字典中获取对应的 `BasicMySQLDatabase` 实例。

            参数：
                :param database_name: 要获取的数据库的名称。

            返回：
                :return - BasicMySQLDatabase: 对应的 `BasicMySQLDatabase` 实例，如果未找到则返回 `None`。

            执行过程：
                1. 从 `_MySQLDatabase` 字典中获取指定名称的数据库实例。

            异常：
                1. 无特殊异常处理。
            """

            return self._MySQLDatabase.get(database_name)

        def executeQuery(self, database_name: str, query: str, params=None):
            """
            在指定的数据库实例中执行给定的 SQL 查询。

            参数：
                :param database_name: 需要执行查询的数据库的名称。
                :param query: 要执行的 SQL 查询语句。
                :param params: 查询语句中的参数（可选）。

            返回：
                :return - 执行查询的结果。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `executeQuery` 方法执行查询。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.executeQuery(query, params)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def fetchQuery(self, database_name: str, query: str, params=None):
            """
            在指定的数据库实例中执行查询并获取结果。

            参数：
                :param database_name: 需要执行查询的数据库的名称。
                :param query: 要执行的 SQL 查询语句。
                :param params: 查询语句中的参数（可选）。

            返回：
                :return - 查询结果的列表。如果数据库实例不存在，则返回 None。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `fetchQuery` 方法执行查询并返回结果。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.fetchQuery(query, params)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def createTable(self, database_name: str, table_name: str, table_structure: str):
            """
            在指定的数据库实例中创建一个表。

            参数：
                :param database_name: 需要创建表的数据库的名称。
                :param table_name: 要创建的表的名称。
                :param table_structure: 表的结构定义，包括字段名和字段类型。

            返回：
                :return - 返回创建表的结果。如果数据库实例不存在，则返回 None。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `createTable` 方法创建表。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.createTable(table_name, table_structure)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def insertData(self, database_name: str, table_name: str, data: tuple):
            """
            在指定的数据库实例中向表中插入数据。

            参数：
                :param database_name: 数据库的名称，数据将被插入到该数据库的表中。
                :param table_name: 数据库表的名称，数据将被插入到该表中。
                :param data: 要插入的数据，以元组形式传递，数据的顺序应与表的列顺序一致。

            返回：
                :return - 返回插入数据的结果。如果数据库实例不存在，则返回 None。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `insertData` 方法将数据插入到指定的表中。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.insertData(table_name, data)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def deleteTable(self, database_name: str, table_name: str):
            """
            在指定的数据库实例中删除表。

            参数：
                :param database_name: 数据库的名称，其中的表将被删除。
                :param table_name: 要删除的表的名称。

            返回：
                :return - 返回删除表的结果。如果数据库实例不存在，则返回 None。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `deleteTable` 方法删除指定的表。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.deleteTable(table_name)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def closeDatabase(self, database_name: str):
            """
            关闭指定的数据库实例的连接。

            参数：
                :param database_name: 要关闭连接的数据库的名称。

            返回：
                :return - 返回关闭数据库连接的结果。如果数据库实例不存在，则返回 None。

            执行过程：
                1. 使用 `getDatabase` 方法获取指定名称的数据库实例。
                2. 如果实例存在，调用该实例的 `closeDatabase` 方法关闭连接。
                3. 如果实例不存在，记录错误日志。

            异常：
                1. 无特殊异常处理，但如果数据库实例不存在，会记录错误日志。
            """

            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.closeDatabase()
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def closeAllDatabase(self):
            """
            关闭所有 MySQL 数据库实例的连接。

            参数：
                无

            返回：
                :return - 无

            执行过程：
                1. 遍历 `_MySQLDatabase` 中所有数据库的名称。
                2. 对每个数据库名称，调用 `closeDatabase` 方法关闭其连接。
                3. 记录日志，指示所有 MySQL 数据库连接已关闭。

            异常：
                1. 无特殊异常处理，所有数据库的关闭过程都由 `closeDatabase` 方法处理。
            """

            for database_name in list(self._MySQLDatabase.keys()):
                self.closeDatabase(database_name)
            self._Logger.debug("All MySQL databases closed.")

# Try defining the Redis database class
try:
    # noinspection PyUnresolvedReferences
    import redis
except ImportError:
    class BasicRedisDatabase:
        # noinspection PyUnusedLocal
        def __init__(self, Config: RedisDatabaseConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The redis connector is not installed. Please install it using 'pip install redis'.")


    class RedisDatabaseManager:
        INSTANCE: RedisDatabaseManager = None

        # noinspection PyUnusedLocal
        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The redis connector is not installed. Please install it using 'pip install redis'.")
else:
    RedisSupport = True


    class BasicRedisDatabase:
        """
        Redis数据库基类，提供对 Redis 数据库的基本操作，包括键值对操作、哈希操作、列表操作、集合操作等。

        参数：
            :param - Config: Redis 数据库配置，类型为 `RedisDatabaseConfig`。
            :param - Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`，默认为 `None`。
            :param - DebugMode: 调试模式开关，类型为布尔值，默认为 `False`。

        属性：
            - _RedisHost: Redis 主机地址。
            - _RedisPort: Redis 端口号。
            - _Password: Redis 密码。
            - _Num: Redis 数据库编号。
            - _Logger: 日志记录器，类型为 `TheSeedCoreLogger` 或 `logging.Logger`。
            - _Encryptor: 加密器，用于加密和解密操作。
            - _Client: Redis 客户端实例，用于执行 Redis 命令。

        设计思路：
            1. 通过配置对象初始化 Redis 客户端。
            2. 提供各种 Redis 数据库操作方法，包括基本的键值对操作、哈希操作、列表操作、集合操作等。
            3. 支持数据加密和解密功能。
            4. 提供事务、流水线、脚本执行等高级操作。
            5. 支持 Redis 的发布/订阅、位图、地理空间、HyperLogLog、流、锁等扩展功能。
            6. 记录操作日志，以便于调试和错误排查。
        """

        def __init__(self, Config: RedisDatabaseConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._configParamsValidation(Config)
            self._RedisHost = Config.Host
            self._RedisPort = Config.Port
            self._Password = Config.Password
            self._Num = Config.Num
            self._Logger = defaultLogger("Redis", DebugMode) if Logger is None else Logger
            self._Encryptor = Config.Encryptor
            self._Client = redis.Redis(host=Config.Host, port=Config.Port, db=Config.Num)

        @staticmethod
        def _configParamsValidation(config: RedisDatabaseConfig):
            if config.Host is None:
                raise ValueError("Host cannot be None.")
            if not isinstance(config.Host, str):
                raise ValueError("Host must be a string.")
            if config.Port is None:
                raise ValueError("Port cannot be None.")
            if not isinstance(config.Port, int):
                raise ValueError("Port must be an integer.")
            if not (isinstance(config.Password, str) or config.Password is None):
                raise ValueError("Password must be a string or None.")
            if config.Num is None:
                raise ValueError("Num cannot be None.")
            if not isinstance(config.Num, int):
                raise ValueError("Num must be an integer.")

        def setKey(self, key, value, ex=None, encrypt=False):
            try:
                if encrypt and self._Encryptor is not None:
                    value = self._Encryptor.aesEncrypt(value)
                self._Client.set(key, value, ex=ex)
                self._Logger.debug(f"Database {self._Client} set key {key} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} set key error : {e}\n\n{traceback.format_exc()}")
                return False

        def getValue(self, key, decrypt=False):
            try:
                value = self._Client.get(key)
                if decrypt and self._Encryptor is not None:
                    value = self._Encryptor.aesDecrypt(value)
                self._Logger.debug(f"Database {self._Client} get key {key} completed")
                return value
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get key error : {e}\n\n{traceback.format_exc()}")
                return None

        def deleteData(self, key):
            try:
                self._Client.delete(key)
                self._Logger.debug(f"Database {self._Client} delete data {key} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} delete data error : {e}\n\n{traceback.format_exc()}")
                return False

        # 哈希操作
        def setHash(self, name, mapping):
            try:
                self._Client.hset(name, mapping)
                self._Logger.debug(f"Database {self._Client} set hash {name} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} set hash error : {e}\n\n{traceback.format_exc()}")
                return False

        def getHash(self, name, key):
            try:
                value = self._Client.hget(name, key)
                self._Logger.debug(f"Database {self._Client} get hash {name} completed")
                return value
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get hash error : {e}\n\n{traceback.format_exc()}")
                return None

        def getAllHash(self, name):
            try:
                value = self._Client.hgetall(name)
                self._Logger.debug(f"Database {self._Client} get all hash {name} completed")
                return value
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get all hash error : {e}\n\n{traceback.format_exc()}")
                return None

        def deleteHashField(self, name, keys):
            try:
                self._Client.hdel(name, keys)
                self._Logger.debug(f"Database {self._Client} delete hash field {keys} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} delete hash field error : {e}\n\n{traceback.format_exc()}")
                return False

        # 列表操作
        def pushList(self, name, *values):
            try:
                self._Client.lpush(name, *values)
                self._Logger.debug(f"Database {self._Client} push list {name} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} push list error : {e}\n\n{traceback.format_exc()}")
                return False

        def popList(self, name):
            try:
                value = self._Client.rpop(name)
                self._Logger.debug(f"Database {self._Client} pop list {name} completed")
                return value
            except Exception as e:
                self._Logger.error(f"Database {self._Client} pop list error : {e}\n\n{traceback.format_exc()}")
                return None

        # 集合操作
        def addSet(self, name, *values):
            try:
                self._Client.sadd(name, *values)
                self._Logger.debug(f"Database {self._Client} add set {name} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} add set error : {e}\n\n{traceback.format_exc()}")
                return False

        def isMemberSet(self, name, value):
            try:
                result = self._Client.sismember(name, value)
                self._Logger.debug(f"Database {self._Client} is member set {name} completed")
                return result
            except Exception as e:
                self._Logger.error(f"Database {self._Client} is member set error : {e}\n\n{traceback.format_exc()}")
                return False

        def removeSetMember(self, name, *values):
            try:
                self._Client.srem(name, *values)
                self._Logger.debug(f"Database {self._Client} remove set member completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} remove set member error : {e}\n\n{traceback.format_exc()}")
                return False

        # 有序集合操作
        def addSortedSet(self, name, mapping):
            try:
                self._Client.zadd(name, mapping)
                self._Logger.debug(f"Database {self._Client} add sorted set {name} completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} add sorted set error : {e}\n\n{traceback.format_exc()}")
                return False

        def getSortedSetRank(self, name, value):
            try:
                rank = self._Client.zrank(name, value)
                self._Logger.debug(f"Database {self._Client} get sorted set rank completed")
                return rank
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get sorted set rank error : {e}\n\n{traceback.format_exc()}")
                return None

        def getSortedSetByScore(self, name, min_score, max_score):
            try:
                values = self._Client.zrangebyscore(name, min_score, max_score)
                self._Logger.debug(f"Database {self._Client} get sorted set by score completed")
                return values
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get sorted set by score error : {e}\n\n{traceback.format_exc()}")
                return []

        def removeSortedSetMember(self, name, *values):
            try:
                self._Client.zrem(name, *values)
                self._Logger.debug(f"Database {self._Client} remove sorted set member completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} remove sorted set member error : {e}\n\n{traceback.format_exc()}")
                return False

        # 键过期设置
        def setKeyExpiry(self, key, seconds):
            try:
                self._Client.expire(key, seconds)
                self._Logger.debug(f"Database {self._Client} set key expiry completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} set key expiry error : {e}\n\n{traceback.format_exc()}")
                return False

        # 发布/订阅
        def publish(self, channel, message):
            try:
                self._Client.publish(channel, message)
                self._Logger.debug(f"Database {self._Client} publish completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} publish error : {e}\n\n{traceback.format_exc()}")
                return False

        def subscribe(self, *channels):
            try:
                pubsub = self._Client.pubsub()
                pubsub.subscribe(*channels)
                self._Logger.debug(f"Database {self._Client} subscribe completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} subscribe error : {e}\n\n{traceback.format_exc()}")
                return False

        # 事务
        def executeTransaction(self, *operations):
            try:
                pipe = self._Client.pipeline()
                for operation in operations:
                    operation(pipe)
                pipe.execute()
                self._Logger.debug(f"Database {self._Client} execute transaction completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} execute transaction error : {e}\n\n{traceback.format_exc()}")
                return False

        # 流水线
        def executePipeline(self, *commands):
            try:
                pipe = self._Client.pipeline()
                for command in commands:
                    command(pipe)
                pipe.execute()
                self._Logger.debug(f"Database {self._Client} execute pipeline completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} execute pipeline error : {e}\n\n{traceback.format_exc()}")
                return False

        # 脚本
        def executeScript(self, script, keys, args):
            try:
                self._Client.eval(script, len(keys), keys, args)
                self._Logger.debug(f"Database {self._Client} execute script completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} execute script error : {e}\n\n{traceback.format_exc()}")
                return False

        # 位图
        def setBit(self, key, offset, value):
            try:
                self._Client.setbit(key, offset, value)
                self._Logger.debug(f"Database {self._Client} set bit completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} set bit error : {e}\n\n{traceback.format_exc()}")
                return False

        def getBit(self, key, offset):
            try:
                value = self._Client.getbit(key, offset)
                self._Logger.debug(f"Database {self._Client} get bit completed")
                return value
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get bit error : {e}\n\n{traceback.format_exc()}")
                return None

        # 地理空间
        def addGeo(self, name, longitude, latitude, member):
            try:
                self._Client.geoadd(name, longitude, latitude, member)
                self._Logger.debug(f"Database {self._Client} add geo completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} add geo error : {e}\n\n{traceback.format_exc()}")
                return False

        def getGeoDistance(self, name, member1, member2):
            try:
                distance = self._Client.geodist(name, member1, member2)
                self._Logger.debug(f"Database {self._Client} get geo distance completed")
                return distance
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get geo distance error : {e}\n\n{traceback.format_exc()}")
                return None

        # HyperLogLog
        def addHyperloglog(self, name, *elements):
            try:
                self._Client.pfadd(name, *elements)
                self._Logger.debug(f"Database {self._Client} add hyperloglog completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} add hyperloglog error : {e}\n\n{traceback.format_exc()}")
                return False

        def countHyperloglog(self, name):
            try:
                count = self._Client.pfcount(name)
                self._Logger.debug(f"Database {self._Client} count hyperloglog completed")
                return count
            except Exception as e:
                self._Logger.error(f"Database {self._Client} count hyperloglog error : {e}\n\n{traceback.format_exc()}")
                return None

        # 流
        def addStream(self, name, fields):
            try:
                self._Client.xadd(name, fields)
                self._Logger.debug(f"Database {self._Client} add stream completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} add stream error : {e}\n\n{traceback.format_exc()}")
                return False

        def getStream(self, name, count=10):
            try:
                stream = self._Client.xrange(name, count=count)
                self._Logger.debug(f"Database {self._Client} get stream completed")
                return stream
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get stream error : {e}\n\n{traceback.format_exc()}")
                return None

        # 锁
        def acquireLock(self, name, timeout=None):
            lock = self._Client.lock(name, timeout=timeout)
            if lock.acquire():
                self._Logger.debug(f"Database {self._Client} acquire lock completed")
                return lock
            return None

        def releaseLock(self, lock):
            try:
                lock.release()
                self._Logger.debug(f"Database {self._Client} release lock completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} release lock error : {e}\n\n{traceback.format_exc()}")
                return False

        # 扩展功能
        def renameKey(self, old_key, new_key):
            try:
                self._Client.rename(old_key, new_key)
                self._Logger.debug(f"Database {self._Client} rename key completed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} rename key error : {e}\n\n{traceback.format_exc()}")
                return False

        def keyExists(self, key):
            try:
                result = self._Client.exists(key)
                self._Logger.debug(f"Database {self._Client} key exists completed")
                return result
            except Exception as e:
                self._Logger.error(f"Database {self._Client} key exists error : {e}\n\n{traceback.format_exc()}")
                return False

        def getKeyType(self, key):
            try:
                result = self._Client.type(key)
                self._Logger.debug(f"Database {self._Client} get key type completed")
                return result
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get key type error : {e}\n\n{traceback.format_exc()}")
                return None

        def getKeyTtl(self, key):
            try:
                result = self._Client.ttl(key)
                self._Logger.debug(f"Database {self._Client} get key ttl completed")
                return result
            except Exception as e:
                self._Logger.error(f"Database {self._Client} get key ttl error : {e}\n\n{traceback.format_exc()}")
                return None

        def closeRedisDatabase(self):
            try:
                self._Client.close()
                self._Logger.debug(f"Database {self._Client} connection closed")
                return True
            except Exception as e:
                self._Logger.error(f"Database {self._Client} close error : {e}\n\n{traceback.format_exc()}")
                return False


    class RedisDatabaseManager:
        """
        Redis数据库管理器，管理 Redis 数据库实例。它允许创建、获取和关闭 Redis 数据库实例。

        参数：
            :param Logger: 日志记录器，可以是 TheSeedCoreLogger 或 logging.Logger 的实例，或者为 None。
            :param DebugMode: 调试模式开关，默认为 False。

        属性：
            - INSTANCE: RedisDatabaseManager 的单例实例。
            - _INITIALIZED: 类是否已初始化的标志。
            - _Logger: 用于记录日志的日志记录器实例。
            - _RedisDatabase: 存储 Redis 数据库实例的字典。
            - IsClosed: 指示所有 Redis 数据库是否已关闭的标志。

        设计思路：
            1. 采用单例模式，确保类的实例唯一。
                a. 使用 __new__ 方法实现单例模式。
            2. 提供接口来创建、获取和关闭 Redis 数据库实例。
                a. createRedisDatabase 方法用于创建新的 Redis 数据库实例。
                b. getRedisDatabase 方法用于获取指定 ID 的 Redis 数据库实例。
                c. closeRedisDatabase 方法用于关闭指定 ID 的 Redis 数据库实例。
                d. closeAllDatabase 方法用于关闭所有的 Redis 数据库实例。
        """
        INSTANCE: RedisDatabaseManager = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if cls.INSTANCE is None:
                # noinspection PySuperArguments
                cls.INSTANCE = super(RedisDatabaseManager, cls).__new__(cls)
            return cls.INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if not self._INITIALIZED:
                self._Logger = defaultLogger("Redis", DebugMode) if Logger is None else Logger
                self._RedisDatabase = {}
                self.IsClosed = False
                RedisDatabaseManager._INITIALIZED = True

        def createRedisDatabase(self, database_id: str, config: RedisDatabaseConfig, logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False):
            try:
                redis_instance = BasicRedisDatabase(config, logger, debug_mode)
                self._RedisDatabase[database_id] = redis_instance
                return True
            except Exception as e:
                self._Logger.error(f"DatabaseManager create redis database error : {e}\n\n{traceback.format_exc()}")
                return False

        def getRedisDatabase(self, database_id: str) -> BasicRedisDatabase:
            return self._RedisDatabase.get(database_id)

        def closeRedisDatabase(self, database_id: str):
            redis_instance: BasicRedisDatabase = self.getRedisDatabase(database_id)
            if redis_instance is not None:
                result = redis_instance.closeRedisDatabase()
                if result:
                    self._RedisDatabase.pop(database_id)
                return result
            else:
                error_msg = f"DatabaseManager redis database '{database_id}' not found."
                self._Logger.error(error_msg)
                return False

        def closeAllDatabase(self):
            if self._RedisDatabase:
                for database_id in list(self._RedisDatabase.keys()):
                    self.closeRedisDatabase(database_id)
            self.IsClosed = True
            self._Logger.debug("All redis databases closed.")
            return True
