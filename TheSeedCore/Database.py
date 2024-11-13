# -*- coding: utf-8 -*-

from __future__ import annotations

__all__ = [
    "SQLiteDatabase",
    "MySQLDatabase",
]

import os
import sqlite3
from typing import TYPE_CHECKING, List, Dict

from . import DatabaseDirectoryPath
from .InstanceManager import DatabaseInstanceManager
from .Logger import consoleLogger
from .Security import AESEncryptor

if TYPE_CHECKING:
    pass

_DefaultLogger = consoleLogger("Database")


class SQLiteDatabase:
    """
    Represents a SQLite database for managing data storage and operations.

    The class provides a simplified interface for managing data storage and operations within a SQLite database.
    It includes functionality for creating, updating, retrieving, and deleting records, as well as managing tables.
    The class also supports optional data encryption and decryption for handling sensitive information.

    InstanceAttribute:
        _Name: The name of the database.
        _Path: The file path of the database.
        _StayConnected: A flag indicating whether to maintain the database connection.
        _Connection: The SQLite database connection object.
        _Encryptor: An optional encryptor for handling sensitive data.

    Method:
        __init__: Initializes the SQLiteDatabase instance and establishes a connection.
        name: Property to get the name of the database.
        _connect: Establishes a connection to the SQLite database.
        _disconnect: Closes the connection to the database.
        deleteDatabase: Deletes the database file from the filesystem.
        checkExistedTable: Checks if a specified table exists in the database.
        getExistedTables: Retrieves a list of all existing tables in the database.
        createTable: Creates a new table in the database if it doesn't already exist.
        createTables: Creates multiple tables in the database based on provided definitions.
        deleteTable: Deletes a specified table from the database.
        deleteTables: Deletes multiple tables from the database.
        insertData: Inserts a single record into a specified table, with optional encryption.
        insertDatas: Inserts multiple records into a specified table, with optional encryption.
        updateData: Updates a record in a specified table based on a condition.
        updateDatas: Updates multiple records in a specified table based on a condition.
        selectData: Retrieves records from a specified table, with optional decryption.
        deleteData: Deletes records from a specified table based on a condition.
    """

    def __init__(self, name: str, path: str = None, stay_connected: bool = False, encryptor: AESEncryptor = None):
        self._Name = name
        self._Path = os.path.join(DatabaseDirectoryPath, f"{name}.db") if path is None else os.path.join(path, f"{name}.db")
        self._StayConnected = stay_connected
        self._Connection = None
        self._Encryptor = encryptor
        self._connect()
        DatabaseInstanceManager.registerSQLiteDatabase(self._Name, self)

    @property
    def name(self):
        return self._Name

    def _connect(self) -> bool:
        """
        Establishes a connection to the SQLite database, creating the database file if it does not already exist.

        :return: A boolean indicating whether the connection operation was successful (True) or not (False).
        setup:
            1. Check if the database file at the specified path (_Path) exists:
                1.1. If it does not exist, create the file by opening it in append mode and immediately closing it.
            2. Check if the _Connection attribute is None, indicating that a connection has not yet been established:
                2.1. If it is None, attempt to connect to the SQLite database using the specified path.
                2.2. If the connection is successful, return True to indicate successful connection.
            3. If an SQLite error occurs during the connection attempt:
                3.1. Log an error message with the details of the error.
                3.2. Return False to indicate failure.
        """

        try:
            if not os.path.exists(self._Path):
                open(self._Path, "a").close()
            if self._Connection is None:
                self._Connection = sqlite3.connect(self._Path)
                return True
        except sqlite3.Error as e:
            _DefaultLogger.error(f"SQLite database [{self._Name}] connection error : {e}")
            return False

    def _disconnect(self) -> bool:
        """
        Closes the connection to the SQLite database if it is open and not marked to stay connected.

        :return: A boolean indicating whether the disconnection operation was successful (True) or not (False).
        setup:
            1. Check if the _Connection attribute exists and if _StayConnected is False:
                1.1. If both conditions are met, close the database connection and set _Connection to None.
            2. Log an informational message indicating that the disconnection was completed successfully.
            3. Return True to indicate successful disconnection.
            4. If an exception occurs during the disconnection process:
                4.1. Log an error message with the details of the error.
                4.2. Return False to indicate failure.
        """

        try:
            if self._Connection and not self._StayConnected:
                self._Connection.close()
                self._Connection = None
            _DefaultLogger.info(f"SQLite database [{self._Name}] disconnection completed")
            return True
        except Exception as e:
            _DefaultLogger.error(f"SQLite database [{self._Name}] disconnect error : {e}")
            return False

    def deleteDatabase(self) -> bool:
        """
        Deletes the SQLite database file from the filesystem.

        :return: A boolean indicating whether the deletion operation was successful (True) or not (False).
        setup:
            1. Set the _StayConnected attribute to False to indicate the intention to disconnect from the database.
            2. Call the _disconnect method to close any existing connections to the database.
            3. Attempt to remove the database file from the specified path:
                3.1. If the removal is successful, return True to indicate successful deletion.
            4. If an OSError occurs during the deletion process:
                4.1. Log an error message with the details of the error.
                4.2. Return False to indicate failure.
            5. Finally, delete the instance of the class to free up resources.
        """

        try:
            self._StayConnected = False
            self._disconnect()
            os.remove(self._Path)
            return True
        except OSError as e:
            _DefaultLogger.error(f"SQLite database [{self._Name}] delete error : {e}")
            return False
        finally:
            del self

    def checkExistedTable(self, table_name: str):
        """
        Checks whether a specified table exists in the SQLite database.

        :param table_name: A string representing the name of the table to check for existence.
        :return: A boolean indicating whether the table exists (True) or not (False).
        setup:
            1. Validate that the provided table_name parameter is a string:
                1.1. If it is not a string, log an error and return False.
            2. Establish a connection to the database by calling the _connect method.
            3. Create a cursor object to execute SQL commands.
            4. Execute a SQL query to check if the specified table exists in the sqlite_master table.
            5. Fetch the result to determine if the table exists:
                5.1. Return True if the table exists; otherwise, return False.
            6. If an SQLite error occurs during execution:
                6.1. Log an error message with the details of the error.
                6.2. Return False to indicate failure.
            7. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not isinstance(table_name, str):
            _DefaultLogger.error(f"SQLite database [{self._Name}] check existed table parameter error : <table_name> must be a string.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] check table existed error : {e}")
            return False
        finally:
            self._disconnect()

    def getExistedTables(self) -> List[str]:
        """
        Retrieves a list of existing tables in the SQLite database.

        :return: A list of strings representing the names of tables currently in the database, or an empty list if an error occurs.
        setup:
            1. Establish a connection to the database by calling the _connect method.
            2. Create a cursor object to execute SQL commands.
            3. Execute a SQL query to select the names of all tables from the sqlite_master table.
            4. Fetch all results and create a list of table names.
            5. Close the cursor after execution.
            6. Return the list of existing table names.
            7. If an SQLite error occurs during execution:
                7.1. Roll back the transaction to revert any changes.
                7.2. Log an error message with the details of the error.
                7.3. Return an empty list to indicate failure.
            8. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

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
            _DefaultLogger.error(f"SQLite database [{self._Name}] get existed tables error : {e}")
            return []
        finally:
            self._disconnect()

    def createTable(self, table_name: str, table_sql: str) -> bool:
        """
        Creates a single table in the SQLite database using the provided table name and SQL statement.

        :param table_name: A string representing the name of the table to be created.
        :param table_sql: A string containing the SQL statement used to create the table.
        :return: A boolean indicating whether the table creation operation was successful (True) or not (False).
        setup:
            1. Validate that both the table_name and table_sql parameters are non-empty strings:
                1.1. If either parameter is invalid, log an error and return False.
            2. Initialize a cursor variable to None.
            3. Establish a connection to the database by calling the _connect method.
            4. Create a cursor object to execute SQL commands.
            5. Check if the specified table already exists in the database by querying the sqlite_master table:
                5.1. If the table does not exist, execute the provided SQL to create the table and commit the transaction.
                5.2. Return True to indicate successful creation.
            6. If the table already exists, return False.
            7. If an SQLite error occurs during execution:
                7.1. Roll back the transaction to revert any changes.
                7.2. Log an error message with the details of the error.
                7.3. Return False to indicate failure.
            8. Ensure the cursor is closed after execution, and the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not (isinstance(table_name, str) and isinstance(table_sql, str)) or not table_name.strip() or not table_sql.strip():
            _DefaultLogger.error(f"SQLite database [{self._Name}] create parameter error: <table_name> and <table_sql> must be non-empty strings.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] create error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            self._disconnect()

    def createTables(self, tables_dict: dict) -> bool:
        """
        Creates multiple tables in the SQLite database based on the provided definitions.

        :param tables_dict: A dictionary where keys are table names (strings) and values are SQL statements for creating those tables.
        :return: A boolean indicating whether the table creation operation was successful (True) or not (False).
        setup:
            1. Check if the provided tables_dict parameter is a dictionary:
                1.1. If it is not a dictionary, log an error and return False.
            2. Initialize a list to keep track of created tables.
            3. Establish a connection to the database by calling the _connect method.
            4. Create a cursor object to execute SQL commands.
            5. Iterate over each item in the tables_dict:
                5.1. Check if both the table name and SQL definition are strings:
                    5.1.1. If not, log an error and continue to the next item.
                5.2. Check if the table already exists in the database by querying the sqlite_master table:
                    5.2.1. If the table does not exist, execute the provided SQL to create the table and add the table name to the created_tables list.
                    5.2.2. If the table already exists, log a debug message indicating this.
            6. Commit the transaction to save changes.
            7. Close the cursor after execution.
            8. If any tables were created, log their names.
            9. Return True to indicate successful creation of tables.
            10. If an SQLite error occurs during execution:
                10.1. Roll back the transaction to revert any changes.
                10.2. Log an error message with the details of the error.
                10.3. Return False to indicate failure.
            11. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not isinstance(tables_dict, dict):
            _DefaultLogger.error(f"SQLite Database [{self._Name}] create parameter error : <tables_dict> must be a dictionary.")
            return False
        created_tables = []
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for table_name, table_sql in tables_dict.items():
                if not isinstance(table_name, str) or not isinstance(table_sql, str):
                    _DefaultLogger.error(f"SQLite database [{self._Name}] invalid table definition for {table_name}.")
                    continue
                # noinspection SqlResolve
                cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(table_sql)
                    created_tables.append(table_name)
                else:
                    _DefaultLogger.debug(f"SQLite database [{self._Name}] table {table_name} already exists.")
            self._Connection.commit()
            cursor.close()
            if created_tables:
                _DefaultLogger.debug(f"SQLite database [{self._Name}] created tables: {', '.join(created_tables)}")
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DefaultLogger.error(f"SQLite database [{self._Name}] create error : {e}")
            return False
        finally:
            self._disconnect()

    def deleteTable(self, table_name: str) -> bool:
        """
        Deletes a specified table from the SQLite database.

        :param table_name: A string representing the name of the table to be deleted.
        :return: A boolean indicating whether the delete operation was successful (True) or not (False).
        setup:
            1. Check if the provided table_name parameter is a string:
                1.1. If it is not a string, log an error and return False.
            2. Establish a connection to the database by calling the _connect method.
            3. Create a cursor object to execute SQL commands.
            4. Check if the specified table exists in the database by querying the sqlite_master table:
                4.1. If the table exists, execute a DROP TABLE command to delete it.
                4.2. Commit the transaction to save changes and close the cursor.
                4.3. Return True to indicate successful deletion.
            5. If the table does not exist, return False.
            6. If an SQLite error occurs during execution:
                6.1. Roll back the transaction to revert any changes.
                6.2. Log an error message with the details of the error.
                6.3. Return False to indicate failure.
            7. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not isinstance(table_name, str):
            _DefaultLogger.error(f"SQLite database [{self._Name}] delete parameter error : <table_name> must be a string.")
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
            return False
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DefaultLogger.error(f"SQLite database [{self._Name}] delete table error : {e}")
            return False
        finally:
            self._disconnect()

    def deleteTables(self, tables: List[str]) -> bool:
        """
        Deletes specified tables from the SQLite database.

        :param tables: A list of strings representing the names of the tables to be deleted.
        :return: A boolean indicating whether the delete operation was successful (True) or not (False).
        setup:
            1. Check if the provided tables parameter is a list:
                1.1. If it is not a list, log an error and return False.
            2. Establish a connection to the database by calling the _connect method.
            3. Create a cursor object to execute SQL commands.
            4. Iterate over each table name in the provided list:
                4.1. Check if the table name is a string:
                    4.1.1. If it is not, log an error and continue to the next iteration.
                4.2. Check if the table exists in the database by querying the sqlite_master table:
                    4.2.1. If the table exists, execute a DROP TABLE command to delete it.
                    4.2.2. If the table does not exist, log a debug message indicating this.
            5. Commit the transaction to save changes.
            6. Close the cursor after execution.
            7. Return True to indicate successful deletion of specified tables.
            8. If an SQLite error occurs during execution:
                8.1. Roll back the transaction to revert any changes.
                8.2. Log an error message with the details of the error.
                8.3. Return False to indicate failure.
            9. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not isinstance(tables, list):
            _DefaultLogger.error(f"SQLite Database [{self._Name}] delete parameter error : <tables> must be a list.")
            return False
        try:
            self._connect()
            cursor = self._Connection.cursor()
            for table in tables:
                if not isinstance(table, str):
                    _DefaultLogger.error(f"SQLite database [{self._Name}] invalid table name {table}.")
                    continue
                # noinspection SqlResolve
                cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone()[0] == 1:
                    cursor.execute(f"DROP TABLE {table}")
                else:
                    _DefaultLogger.debug(f"SQLite database [{self._Name}] table {table} not exists.")
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DefaultLogger.error(f"SQLite database [{self._Name}] delete error : {e}")
            return False
        finally:
            self._disconnect()

    def insertData(self, table_name: str, data: Dict[str, str], encrypt_columns: List[str] = None) -> bool:
        """
        Inserts a single record into a specified table of the SQLite database, with options for encryption.

        :param table_name: A string representing the name of the table to insert data into.
        :param data: A dictionary containing the column-value pairs for the insertion.
        :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before insertion (default is None).
        :return: A boolean indicating whether the insert operation was successful (True) or not (False).
        setup:
            1. Check if the data dictionary is empty:
                1.1. If it is empty, log an error and return False.
            2. Check if encryption is required:
                2.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
            3. Create a string of columns and a string of placeholders for the SQL INSERT statement.
            4. Prepare the item data as a tuple of values from the data dictionary.
            5. If encryption is required:
                5.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
            6. Establish a connection to the database by calling the _connect method.
            7. Create a cursor object to execute SQL commands.
            8. Execute the INSERT SQL command with the constructed columns and values.
            9. Commit the transaction to save changes.
            10. Close the cursor after execution.
            11. Return True to indicate successful insertion.
            12. If an SQLite error occurs during execution:
                12.1. Roll back the transaction to revert any changes.
                12.2. Log an error message with the details of the error.
                12.3. Return False to indicate failure.
            13. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not data:
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert data parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert data parameter error: no encryptor provided.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert data error : {e}")
            return False
        finally:
            self._disconnect()

    def insertDatas(self, table_name: str, data: List[Dict[str, str]], encrypt_columns: List[str] = None) -> bool:
        """
        Inserts multiple records into a specified table of the SQLite database, with options for encryption.

        :param table_name: A string representing the name of the table to insert data into.
        :param data: A list of dictionaries where each dictionary contains column-value pairs for the insertion.
        :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before insertion (default is None).
        :return: A boolean indicating whether the insert operation was successful (True) or not (False).
        setup:
            1. Check if the data list is empty:
                1.1. If it is empty, log an error and return False.
            2. Check if encryption is required:
                2.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
            3. Gather all unique column names from the provided data:
                3.1. Create a set to collect column names from each item in the data.
                3.2. Sort the collected column names for consistent ordering.
            4. Create a string of columns and a string of placeholders for the SQL INSERT statement.
            5. Initialize a list to hold the values for each insert operation.
            6. Establish a connection to the database by calling the _connect method.
            7. Create a cursor object to execute SQL commands.
            8. Iterate over each item in the data:
                8.1. Retrieve the values for each column based on the collected column names.
                8.2. If encryption is required:
                    8.2.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
                8.3. Append the prepared item values to the all_data list as a tuple.
            9. Execute the INSERT SQL command using the executemany method with the constructed columns and values.
            10. Commit the transaction to save changes.
            11. Close the cursor after execution.
            12. Return True to indicate successful insertion.
            13. If an SQLite error occurs during execution:
                13.1. Roll back the transaction to revert any changes.
                13.2. Log an error message with the details of the error.
                13.3. Return False to indicate failure.
            14. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not data:
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert datas parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert datas parameter error: no encryptor provided.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] insert datas error: {e}")
            return False
        finally:
            self._disconnect()

    def updateData(self, table_name: str, data: Dict[str, str], condition: str, encrypt_columns: List[str] = None) -> bool:
        """
        Updates a single record in a specified table of the SQLite database based on the provided data and condition.

        :param table_name: A string representing the name of the table to update.
        :param data: A dictionary containing the column-value pairs for the update.
        :param condition: A string representing the SQL condition to identify which record to update.
        :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before updating (default is None).
        :return: A boolean indicating whether the update operation was successful (True) or not (False).
        setup:
            1. Check if the data dictionary is empty:
                1.1. If it is empty, log an error and return False.
            2. Check if encryption is required:
                2.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
            3. Create a string of placeholders for the SQL UPDATE statement based on the keys in the data dictionary.
            4. Prepare the item data as a tuple of values from the data dictionary.
            5. If encryption is required:
                5.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
            6. Establish a connection to the database by calling the _connect method.
            7. Create a cursor object to execute SQL commands.
            8. Execute the UPDATE SQL command with the constructed placeholders and values.
            9. Commit the transaction to save changes.
            10. Close the cursor after execution.
            11. Return True to indicate successful update.
            12. If an SQLite error occurs during execution:
                12.1. Roll back the transaction to revert any changes.
                12.2. Log an error message with the details of the error.
                12.3. Return False to indicate failure.
            13. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not data:
            _DefaultLogger.error(f"SQLite database [{self._Name}] update data parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DefaultLogger.error(f"SQLite database [{self._Name}] update data parameter error: no encryptor provided.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] update data error: {e}")
            return False
        finally:
            self._disconnect()

    def updateDatas(self, table_name: str, data: List[Dict[str, str]], condition: str, encrypt_columns: List[str] = None) -> bool:
        """
        Updates multiple records in a specified table of the SQLite database based on the provided data and condition.

        :param table_name: A string representing the name of the table to update.
        :param data: A list of dictionaries where each dictionary contains column-value pairs for the update.
        :param condition: A string representing the SQL condition to identify which records to update.
        :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before updating (default is None).
        :return: A boolean indicating whether the update operation was successful (True) or not (False).
        setup:
            1. Check if the data list is empty:
                1.1. If it is empty, log an error and return False.
            2. Check if encryption is required:
                2.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
            3. Gather all unique column names from the provided data:
                3.1. Create a set to collect column names from each item in the data.
                3.2. Sort the collected column names for consistent ordering.
            4. Create a string of placeholders for the SQL UPDATE statement based on the collected column names.
            5. Initialize a list to hold the values for each update operation.
            6. Establish a connection to the database by calling the _connect method.
            7. Create a cursor object to execute SQL commands.
            8. Iterate over each item in the data:
                8.1. Retrieve the values for each column based on the collected column names.
                8.2. If encryption is required:
                    8.2.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
                8.3. Append the prepared item values to the all_data list as a tuple.
            9. Execute the UPDATE SQL command using the executemany method with the constructed placeholders and values.
            10. Commit the transaction to save changes.
            11. Close the cursor after execution.
            12. Return True to indicate successful update.
            13. If an SQLite error occurs during execution:
                13.1. Roll back the transaction to revert any changes.
                13.2. Log an error message with the details of the error.
                13.3. Return False to indicate failure.
            14. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not data:
            _DefaultLogger.error(f"SQLite database [{self._Name}] update datas parameter error: <data> is empty.")
            return False
        if encrypt_columns is not None and self._Encryptor is None:
            _DefaultLogger.error(f"SQLite database [{self._Name}] update datas parameter error: no encryptor provided.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] update data error: {e}")
            return False
        finally:
            self._disconnect()

    def selectData(self, table_name: str, columns: List[str], condition: str = None, dencrypt_columns: List[str] = None, order_by: str = None, limit: int = None) -> List[Dict[str, str]]:
        """
        Selects data from a specified table in the SQLite database, with options for filtering, ordering, and decryption.

        :param table_name: A string representing the name of the table from which to select data.
        :param columns: A list of strings representing the names of the columns to select.
        :param condition: An optional string representing the SQL condition to filter the results (default is None).
        :param dencrypt_columns: An optional list of strings representing the names of columns to decrypt (default is None).
        :param order_by: An optional string representing the column to order the results by (default is None).
        :param limit: An optional integer specifying the maximum number of records to return (default is None).
        :return: A list of dictionaries, each representing a row of the selected data, or an empty list if an error occurs.
        setup:
            1. Validate that the columns parameter is a list; if not, log an error and return an empty list.
            2. Convert the columns list to a string for the SQL query.
            3. Check if decryption is required:
                3.1. If dencrypt_columns is provided but no encryptor is available, log an error and return an empty list.
                3.2. Identify the indices of the columns that need to be decrypted.
            4. Establish a connection to the database by calling the _connect method.
            5. Create a cursor object to execute SQL commands.
            6. Construct the SQL SELECT query based on the provided parameters:
                6.1. Include the condition if specified.
                6.2. Include ordering if specified.
                6.3. Include a limit if specified, adding it to the query parameters.
            7. Execute the constructed query with the parameters.
            8. Fetch all results from the executed query.
            9. Process the fetched data:
                9.1. For each row, create a dictionary mapping column names to their values, decrypting values as needed.
            10. Close the cursor after execution.
            11. Return the list of processed results.
            12. If an SQLite error occurs during execution:
                12.1. Roll back the transaction.
                12.2. Log an error message with the details of the error.
                12.3. Return an empty list.
            13. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        if not isinstance(columns, list):
            _DefaultLogger.error(f"SQLite database [{self._Name}] select data parameter error: <columns> must be a list.")
            return []
        columns_str = ", ".join(columns)
        columns_list = columns
        if dencrypt_columns is not None and self._Encryptor is None:
            _DefaultLogger.error(f"SQLite database [{self._Name}] select data parameter error: no encryptor provided.")
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
            _DefaultLogger.error(f"SQLite database [{self._Name}] select data error: {e}")
            return []
        finally:
            self._disconnect()

    def deleteData(self, table_name: str, condition: str, condition_params: tuple = ()) -> bool:
        """
        Deletes data from a specified table in the SQLite database based on a given condition.

        :param table_name: A string representing the name of the table from which data will be deleted.
        :param condition: A string representing the SQL condition to filter which records to delete.
        :param condition_params: A tuple containing the parameters to bind to the SQL condition (default is an empty tuple).
        :return: A boolean indicating whether the deletion was successful (True) or not (False).
        setup:
            1. Establish a connection to the database by calling the _connect method.
            2. Create a cursor object to execute SQL commands.
            3. Execute a DELETE SQL statement using the provided table name and condition, binding the parameters.
            4. Commit the transaction to save changes.
            5. Close the cursor after execution.
            6. Return True to indicate successful deletion.
            7. If an SQLite error occurs during execution:
                7.1. Roll back the transaction to revert any changes made during the current operation.
                7.2. Log an error message with the details of the error.
                7.3. Return False to indicate failure.
            8. Ensure the database connection is closed by calling the _disconnect method in the finally block.
        """

        try:
            self._connect()
            cursor = self._Connection.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE {condition}", condition_params)
            self._Connection.commit()
            cursor.close()
            return True
        except sqlite3.Error as e:
            self._Connection.rollback()
            _DefaultLogger.error(f"SQLite database [{self._Name}] delete data error: {e}")
            return False
        finally:
            self._disconnect()

    def __del__(self):
        self._StayConnected = False
        self._disconnect()


# Define the MySQLDatabase class
try:
    # noinspection PyUnresolvedReferences
    import mysql.connector
    # noinspection PyUnresolvedReferences
    from mysql.connector import Error


    class MySQLDatabase:
        """
        Represents a MySQL database for managing data storage and operations.

        The class provides a structured interface for managing data storage and operations within a MySQL database.
        It supports fundamental database operations such as creating tables, inserting data, updating records, and querying information.
        This class also includes optional encryption and decryption for handling sensitive data.

        InstanceAttribute:
            _Name: The name of the database.
            _Host: The host address of the MySQL server.
            _User: The username for connecting to the MySQL database.
            _Password: The password for connecting to the MySQL database.
            _StayConnected: A flag indicating whether to maintain the database connection.
            _Connection: The MySQL database connection object.
            _Encryptor: An optional encryptor for handling sensitive data.

        Method:
            __init__: Initializes the MySQLDatabase instance and establishes a connection.
            name: Property to get the name of the database.
            _connect: Establishes a connection to the MySQL database.
            _disconnect: Closes the connection to the database.
            deleteDatabase: Deletes the database from the MySQL server.
            checkExistedTable: Checks if a specified table exists in the database.
            getExistedTables: Retrieves a list of all existing tables in the database.
            createTable: Creates a new table in the database if it doesn't already exist.
            createTables: Creates multiple tables in the database based on provided definitions.
            deleteTable: Deletes a specified table from the database.
            deleteTables: Deletes multiple tables from the database.
            insertData: Inserts a single record into a specified table, with optional encryption.
            insertDatas: Inserts multiple records into a specified table, with optional encryption.
            updateData: Updates a record in a specified table based on a condition.
            updateDatas: Updates multiple records in a specified table based on a condition.
            selectData: Retrieves records from a specified table, with optional decryption.
            deleteData: Deletes records from a specified table based on a condition.
            __del__: Destructor to ensure the database connection is closed upon deletion of the instance.
        """

        def __init__(self, name: str, host: str, user: str, password: str, stay_connected: bool = False, encryptor=None):
            self._Name = name
            self._Host = host
            self._User = user
            self._Password = password
            self._StayConnected = stay_connected
            self._Connection = None
            self._Encryptor = encryptor
            self._connect()
            DatabaseInstanceManager.registerMySQLDatabase(self._Name, self)

        @property
        def name(self):
            return self._Name

        def _connect(self) -> bool:
            """
            Establishes a connection to the MySQL database.

            :return: A boolean indicating whether the connection operation was successful (True) or not (False).
            setup:
                1. Check if the current connection (_Connection) is None:
                    1.1. If it is None, attempt to connect to the MySQL database using the provided host, user, password, and database name.
                    1.2. If the connection is successful, return True.
                2. If an error occurs during the connection attempt:
                    2.1. Log an error message with the details of the error.
                    2.2. Return False to indicate failure.
            """

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
                _DefaultLogger.error(f"MySQL database [{self._Name}] connection error : {e}")
                return False

        def _disconnect(self) -> bool:
            """
            Closes the connection to the MySQL database if it is currently open.

            :return: A boolean indicating whether the disconnect operation was successful (True) or not (False).
            setup:
                1. Check if there is an active connection (_Connection) and if the _StayConnected flag is False:
                    1.1. If both conditions are met, close the connection.
                    1.2. Set the _Connection attribute to None to indicate that there is no active connection.
                    1.3. Return True to indicate successful disconnection.
                2. If an error occurs during disconnection:
                    2.1. Log an error message with the details of the error.
                    2.2. Return False to indicate failure.
            """

            try:
                if self._Connection and not self._StayConnected:
                    self._Connection.close()
                    self._Connection = None
                    return True
            except Error as e:
                _DefaultLogger.error(f"MySQL database [{self._Name}] disconnect error : {e}")
                return False

        def deleteDatabase(self) -> bool:
            """
            Deletes the MySQL database.

            :return: A boolean indicating whether the delete operation was successful (True) or not (False).
            setup:
                1. Set the _StayConnected flag to False to indicate that the connection should be closed.
                2. Disconnect from the current database by calling the _disconnect method.
                3. Establish a new connection to the MySQL server using the provided host, user, and password.
                4. Create a cursor object to execute SQL commands.
                5. Execute the SQL command to drop the database with the specified name.
                6. Close the cursor and the connection after execution.
                7. Return True to indicate successful deletion of the database.
                8. If a database error occurs during execution:
                    8.1. Log an error message with the details of the error.
                    8.2. Return False to indicate failure.
                9. Ensure the instance of the database class is deleted by using del self in the finally block.
            """

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
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete error : {e}")
                return False
            finally:
                del self

        def checkExistedTable(self, table_name: str) -> bool:
            """
            Checks whether a specified table exists in the MySQL database.

            :param table_name: A string representing the name of the table to check.
            :return: A boolean indicating whether the table exists (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Establish a connection to the database by calling the _connect method.
                3. Create a cursor object to execute SQL commands.
                4. Execute the SQL command to check if the specified table exists using a LIKE clause.
                5. Fetch the result and determine if the table exists.
                6. Close the cursor after execution.
                7. Return True if the table exists, otherwise return False.
                8. If a database error occurs during execution:
                    8.1. Log an error message with the details of the error.
                    8.2. Return False to indicate failure.
                9. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] check existed table parameter error : <table_name> must be a string.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                exists = cursor.fetchone() is not None
                cursor.close()
                return exists
            except Error as e:
                _DefaultLogger.error(f"MySQL database [{self._Name}] check table existed error : {e}")
                return False
            finally:
                self._disconnect()

        def getExistedTables(self) -> List[str]:
            """
            Retrieves a list of existing table names in the MySQL database.

            :return: A list of strings representing the names of the tables in the database. If an error occurs, returns an empty list.
            setup:
                1. Establish a connection to the database by calling the _connect method.
                2. Create a cursor object to execute SQL commands.
                3. Execute the SQL command to show all tables in the database.
                4. Fetch all results and extract the table names into a list.
                5. Close the cursor after execution.
                6. Return the list of table names.
                7. If a database error occurs during execution:
                    7.1. Log an error message with the details of the error.
                    7.2. Return an empty list to indicate failure.
                8. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            try:
                self._connect()
                cursor = self._Connection.cursor()
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                cursor.close()
                return tables
            except Error as e:
                _DefaultLogger.error(f"MySQL database [{self._Name}] get existed tables error : {e}")
                return []
            finally:
                self._disconnect()

        def createTable(self, table_name: str, table_sql: str) -> bool:
            """
            Creates a single table in the MySQL database based on the provided name and SQL definition.

            :param table_name: A string representing the name of the table to create.
            :param table_sql: A string containing the SQL column definitions for the table.
            :return: A boolean indicating whether the create operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Validate that the provided table_sql parameter is a string:
                    2.1. If it is not a string, log an error and return False.
                3. Establish a connection to the database by calling the _connect method.
                4. Create a cursor object to execute SQL commands.
                5. Execute the CREATE TABLE command with the provided table name and SQL definition, using IF NOT EXISTS to avoid errors if the table already exists.
                6. Commit the transaction to save changes.
                7. Close the cursor after execution.
                8. Return True to indicate successful creation of the table.
                9. If a database error occurs during execution:
                    9.1. Roll back the transaction to revert any changes.
                    9.2. Log an error message with the details of the error.
                    9.3. Return False to indicate failure.
                10. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] create table parameter error : <table_name> must be non-empty strings.")
                return False
            if not isinstance(table_sql, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] create table parameter error : <table_sql> must be a string.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] create table error : {e}")
                return False
            finally:
                self._disconnect()

        def createTables(self, tables_dict: dict) -> bool:
            """
            Creates multiple tables in the MySQL database based on the provided definitions.

            :param tables_dict: A dictionary where each key is a string representing the name of the table to create,
                                and each value is a string containing the SQL column definitions for that table.
            :return: A boolean indicating whether the create operation was successful (True) or not (False).
            setup:
                1. Validate that the provided tables_dict parameter is a dictionary:
                    1.1. If it is not a dictionary, log an error and return False.
                2. Initialize a list to keep track of created tables.
                3. Establish a connection to the database by calling the _connect method.
                4. Create a cursor object to execute SQL commands.
                5. Iterate over each key-value pair in the tables_dict:
                    5.1. Check if both the table name and SQL definition are strings:
                        5.1.1. If not, log an error and skip to the next iteration.
                    5.2. Check if the table already exists by executing a SHOW TABLES command:
                        5.2.1. If the table does not exist, execute the CREATE TABLE command using the provided SQL definition.
                        5.2.2. Append the created table name to the created_tables list.
                        5.2.3. If the table already exists, log a debug message.
                6. Commit the transaction to save changes.
                7. Close the cursor after execution.
                8. If any tables were created, log a debug message listing the created tables.
                9. Return True to indicate successful creation of the tables.
                10. If a database error occurs during execution:
                    10.1. Roll back the transaction to revert any changes.
                    10.2. Log an error message with the details of the error.
                    10.3. Return False to indicate failure.
                11. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(tables_dict, dict):
                _DefaultLogger.error(f"MySQL database [{self._Name}] create tables parameter error : <tables_dict> must be a dictionary.")
                return False
            created_tables = []
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for table_name, table_sql in tables_dict.items():
                    if not isinstance(table_name, str) or not isinstance(table_sql, str):
                        _DefaultLogger.error(f"MySQL database [{self._Name}] invalid table definition for {table_name}.")
                        continue
                    cursor.execute(f"SHOW TABLES LIKE %s", (table_name,))
                    if cursor.fetchone() is None:
                        cursor.execute(f"CREATE TABLE {table_name} ({table_sql})")
                        created_tables.append(table_name)
                    else:
                        _DefaultLogger.debug(f"MySQL database [{self._Name}] table {table_name} already exists.")
                self._Connection.commit()
                cursor.close()
                if created_tables:
                    _DefaultLogger.debug(f"MySQL database [{self._Name}] created tables: {', '.join(created_tables)}")
                return True
            except Error as e:
                self._Connection.rollback()
                _DefaultLogger.error(f"MySQL database [{self._Name}] create tables error : {e}")
                return False
            finally:
                self._disconnect()

        def deleteTable(self, table_name: str) -> bool:
            """
            Deletes a specified table from the MySQL database.

            :param table_name: A string representing the name of the table to delete.
            :return: A boolean indicating whether the delete operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Establish a connection to the database by calling the _connect method.
                3. Create a cursor object to execute SQL commands.
                4. Execute the SQL command to drop the table if it exists.
                5. Commit the transaction to save changes.
                6. Close the cursor after execution.
                7. Return True to indicate successful deletion of the table.
                8. If a database error occurs during execution:
                    8.1. Roll back the transaction to revert any changes.
                    8.2. Log an error message with the details of the error.
                    8.3. Return False to indicate failure.
                9. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete table parameter error : <table_name> must be a string.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete table error : {e}")
                return False
            finally:
                self._disconnect()

        def deleteTables(self, tables: List[str]) -> bool:
            """
            Deletes multiple tables from the MySQL database based on the provided list of table names.

            :param tables: A list of strings representing the names of the tables to delete.
            :return: A boolean indicating whether the delete operation was successful (True) or not (False).
            setup:
                1. Validate that the provided tables parameter is a list:
                    1.1. If it is not a list, log an error and return False.
                2. Establish a connection to the database by calling the _connect method.
                3. Create a cursor object to execute SQL commands.
                4. Iterate over each table name in the provided list:
                    4.1. Check if the table name is a string:
                        4.1.1. If it is not a string, log an error and skip to the next iteration.
                    4.2. Execute the SQL command to drop the table if it exists.
                5. Commit the transaction to save changes.
                6. Close the cursor after execution.
                7. Return True to indicate successful deletion of the tables.
                8. If a database error occurs during execution:
                    8.1. Roll back the transaction to revert any changes.
                    8.2. Log an error message with the details of the error.
                    8.3. Return False to indicate failure.
                9. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(tables, list):
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete tables parameter error : <tables> must be a list.")
                return False
            try:
                self._connect()
                cursor = self._Connection.cursor()
                for table in tables:
                    if not isinstance(table, str):
                        _DefaultLogger.error(f"MySQL database [{self._Name}] invalid table name {table}.")
                        continue
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                self._Connection.commit()
                cursor.close()
                return True
            except Error as e:
                self._Connection.rollback()
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete tables error : {e}")
                return False
            finally:
                self._disconnect()

        def insertData(self, table_name: str, data: Dict[str, str], encrypt_columns: List[str] = None) -> bool:
            """
            Inserts a single record into a specified table of the MySQL database based on the provided data.

            :param table_name: A string representing the name of the table to insert data into.
            :param data: A dictionary containing column-value pairs for the insert.
            :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before inserting (default is None).
            :return: A boolean indicating whether the insert operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Check if the data dictionary is empty:
                    2.1. If it is empty, log an error and return False.
                3. Validate that the data parameter is a dictionary:
                    3.1. If it is not a dictionary, log an error and return False.
                4. Check if encryption is required:
                    4.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
                5. Establish a connection to the database by calling the _connect method.
                6. Create a cursor object to execute SQL commands.
                7. Create a string of columns and placeholders for the SQL INSERT statement based on the keys in the data dictionary.
                8. Prepare the item data as a tuple of values from the data dictionary.
                9. If encryption is required:
                    9.1. Encrypt the specified columns' values using the encryptor.
                10. Execute the INSERT SQL command using the constructed columns and item data.
                11. Commit the transaction to save changes.
                12. Close the cursor after execution.
                13. Return True to indicate successful insertion of data.
                14. If a database error occurs during execution:
                    14.1. Roll back the transaction to revert any changes.
                    14.2. Log an error message with the details of the error.
                    14.3. Return False to indicate failure.
                15. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert data parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert data parameter error : <data> is empty.")
                return False
            if not isinstance(data, dict):
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert data parameter error : <data> must be a dictionary.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert data parameter error : no encryptor provided.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert data error : {e}")
                return False
            finally:
                self._disconnect()

        def insertDatas(self, table_name: str, data: List[Dict[str, str]], encrypt_columns: List[str] = None) -> bool:
            """
            Inserts multiple records into a specified table of the MySQL database based on the provided data.

            :param table_name: A string representing the name of the table to insert data into.
            :param data: A list of dictionaries, where each dictionary contains column-value pairs for the insert.
            :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before inserting (default is None).
            :return: A boolean indicating whether the insert operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Check if the data list is empty:
                    2.1. If it is empty, log an error and return False.
                3. Check if encryption is required:
                    3.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
                4. Gather all unique column names from the provided data:
                    4.1. Create a set to collect column names from each item in the data.
                    4.2. Sort the collected column names for consistent ordering.
                5. Create a string of columns and placeholders for the SQL INSERT statement based on the collected column names.
                6. Initialize a list to hold the values for each insert operation.
                7. Establish a connection to the database by calling the _connect method.
                8. Create a cursor object to execute SQL commands.
                9. Iterate over each item in the data:
                    9.1. Retrieve the values for each column based on the collected column names.
                    9.2. If encryption is required:
                        9.2.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
                    9.3. Append the prepared item values to the all_data list as a tuple.
                10. Execute the INSERT SQL command using the executemany method with the constructed columns and values.
                11. Commit the transaction to save changes.
                12. Close the cursor after execution.
                13. Return True to indicate successful insertion of data.
                14. If a database error occurs during execution:
                    14.1. Roll back the transaction to revert any changes.
                    14.2. Log an error message with the details of the error.
                    14.3. Return False to indicate failure.
                15. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert datas parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert datas parameter error : <data> is empty.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert datas parameter error : no encryptor provided.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] insert datas error : {e}")
                return False
            finally:
                self._disconnect()

        def updateData(self, table_name: str, data: Dict[str, str], condition: str, encrypt_columns: List[str] = None) -> bool:
            """
            Updates a single record in a specified table of the MySQL database based on the provided data and condition.

            :param table_name: A string representing the name of the table to update.
            :param data: A dictionary containing column-value pairs for the update.
            :param condition: A string representing the SQL condition to identify which record to update.
            :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before updating (default is None).
            :return: A boolean indicating whether the update operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Check if the data dictionary is empty:
                    2.1. If it is empty, log an error and return False.
                3. Validate that the data parameter is a dictionary:
                    3.1. If it is not a dictionary, log an error and return False.
                4. Check if encryption is required:
                    4.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
                5. Establish a connection to the database by calling the _connect method.
                6. Create a cursor object to execute SQL commands.
                7. Create a string of SET clauses for the SQL UPDATE statement based on the keys in the data dictionary.
                8. Prepare the item data as a tuple of values from the data dictionary.
                9. If encryption is required:
                    9.1. Encrypt the specified columns' values using the encryptor.
                10. Execute the UPDATE SQL command using the constructed SET clauses and item data.
                11. Commit the transaction to save changes.
                12. Close the cursor after execution.
                13. Return True to indicate successful update.
                14. If a database error occurs during execution:
                    14.1. Roll back the transaction to revert any changes.
                    14.2. Log an error message with the details of the error.
                    14.3. Return False to indicate failure.
                15. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] update data parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DefaultLogger.error(f"MySQL database [{self._Name}] update data parameter error : <data> is empty.")
                return False
            if not isinstance(data, dict):
                _DefaultLogger.error(f"MySQL database [{self._Name}] update data parameter error : <data> must be a dictionary.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DefaultLogger.error(f"MySQL database [{self._Name}] update data parameter error : no encryptor provided.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] update data error : {e}")
                return False
            finally:
                self._disconnect()

        def updateDatas(self, table_name: str, data: List[Dict[str, str]], condition: str, encrypt_columns: List[str] = None) -> bool:
            """
            Updates multiple records in a specified table of the MySQL database based on the provided data and condition.

            :param table_name: A string representing the name of the table to update.
            :param data: A list of dictionaries, where each dictionary contains column-value pairs for the update.
            :param condition: A string representing the SQL condition to identify which records to update.
            :param encrypt_columns: An optional list of strings representing the names of columns to encrypt before updating (default is None).
            :return: A boolean indicating whether the update operation was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Check if the data list is empty:
                    2.1. If it is empty, log an error and return False.
                3. Check if encryption is required:
                    3.1. If encrypt_columns is provided but no encryptor is available, log an error and return False.
                4. Gather all unique column names from the provided data:
                    4.1. Create a set to collect column names from each item in the data.
                    4.2. Sort the collected column names for consistent ordering.
                5. Create a string of SET clauses for the SQL UPDATE statement based on the keys in the data dictionaries.
                6. Initialize a list to hold the values for each update operation.
                7. Establish a connection to the database by calling the _connect method.
                8. Create a cursor object to execute SQL commands.
                9. Iterate over each item in the data:
                    9.1. Retrieve the values for each column based on the collected column names.
                    9.2. If encryption is required:
                        9.2.1. Identify which columns need to be encrypted and encrypt their values using the encryptor.
                    9.3. Append the prepared item values to the all_data list as a tuple.
                10. Execute the UPDATE SQL command using the executemany method with the constructed SET clauses and values.
                11. Commit the transaction to save changes.
                12. Close the cursor after execution.
                13. Return True to indicate successful update.
                14. If a database error occurs during execution:
                    14.1. Roll back the transaction to revert any changes.
                    14.2. Log an error message with the details of the error.
                    14.3. Return False to indicate failure.
                15. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] update datas parameter error : <table_name> must be a string.")
                return False
            if not data:
                _DefaultLogger.error(f"MySQL database [{self._Name}] update datas parameter error : <data> is empty.")
                return False
            if encrypt_columns is not None and self._Encryptor is None:
                _DefaultLogger.error(f"MySQL database [{self._Name}] update datas parameter error : no encryptor provided.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] update datas error : {e}")
                return False
            finally:
                self._disconnect()

        def selectData(self, table_name: str, columns: List[str], condition: str = None, dencrypt_columns: List[str] = None) -> List[Dict[str, str]]:
            """
            Selects data from a specified table in the MySQL database with options for filtering and decryption.

            :param table_name: A string representing the name of the table from which to select data.
            :param columns: A list of strings representing the names of the columns to select.
            :param condition: An optional string representing the SQL condition to filter the results (default is None).
            :param dencrypt_columns: An optional list of strings representing the names of columns to decrypt after selection (default is None).
            :return: A list of dictionaries, each representing a row of the selected data, or an empty list if an error occurs.
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return an empty list.
                2. Validate that the provided columns parameter is a list:
                    2.1. If it is not a list, log an error and return an empty list.
                3. Check if decryption is required:
                    3.1. If dencrypt_columns is provided but no encryptor is available, log an error and return an empty list.
                4. Establish a connection to the database by calling the _connect method.
                5. Create a cursor object to execute SQL commands, specifying dictionary output for easy row handling.
                6. Construct the SQL SELECT query based on the provided parameters:
                    6.1. Include the condition if specified.
                7. Execute the constructed query.
                8. Fetch all results from the executed query.
                9. If decryption is required, iterate over the fetched results and decrypt specified columns using the encryptor.
                10. Close the cursor after execution.
                11. Return the list of processed results.
                12. If a database error occurs during execution:
                    12.1. Log an error message with the details of the error.
                    12.2. Return an empty list.
                13. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] select data parameter error : <table_name> must be a string.")
                return []
            if not isinstance(columns, list):
                _DefaultLogger.error(f"MySQL database [{self._Name}] select data parameter error : <columns> must be a list.")
                return []
            if dencrypt_columns is not None and self._Encryptor is None:
                _DefaultLogger.error(f"MySQL database [{self._Name}] select data parameter error : no encryptor provided.")
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
                _DefaultLogger.error(f"MySQL database [{self._Name}] select data error : {e}")
                return []
            finally:
                self._disconnect()

        def deleteData(self, table_name: str, condition: str) -> bool:
            """
            Deletes data from a specified table in the MySQL database based on a given condition.

            :param table_name: A string representing the name of the table from which data will be deleted.
            :param condition: A string representing the SQL condition to filter which records to delete.
            :return: A boolean indicating whether the deletion was successful (True) or not (False).
            setup:
                1. Validate that the provided table_name parameter is a string:
                    1.1. If it is not a string, log an error and return False.
                2. Establish a connection to the database by calling the _connect method.
                3. Create a cursor object to execute SQL commands.
                4. Execute a DELETE SQL statement using the provided table name and condition.
                5. Commit the transaction to save changes.
                6. Close the cursor after execution.
                7. Return True to indicate successful deletion.
                8. If a database error occurs during execution:
                    8.1. Roll back the transaction to revert any changes made during the current operation.
                    8.2. Print an error message with the details of the error.
                    8.3. Return False to indicate failure.
                9. Ensure the database connection is closed by calling the _disconnect method in the finally block.
            """

            if not isinstance(table_name, str):
                _DefaultLogger.error(f"MySQL database [{self._Name}] delete data parameter error : <table_name> must be a string.")
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

        def __del__(self):
            self._StayConnected = False
            self._disconnect()
except ImportError as _:
    class MySQLDatabase:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DefaultLogger.error(f"MySQLiteDatabase is not available. Please install mysql-connector-python package.")

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
