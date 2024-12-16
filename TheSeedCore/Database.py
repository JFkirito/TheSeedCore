# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING, List, Dict

from .Logger import consoleLogger

if TYPE_CHECKING:
    from .Security import AESEncryptor

__all__ = [
    "SQLiteDatabase",
    "MySQLDatabase",
]

_DEFAULT_LOGGER = consoleLogger("Database")


class SQLiteDatabase:
    def __init__(self, name: str, path: str, stay_connected: bool = False, encryptor: AESEncryptor = None):
        self._Name = name
        self._Path = os.path.join(path, f"{name}.db")
        self._StayConnected = stay_connected
        self._Connection = None
        self._Encryptor = encryptor
        self._connect()

    @property
    def name(self):
        return self._Name

    def _connect(self) -> bool:
        try:
            if not os.path.exists(self._Path):
                open(self._Path, "a").close()
            if self._Connection is None:
                self._Connection = sqlite3.connect(self._Path)
                return True
            return False
        except sqlite3.Error as e:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] connection error : {e}")
            return False

    def _disconnect(self) -> bool:
        try:
            if self._Connection and not self._StayConnected:
                self._Connection.close()
                self._Connection = None
            _DEFAULT_LOGGER.info(f"SQLite database [{self._Name}] disconnection completed")
            return True
        except Exception as e:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] disconnect error : {e}")
            return False

    def deleteDatabase(self) -> bool:
        try:
            self._StayConnected = False
            self._disconnect()
            os.remove(self._Path)
            return True
        except OSError as e:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] delete error : {e}")
            return False
        finally:
            del self

    def checkExistedTable(self, table_name: str):
        if not isinstance(table_name, str):
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] check existed table parameter error : <table_name> must be a string.")
            return False

        try:
            self._connect()
            cursor = self._Connection.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone()[0] == 1
            if exists:
                return exists
            return exists
        except sqlite3.Error as e:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] check table existed error : {e}")
            return False
        finally:
            self._disconnect()

    def getExistedTables(self) -> List[str]:
        try:
            self._connect()
            cursor = self._Connection.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [table[0] for table in cursor.fetchall()]
            cursor.close()
            return existing_tables
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] get existed tables error : {e}")
            return []
        finally:
            self._disconnect()

    def createTable(self, table_name: str, table_sql: str) -> bool:
        if not (isinstance(table_name, str) and isinstance(table_sql, str)) or not table_name.strip() or not table_sql.strip():
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] create parameter error: <table_name> and <table_sql> must be non-empty strings.")
            return False
        cursor = None
        try:
            self._connect()
            cursor = self._Connection.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
            if cursor.fetchone() is None:
                cursor.execute(table_sql)
                self._Connection.commit()
                return True
            return False
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] create error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            self._disconnect()

    def createTables(self, tables_dict: dict) -> bool:
        if not isinstance(tables_dict, dict):
            _DEFAULT_LOGGER.error(f"SQLite Database [{self._Name}] create parameter error : <tables_dict> must be a dictionary.")
            return False
        created_tables = []
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for table_name, table_sql in tables_dict.items():
                if not isinstance(table_name, str) or not isinstance(table_sql, str):
                    _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] invalid table definition for {table_name}.")
                    continue
                # noinspection SqlResolve
                cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(table_sql)
                    created_tables.append(table_name)
                else:
                    _DEFAULT_LOGGER.debug(f"SQLite database [{self._Name}] table {table_name} already exists.")
            self._Connection.commit()
            cursor.close()
            if created_tables:
                _DEFAULT_LOGGER.debug(f"SQLite database [{self._Name}] created tables: {', '.join(created_tables)}")
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] create error : {e}")
            return False
        finally:
            self._disconnect()

    def deleteTable(self, table_name: str) -> bool:
        if not isinstance(table_name, str):
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] delete parameter error : <table_name> must be a string.")
            return False
        try:
            self._connect()
            cursor = self._Connection.cursor()
            # noinspection SqlResolve
            cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone()[0] == 1:
                cursor.execute(f"DROP TABLE {table_name}")
                self._Connection.commit()
                cursor.close()
                return True
            _DEFAULT_LOGGER.warning(f"SQLite database [{self._Name}] table {table_name} not exists.")
            return False
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] delete table error : {e}")
            return False
        finally:
            self._disconnect()

    def deleteTables(self, tables: List[str]) -> bool:
        if not isinstance(tables, list):
            _DEFAULT_LOGGER.error(f"SQLite Database [{self._Name}] delete parameter error : <tables> must be a list.")
            return False
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for table in tables:
                if not isinstance(table, str):
                    _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] invalid table name {table}.")
                    continue
                # noinspection SqlResolve
                cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone()[0] == 1:
                    cursor.execute(f"DROP TABLE {table}")
                else:
                    _DEFAULT_LOGGER.debug(f"SQLite database [{self._Name}] table {table} not exists.")
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] delete error : {e}")
            return False
        finally:
            self._disconnect()

    def insertData(self, table_name: str, data: Dict[str, str], encrypt_columns: List[str] = None) -> bool:
        if not data:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert data parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert data parameter error: no encryptor provided.")
            return False
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        item_data = tuple(data.values())
        if encrypt_columns is not None:
            columns_list = list(data.keys())
            encrypt_column_indices = [columns_list.index(col) for col in encrypt_columns if col in columns_list]
            encrypted_data = []
            for index, value in enumerate(item_data):
                if index in encrypt_column_indices:
                    encrypted_data.append(self._Encryptor.encrypt(value))
                else:
                    encrypted_data.append(value)
            item_data = tuple(encrypted_data)
        else:
            item_data = tuple(data.values())
        try:
            self._connect()
            cursor = self._Connection.cursor()
            cursor.execute(f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})", item_data)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert data error : {e}")
            return False
        finally:
            self._disconnect()

    def insertDatas(self, table_name: str, data: List[Dict[str, str]], encrypt_columns: List[str] = None) -> bool:
        if not data:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert datas parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert datas parameter error: no encryptor provided.")
            return False
        all_columns = set()
        for item_data in data:
            all_columns.update(item_data.keys())
        all_columns = sorted(all_columns)
        columns = ", ".join(all_columns)
        placeholders = ", ".join(["?"] * len(all_columns))
        all_data = []
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for item_data in data:
                item_values = [item_data.get(col, None) for col in all_columns]
                if encrypt_columns is not None:
                    encrypt_column_indices = [all_columns.index(col) for col in encrypt_columns if col in all_columns]
                    encrypted_data = []
                    for index, value in enumerate(item_values):
                        if index in encrypt_column_indices:
                            encrypted_data.append(self._Encryptor.encrypt(value))
                        else:
                            encrypted_data.append(value)
                    item_values = tuple(encrypted_data)
                else:
                    item_values = tuple(item_values)
                all_data.append(item_values)
            cursor.executemany(f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})", all_data)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] insert datas error: {e}")
            return False
        finally:
            self._disconnect()

    def updateData(self, table_name: str, data: Dict[str, str], condition: str, encrypt_columns: List[str] = None) -> bool:
        if not data:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update data parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update data parameter error: no encryptor provided.")
            return False
        placeholders = ", ".join([f"{col} = ?" for col in data.keys()])
        item_data = tuple(data.values())
        if encrypt_columns is not None:
            columns_list = list(data.keys())
            encrypt_column_indices = [columns_list.index(col) for col in encrypt_columns if col in columns_list]
            encrypted_data = []
            for index, value in enumerate(item_data):
                if index in encrypt_column_indices:
                    encrypted_data.append(self._Encryptor.encrypt(value))
                else:
                    encrypted_data.append(value)
            item_data = tuple(encrypted_data)
        try:
            self._connect()
            cursor = self._Connection.cursor()
            cursor.execute(f"UPDATE {table_name} SET {placeholders} WHERE {condition}", item_data)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update data error: {e}")
            return False
        finally:
            self._disconnect()

    def updateDatas(self, table_name: str, data: List[Dict[str, str]], condition: str, encrypt_columns: List[str] = None) -> bool:
        if not data:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update datas parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update datas parameter error: no encryptor provided.")
            return False
        all_columns = set()
        for item_data in data:
            all_columns.update(item_data.keys())
        all_columns = sorted(all_columns)
        placeholders = ", ".join([f"{col} = ?" for col in all_columns])
        all_data = []
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for item_data in data:
                item_values = [item_data.get(col, None) for col in all_columns]
                if encrypt_columns is not None:
                    encrypt_column_indices = [all_columns.index(col) for col in encrypt_columns if col in all_columns]
                    encrypted_data = []
                    for index, value in enumerate(item_values):
                        if index in encrypt_column_indices and value is not None:
                            encrypted_data.append(self._Encryptor.encrypt(value))
                        else:
                            encrypted_data.append(value)
                    item_values = tuple(encrypted_data)
                else:
                    item_values = tuple(item_values)

                all_data.append(item_values)
            cursor.executemany(f"UPDATE {table_name} SET {placeholders} WHERE {condition}", all_data)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] update data error: {e}")
            return False
        finally:
            self._disconnect()

    def selectData(self, table_name: str, columns: List[str], condition: str = None, dencrypt_columns: List[str] = None, order_by: str = None, limit: int = None) -> List[Dict[str, str]]:
        if not isinstance(columns, list):
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] select data parameter error: <columns> must be a list.")
            return []
        columns_str = ", ".join(columns)
        columns_list = columns
        if dencrypt_columns is not None and self._Encryptor is None:
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] select data parameter error: no encryptor provided.")
            return []
        if dencrypt_columns is not None:
            dencrypt_column_indices = [columns_list.index(col) for col in dencrypt_columns if col in columns_list]
        else:
            dencrypt_column_indices = []
        try:
            self._connect()
            cursor = self._Connection.cursor()
            query = f"SELECT {columns_str} FROM {table_name}"
            query_params = []
            if condition:
                query += f" WHERE {condition}"
            if order_by:
                query += f" ORDER BY {order_by}"
            if limit:
                query += f" LIMIT ?"
                query_params.append(limit)
            cursor.execute(query, query_params)
            fetched_data = cursor.fetchall()
            result = []
            for row in fetched_data:
                item = {}
                for index, value in enumerate(row):
                    if index in dencrypt_column_indices:
                        item[columns_list[index]] = self._Encryptor.decrypt(value) if value is not None else value
                    else:
                        item[columns_list[index]] = value
                result.append(item)
            cursor.close()
            return result
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] select data error: {e}")
            return []
        finally:
            self._disconnect()

    def deleteData(self, table_name: str, condition: str, condition_params: tuple = ()) -> bool:
        try:
            self._connect()
            cursor = self._Connection.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE {condition}", condition_params)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DEFAULT_LOGGER.error(f"SQLite database [{self._Name}] delete data error: {e}")
            return False
        finally:
            self._disconnect()


