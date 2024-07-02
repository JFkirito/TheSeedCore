# -*- coding: utf-8 -*-
"""
TheSeed Database Module

# This module manages operations for SQLite and Redis databases, encompassing essential functionalities for database management.
# It supports creating, connecting to, disconnecting from, and operating databases. The module is also equipped with encryption
# and logging functionalities to secure data and track operations. Key components include foundational classes for both SQLite
# and Redis databases, as well as a comprehensive database manager for managing multiple database instances and configurations.
#
# Key Components:
# 1. _BasicSQLiteDatabase: Handles basic SQLite database operations like connection, table creation, and data manipulation.
# 2. _BasicRedisDatabase: Manages Redis database operations, dealing with key-value storage and other Redis-specific data structures.
# 3. TheSeedDatabaseManager: Inherits from _BasicSQLiteDatabase to manage TheSeed's core configurations.
# 4. SQLiteDatabaseManager: Manages multiple SQLite databases, enabling dynamic creation and database operations.
# 5. RedisDatabaseManager: Oversees multiple Redis instances, facilitating dynamic database creation and management.
#
# Module Functions:
# - Facilitates basic and advanced database management.
# - Ensures secure data storage and transmission through encryption.
# - Integrates comprehensive logging to document database operations.
# - Employs type checking to safeguard data operations.
#
# Usage Scenarios:
# - Embedding SQLite databases in Python applications.
# - Utilizing Redis for effective data caching and management.
# - Securing database operations through encryption.
# - Maintaining detailed logs for database operations.
#
# Dependencies:
# - sqlite3: A Python library for SQLite database operations.
# - redis: A library for managing Redis databases.
# - EncryptionModule and LoggerModule: Provide encryption and logging functionalities, respectively.

"""

from __future__ import annotations

__all__ = ["TheSeedDatabaseManager", "SQLiteDatabaseManager", "RedisDatabaseManager"]

import os
import sqlite3
import traceback
from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from .EncryptionModule import TheSeedEncryptor
    from .LoggerModule import TheSeedCoreLogger


