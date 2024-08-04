# -*- coding: utf-8 -*-
"""
TheSeedCore Database Module

Module Description:
This module implements a comprehensive database system to manage and interact with multiple types of databases including SQLite, MySQL, and Redis.
It provides a unified interface for various database operations such as creating, reading, updating, and deleting data.
The module ensures robust error handling, logging, and supports optional encryption for sensitive data.

Main Components:
1. Dependency Check and Import: Checks and imports necessary modules and libraries such as sqlite3, mysql.Connector, redis, etc.
2. Logger Setup: Configures default loggers for different database types to handle logging of database operations and errors.
3. Database Configurations: Defines configuration data classes for SQLite, MySQL, and Redis databases to standardize the setup and validation of database parameters.
4. Basic Database Classes: Implements core classes for SQLite, MySQL, and Redis databases to handle basic database operations including connection management, query execution, and error handling.
5. Database Managers: Implements manager classes for SQLite, MySQL, and Redis databases to handle multiple database instances, providing methods for creating, accessing, and closing databases.
6. Additional Database Operations: Provides extended functionality for Redis such as handling hashes, lists, sets, sorted sets, transactions, and scripts.

Module Functionality Overview:
- Supports multiple database types (SQLite, MySQL, Redis) with a unified interface.
- Handles connection management and ensures proper resource cleanup.
- Provides comprehensive logging for database operations and errors.
- Supports optional data encryption for sensitive information.
- Implements retry mechanisms and detailed error handling for robust operation.
- Provides extended operations for Redis including publish/subscribe, transactions, and pipelines.

Key Classes and Methods:
- _checkDependencies(): Checks and imports module dependencies.
- defaultLogger(): Configures and returns a logger for database operations.
- SQLiteDatabaseConfig: Data class for SQLite database configuration parameters.
- BasicSQLiteDatabase: Core class for SQLite database operations.
- MySQLDatabaseConfig: Data class for MySQL database configuration parameters.
- BasicMySQLDatabase: Core class for MySQL database operations.
- RedisDatabaseConfig: Data class for Redis database configuration parameters.
- BasicRedisDatabase: Core class for Redis database operations.
- SQLiteDatabaseManager: Manages multiple SQLite database instances.
- MySQLDatabaseManager: Manages multiple MySQL database instances.
- RedisDatabaseManager: Manages multiple Redis database instances.
- Additional Redis Operations: Includes methods for handling hashes, lists, sets, sorted sets, transactions, pipelines, and publish/subscribe.

Notes:
- Ensure all necessary dependencies (sqlite3, mysql.Connector, redis, etc.) are installed before using this module.
- Configure database parameters appropriately in the respective configuration data classes.
- Utilize the manager classes to handle multiple database instances and ensure proper resource cleanup.
- Refer to the logging output for detailed information on database operations and errors.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, Literal

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger
    from .EncryptionModule import TheSeedCoreEncryptor

_MySQLSupport: bool = False
_RedisSupport: bool = False


def _checkDependencies():
    global _MySQLSupport, _RedisSupport
    try:
        # noinspection PyUnresolvedReferences
        import mysql.connector
        # noinspection PyUnresolvedReferences
        from mysql.connector import errorcode
        _MySQLSupport = True
    except ImportError as _:
        _MySQLSupport = False

    try:
        # noinspection PyUnresolvedReferences
        import redis
        _RedisSupport = True
    except ImportError as _:
        _RedisSupport = False


_checkDependencies()


def defaultLogger(database_type: Literal["SQLite", "Redis", "MySQL"], debug_mode: bool = False) -> logging.Logger:
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


if _MySQLSupport:
    # noinspection PyUnresolvedReferences
    import mysql.connector
    # noinspection PyUnresolvedReferences
    from mysql.connector import errorcode


    @dataclass
    class MySQLDatabaseConfig:
        """
        MySQL数据库配置。

        属性:
            - Host : MySQL主机地址。
            - Port : MySQL端口。
            - User : MySQL用户名。
            - Password : MySQL密码。
            - Database : 数据库名称。
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


    class BasicMySQLDatabase:
        def __init__(self, Config: MySQLDatabaseConfig, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._Config = Config
            self._Connection = None
            self._Cursor = None
            self._Logger = defaultLogger("MySQL", DebugMode) if Logger is None else Logger
            self._StayConnected = False

        def _connect(self):
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
            if self._Connection and not self._StayConnected:
                self._Connection.close()
                self._Connection = None
                self._Cursor = None
                self._Logger.debug(f"Disconnected from database {self._Config.Database}")

        def executeQuery(self, query: str, params=None):
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
            try:
                self.executeQuery(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_structure})")
                self._Logger.debug(f"Database {self._Config.Database} table created.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} creating table error : {e}\n\n{traceback.format_exc()}")

        def insertData(self, query: str, data: tuple):
            try:
                self.executeQuery(query, data)
                self._Logger.debug(f"Database {self._Config.Database} data inserted.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} inserting data error : {e}\n\n{traceback.format_exc()}")

        def deleteTable(self, table_name: str):
            try:
                self.executeQuery(f"DROP TABLE IF EXISTS {table_name}")
                self._Logger.debug(f"Database {self._Config.Database} table {table_name} deleted.")
            except mysql.connector.Error as e:
                self._Connection.rollback()
                self._Logger.error(f"Database {self._Config.Database} deleting table error : {e}\n\n{traceback.format_exc()}")

        def closeDatabase(self):
            self._disconnect()


    class MySQLDatabaseManager:
        INSTANCE: MySQLDatabaseManager = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, *args, **kwargs):
            if not cls.INSTANCE:
                cls.INSTANCE = super(MySQLDatabaseManager, cls).__new__(cls)
            return cls.INSTANCE

        def __init__(self, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if not self._INITIALIZED:
                self._Logger = defaultLogger("MySQL", DebugMode) if Logger is None else Logger
                self._MySQLDatabase = {}
                MySQLDatabaseManager._INITIALIZED = True

        def createMySQLDatabase(self, config: MySQLDatabaseConfig, logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, debug_mode: bool = False):
            if config.Database not in self._MySQLDatabase:
                self._MySQLDatabase[config.Database] = BasicMySQLDatabase(config, logger, debug_mode)
                self._Logger.debug(f"Database {config.Database} created.")

        def getDatabase(self, database_name: str) -> BasicMySQLDatabase:
            return self._MySQLDatabase.get(database_name)

        def executeQuery(self, database_name: str, query: str, params=None):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.executeQuery(query, params)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def fetchQuery(self, database_name: str, query: str, params=None):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.fetchQuery(query, params)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def createTable(self, database_name: str, table_name: str, table_structure: str):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.createTable(table_name, table_structure)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def insertData(self, database_name: str, table_name: str, data: tuple):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.insertData(table_name, data)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def deleteTable(self, database_name: str, table_name: str):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.deleteTable(table_name)
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def closeDatabase(self, database_name: str):
            database_instance = self.getDatabase(database_name)
            if database_instance:
                return database_instance.closeDatabase()
            else:
                self._Logger.error(f"Database {database_name} not found.")

        def closeAllDatabase(self):
            for database_name in list(self._MySQLDatabase.keys()):
                self.closeDatabase(database_name)
            self._Logger.debug("All MySQL databases closed.")

if _RedisSupport:
    # noinspection PyUnresolvedReferences
    import redis


    @dataclass
    class RedisDatabaseConfig:
        """
        Redis数据库配置。

        属性:
            - Host : Redis主机地址。
            - Port : Redis端口。
            - Password : Redis密码。
            - Num : 数据库编号。
            - Encryptor : 加密器。
        """
        Host: str
        Port: int
        Password: str
        Num: int
        Encryptor: TheSeedCoreEncryptor

        def __post_init__(self):
            if not isinstance(self.Host, str):
                raise ValueError("The redis database host must be a string.")
            if not isinstance(self.Port, int):
                raise ValueError("The redis database port must be an integer.")
            if not isinstance(self.Password, str):
                raise ValueError("The redis database password must be a string.")
            if not isinstance(self.Num, int):
                raise ValueError("The redis database number must be an integer.")


    class BasicRedisDatabase:
        """
        TheSeedCore 基础Redis数据库，用于创建和操作Redis数据库连接。

        参数:
            :param Config : 数据库配置数据类。
        属性:
            - _RedisHost : Redis服务器地址。
            - _RedisPort : Redis服务器端口。
            - _Password : Redis服务器密码。
            - _Num : 数据库编号。
            - _Logger : 日志记录器。
            - _Encryptor : 加密器。
            - _Client : Redis客户端。
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
            """
            设置键值对。

            参数:
                :param key : 键。
                :param value : 值。
                :param ex : 过期时间。
                :param encrypt : 是否加密。
            返回:
                :return : 设置成功返回True，失败返回False。
            """
            try:
                if encrypt and self._Encryptor is not None:
                    value = self._Encryptor.aesEncrypt(value)
                self._Client.set(key, value, ex=ex)
                self._Logger.debug(f"Database {self._Client} set key {key} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} set key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getValue(self, key, decrypt=False):
            """
            获取值。

            参数:
                :param key : 键
                :param decrypt : 是否解密
            返回:
                :return : 获取成功返回值，失败返回None。
            """
            try:
                value = self._Client.get(key)
                if decrypt and self._Encryptor is not None:
                    value = self._Encryptor.aesDecrypt(value)
                self._Logger.debug(f"Database {self._Client} get key {key} completed")
                return value
            except Exception as e:
                error_msg = f"Database {self._Client} get key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def deleteData(self, key):
            """
            删除键值对。

            参数:
                :param key : 键
            返回:
                :return : 删除成功返回True，失败返回False。
            """
            try:
                self._Client.delete(key)
                self._Logger.debug(f"Database {self._Client} delete data {key} completed")
            except Exception as e:
                error_msg = f"Database {self._Client} delete data error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)

        # 哈希操作
        def setHash(self, name, mapping):
            """
            设置哈希表。

            参数:
                :param name : 哈希表名
                :param mapping : 哈希表键值对
            返回:
                :return : 设置成功返回True，失败返回False。
            """
            try:
                self._Client.hset(name, mapping)
                self._Logger.debug(f"Database {self._Client} set hash {name} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} set hash error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getHash(self, name, key):
            """
            获取哈希表中的值。

            参数:
                :param name : 哈希表名
                :param key : 键
            返回:
                :return : 获取成功返回值，失败返回None。
            """
            try:
                value = self._Client.hget(name, key)
                self._Logger.debug(f"Database {self._Client} get hash {name} completed")
                return value
            except Exception as e:
                error_msg = f"Database {self._Client} get hash error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def getAllHash(self, name):
            """
            获取哈希表中的所有键值对。

            参数:
                :param name : 哈希表名
            返回:
                :return : 获取成功返回字典，失败返回None。
            """
            try:
                value = self._Client.hgetall(name)
                self._Logger.debug(f"Database {self._Client} get all hash {name} completed")
                return value
            except Exception as e:
                error_msg = f"Database {self._Client} get all hash error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def deleteHashField(self, name, keys):
            """
            删除哈希表中的键值对。

            参数:
                :param name : 哈希表名
                :param keys : 键
            返回:
                :return : 删除成功返回True，失败返回False。
            """
            try:
                self._Client.hdel(name, keys)
                self._Logger.debug(f"Database {self._Client} delete hash field {keys} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} delete hash field error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 列表操作
        def pushList(self, name, *values):
            """
            向列表中添加元素。

            参数:
                :param name : 表名
                :param values : 元素
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.lpush(name, *values)
                self._Logger.debug(f"Database {self._Client} push list {name} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} push list error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def popList(self, name):
            """
            从列表中移除元素。

            参数:
                :param name : 表名
            返回:
                :return : 移除成功返回值，失败返回None。
            """
            try:
                value = self._Client.rpop(name)
                self._Logger.debug(f"Database {self._Client} pop list {name} completed")
                return value
            except Exception as e:
                error_msg = f"Database {self._Client} pop list error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        # 集合操作
        def addSet(self, name, *values):
            """
            向集合中添加元素。

            参数:
                :param name : 集合名
                :param values : 元素
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.sadd(name, *values)
                self._Logger.debug(f"Database {self._Client} add set {name} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} add set error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def isMemberSet(self, name, value):
            """
            检查集合中是否存在元素。

            参数:
                :param name : 集合名
                :param value : 元素
            返回:
                :return : 存在返回True，不存在返回False。
            """
            try:
                result = self._Client.sismember(name, value)
                self._Logger.debug(f"Database {self._Client} is member set {name} completed")
                return result
            except Exception as e:
                error_msg = f"Database {self._Client} is member set error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def removeSetMember(self, name, *values):
            """
            从集合中移除元素。

            参数:
                :param name : 集合名
                :param values : 元素
            返回:
                :return : 移除成功返回True，失败返回False。
            """
            try:
                self._Client.srem(name, *values)
                self._Logger.debug(f"Database {self._Client} remove set member completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} remove set member error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 有序集合操作
        def addSortedSet(self, name, mapping):
            """
            向有序集合中添加元素。

            参数:
                :param name : 集合名
                :param mapping : 键值对
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.zadd(name, mapping)
                self._Logger.debug(f"Database {self._Client} add sorted set {name} completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} add sorted set error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getSortedSetRank(self, name, value):
            """
            获取有序集合中元素的排名。

            参数:
                :param name : 集合名
                :param value : 元素
            返回:
                :return : 获取成功返回排名，失败返回None。
            """
            try:
                rank = self._Client.zrank(name, value)
                self._Logger.debug(f"Database {self._Client} get sorted set rank completed")
                return rank
            except Exception as e:
                error_msg = f"Database {self._Client} get sorted set rank error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def getSortedSetByScore(self, name, min_score, max_score):
            """
            获取有序集合中指定分数范围的元素。

            参数:
                :param name : 集合名
                :param min_score : 最小分数
                :param max_score : 最大分数
            返回:
                :return : 获取成功返回元素列表，失败返回空列表。
            """
            try:
                values = self._Client.zrangebyscore(name, min_score, max_score)
                self._Logger.debug(f"Database {self._Client} get sorted set by score completed")
                return values
            except Exception as e:
                error_msg = f"Database {self._Client} get sorted set by score error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return []

        def removeSortedSetMember(self, name, *values):
            """
            从有序集合中移除元素。

            参数:
                :param name : 集合名
                :param values : 元素
            返回:
                :return : 移除成功返回True，失败返回False。
            """
            try:
                self._Client.zrem(name, *values)
                self._Logger.debug(f"Database {self._Client} remove sorted set member completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} remove sorted set member error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 键过期设置
        def setKeyExpiry(self, key, seconds):
            """
            设置键的过期时间。

            参数:
                :param key : 键
                :param seconds : 过期时间
            返回:
                :return : 设置成功返回True，失败返回False。
            """
            try:
                self._Client.expire(key, seconds)
                self._Logger.debug(f"Database {self._Client} set key expiry completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} set key expiry error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 发布/订阅
        def publish(self, channel, message):
            """
            发布消息。

            参数:
                :param channel : 频道
                :param message : 消息
            返回:
                :return : 发布成功返回True，失败返回False。
            """
            try:
                self._Client.publish(channel, message)
                self._Logger.debug(f"Database {self._Client} publish completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} publish error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def subscribe(self, *channels):
            """
            订阅频道。

            参数:
                :param channels : 频道
            返回:
                :return : 订阅成功返回True，失败返回False。
            """
            try:
                pubsub = self._Client.pubsub()
                pubsub.subscribe(*channels)
                self._Logger.debug(f"Database {self._Client} subscribe completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} subscribe error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 事务
        def executeTransaction(self, *operations):
            """
            执行事务。

            参数:
                :param operations : 操作
            返回:
                :return : 执行成功返回True，失败返回False。
            """
            try:
                pipe = self._Client.pipeline()
                for operation in operations:
                    operation(pipe)
                pipe.execute()
                self._Logger.debug(f"Database {self._Client} execute transaction completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} execute transaction error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 流水线
        def executePipeline(self, *commands):
            """
            执行流水线。

            参数:
                :param commands : 命令
            返回:
                :return : 执行成功返回True，失败返回False。
            """
            try:
                pipe = self._Client.pipeline()
                for command in commands:
                    command(pipe)
                pipe.execute()
                self._Logger.debug(f"Database {self._Client} execute pipeline completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} execute pipeline error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 脚本
        def executeScript(self, script, keys, args):
            """
            执行脚本。

            参数:
                :param script : 脚本
                :param keys : 键
                :param args : 参数
            返回:
                :return : 执行成功返回True，失败返回False。
            """
            try:
                self._Client.eval(script, len(keys), keys, args)
                self._Logger.debug(f"Database {self._Client} execute script completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} execute script error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 位图
        def setBit(self, key, offset, value):
            """
            设置位图。

            参数:
                :param key : 键
                :param offset : 位
                :param value : 值
            返回:
                :return : 设置成功返回True，失败返回False。
            """
            try:
                self._Client.setbit(key, offset, value)
                self._Logger.debug(f"Database {self._Client} set bit completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} set bit error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getBit(self, key, offset):
            """
            获取位图。

            参数:
                :param key : 键
                :param offset : 位
            返回:
                :return : 获取成功返回值，失败返回None。
            """
            try:
                value = self._Client.getbit(key, offset)
                self._Logger.debug(f"Database {self._Client} get bit completed")
                return value
            except Exception as e:
                error_msg = f"Database {self._Client} get bit error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        # 地理空间
        def addGeo(self, name, longitude, latitude, member):
            """
            添加地理位置。

            参数:
                :param name : 名称
                :param longitude : 经度
                :param latitude : 纬度
                :param member : 成员
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.geoadd(name, longitude, latitude, member)
                self._Logger.debug(f"Database {self._Client} add geo completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} add geo error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getGeoDistance(self, name, member1, member2):
            """
            获取地理位置之间的距离。

            参数:
                :param name : 名称
                :param member1 : 成员1
                :param member2 : 成员2
            返回:
                :return : 获取成功返回距离，失败返回None。
            """
            try:
                distance = self._Client.geodist(name, member1, member2)
                self._Logger.debug(f"Database {self._Client} get geo distance completed")
                return distance
            except Exception as e:
                error_msg = f"Database {self._Client} get geo distance error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        # HyperLogLog
        def addHyperloglog(self, name, *elements):
            """
            添加 HyperLogLog。

            参数:
                :param name : 名称
                :param elements : 元素
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.pfadd(name, *elements)
                self._Logger.debug(f"Database {self._Client} add hyperloglog completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} add hyperloglog error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def countHyperloglog(self, name):
            """
            统计 HyperLogLog。

            参数:
                :param name : 名称
            返回:
                :return : 统计结果，失败返回None。
            """
            try:
                count = self._Client.pfcount(name)
                self._Logger.debug(f"Database {self._Client} count hyperloglog completed")
                return count
            except Exception as e:
                error_msg = f"Database {self._Client} count hyperloglog error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        # 流
        def addStream(self, name, fields):
            """
            添加流。

            参数:
                :param name : 名称
                :param fields : 字段
            返回:
                :return : 添加成功返回True，失败返回False。
            """
            try:
                self._Client.xadd(name, fields)
                self._Logger.debug(f"Database {self._Client} add stream completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} add stream error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getStream(self, name, count=10):
            """
            获取流。

            参数:
                :param name : 名称
                :param count : 数量
            返回:
                :return : 获取成功返回流，失败返回None。
            """
            try:
                stream = self._Client.xrange(name, count=count)
                self._Logger.debug(f"Database {self._Client} get stream completed")
                return stream
            except Exception as e:
                error_msg = f"Database {self._Client} get stream error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        # 锁
        def acquireLock(self, name, timeout=None):
            """
            获取锁。

            参数:
                :param name : 名称
                :param timeout : 超时时间
            返回:
                :return : 获取成功返回锁，失败返回None。
            """
            lock = self._Client.lock(name, timeout=timeout)
            if lock.acquire():
                self._Logger.debug(f"Database {self._Client} acquire lock completed")
                return lock
            return None

        def releaseLock(self, lock):
            """
            释放锁。

            参数:
                :param lock : 锁
            返回:
                :return : 释放成功返回True，失败返回False。
            """
            try:
                lock.release()
                self._Logger.debug(f"Database {self._Client} release lock completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} release lock error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        # 扩展功能
        def renameKey(self, old_key, new_key):
            """
            重命名键。

            参数:
                :param old_key : 旧键
                :param new_key : 新键
            返回:
                :return : 重命名成功返回True，失败返回False。
            """
            try:
                self._Client.rename(old_key, new_key)
                self._Logger.debug(f"Database {self._Client} rename key completed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} rename key error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def keyExists(self, key):
            """
            检查键是否存在。

            参数:
                :param key : 键
            返回:
                :return : 存在返回True，不存在返回False。
            """
            try:
                result = self._Client.exists(key)
                self._Logger.debug(f"Database {self._Client} key exists completed")
                return result
            except Exception as e:
                error_msg = f"Database {self._Client} key exists error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getKeyType(self, key):
            """
            获取键的类型。

            参数:
                :param key : 键
            返回:
                :return : 类型，失败返回None。
            """
            try:
                result = self._Client.type(key)
                self._Logger.debug(f"Database {self._Client} get key type completed")
                return result
            except Exception as e:
                error_msg = f"Database {self._Client} get key type error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def getKeyTtl(self, key):
            """
            获取键的过期时间。

            参数:
                :param key : 键
            返回:
                :return : 过期时间，失败返回None。
            """
            try:
                result = self._Client.ttl(key)
                self._Logger.debug(f"Database {self._Client} get key ttl completed")
                return result
            except Exception as e:
                error_msg = f"Database {self._Client} get key ttl error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return None

        def closeRedisDatabase(self):
            """
            关闭连接。

            返回:
                :return : 关闭成功返回True，失败返回False。
            """
            try:
                self._Client.close()
                self._Logger.debug(f"Database {self._Client} connection closed")
                return True
            except Exception as e:
                error_msg = f"Database {self._Client} close error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False


    class RedisDatabaseManager:
        """
        TheSeed Redis 数据库管理器

        属性:
            - _INSTANCE : 单例实例。
            - _Logger : 日志记录器。
            - _Encryptor : 加密器。
            - _RedisDatabase : Redis 数据库字典。
            - IsClosed : 是否关闭。
        """
        INSTANCE: RedisDatabaseManager = None
        _INITIALIZED: bool = False

        def __new__(cls, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            if cls.INSTANCE is None:
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
                error_msg = f"DatabaseManager create redis database error : {e}\n\n{traceback.format_exc()}"
                self._Logger.error(error_msg)
                return False

        def getRedisDatabase(self, database_id: str):
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


@dataclass
class SQLiteDatabaseConfig:
    """
    SQLite数据库配置。

    属性:
        - DatabasePath : 数据库文件的路径。
        - Logger : 日志记录器。
        - Encryptor : 加密器。
        - StayConnected : 是否保持数据库连接。
    """
    DatabaseID: str
    DatabasePath: str
    Encryptor: Union[None, TheSeedCoreEncryptor]
    StayConnected: bool

    def __post_init__(self):
        if not isinstance(self.DatabaseID, str):
            raise ValueError("The sqlite database ID must be a string.")
        if not isinstance(self.DatabasePath, str):
            raise ValueError("The sqlite database path must be a string.")
        if not isinstance(self.StayConnected, bool):
            raise ValueError("The sqlite database stay connected flag must be a boolean.")


class BasicSQLiteDatabase:
    """
    TheSeedCore 基础SQLite数据库，用于创建和操作SQLite数据库连接。

    参数:
        :param Config : 数据库配置数据类。
    属性:
        - _DatabaseID : 数据库ID。
        - _DatabasePath : 数据库文件的路径。
        - _Database : 数据库文件。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _StayConnected : 是否保持数据库连接。
        - _ConnectedDatabase : 数据库连接。

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
        连接到数据库。如果数据库文件不存在，则创建它。

        参数:
            :param 无

        返回:
            :return: 如果成功连接到数据库，返回 True；如果连接失败，返回 False。

        执行过程:
            1. 检查是否已连接到数据库。
                a. 如果尚未连接到数据库，则检查数据库文件是否存在。
                b. 如果数据库文件不存在，则创建一个新的空文件。
            2. 尝试连接到数据库。
                a. 使用 `sqlite3.connect` 方法连接到数据库。
                b. 记录连接成功的日志消息。
            3. 如果连接过程中发生错误，捕获异常并记录错误日志。
                a. 如果发生 `sqlite3.Error` 异常，记录详细的错误信息和堆栈跟踪。
        """
        try:
            if not self._ConnectedDatabase:
                if not os.path.exists(self._Database):
                    open(self._Database, "a").close()
                self._ConnectedDatabase = sqlite3.connect(self._Database)
                self._Logger.debug(f"Database {self._DatabaseID} connection completed")
                return True
        except sqlite3.Error as e:
            error_msg = f"Database {self._DatabaseID} connection error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def _disconnect(self) -> bool:
        """
        断开与数据库的连接。

        参数:
            :param 无

        返回:
            :return: 如果成功断开数据库连接，返回 True；如果断开连接失败，返回 False。

        执行过程:
            1. 检查当前是否连接到数据库，并且是否允许断开连接。
                a. 如果已连接到数据库且不需要保持连接，则关闭数据库连接。
            2. 尝试断开数据库连接。
                a. 使用 `close` 方法断开连接，并将连接对象设置为 `None`。
                b. 记录断开连接成功的日志消息。
            3. 如果断开连接过程中发生错误，捕获异常并记录错误日志。
                a. 如果发生任何异常，记录详细的错误信息和堆栈跟踪。
        """
        try:
            if self._ConnectedDatabase and not self._StayConnected:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.debug(f"Database {self._DatabaseID} disconnection completed")
                return True
        except Exception as e:
            error_msg = f"Database {self._DatabaseID} disconnect error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def basicCreateDatabase(self, tables_dict: dict) -> bool:
        """
        创建数据库及其表格。

        参数:
            :param tables_dict: 一个字典，其中键是表格名称，值是创建表格的 SQL 语句。

        返回:
            :return: 如果成功创建表格，返回 True；如果创建表格失败，返回 False。

        执行过程:
            1. 检查 `tables_dict` 是否为字典类型。
                a. 如果 `tables_dict` 不是字典，则记录错误日志并返回 False。
            2. 尝试连接到数据库。
                a. 调用 `_connect` 方法建立数据库连接。
            3. 如果 `tables_dict` 非空，遍历字典中的每个表格。
                a. 使用 `cursor` 对象检查表格是否已经存在。
                b. 如果表格不存在，执行 SQL 语句创建表格，并将表格名称添加到 `created_tables` 列表中。
            4. 提交对数据库的更改。
                a. 使用 `commit` 方法提交创建表格的更改。
            5. 如果 `tables_dict` 为空，则记录错误日志并返回 False。
            6. 如果在创建表格过程中发生任何 SQLite 错误，回滚数据库更改并记录错误日志。
                a. 使用 `rollback` 方法回滚更改。
                b. 记录详细的错误信息和堆栈跟踪。
            7. 最后，断开数据库连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(tables_dict, dict):
            error_msg = f"Database {self._DatabaseID} create database parameter error : tables_dict must be a dictionary."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} create database error : tables_dict is empty."
            self._Logger.error(error_msg)
            return False
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"Database {self._DatabaseID} create database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.debug(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteDatabase(self) -> bool:
        """
        删除数据库文件。

        返回:
            :return: 如果成功删除数据库文件，返回 True；如果删除文件失败，返回 False。

        执行过程:
            1. 设置 `_StayConnected` 属性为 False，确保数据库不会保持连接。
            2. 尝试断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
            3. 尝试删除数据库文件。
                a. 使用 `os.remove` 删除数据库文件。
            4. 记录删除成功的日志信息。
                a. 记录数据库删除的日志。
            5. 如果在删除数据库文件过程中发生任何操作系统错误，回滚数据库更改并记录错误日志。
                a. 使用 `rollback` 方法回滚数据库更改。
                b. 记录详细的错误信息和堆栈跟踪。
        """
        try:
            self._StayConnected = False
            self._disconnect()
            os.remove(self._Database)
            self._Logger.debug(f"Database {self._DatabaseID} deleted")
            return True
        except OSError as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"Database {self._DatabaseID} delete database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def basicGetExistingTables(self) -> list:
        """
        获取数据库中所有现有表的名称。

        返回:
            :return: 包含表名的列表，如果操作失败返回空列表。

        执行过程:
            1. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            2. 使用游标对象执行 SQL 查询。
                a. 查询 `sqlite_master` 表以获取所有表的名称。
            3. 处理查询结果。
                a. 将查询结果中的表名提取到列表 `existing_tables` 中。
            4. 记录现有表名的日志信息。
                a. 记录包含所有现有表名的日志。
            5. 如果在获取表名过程中发生 SQLite 错误，回滚数据库更改并记录错误日志。
                a. 使用 `rollback` 方法回滚数据库更改。
                b. 记录详细的错误信息和堆栈跟踪。
            6. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
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
            error_msg = f"Database {self._DatabaseID} get existing tables error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicCheckExistingTables(self, table_name: str) -> bool:
        """
        检查指定的表是否存在于数据库中。

        参数:
            :param table_name: 要检查的表名，必须是字符串。

        返回:
            :return: 如果表存在，则返回 `True`；否则返回 `False`。如果操作失败，则返回 `False`。

        执行过程:
            1. 检查参数类型。
                a. 如果 `table_name` 不是字符串，记录错误日志并返回 `False`。
            2. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            3. 使用游标对象执行 SQL 查询。
                a. 查询 `sqlite_master` 表以检查指定的表是否存在。
            4. 处理查询结果。
                a. 如果表存在，记录存在的日志信息，并返回 `True`。
                b. 如果表不存在，记录不存在的日志信息，并返回 `False`。
            5. 如果在检查表是否存在的过程中发生 SQLite 错误，记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
            6. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(table_name, str):
            error_msg = f"Database {self._DatabaseID} check existing tables parameter error : table_name must be a string."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} check table exists error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicCreateTable(self, table_name, table_sql) -> bool:
        """
        创建一个新的数据库表。如果表已经存在，则不执行创建操作。

        参数:
            :param table_name: 要创建的表名，必须是字符串。
            :param table_sql: 创建表的 SQL 语句，必须是字符串。

        返回:
            :return: 如果表成功创建，则返回 `True`；如果表已经存在，则返回 `False`。如果操作失败，则返回 `False`。

        执行过程:
            1. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            2. 使用游标对象执行 SQL 查询。
                a. 查询 `sqlite_master` 表以检查指定的表是否已存在。
            3. 根据查询结果决定是否创建新表。
                a. 如果表不存在，执行 `table_sql` 语句创建表，并提交事务。
                b. 记录表创建成功的日志信息。
                c. 返回 `True`。
                d. 如果表已存在，记录表已存在的日志信息。
                e. 返回 `False`。
            4. 如果在创建表的过程中发生 SQLite 错误，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
            5. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
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
            error_msg = f"Database {self._DatabaseID} create table error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteTable(self, table_name: str) -> bool:
        """
        删除指定的数据库表。如果表不存在，则不会抛出异常。

        参数:
            :param table_name: 要删除的表名，必须是字符串。

        返回:
            :return: 如果表成功删除，则返回 `True`；如果操作失败，则返回 `False`。

        执行过程:
            1. 验证 `table_name` 是否为字符串。
                a. 如果不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            3. 使用游标对象执行 SQL 删除语句。
                a. 如果表存在， 执行 `DROP TABLE IF EXISTS {table_name}` 语句以删除指定的表。
            4. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录表删除成功的日志信息。
                c. 返回 `True`。
            5. 如果在删除表的过程中发生 SQLite 错误，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            6. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(table_name, str):
            error_msg = f"Database {self._DatabaseID} delete table parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            self._ConnectedDatabase.commit()
            self._Logger.debug(f"Database {self._DatabaseID} table {table_name} deleted")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"Database {self._DatabaseID} delete table error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicInsertData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        将数据插入到数据库中。支持对指定列的数据进行加密。

        参数:
            :param query: 执行的 SQL 插入语句，必须是字符串。
            :param data: 插入的数据，可以是元组、列表或字典。
            :param encrypt: 是否对数据进行加密，默认为 `False`。
            :param encrypt_column: 需要加密的列名列表，仅在 `encrypt` 为 `True` 时有效。默认为 `None`。

        返回:
            :return: 如果数据插入成功，则返回 `True`；如果操作失败，则返回 `False`。

        执行过程:
            1. 验证 `query` 是否为字符串。
                a. 如果不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 验证 `data` 是否为元组、列表或字典。
                a. 如果不是这些类型，记录参数错误的日志信息，并返回 `False`。
            3. 验证 `encrypt` 是否为布尔值。
                a. 如果不是布尔值，记录参数错误的日志信息，并返回 `False`。
            4. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            5. 如果 `encrypt` 为 `True` 并且 `encrypt_column` 不为 `None`，且 `_Encryptor` 不为 `None`：
                a. 对 `data` 中指定列的数据进行加密。
                b. 使用 `self._Encryptor.aesEncrypt` 方法对需要加密的列数据进行加密。
            6. 使用游标对象执行 SQL 插入语句。
                a. 执行 `query` 语句，将 `data` 插入到数据库中。
            7. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录数据插入成功的日志信息。
                c. 返回 `True`。
            8. 如果在插入数据的过程中发生 SQLite 错误，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            9. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(query, str):
            error_msg = f"Database {self._DatabaseID} insert data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict)):
            error_msg = f"Database {self._DatabaseID} insert data parameter error : data must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"Database {self._DatabaseID} insert data parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} insert data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicInsertDatas(self, query: str, data_list: list, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        将多条数据插入到数据库中。支持对指定列的数据进行加密。

        参数:
            :param query: 执行的 SQL 插入语句，必须是字符串。
            :param data_list: 要插入的数据列表，每项可以是元组、列表或字典。
            :param encrypt: 是否对数据进行加密，默认为 `False`。
            :param encrypt_column: 需要加密的列名列表，仅在 `encrypt` 为 `True` 时有效。默认为 `None`。

        返回:
            :return: 如果数据插入成功，则返回 `True`；如果操作失败，则返回 `False`。

        执行过程:
            1. 验证 `query` 是否为字符串。
                a. 如果不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 验证 `data_list` 是否为列表。
                a. 如果不是列表，记录参数错误的日志信息，并返回 `False`。
            3. 验证 `encrypt` 是否为布尔值。
                a. 如果不是布尔值，记录参数错误的日志信息，并返回 `False`。
            4. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            5. 创建游标对象。
            6. 遍历 `data_list` 中的每条数据：
                a. 如果 `encrypt` 为 `True` 并且 `encrypt_column` 不为 `None`，且 `_Encryptor` 不为 `None`：
                    i. 对数据中指定列的数据进行加密。
                    ii. 使用 `self._Encryptor.aesEncrypt` 方法对需要加密的列数据进行加密。
                b. 使用游标对象执行 SQL 插入语句，将每条数据插入到数据库中。
            7. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录数据插入成功的日志信息。
                c. 返回 `True`。
            8. 如果在插入数据的过程中发生异常，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            9. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(query, str):
            error_msg = f"Database {self._DatabaseID} insert datas parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data_list, (tuple, list, dict)):
            error_msg = f"Database {self._DatabaseID} insert datas parameter error : data_list must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"Database {self._DatabaseID} insert datas parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} insert datas error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteData(self, query: str, data: tuple | list | dict | str) -> bool:
        """
        从数据库中删除数据。支持多种数据格式。

        参数:
            :param query: 执行的 SQL 删除语句，必须是字符串。
            :param data: 要删除的数据，支持的格式有元组、列表、字典或字符串。

        返回:
            :return: 如果数据删除成功，则返回 `True`；如果操作失败，则返回 `False`。

        执行过程:
            1. 验证 `query` 是否为字符串。
                a. 如果不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 验证 `data` 是否为元组、列表、字典或字符串。
                a. 如果 `data` 不属于这些类型，记录参数错误的日志信息，并返回 `False`。
            3. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            4. 创建游标对象。
            5. 执行 SQL 删除语句。
                a. 使用游标对象执行 `query` 语句，并将 `data` 作为参数传递。
            6. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录数据删除成功的日志信息。
                c. 返回 `True`。
            7. 如果在删除数据的过程中发生异常，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            8. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(query, str):
            error_msg = f"Database {self._DatabaseID} delete data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict, str)):
            error_msg = f"Database {self._DatabaseID} delete data parameter error : data must be a tuple or list or dict or str."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} delete data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteAllData(self, table_name: str) -> bool:
        """
        删除指定表中的所有数据。

        参数:
            :param table_name: 表名，必须是字符串。

        返回:
            :return: 如果成功删除所有数据，返回 `True`；如果操作失败，返回 `False`。

        执行过程:
            1. 验证 `table_name` 是否为字符串。
                a. 如果 `table_name` 不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            3. 创建游标对象。
            4. 执行删除所有数据的 SQL 查询。
                a. 构造删除所有数据的 SQL 语句：`DELETE FROM {table_name}`。
                b. 使用游标对象执行该 SQL 语句。
            5. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录删除所有数据成功的日志信息。
                c. 返回 `True`。
            6. 如果在删除数据的过程中发生异常，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            7. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(table_name, str):
            error_msg = f"Database {self._DatabaseID} delete all data parameter error : table_name must be a string."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} delete all data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicUpdateData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        更新数据库中的数据。

        参数:
            :param query: 执行更新操作的 SQL 查询语句，必须是字符串。
            :param data: 更新操作的数据，可以是元组、列表或字典。
            :param encrypt: 是否对数据进行加密，默认为 `False`。
            :param encrypt_column: 需要加密的列索引列表，如果 `encrypt` 为 `True`，则此参数不能为 `None`，且必须是列表。

        返回:
            :return: 如果数据更新成功，返回 `True`；如果操作失败，返回 `False`。

        执行过程:
            1. 验证 `query` 是否为字符串。
                a. 如果 `query` 不是字符串，记录参数错误的日志信息，并返回 `False`。
            2. 验证 `data` 是否为元组、列表或字典。
                a. 如果 `data` 不是这些类型，记录参数错误的日志信息，并返回 `False`。
            3. 验证 `encrypt` 是否为布尔值。
                a. 如果 `encrypt` 不是布尔值，记录参数错误的日志信息，并返回 `False`。
            4. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            5. 创建游标对象。
            6. 如果需要加密数据且加密列索引列表不为 `None`，对指定列的数据进行加密。
                a. 遍历 `data` 中的每个元素。
                b. 如果元素的索引在 `encrypt_column` 中且元素是字符串，使用 `_Encryptor` 进行 AES 加密。
                c. 其他情况保持原样。
            7. 执行更新数据的 SQL 查询。
                a. 使用游标对象执行 `query` 语句，并传递 `data` 作为参数。
            8. 提交事务。
                a. 调用 `commit` 方法保存对数据库的更改。
                b. 记录更新数据成功的日志信息。
                c. 返回 `True`。
            9. 如果在更新数据的过程中发生异常，回滚事务，并记录错误日志。
                a. 记录详细的错误信息和堆栈跟踪。
                b. 返回 `False`。
            10. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(query, str):
            error_msg = f"Database {self._DatabaseID} update data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict)):
            error_msg = f"Database {self._DatabaseID} update data parameter error : data must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"Database {self._DatabaseID} update data parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
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
            error_msg = f"Database {self._DatabaseID} update data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicSearchData(self, table_name: str, unique_id: str, unique_id_row: str, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        从数据库中检索数据。

        参数:
            :param table_name: 数据表的名称，必须是字符串。
            :param unique_id: 用于检索数据的唯一标识符，必须是字符串。
            :param unique_id_row: 唯一标识符所在的列名，必须是字符串。
            :param decrypt: 是否对检索到的数据进行解密，默认为 `False`。
            :param decrypt_column: 需要解密的列索引列表，如果 `decrypt` 为 `True`，则此参数不能为 `None`，且必须是列表。

        返回:
            :return: 如果数据检索成功，返回包含检索结果的列表。如果没有找到数据或发生错误，返回空列表。

        执行过程:
            1. 验证 `table_name` 是否为字符串。
                a. 如果 `table_name` 不是字符串，记录参数错误的日志信息，并返回空列表。
            2. 验证 `unique_id` 是否为字符串。
                a. 如果 `unique_id` 不是字符串，记录参数错误的日志信息，并返回空列表。
            3. 验证 `unique_id_row` 是否为字符串。
                a. 如果 `unique_id_row` 不是字符串，记录参数错误的日志信息，并返回空列表。
            4. 验证 `decrypt` 是否为布尔值。
                a. 如果 `decrypt` 不是布尔值，记录参数错误的日志信息，并返回空列表。
            5. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            6. 创建游标对象。
            7. 执行检索数据的 SQL 查询。
                a. 使用游标对象执行 `query` 语句，并传递 `unique_id` 作为参数。
            8. 获取检索结果。
                a. 使用 `fetchone` 方法获取单条数据。
                b. 如果没有找到数据，记录信息日志并返回空列表。
            9. 如果需要解密数据且解密列索引列表不为 `None`，对指定列的数据进行解密。
                a. 遍历 `row` 中的每个元素。
                b. 如果元素的索引在 `decrypt_column` 中且元素是字符串，使用 `_Encryptor` 进行 AES 解密。
                c. 其他情况保持原样。
            10. 记录数据检索成功的日志信息，并返回检索结果。
            11. 如果在检索数据的过程中发生异常，记录错误日志，并返回空列表。
                a. 记录详细的错误信息和堆栈跟踪。
            12. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(table_name, str):
            error_msg = f"Database {self._DatabaseID} search data parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(unique_id, str):
            error_msg = f"Database {self._DatabaseID} search data parameter error : unique_id must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(unique_id_row, str):
            error_msg = f"Database {self._DatabaseID} search data parameter error : unique_id_row must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(decrypt, bool):
            error_msg = f"Database {self._DatabaseID} search data parameter error : decrypt must be a boolean."
            self._Logger.error(error_msg)
            return []
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            query = f"SELECT * FROM {table_name} WHERE {unique_id_row} = ?"
            cursor.execute(query, (unique_id,))
            row = cursor.fetchone()
            if row is None:
                info_msg = f"Database {self._DatabaseID} No data found for ID {unique_id}"
                self._Logger.info(info_msg)
                return []
            if decrypt and decrypt_column is not None and row and self._Encryptor is not None:
                row = [self._Encryptor.aesDecrypt(row[i])
                       if i in decrypt_column and isinstance(row[i], str)
                       else row[i] for i in range(len(row))
                       ]
            self._Logger.debug(f"Database {self._DatabaseID} search data completed")
            return row
        except sqlite3.Error as e:
            error_msg = f"Database {self._DatabaseID} search data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicSearchDatas(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        从数据库中检索所有数据，并可选择按指定列排序和解密数据。

        参数:
            :param table_name: 数据表的名称，必须是字符串。
            :param sort_by_column: 按指定列排序的列索引，必须是整数。如果不排序，则为 `None`。
            :param decrypt: 是否对检索到的数据进行解密，默认为 `False`。
            :param decrypt_column: 需要解密的列索引列表，如果 `decrypt` 为 `True`，则此参数不能为 `None`，且必须是列表。

        返回:
            :return: 如果数据检索成功，返回包含所有数据的列表。如果发生错误或数据检索失败，返回空列表。

        执行过程:
            1. 验证 `table_name` 是否为字符串。
                a. 如果 `table_name` 不是字符串，记录参数错误的日志信息，并返回空列表。
            2. 验证 `sort_by_column` 是否为整数（如果提供了该参数）。
                a. 如果 `sort_by_column` 不是整数，记录参数错误的日志信息，并返回空列表。
            3. 验证 `decrypt` 是否为布尔值。
                a. 如果 `decrypt` 不是布尔值，记录参数错误的日志信息，并返回空列表。
            4. 连接到数据库。
                a. 调用 `_connect` 方法建立与数据库的连接。
            5. 创建游标对象。
            6. 构建查询 SQL 语句。
                a. 基本查询语句为 `SELECT * FROM {table_name}`。
                b. 如果提供了 `sort_by_column`，则在查询语句中添加排序条件 `ORDER BY {sort_by_column}`。
            7. 执行 SQL 查询。
                a. 使用游标对象执行构建好的查询语句。
            8. 获取检索结果。
                a. 使用 `fetchall` 方法获取所有行数据。
            9. 如果需要解密数据且解密列索引列表不为 `None`，对指定列的数据进行解密。
                a. 遍历每一行数据。
                b. 对于每一行，遍历每个元素。
                c. 如果元素的索引在 `decrypt_column` 中且元素是字符串，使用 `_Encryptor` 进行 AES 解密。
                d. 其他情况保持原样。
                e. 将解密后的行数据添加到 `decrypted_rows` 列表中。
                f. 记录数据检索完成的信息日志，并返回解密后的数据列表。
            10. 记录数据检索成功的日志信息，并返回原始数据列表。
            11. 如果在检索数据的过程中发生异常，记录错误日志，并返回空列表。
                a. 记录详细的错误信息和堆栈跟踪。
            12. 断开与数据库的连接。
                a. 调用 `_disconnect` 方法关闭数据库连接。
        """
        if not isinstance(table_name, str):
            error_msg = f"Database {self._DatabaseID} search datas parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return []
        if sort_by_column is not None and not isinstance(sort_by_column, int):
            error_msg = f"Database {self._DatabaseID} search datas parameter error : sort_by_column must be an integer."
            self._Logger.error(error_msg)
            return []
        if not isinstance(decrypt, bool):
            error_msg = f"Database {self._DatabaseID} search datas parameter error : decrypt must be a boolean."
            self._Logger.error(error_msg)
            return []
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
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
                info_msg = f"Database {self._DatabaseID} search datas completed"
                self._Logger.info(info_msg)
                return decrypted_rows
            self._Logger.debug(f"Database {self._DatabaseID} search datas completed")
            return rows
        except sqlite3.Error as e:
            error_msg = f"Database {self._DatabaseID} search datas error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicCloseDatabase(self) -> bool:
        """
        关闭数据库连接并清理资源。

        返回:
            :return: 关闭连接成功返回True，如果操作失败返回False。
        """
        try:
            if self._ConnectedDatabase:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.debug(f"Database {self._DatabaseID} connection closed")
                return True
        except Exception as e:
            error_msg = f"Database {self._DatabaseID} close database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False


class ExpandSQLiteDatabase(BasicSQLiteDatabase):
    """
    TheSeedCore 拓展SQLite数据库，用于创建和操作SQLite数据库连接。

    参数:
        :param TablesDict : 数据表字典。
        :param Config : 数据库配置数据类。
    属性:
        - _TablesDict : 数据表字典。
        - _DatabasePath : 数据库文件路径。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _ConnectedDatabase : 数据库连接。
    """

    def __init__(self, TablesDict: dict, Config: SQLiteDatabaseConfig, Logger: Union[TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        super().__init__(Config, Logger, DebugMode)
        self.basicCreateDatabase(TablesDict)

    def expandCreateTable(self, table_name, tables_structured: dict):
        """
        创建数据表。

        参数:
            :param table_name : 表名。
            :param tables_structured : 表结构字典。
        返回:
            :return : 创建成功返回True，失败返回False。
        """
        pk_name, pk_type = tables_structured["primary_key"]
        columns_sql = ", ".join([f"{item_name} {item_type}" for item_name, item_type in tables_structured["columns"].items()])
        table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({pk_name} {pk_type}, {columns_sql})"
        create_result = self.basicCreateTable(table_name, table_sql)
        return create_result

    def expandUpsertItem(self, table_name: str, item_data: dict, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        插入或更新表中的数据项。如果指定的数据项已存在，则更新它；否则，插入新的数据项。

        参数:
            :param table_name : 操作的目标表名。
            :param item_data : 字典格式，包含要插入或更新的数据。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_columns : 需要加密的列名列表。

        返回:
            :return : 操作成功返回True，失败返回False。
        """
        columns = ", ".join(item_data.keys())
        placeholders = ", ".join(["?"] * len(item_data))
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
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
        return self.basicInsertData(sql, data, encrypt=False)

    def expandUpsertItems(self, table_name: str, items_data: list[dict], encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        插入或更新表中的多条数据项。对每条数据项，如果指定的数据项已存在，则更新它；否则，插入新的数据项。

        参数:
            :param table_name : 操作的目标表名。
            :param items_data : 包含多个字典的列表，每个字典包含要插入或更新的数据。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_columns : 需要加密的列名列表。

        返回:
            :return : 所有操作成功返回True，任一失败返回False。
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
        更新指定表中的一条数据。

        参数:
            :param table_name : 表名。
            :param update_data : 要更新的数据，键为列名，值为数据值。
            :param where_clause : 条件子句，用于定位要更新的数据。
            :param where_args : 条件参数。
            :param encrypt : 是否加密数据，默认不加密。
            :param encrypt_columns : 需要加密的列名列表。

        返回:
            :return : 更新成功返回True，否则返回False。
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
        查询并返回指定表中的单条数据。

        参数:
            :param table_name : 表名。
            :param unique_id : 唯一标识符的值。
            :param unique_id_column : 唯一标识符的列名。
            :param decrypt : 是否对数据解密，默认为False。
            :param decrypt_columns : 需要解密的列的列表。

        返回:
            :return : 单条数据记录列表。
        """
        return self.basicSearchData(table_name, unique_id, unique_id_column, decrypt, decrypt_columns)

    def expandSearchItems(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        查询并返回指定表中的所有数据。

        参数:
            :param table_name : 表名。
            :param sort_by_column : 可选，按指定列排序。
            :param decrypt : 是否对数据解密，默认为False。
            :param decrypt_columns : 需要解密的列名列表。

        返回:
            :return : 所有数据记录列表。
        """
        return self.basicSearchDatas(table_name, sort_by_column, decrypt, decrypt_columns)

    def expandDeleteItem(self, table_name: str, where_clause: str, where_args: list) -> bool:
        """
        删除指定表中的单条数据。

        参数:
            :param table_name : 表名。
            :param where_clause : 条件子句，用于定位要删除的数据。
            :param where_args : 条件参数。

        返回:
            :return : 删除成功返回True，否则返回False。
        """
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        return self.basicDeleteData(query, where_args)

    def expandDeleteItems(self, table_name: str, where_clause: str = None, where_args: list = None) -> bool:
        """
        删除指定表中的多条数据或所有数据。

        参数:
            :param table_name : 表名。
            :param where_clause : 可选，定位要删除数据的SQL条件子句。
            :param where_args : 可选，条件子句中使用的参数。

        返回:
            :return : 如果删除成功则返回True，否则返回False。
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
    TheSeedCore 数据库

    参数:
        :param Config : 数据库配置数据类。
    属性:
        - _INSTANCE : 单例实例。
        - _Logger : 日志记录器。
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
        """初始化 TheSeedCore 数据库，添加初始配置项。"""
        try:
            item_list = [
                {"ItemID": "FirstRun", "ItemValue": "0"},
                {"ItemID": "StartTime", "ItemValue": "0"},
                {"ItemID": "CloseTime", "ItemValue": "0"},
                {"ItemID": "PerformanceMode", "ItemValue": "Balance"},
                {"ItemID": "TaskThreshold", "ItemValue": "10"},
                {"ItemID": "TheSeedHost", "ItemValue": ""},
                {"ItemID": "TheSeedHttpPort", "ItemValue": ""},
                {"ItemID": "TheSeedWsPort", "ItemValue": ""},
            ]
            self.upsertItems(item_list)
        except Exception as e:
            error_msg = f"TheSeedDatabaseManager init TheSeedCore database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)

    def upsertItem(self, item_id: str, item_value: str, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        插入或更新数据库中的单条数据。

        参数:
            :param item_id : 数据项的唯一标识。
            :param item_value : 数据项的值。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_column : 需要加密的数据列列表。

        返回:
            :return : 操作成功返回True，否则返回False。
        """
        query = "INSERT OR REPLACE INTO TheSeedCore (ItemID, ItemValue) VALUES (?, ?)"
        data = (item_id, item_value)
        return self.basicInsertData(query, data, encrypt, encrypt_column if encrypt else None)

    def upsertItems(self, items_data: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        批量插入或更新数据库中的数据。

        参数:
            :param items_data : 包含数据项字典的列表。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_columns : 需要加密的数据列列表。

        返回:
            :return : 所有操作都成功则返回True，否则返回False。
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

    def updateItem(self, item_id: str, item_value: str, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        更新数据库中的单个数据项。

        参数:
            :param item_id: 数据项的唯一标识。
            :param item_value: 数据项的新值。
            :param encrypt: 是否对数据进行加密，默认为False。
            :param encrypt_column: 需要加密的数据列列表。

        返回:
            :return : 操作成功返回True，否则返回False。
        """
        # noinspection SqlResolve
        query = "UPDATE TheSeedCore SET ItemValue = ? WHERE ItemID = ?"
        data = (item_value, item_id)
        return self.basicUpdateData(query, data, encrypt, encrypt_column if encrypt else None)

    def searchItem(self, item_id, decrypt=False, decrypt_column=None) -> list:
        """
        搜索数据库中的单个数据项。

        参数:
            :param item_id : 要搜索的数据项的唯一标识符。
            :param decrypt : 是否解密数据，默认为False。
            :param decrypt_column : 需要解密的数据列列表。

        返回:
            :return : 查询到的数据列表。
        """
        return self.basicSearchData("TheSeedCore", item_id, "ItemID", decrypt, decrypt_column)

    def searchItems(self, order_by_column=None, decrypt=False, decrypt_column=None) -> list:
        """
        搜索数据库中的所有数据项。

        参数:
            :param order_by_column: 排序列的名称，可选。
            :param decrypt: 是否解密数据，默认为False。
            :param decrypt_column: 需要解密的数据列列表。

        返回:
            :return : 查询到的所有数据项列表。
        """
        return self.basicSearchDatas("TheSeedCore", order_by_column, decrypt, decrypt_column)

    def deleteItem(self, item_id: str) -> bool:
        """
        删除数据库中的单个数据项。

        参数:
            :param item_id : 要删除的数据项的唯一标识符。

        返回:
            :return : 删除成功返回True，否则返回False。
        """
        # noinspection SqlResolve
        query = "DELETE FROM TheSeedCore WHERE ItemID = ?"
        return self.basicDeleteData(query, item_id)

    def deleteAllItems(self) -> bool:
        """
        删除数据库中的所有数据项。

        返回:
            :return : 删除成功返回True，否则返回False。
        """
        return self.basicDeleteAllData("TheSeedCore")

    def closeDatabase(self):
        """
        关闭数据库连接。
        """
        self.basicCloseDatabase()


class SQLiteDatabaseManager:
    """
    TheSeedCore SQLite 数据库管理器

    参数:
        :param Logger : 日志记录器。
    属性:
        - _INSTANCE : 单例实例。
        - _Logger : 日志记录器。
        - _DatabaseDict : 数据库实例字典。
        - IsClosed : 是否关闭。
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
        创建一个拓展数据库实例，并在内部字典中注册。

        参数:
            :param tables_structured : 数据库表结构定义，包括表名和列信息。
            :param config : 数据库配置。
            :param expand_database : 拓展数据库类。
            :param logger : 日志记录器。
            :param debug_mode : 调试模式。
        返回:
            :return : 创建成功返回True，失败返回False。
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
            return True
        except Exception as e:
            error_msg = f"SQLiteDatabaseManager create expand database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def getDatabase(self, database_id: str) -> ExpandSQLiteDatabase:
        """
        根据数据库ID获取拓展数据库实例。

        参数:
            :param database_id : 数据库唯一标识符。

        返回:
            :return : 返回对应的数据库实例，如果不存在返回None。
        """
        return self._SQLiteDatabase.get(database_id)

    def getExistingTables(self, database_id) -> list:
        """
        获取指定数据库中的所有表。

        参数:
            :param database_id : 数据库ID
        返回:
            :return : 包含所有表的列表
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicGetExistingTables"):
            return database_instance.basicGetExistingTables()
        else:
            error_msg = f"SQLiteDatabaseManager get existing tables error : Database '{database_id}' not found."
            self._Logger.error(error_msg)
            return []

    def checkExistingTables(self, database_id, table_name) -> bool:
        """
        检查指定数据库中是否存在指定表。

        参数:
            :param database_id : 数据库ID
            :param table_name : 表名
        返回:
            :return : 存在返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicCheckExistingTables"):
            return database_instance.basicCheckExistingTables(table_name)
        else:
            error_msg = f"SQLiteDatabaseManager check existing tables error : Database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def createTable(self, database_id: str, table_name: str, tables_structured: dict) -> bool:
        """
        在指定数据库中创建表。

        参数:
            :param database_id : 数据库ID
            :param table_name : 表名
            :param tables_structured : 表结构字典
        返回:
            :return : 创建成功返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "expandCreateTable"):
            result = database_instance.expandCreateTable(table_name, tables_structured)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager create table error : Database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def deleteTable(self, database_id: str, table_name: str) -> bool:
        """
        删除指定数据库中的指定表。

        参数:
            :param database_id : 数据库ID
            :param table_name : 表名
        返回:
            :return : 删除成功返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "basicDeleteTable"):
            result = database_instance.basicDeleteTable(table_name)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager delete table error : Database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def upsertData(self, database_id: str, table_name: str, update_data: dict, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        更新或插入指定数据库的表中的一条数据。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param update_data : 要更新的数据，键为列名，值为数据值。
            :param encrypt : 是否加密数据，默认不加密。
            :param encrypt_columns : 需要加密的列名的列表。

        返回:
            :return : 如果更新成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpsertItem"):
            result = database_instance.expandUpsertItem(table_name, update_data, encrypt, encrypt_columns)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager upsert data error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def upsertDatas(self, database_id: str, table_name: str, update_data: list, encrypt: bool = False, encrypt_columns: list = None):
        """
        更新或插入指定数据库的表中的多条数据。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param update_data : 要更新的数据列表，每个元素为一个字典，键为列名，值为数据值。
            :param encrypt : 是否加密数据，默认不加密。
            :param encrypt_columns : 需要加密的列名的列表。

        返回:
            :return : 如果更新成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpsertItems"):
            result = database_instance.expandUpsertItems(table_name, update_data, encrypt, encrypt_columns)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager upsert datas error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def updateData(self, database_id: str, table_name: str, update_data: dict, where_clause: str, where_args: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
        """
        更新指定数据库的表中的一条数据。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param update_data : 要更新的数据，键为列名，值为数据值。
            :param where_clause : 条件子句，用于定位要更新的数据。
            :param where_args : 条件参数。
            :param encrypt : 是否加密数据，默认不加密。
            :param encrypt_columns : 需要加密的列名的列表。

        返回:
            :return : 如果更新成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customUpdateItem"):
            result = database_instance.expandUpdateItem(table_name, update_data, where_clause, where_args, encrypt, encrypt_columns)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager update data error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def searchData(self, database_id: str, table_name: str, unique_id: str, unique_id_column: str, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        查询并返回指定数据库表中的单条数据列表。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param unique_id: 唯一标识符的值。
            :param unique_id_column: 唯一标识符的列名。
            :param decrypt : 是否对数据解密，默认为 False。
            :param decrypt_columns : 需要解密的列名索引列表。

        返回:
            :return : 单条数据记录列表。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customSearchItem"):
            row = database_instance.expandSearchItem(table_name, unique_id, unique_id_column, decrypt, decrypt_columns)
            return row
        else:
            error_msg = f"SQLiteDatabaseManager search data error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return []

    def searchDatas(self, database_id: str, table_name: str, sort_by_column=None, decrypt: bool = False, decrypt_columns: list = None) -> list:
        """
        查询并返回指定数据库表中的所有数据列表。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param sort_by_column : 可选，按指定列排序。
            :param decrypt : 是否对数据解密，默认为 False。
            :param decrypt_columns : 需要解密的列名的列表。

        返回:
            :return : 多条数据记录列表。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customSearchItems"):
            rows = database_instance.expandSearchItems(table_name, sort_by_column, decrypt, decrypt_columns)
            return rows
        else:
            error_msg = f"SQLiteDatabaseManager search datas error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return []

    def deleteData(self, database_id: str, table_name: str, where_clause: str, where_args: list) -> bool:
        """
        删除指定数据库表中的单条数据。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param where_clause : 条件子句，用于定位要删除的数据。
            :param where_args : 条件参数。

        返回:
            :return : 如果删除成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customDeleteItem"):
            result = database_instance.expandDeleteItem(table_name, where_clause, where_args)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager delete data error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def deleteDatas(self, database_id: str, table_name: str, where_clause: str = None, where_args: list = None) -> bool:
        """
        删除指定数据库表中的多条数据，如果不指定条件则删除所有数据。

        参数:
            :param database_id : 数据库ID。
            :param table_name : 表名。
            :param where_clause : 可选，条件子句，用于定位要删除的数据。
            :param where_args : 可选，条件参数。

        返回:
            :return : 如果删除成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance and hasattr(database_instance, "customDeleteItems"):
            result = database_instance.expandDeleteItems(table_name, where_clause, where_args)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager delete datas error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def closeDatabase(self, database_id: str) -> bool:
        """
        关闭指定ID的自定义数据库连接。

        参数:
            :param database_id : 数据库ID。

        返回:
            :return : 如果关闭成功则返回True，否则返回False。
        """
        database_instance = self.getDatabase(database_id)
        if database_instance is not None and hasattr(database_instance, "basicCloseDatabase"):
            result = database_instance.basicCloseDatabase()
            if result:
                self._SQLiteDatabase.pop(database_id)
            return result
        else:
            error_msg = f"SQLiteDatabaseManager close database error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def closeAllDatabase(self) -> bool:
        """关闭所有管理的数据库连接。"""
        if self._SQLiteDatabase:
            for database_id in list(self._SQLiteDatabase.keys()):
                self.closeDatabase(database_id)
        self.IsClosed = True
        self._Logger.debug("All sqlite databases closed.")
        return True