# Define the MySQLDatabase class
try:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import mysql.connector
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from mysql.connector import Error


    class MySQLDatabase:
        def __init__(self, name: str, host: str, user: str, password: str, stay_connected: bool = False, encryptor=None):
            self._Name = name
            self._Host = host
            self._User = user
            self._Password = password
            self._StayConnected = stay_connected
            self._Connection = None
            self._Encryptor = encryptor
            self._connect()

        @property
        def name(self):
            return self._Name

        def _connect(self) -> bool:
            try:
                if self._Connection is None:
                    self._Connection = mysql.connector.connect(
                        host=self._Host,
                        user=self._User,
                        password=self._Password,
                        database=self._Name
                    )
                    return True
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] connection error : {e}")
                return False

        def _disconnect(self) -> bool:
            try:
                if self._Connection and not self._StayConnected:
                    self._Connection.close()
                    self._Connection = None
                    return True
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] disconnect error : {e}")
                return False

        def deleteDatabase(self) -> bool:
            try:
                self._StayConnected = False
                self._disconnect()
                conn = mysql.connector.connect(
                    host=self._Host,
                    user=self._User,
                    password=self._Password
                )
                cursor = conn.cursor()
                cursor.execute(f"DROP DATABASE {self._Name}")
                cursor.close()
                conn.close()
                return True
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete error : {e}")
                return False
            finally:
                del self

        def checkExistedTable(self, table_name: str) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] check existed table parameter error : <table_name> must be a string.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                exists = cursor.fetchone() is not None
                cursor.close()
                return exists
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] check table existed error : {e}")
                return False
            finally:
                self._disconnect()

        def getExistedTables(self) -> List[str]:
            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                cursor.close()
                return tables
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] get existed tables error : {e}")
                return []
            finally:
                self._disconnect()

        def createTable(self, table_name: str, table_sql: str) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] create table parameter error : <table_name> must be non-empty strings.")
                return False
            if not isinstance(table_sql, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] create table parameter error : <table_sql> must be a string.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_sql})")
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] create table error : {e}")
                return False
            finally:
                self._disconnect()

        def createTables(self, tables_dict: dict) -> bool:
            if not isinstance(tables_dict, dict):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] create tables parameter error : <tables_dict> must be a dictionary.")
                return False
            created_tables = []
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for table_name, table_sql in tables_dict.items():
                    if not isinstance(table_name, str) or not isinstance(table_sql, str):
                        _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] invalid table definition for {table_name}.")
                        continue
                    cursor.execute(f"SHOW TABLES LIKE %s", (table_name,))
                    if cursor.fetchone() is None:
                        cursor.execute(f"CREATE TABLE {table_name} ({table_sql})")
                        created_tables.append(table_name)
                    else:
                        _DEFAULT_LOGGER.debug(f"MySQL database [{self._Name}] table {table_name} already exists.")
                self._Connection.commit()
                cursor.close()
                if created_tables:
                    _DEFAULT_LOGGER.debug(f"MySQL database [{self._Name}] created tables: {', '.join(created_tables)}")
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] create tables error : {e}")
                return False
            finally:
                self._disconnect()

        def deleteTable(self, table_name: str) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete table parameter error : <table_name> must be a string.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete table error : {e}")
                return False
            finally:
                self._disconnect()

        def deleteTables(self, tables: List[str]) -> bool:
            if not isinstance(tables, list):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete tables parameter error : <tables> must be a list.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for table in tables:
                    if not isinstance(table, str):
                        _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] invalid table name {table}.")
                        continue
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete tables error : {e}")
                return False
            finally:
                self._disconnect()

        def insertData(self, table_name: str, data: Dict[str, str], encrypt_columns: List[str] = None) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert data parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert data parameter error : <data> is empty.")
                return False
            if not isinstance(data, dict):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert data parameter error : <data> must be a dictionary.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert data parameter error : no encryptor provided.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                item_data = tuple(data.values())
                if encrypt_columns:
                    item_data = tuple(
                        self._Encryptor.encrypt(value) if col in encrypt_columns else value
                        for col, value in data.items()
                    )
                cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", item_data)
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert data error : {e}")
                return False
            finally:
                self._disconnect()

        def insertDatas(self, table_name: str, data: List[Dict[str, str]], encrypt_columns: List[str] = None) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert datas parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert datas parameter error : <data> is empty.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert datas parameter error : no encryptor provided.")
                return False
            all_columns = set()
            for item_data in data:
                all_columns.update(item_data.keys())
            all_columns = sorted(all_columns)
            columns = ", ".join(all_columns)
            placeholders = ", ".join(["%s"] * len(all_columns))
            all_data = []
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for item_data in data:
                    item_values = [item_data.get(col, None) for col in all_columns]
                    if encrypt_columns:
                        encrypt_column_indices = [all_columns.index(col) for col in encrypt_columns if col in all_columns]
                        encrypted_data = []
                        for index, value in enumerate(item_values):
                            if index in encrypt_column_indices:
                                encrypted_data.append(self._Encryptor.encrypt(value))
                            else:
                                encrypted_data.append(value)
                        item_values = tuple(encrypted_data)
                    else:
                        item_values = tuple(item_values)
                    all_data.append(item_values)
                cursor.executemany(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", all_data)
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] insert datas error : {e}")
                return False
            finally:
                self._disconnect()

        def updateData(self, table_name: str, data: Dict[str, str], condition: str, encrypt_columns: List[str] = None) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update data parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update data parameter error : <data> is empty.")
                return False
            if not isinstance(data, dict):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update data parameter error : <data> must be a dictionary.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update data parameter error : no encryptor provided.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                set_clause = ", ".join([f"{col} = %s" for col in data.keys()])
                item_data = tuple(data.values())
                if encrypt_columns:
                    item_data = tuple(
                        self._Encryptor.encrypt(value) if col in encrypt_columns else value
                        for col, value in data.items()
                    )
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {condition}", item_data)
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update data error : {e}")
                return False
            finally:
                self._disconnect()

        def updateDatas(self, table_name: str, data: List[Dict[str, str]], condition: str, encrypt_columns: List[str] = None) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update datas parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update datas parameter error : <data> is empty.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update datas parameter error : no encryptor provided.")
                return False
            all_columns = set()
            for item_data in data:
                all_columns.update(item_data.keys())
            all_columns = sorted(all_columns)
            set_clause = ", ".join([f"{col} = %s" for col in all_columns])
            all_data = []
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for item_data in data:
                    item_values = [item_data.get(col, None) for col in all_columns]
                    if encrypt_columns:
                        encrypt_column_indices = [all_columns.index(col) for col in encrypt_columns if col in all_columns]
                        encrypted_data = []
                        for index, value in enumerate(item_values):
                            if index in encrypt_column_indices:
                                encrypted_data.append(self._Encryptor.encrypt(value))
                            else:
                                encrypted_data.append(value)
                        item_values = tuple(encrypted_data)
                    else:
                        item_values = tuple(item_values)
                    all_data.append(item_values)
                cursor.executemany(f"UPDATE {table_name} SET {set_clause} WHERE {condition}", all_data)
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] update datas error : {e}")
                return False
            finally:
                self._disconnect()

        def selectData(self, table_name: str, columns: List[str], condition: str = None, dencrypt_columns: List[str] = None) -> List[Dict[str, str]]:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] select data parameter error : <table_name> must be a string.")
                return []
            if not isinstance(columns, list):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] select data parameter error : <columns> must be a list.")
                return []
            if dencrypt_columns is not None and self._Encryptor is None:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] select data parameter error : no encryptor provided.")
                return []
            try:
                self._connect()
                cursor = self._Connection.cursor(dictionary=True)
                columns_str = ", ".join(columns)
                query = f"SELECT {columns_str} FROM {table_name}"
                if condition:
                    query += f" WHERE {condition}"
                cursor.execute(query)
                results = cursor.fetchall()
                if dencrypt_columns:
                    for row in results:
                        for col in dencrypt_columns:
                            row[col] = self._Encryptor.decrypt(row[col]) if row[col] else row[col]
                cursor.close()
                return results
            except Error as e:
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] select data error : {e}")
                return []
            finally:
                self._disconnect()

        def deleteData(self, table_name: str, condition: str) -> bool:
            if not isinstance(table_name, str):
                _DEFAULT_LOGGER.error(f"MySQL database [{self._Name}] delete data parameter error : <table_name> must be a string.")
                return False

            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute(f"DELETE FROM {table_name} WHERE {condition}")
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                print(f"Error deleting data from MySQL database [{self._Name}]: {e}")
                return False
            finally:
                self._disconnect()
except ImportError as _:
    class MySQLDatabase:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.error(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def deleteDatabase(self) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def checkExistedTable(self, table_name: str) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def getExistedTables(self) -> List[str]:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def createTable(self, table_name: str, table_sql: str) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def createTables(self, tables_dict: dict) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def deleteTable(self, table_name: str) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def deleteTables(self, tables: List[str]) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def insertData(self, table_name: str, data: Dict[str, str], encrypt_columns: List[str] = None) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def insertDatas(self, table_name: str, data: List[Dict[str, str]], encrypt_columns: List[str] = None) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def updateData(self, table_name: str, data: Dict[str, str], condition: str, encrypt_columns: List[str] = None) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def updateDatas(self, table_name: str, data: List[Dict[str, str]], condition: str, encrypt_columns: List[str] = None) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def selectData(self, table_name: str, columns: List[str], condition: str = None, dencrypt_columns: List[str] = None) -> List[Dict[str, str]]:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

        def deleteData(self, table_name: str, condition: str) -> bool:
            raise NotImplementedError(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")