class _BasicSQLiteDatabase:
    """
    TheSeed基础SQLite数据库，用于创建和操作SQLite数据库连接。

    参数:
        :param DatabasePath : 数据库文件的路径。
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
        :param StayConnected : 是否保持数据库连接，默认为False。
    属性:
        - _DatabasePath : 数据库文件的路径。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _StayConnected : 是否保持数据库连接。
        - _ConnectedDatabase : 数据库连接。

    """

    def __init__(self, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor, StayConnected: bool = False):
        self._DatabasePath = DatabasePath
        self._Logger = Logger
        self._Encryptor = Encryptor
        self._StayConnected = StayConnected
        self._ConnectedDatabase = None
        self._DatabaseName = self._extractDatabaseName()

    def _connect(self) -> bool:
        """
        连接数据库。如果数据库文件不存在，将会创建它。

        返回:
            :return 连接成功返回True，失败返回False。
        """
        try:
            if not self._ConnectedDatabase:
                if not os.path.exists(self._DatabasePath):
                    open(self._DatabasePath, "a").close()
                self._ConnectedDatabase = sqlite3.connect(self._DatabasePath)
                self._Logger.info(f"{self._DatabaseName} connection completed")
                return True
        except Exception as e:
            error_msg = f"{self._DatabaseName} connection error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def _disconnect(self) -> bool:
        """
        断开数据库连接。

        返回:
            :return 断开成功返回True，失败返回False。
        """
        try:
            if self._ConnectedDatabase and not self._StayConnected:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.info(f"{self._DatabaseName} disconnection completed")
                return True
        except Exception as e:
            error_msg = f"{self._DatabaseName} disconnect error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def _extractDatabaseName(self) -> str:
        database_full_name = os.path.basename(self._DatabasePath)
        return database_full_name

    def basicCreateDatabase(self, tables_dict: dict) -> bool:
        """
        根据提供的字典创建数据库中的表。

        参数:
            :param tables_dict : 包含表名和SQL创建语句的字典。

        返回:
            :return : 创建成功返回True，失败返回False。
        """
        if not isinstance(tables_dict, dict):
            error_msg = f"{self._DatabaseName} create database parameter error : tables_dict must be a dictionary."
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
                self._Logger.info(f"{self._DatabaseName} created tables : {', '.join(created_tables)}")
                return True
            error_msg = f"{self._DatabaseName} create database error : tables_dict is empty."
            self._Logger.error(error_msg)
            return False
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} create database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteDatabase(self) -> bool:
        """
        删除整个数据库文件。

        返回:
            :return : 删除成功返回True，失败返回False。
        """
        try:
            self._StayConnected = False
            self._disconnect()
            os.remove(self._DatabasePath)
            self._Logger.info(f"{self._DatabaseName} deleted")
            return True
        except OSError as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} delete database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def basicGetExistingTables(self) -> list:
        """
        获取数据库中所有现有表的名称。

        返回:
            :return : 包含表名的列表，如果操作失败返回空列表。
        """
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [table[0] for table in cursor.fetchall()]
            self._Logger.info(f"{self._DatabaseName} existing tables : {', '.join(existing_tables)}")
            return existing_tables
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} get existing tables error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicCheckExistingTables(self, table_name: str) -> bool:
        """
        检查指定的表是否存在于数据库中。

        参数:
            :param table_name : 表名。

        返回:
            :return : 表存在返回True，不存在返回False。
        """
        if not isinstance(table_name, str):
            error_msg = f"{self._DatabaseName} check existing tables parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone()[0] == 1
            if exists:
                self._Logger.info(f"{self._DatabaseName} table {table_name} exists")
                return exists
            self._Logger.info(f"{self._DatabaseName} table {table_name} not exists")
            return exists
        except sqlite3.Error as e:
            error_msg = f"{self._DatabaseName} check table exists error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteTable(self, table_name: str) -> bool:
        """
        从数据库中删除指定的表。

        参数:
            :param table_name : 表名。

        返回:
            :return : 删除成功返回True，失败返回False。
        """
        if not isinstance(table_name, str):
            error_msg = f"{self._DatabaseName} delete table parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} table {table_name} deleted")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} delete table error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicInsertData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        向数据库中插入数据。

        参数:
            :param query : SQL插入语句。
            :param data : 要插入的数据。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_column : 需要加密的列的索引列表。

        返回:
            :return : 插入成功返回True，失败返回False。
        """
        if not isinstance(query, str):
            error_msg = f"{self._DatabaseName} insert data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict)):
            error_msg = f"{self._DatabaseName} insert data parameter error : data must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"{self._DatabaseName} insert data parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
            return False
        if encrypt and not encrypt_column:
            error_msg = f"{self._DatabaseName} insert data parameter error : encrypt is True but encrypt_column is None or empty."
            self._Logger.error(error_msg)
            return False
        if not encrypt and encrypt_column and encrypt_column is not None:
            error_msg = f"{self._DatabaseName} insert data parameter error : encrypt is False but encrypt_column is not None or empty."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            if encrypt and encrypt_column:
                data = [
                    self._Encryptor.aesEncrypt(data[i])
                    if i in encrypt_column and isinstance(data[i], str)
                    else data[i]
                    for i in range(len(data))
                ]
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} insert data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} insert data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicInsertDatas(self, query: str, data_list: list, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        向数据库中插入多条数据。

        参数:
            :param query: SQL插入语句。
            :param data_list: 要插入的数据列表。
            :param encrypt: 是否对数据进行加密，默认为False。
            :param encrypt_column: 需要加密的列的索引列表。

        返回:
            :return : 所有数据插入成功返回True，任一失败返回False。
        """
        if not isinstance(query, str):
            error_msg = f"{self._DatabaseName} insert datas parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data_list, (tuple | list | dict)):
            error_msg = f"{self._DatabaseName} insert datas parameter error : data_list must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"{self._DatabaseName} insert datas parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
            return False
        if encrypt and not encrypt_column:
            error_msg = f"{self._DatabaseName} insert datas parameter error : encrypt is True but encrypt_column is None or empty."
            self._Logger.error(error_msg)
            return False
        if not encrypt and encrypt_column and encrypt_column is not None:
            error_msg = f"{self._DatabaseName} insert datas parameter error : encrypt is False but encrypt_column is not None or empty."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            for data in data_list:
                if encrypt and encrypt_column:
                    data = [
                        self._Encryptor.aesEncrypt(data[i])
                        if i in encrypt_column and isinstance(data[i], str)
                        else data[i]
                        for i in range(len(data))
                    ]
                cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} insert datas completed")
            return True
        except Exception as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} insert datas error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteData(self, query: str, data: tuple | list | dict | str) -> bool:
        """
        删除数据库中的指定数据。

        参数:
            :param query : SQL删除语句。
            :param data : 指定的数据。

        返回:
            :return : 删除成功返回True，失败返回False。
        """
        if not isinstance(query, str):
            error_msg = f"{self._DatabaseName} delete data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict, str)):
            error_msg = f"{self._DatabaseName}r delete data parameter error : data must be a tuple or list or dict or str."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} delete data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} delete data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicDeleteAllData(self, table_name: str) -> bool:
        """
        删除指定表中的所有数据。

        参数:
            :param table_name : 表名。

        返回:
            :return : 删除成功返回True，失败返回False。
        """
        if not isinstance(table_name, str):
            error_msg = f"{self._DatabaseName} delete all data parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            # noinspection SqlWithoutWhere
            query = f"DELETE FROM {table_name}"
            cursor.execute(query)
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} delete all data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} delete all data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicUpdateData(self, query: str, data: tuple | list | dict, encrypt: bool = False, encrypt_column: list = None) -> bool:
        """
        更新数据库中的数据。

        参数:
            :param query : SQL更新语句。
            :param data : 要更新的数据。
            :param encrypt : 是否对数据进行加密，默认为False。
            :param encrypt_column : 需要加密的列的索引列表。

        返回:
            :return : 更新成功返回True，失败返回False。
        """
        if not isinstance(query, str):
            error_msg = f"{self._DatabaseName} update data parameter error : query must be a string."
            self._Logger.error(error_msg)
            return False
        if not isinstance(data, (tuple, list, dict)):
            error_msg = f"{self._DatabaseName} update data parameter error : data must be a tuple or list or dict."
            self._Logger.error(error_msg)
            return False
        if not isinstance(encrypt, bool):
            error_msg = f"{self._DatabaseName} update data parameter error : encrypt must be a boolean."
            self._Logger.error(error_msg)
            return False
        if encrypt and not encrypt_column:
            error_msg = f"{self._DatabaseName} update data parameter error : encrypt is True but encrypt_column is None or empty."
            self._Logger.error(error_msg)
            return False
        if not encrypt and encrypt_column and encrypt_column is not None:
            error_msg = f"{self._DatabaseName} update data parameter error : encrypt is False but encrypt_column is not None or empty."
            self._Logger.error(error_msg)
            return False
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            if encrypt and encrypt_column:
                data = [
                    self._Encryptor.aesEncrypt(data[i])
                    if i in encrypt_column and isinstance(data[i], str)
                    else data[i]
                    for i in range(len(data))
                ]
            cursor.execute(query, data)
            self._ConnectedDatabase.commit()
            self._Logger.info(f"{self._DatabaseName} update data completed")
            return True
        except sqlite3.Error as e:
            self._ConnectedDatabase.rollback()
            error_msg = f"{self._DatabaseName} update data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False
        finally:
            self._disconnect()

    def basicSearchData(self, table_name: str, unique_id: str, unique_id_row: str, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        从数据库中查找指定的单条数据。

        参数:
            :param table_name : 表名。
            :param unique_id : 唯一标识符的值。
            :param unique_id_row : 唯一标识符的列名。
            :param decrypt : 是否解密数据，默认为False。
            :param decrypt_column : 需要解密的列的索引列表。

        返回:
            :return : 查找到的数据，如果查询失败则返回空列表。
        """
        if not isinstance(table_name, str):
            error_msg = f"{self._DatabaseName} search data parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(unique_id, str):
            error_msg = f"{self._DatabaseName} search data parameter error : unique_id must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(unique_id_row, str):
            error_msg = f"{self._DatabaseName} search data parameter error : unique_id_row must be a string."
            self._Logger.error(error_msg)
            return []
        if not isinstance(decrypt, bool):
            error_msg = f"{self._DatabaseName} search data parameter error : decrypt must be a boolean."
            self._Logger.error(error_msg)
            return []
        if decrypt and not decrypt_column:
            error_msg = f"{self._DatabaseName} search data parameter error : decrypt is True but decrypt_column is None or empty."
            self._Logger.error(error_msg)
            return []
        if not decrypt and decrypt_column and decrypt_column is not None:
            error_msg = f"{self._DatabaseName} search data parameter error : decrypt is False but decrypt_column is not None or empty."
            self._Logger.error(error_msg)
            return []
        try:
            self._connect()
            cursor = self._ConnectedDatabase.cursor()
            query = f"SELECT * FROM {table_name} WHERE {unique_id_row} = ?"
            cursor.execute(query, (unique_id,))
            row = cursor.fetchone()
            if row is None:
                info_msg = f"{self._DatabaseName} No data found for ID {unique_id}"
                self._Logger.info(info_msg)
                return []
            if decrypt and decrypt_column and row:
                row = [self._Encryptor.aesDecrypt(row[i])
                       if i in decrypt_column and isinstance(row[i], str)
                       else row[i] for i in range(len(row))
                       ]
            self._Logger.info(f"{self._DatabaseName} search data completed")
            return row
        except sqlite3.Error as e:
            error_msg = f"{self._DatabaseName} search data error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicSearchDatas(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_column: list = None) -> list:
        """
        从数据库中查找所有数据。

        参数:
            :param table_name : 表名。
            :param sort_by_column : 排序依据的列的索引，可选。
            :param decrypt : 是否解密数据，默认为False。
            :param decrypt_column : 需要解密的列的索引列表。

        返回:
            :return : 查询到的数据列表，如果查询失败则返回空列表。
        """
        if not isinstance(table_name, str):
            error_msg = f"{self._DatabaseName} search datas parameter error : table_name must be a string."
            self._Logger.error(error_msg)
            return []
        if sort_by_column is not None and not isinstance(sort_by_column, int):
            error_msg = f"{self._DatabaseName} search datas parameter error : sort_by_column must be an integer."
            self._Logger.error(error_msg)
            return []
        if not isinstance(decrypt, bool):
            error_msg = f"{self._DatabaseName} search datas parameter error : decrypt must be a boolean."
            self._Logger.error(error_msg)
            return []
        if decrypt and not decrypt_column:
            error_msg = f"{self._DatabaseName} search datas parameter error : decrypt is True but decrypt_column is None or empty."
            self._Logger.error(error_msg)
            return []
        if not decrypt and decrypt_column and decrypt_column is not None:
            error_msg = f"{self._DatabaseName} search datas parameter error : decrypt is False but decrypt_column is not None or empty."
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
            if decrypt and decrypt_column:
                decrypted_rows = []
                for row in rows:
                    decrypted_row = [
                        self._Encryptor.aesDecrypt(row[i])
                        if i in decrypt_column and isinstance(row[i], str)
                        else row[i] for i in range(len(row))
                    ]
                    decrypted_rows.append(decrypted_row)
                info_msg = f"{self._DatabaseName} search datas completed"
                self._Logger.info(info_msg)
                return decrypted_rows
            self._Logger.info(f"{self._DatabaseName} search datas completed")
            return rows
        except sqlite3.Error as e:
            error_msg = f"{self._DatabaseName} search datas error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return []
        finally:
            self._disconnect()

    def basicCloseDatabase(self) -> bool:
        """
        关闭数据库连接。

        返回:
            :return : 关闭成功返回True，失败返回False。
        """
        try:
            if self._ConnectedDatabase:
                self._ConnectedDatabase.close()
                self._ConnectedDatabase = None
                self._Logger.info(f"{self._DatabaseName} connection closed")
                return True
        except Exception as e:
            error_msg = f"{self._DatabaseName} close database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False


class _BasicRedisDatabase:
    """
    TheSeed基础Redis数据库，用于创建和操作Redis数据库连接。

    参数:
        :param RedisHost : Redis服务器地址。
        :param RedisPort : Redis服务器端口。
        :param Password : Redis服务器密码。
        :param Num : 数据库编号。
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
    属性:
        - _RedisHost : Redis服务器地址。
        - _RedisPort : Redis服务器端口。
        - _Password : Redis服务器密码。
        - _Num : 数据库编号。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _Client : Redis客户端。
    """

    def __init__(self, RedisHost: str, RedisPort: str, Password: str, Num: int, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor):
        self._RedisHost = RedisHost
        self._RedisPort = RedisPort
        self._Password = Password
        self._Num = Num
        self._Logger = Logger
        self._Encryptor = Encryptor
        self._Client = redis.Redis(host=RedisHost, port=RedisPort, db=Num)

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
            if encrypt:
                value = self._Encryptor.aesEncrypt(value)
            self._Client.set(key, value, ex=ex)
            self._Logger.info(f"RedisDatabase {self._Client} set key {key} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} set key error : {e}\n\n{traceback.format_exc()}"
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
            if decrypt:
                value = self._Encryptor.aesDecrypt(value)
            self._Logger.info(f"RedisDatabase {self._Client} get key {key} completed")
            return value
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get key error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} delete data {key} completed")
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} delete data error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} set hash {name} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} set hash error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get hash {name} completed")
            return value
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get hash error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get all hash {name} completed")
            return value
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get all hash error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} delete hash field {keys} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} delete hash field error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} push list {name} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} push list error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} pop list {name} completed")
            return value
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} pop list error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} add set {name} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} add set error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} is member set {name} completed")
            return result
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} is member set error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} remove set member completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} remove set member error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} add sorted set {name} completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} add sorted set error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get sorted set rank completed")
            return rank
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get sorted set rank error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get sorted set by score completed")
            return values
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get sorted set by score error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} remove sorted set member completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} remove sorted set member error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} set key expiry completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} set key expiry error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} publish completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} publish error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} subscribe completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} subscribe error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} execute transaction completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} execute transaction error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} execute pipeline completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} execute pipeline error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} execute script completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} execute script error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} set bit completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} set bit error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get bit completed")
            return value
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get bit error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} add geo completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} add geo error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get geo distance completed")
            return distance
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get geo distance error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} add hyperloglog completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} add hyperloglog error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} count hyperloglog completed")
            return count
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} count hyperloglog error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} add stream completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} add stream error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get stream completed")
            return stream
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get stream error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} acquire lock completed")
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
            self._Logger.info(f"RedisDatabase {self._Client} release lock completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} release lock error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} rename key completed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} rename key error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} key exists completed")
            return result
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} key exists error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get key type completed")
            return result
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get key type error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} get key ttl completed")
            return result
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} get key ttl error : {e}\n\n{traceback.format_exc()}"
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
            self._Logger.info(f"RedisDatabase {self._Client} connection closed")
            return True
        except Exception as e:
            error_msg = f"RedisDatabase {self._Client} close error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False


class _CustomSQLiteDatabase(_BasicSQLiteDatabase):
    """
    TheSeed自定义SQLite数据库，用于创建和操作SQLite数据库连接。

    参数:
        :param TablesDict : 数据表字典。
        :param DatabasePath : 数据库文件路径。
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
        :param StayConnected : 是否保持连接。
    属性:
        - _TablesDict : 数据表字典。
        - _DatabasePath : 数据库文件路径。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _ConnectedDatabase : 数据库连接。
    """

    def __init__(self, TablesDict: dict, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor, StayConnected: bool):
        super().__init__(DatabasePath, Logger, Encryptor, StayConnected)
        self.basicCreateDatabase(TablesDict)

    def customUpsertItem(self, table_name: str, item_data: dict, encrypt: bool = False, encrypt_columns: list = None) -> bool:
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
        if encrypt and encrypt_columns:
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

    def customUpsertItems(self, table_name: str, items_data: list[dict], encrypt: bool = False, encrypt_columns: list = None) -> bool:
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
            if encrypt and encrypt_columns:
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

    def customUpdateItem(self, table_name: str, update_data: dict, where_clause: str, where_args: list, encrypt: bool = False, encrypt_columns: list = None) -> bool:
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

        if encrypt and encrypt_columns:
            encrypt_column_indices = [list(update_data.keys()).index(col) for col in encrypt_columns if col in update_data]
        else:
            encrypt_column_indices = None
        return self.basicUpdateData(sql, data, encrypt=encrypt, encrypt_column=encrypt_column_indices)

    def customSearchItem(self, table_name: str, unique_id: str, unique_id_column: str, decrypt: bool = False, decrypt_columns: list = None) -> list:
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

    def customSearchItems(self, table_name: str, sort_by_column: int = None, decrypt: bool = False, decrypt_columns: list = None) -> list:
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

    def customDeleteItem(self, table_name: str, where_clause: str, where_args: list) -> bool:
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

    def customDeleteItems(self, table_name: str, where_clause: str = None, where_args: list = None) -> bool:
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


class TheSeedDatabaseManager(_BasicSQLiteDatabase):
    """
    TheSeed 核心数据库管理器

    参数:
        :param DatabasePath : 数据库文件路径。
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
        :param StayConnected : 是否保持连接。
    属性:
        - _INSTANCE : 单例实例。
        - _Logger : 日志记录器。
    """

    _INSTANCE: TheSeedDatabaseManager = None

    def __new__(cls, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor, StayConnected: bool):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(TheSeedDatabaseManager, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor, StayConnected: bool):
        super().__init__(DatabasePath, Logger, Encryptor, StayConnected)
        self._Logger = Logger
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
    TheSeed SQLite 数据库管理器

    参数:
        :param DatabasePath : 数据库文件路径。
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
    属性:
        - _INSTANCE : 单例实例。
        - _Logger : 日志记录器。
        - _DatabasePath : 数据库文件路径。
        - _Encryptor : 加密器。
        - _DatabaseDict : 数据库字典。
        - IsClosed : 是否关闭。
    """
    _INSTANCE: SQLiteDatabaseManager = None

    def __new__(cls, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(SQLiteDatabaseManager, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, DatabasePath: str, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor):
        self._Logger = Logger
        self._DatabasePath = DatabasePath
        self._Encryptor = Encryptor
        self._DatabaseDict: dict = {}
        self.IsClosed = False

    def _checkDatabasePath(self, database_id: str, database_path: str) -> str:
        """
        检查数据库文件路径。如果未提供路径，则生成默认路径。

        参数:
            :param database_id : 数据库ID。
            :param database_path:  自定义数据库路径。

        返回:
            :return : 完整的数据库文件路径。
        """
        if database_path is None:
            return os.path.join(self._DatabasePath, f"{database_id}.db")
        else:
            return database_path

    def _checkLogger(self, logger) -> TheSeedCoreLogger:
        """
        检查日志记录器实例。如果未提供，则使用默认记录器。

        参数:
            :param logger: 自定义日志记录器实例。

        返回:
            :return : 日志记录器实例。
        """
        if logger is None:
            return self._Logger
        else:
            return logger

    def _checkEncryptor(self, encryptor) -> TheSeedEncryptor:
        """
        检查加密器实例。如果未提供，则使用默认加密器。

        参数:
            :param encryptor: 自定义加密器实例。

        返回:
            :return : 加密器实例。
        """
        if encryptor is None:
            return self._Encryptor
        else:
            return encryptor

    def createSQLiteDatabase(self, database_id: str, tables_structured: dict, stay_connected: bool = False, database_path: str = None, logger=None, encryptor=None) -> bool:
        """
        创建一个自定义数据库实例，并在内部字典中注册。

        参数:
            :param database_id : 数据库唯一标识符。
            :param tables_structured : 数据库表结构定义，包括表名和列信息。
            :param stay_connected : 创建后是否保持数据库连接。
            :param database_path : 数据库文件路径，如果为空则使用默认路径。
            :param logger : 日志记录器实例，如果为空则使用默认实例。
            :param encryptor : 加密器实例，如果为空则使用默认实例。

        返回:
            :return : 创建成功返回True，失败返回False。
        """
        try:
            tables_dict = {}
            custom_database_path = self._checkDatabasePath(database_id, database_path)
            custom_database_logger = self._checkLogger(logger)
            custom_database_encryption = self._checkEncryptor(encryptor)
            for table_name, structure in tables_structured.items():
                pk_name, pk_type = structure["primary_key"]
                columns_sql = ", ".join([f"{item_name} {item_type}" for item_name, item_type in structure["columns"].items()])
                table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({pk_name} {pk_type}, {columns_sql})"
                tables_dict[table_name] = table_sql
            custom_database = _CustomSQLiteDatabase(
                tables_dict,
                custom_database_path,
                custom_database_logger,
                custom_database_encryption,
                stay_connected,
            )
            self._DatabaseDict[database_id] = custom_database
            return True
        except Exception as e:
            error_msg = f"SQLiteDatabaseManager create custom database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def getDatabase(self, database_id: str) -> _CustomSQLiteDatabase:
        """
        根据数据库ID获取数据库实例。

        参数:
            :param database_id : 数据库唯一标识符。

        返回:
            :return : 返回对应的数据库实例，如果不存在返回None。
        """
        return self._DatabaseDict.get(database_id)

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
            result = database_instance.customUpsertItem(table_name, update_data, encrypt, encrypt_columns)
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
            result = database_instance.customUpsertItems(table_name, update_data, encrypt, encrypt_columns)
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
            result = database_instance.customUpdateItem(table_name, update_data, where_clause, where_args, encrypt, encrypt_columns)
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
            row = database_instance.customSearchItem(table_name, unique_id, unique_id_column, decrypt, decrypt_columns)
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
            rows = database_instance.customSearchItems(table_name, sort_by_column, decrypt, decrypt_columns)
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
            result = database_instance.customDeleteItem(table_name, where_clause, where_args)
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
            result = database_instance.customDeleteItems(table_name, where_clause, where_args)
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
                self._DatabaseDict.pop(database_id)
                self._Logger.info(f"{database_id} connection closed.")
            return result
        else:
            error_msg = f"SQLiteDatabaseManager close database error : database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def closeAllDatabase(self) -> bool:
        """关闭所有管理的数据库连接。"""
        if self._DatabaseDict:
            for database_id in list(self._DatabaseDict.keys()):
                self.closeDatabase(database_id)
        self.IsClosed = True
        self._Logger.info("All sqlite databases closed.")
        return True


class RedisDatabaseManager:
    """
    TheSeed Redis 数据库管理器

    参数:
        :param Logger : 日志记录器。
        :param Encryptor : 加密器。
    属性:
        - _INSTANCE : 单例实例。
        - _Logger : 日志记录器。
        - _Encryptor : 加密器。
        - _RedisDatabase : Redis 数据库字典。
        - IsClosed : 是否关闭。
    """
    _INSTANCE: RedisDatabaseManager = None

    def __new__(cls, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(RedisDatabaseManager, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Logger: TheSeedCoreLogger, Encryptor: TheSeedEncryptor):
        self._Logger = Logger
        self._Encryptor = Encryptor
        self._RedisDatabase = {}
        self.IsClosed = False

    def createRedisDatabase(self, database_id: str, host: str, port: str, password: str = None, db: int = 0, logger=None, encryptor=None):
        try:
            if logger is None:
                logger = self._Logger
            if encryptor is None:
                encryptor = self._Encryptor
            redis_instance = _BasicRedisDatabase(RedisHost=host, RedisPort=port, Password=password, Num=db, Logger=logger, Encryptor=encryptor)
            self._RedisDatabase[database_id] = redis_instance
            return True
        except Exception as e:
            error_msg = f"RedisDatabaseManager create redis database error : {e}\n\n{traceback.format_exc()}"
            self._Logger.error(error_msg)
            return False

    def getRedisDatabase(self, database_id: str):
        return self._RedisDatabase.get(database_id)

    def closeRedisDatabase(self, database_id: str):
        redis_instance = self.getRedisDatabase(database_id)
        if redis_instance is not None:
            result = redis_instance.close()
            if result:
                self._RedisDatabase.pop(database_id)
                self._Logger.info(f"{database_id} connection closed.")
            return result
        else:
            error_msg = f"Redis database '{database_id}' not found."
            self._Logger.error(error_msg)
            return False

    def closeAllDatabase(self):
        if self._RedisDatabase:
            for database_id in list(self._RedisDatabase.keys()):
                self.closeRedisDatabase(database_id)
        self.IsClosed = True
        self._Logger.info("All redis databases closed.")
        return True
