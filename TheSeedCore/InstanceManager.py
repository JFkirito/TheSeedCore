# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "DatabaseInstanceManager",
    "NetworkInstanceManager",
]

from typing import TYPE_CHECKING, Dict, Optional

from .Logger import consoleLogger

if TYPE_CHECKING:
    from .Database import SQLiteDatabase, MySQLDatabase
    from .Network import HTTPServer, WebSocketServer, WebSocketClient

_DefaultLogger = consoleLogger("InstanceManager")


class DatabaseInstanceManager:
    """
    Manages instances of SQLite and MySQL databases, allowing for registration, unregistration, and retrieval.

    The class is responsible for managing multiple instances of SQLite and MySQL databases.
    It provides methods to register, unregister, and retrieve database instances,
    allowing centralized control and easy access to multiple databases in a system.

    ClassAttribute:
        _SQLiteDatabaseInstances: A dictionary holding registered SQLiteDatabase instances.
        _MySQLDatabaseInstances: A dictionary holding registered MySQLDatabase instances.

    Method:
        registerSQLiteDatabase: Registers a new SQLiteDatabase instance.
        unregisterSQLiteDatabase: Unregisters an existing SQLiteDatabase instance.
        getSQLiteDatabaseInstance: Retrieves a specific SQLiteDatabase instance by name.
        getAllSQLiteDatabaseInstances: Returns all registered SQLiteDatabase instances.
        registerMySQLDatabase: Registers a new MySQLDatabase instance.
        unregisterMySQLDatabase: Unregisters an existing MySQLDatabase instance.
        getMySQLDatabaseInstance: Retrieves a specific MySQLDatabase instance by name.
        getAllMySQLDatabaseInstances: Returns all registered MySQLDatabase instances.
    """

    _SQLiteDatabaseInstances: Dict[str, SQLiteDatabase] = {}
    _MySQLDatabaseInstances: Dict[str, MySQLDatabase] = {}

    @classmethod
    def registerSQLiteDatabase(cls, name: str, instance: SQLiteDatabase):
        """
        Registers a new SQLiteDatabase instance under a specified name.

        :param name: A string representing the name under which to register the SQLiteDatabase instance.
        :param instance: An instance of SQLiteDatabase to be registered.
        setup:
            1. Check if the provided name already exists in the class variable _SQLiteDatabaseInstances:
                1.1. If the name exists, log a warning message indicating that the instance already exists and return.
            2. If the name does not exist, add the provided instance to the _SQLiteDatabaseInstances dictionary using the specified name as the key.
        """

        if name in cls._SQLiteDatabaseInstances:
            _DefaultLogger.warning(f"SQLiteDatabase instance {name} already exists.")
            return
        cls._SQLiteDatabaseInstances[name] = instance

    @classmethod
    def unregisterSQLiteDatabase(cls, name: str):
        """
        Unregisters a SQLiteDatabase instance by its name, removing it from the list of available instances.

        :param name: A string representing the name of the SQLiteDatabase instance to unregister.
        setup:
            1. Check if the provided name exists in the class variable _SQLiteDatabaseInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return.
            2. If the instance exists, remove it from the _SQLiteDatabaseInstances dictionary using the pop method.
        """

        if name not in cls._SQLiteDatabaseInstances:
            _DefaultLogger.warning(f"SQLiteDatabase instance {name} does not exist.")
            return
        cls._SQLiteDatabaseInstances.pop(name)

    @classmethod
    def getSQLiteDatabaseInstance(cls, name: str) -> Optional[SQLiteDatabase]:
        """
        Retrieves a specific instance of SQLiteDatabase by its name.

        :param name: A string representing the name of the SQLiteDatabase instance to retrieve.
        :return: The SQLiteDatabase instance associated with the given name, or None if the instance does not exist.
        setup:
            1. Check if the provided name exists in the class variable _SQLiteDatabaseInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return None.
            2. If the instance exists, return the corresponding SQLiteDatabase instance from the _SQLiteDatabaseInstances dictionary.
        """

        if name not in cls._SQLiteDatabaseInstances:
            _DefaultLogger.warning(f"SQLiteDatabase instance {name} does not exist.")
            return None
        return cls._SQLiteDatabaseInstances[name]

    @classmethod
    def getAllSQLiteDatabaseInstances(cls) -> Dict[str, SQLiteDatabase]:
        """
        Retrieves all instances of SQLiteDatabase currently available.

        :return: A dictionary where the keys are the names of the databases and the values are the corresponding SQLiteDatabase instances.
        setup:
            1. Access the class variable _SQLiteDatabaseInstances, which holds all SQLiteDatabase instances.
            2. Return this dictionary to provide access to all instances.
        """

        return cls._SQLiteDatabaseInstances

    @classmethod
    def registerMySQLDatabase(cls, name: str, instance: MySQLDatabase):
        """
        Registers a new MySQLDatabase instance under a specified name.

        :param name: A string representing the name under which to register the MySQLDatabase instance.
        :param instance: An instance of MySQLDatabase to be registered.
        setup:
            1. Check if the provided name already exists in the class variable _MySQLDatabaseInstances:
                1.1. If the name exists, log a warning message indicating that the instance already exists and return.
            2. If the name does not exist, add the provided instance to the _MySQLDatabaseInstances dictionary using the specified name as the key.
        """

        if name in cls._MySQLDatabaseInstances:
            _DefaultLogger.warning(f"MySQLDatabase instance {name} already exists.")
            return
        cls._MySQLDatabaseInstances[name] = instance

    @classmethod
    def unregisterMySQLDatabase(cls, name: str):
        """
        Unregisters a MySQLDatabase instance by its name, removing it from the list of available instances.

        :param name: A string representing the name of the MySQLDatabase instance to unregister.
        setup:
            1. Check if the provided name exists in the class variable _MySQLDatabaseInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return.
            2. If the instance exists, remove it from the _MySQLDatabaseInstances dictionary using the pop method.
        """

        if name not in cls._MySQLDatabaseInstances:
            _DefaultLogger.warning(f"MySQLDatabase instance {name} does not exist.")
            return
        cls._MySQLDatabaseInstances.pop(name)

    @classmethod
    def getMySQLDatabaseInstance(cls, name: str) -> Optional[MySQLDatabase]:
        """
        Retrieves a specific instance of MySQLDatabase by its name.

        :param name: A string representing the name of the MySQLDatabase instance to retrieve.
        :return: The MySQLDatabase instance associated with the given name, or None if the instance does not exist.
        setup:
            1. Check if the provided name exists in the class variable _MySQLDatabaseInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return None.
            2. If the instance exists, return the corresponding MySQLDatabase instance from the _MySQLDatabaseInstances dictionary.
        """

        if name not in cls._MySQLDatabaseInstances:
            _DefaultLogger.warning(f"MySQLDatabase instance {name} does not exist.")
            return None
        return cls._MySQLDatabaseInstances[name]

    @classmethod
    def getAllMySQLDatabaseInstances(cls) -> Dict[str, MySQLDatabase]:
        """
        Retrieves all instances of MySQLDatabase currently available.

        :return: A dictionary where the keys are the names of the databases and the values are the corresponding MySQLDatabase instances.
        setup:
            1. Access the class variable _MySQLDatabaseInstances, which holds all MySQLDatabase instances.
            2. Return this dictionary to provide access to all instances.
        """

        return cls._MySQLDatabaseInstances


class NetworkInstanceManager:
    """
    Manages instances of HTTP and WebSocket servers and clients, allowing for registration, unregistration, and retrieval.

    The class provides centralized management of HTTP and WebSocket server and client instances.
    It allows for the registration, unregistration, and retrieval of instances,
    making it easy to organize and access various server and client components within a system.

    Class Attributes:
        _HTTPServerInstances: A dictionary holding registered HTTPServer instances.
        _WebSocketServerInstances: A dictionary holding registered WebSocketServer instances.
        _WebSocketClientInstances: A dictionary holding registered WebSocketClient instances.

    Methods:
        registerHTTPServer: Registers a new HTTPServer instance.
        unregisterHTTPServer: Unregisters an existing HTTPServer instance.
        getHTTPServerInstance: Retrieves a specific HTTPServer instance by name.
        getAllHTTPServerInstances: Returns all registered HTTPServer instances.
        registerWebSocketServer: Registers a new WebSocketServer instance.
        unregisterWebSocketServer: Unregisters an existing WebSocketServer instance.
        getWebSocketServerInstance: Retrieves a specific WebSocketServer instance by name.
        getAllWebSocketServerInstances: Returns all registered WebSocketServer instances.
        registerWebSocketClient: Registers a new WebSocketClient instance.
        unregisterWebSocketClient: Unregisters an existing WebSocketClient instance.
        getWebSocketClientInstance: Retrieves a specific WebSocketClient instance by name.
        getAllWebSocketClientInstances: Returns all registered WebSocketClient instances.
    """

    _HTTPServerInstances: Dict[str, HTTPServer] = {}
    _WebSocketServerInstances: Dict[str, WebSocketServer] = {}
    _WebSocketClientInstances: Dict[str, WebSocketClient] = {}

    @classmethod
    def registerHTTPServer(cls, name: str, instance: HTTPServer):
        """
        Registers a new HTTPServer instance under a specified name.

        :param name: A string representing the name under which to register the HTTPServer instance.
        :param instance: An instance of HTTPServer to be registered.
        setup:
            1. Check if the provided name already exists in the class variable _HTTPServerInstances:
                1.1. If the name exists, log a warning message indicating that the instance already exists and return.
            2. If the name does not exist, add the provided instance to the _HTTPServerInstances dictionary using the specified name as the key.
        """

        if name in cls._HTTPServerInstances:
            _DefaultLogger.warning(f"HTTPServer instance {name} already exists.")
            return
        cls._HTTPServerInstances[name] = instance

    @classmethod
    def unregisterHTTPServer(cls, name: str):
        """
        Unregisters an HTTPServer instance by its name, removing it from the list of available instances.

        :param name: A string representing the name of the HTTPServer instance to unregister.
        setup:
            1. Check if the provided name exists in the class variable _HTTPServerInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return.
            2. If the instance exists, remove it from the _HTTPServerInstances dictionary using the pop method.
        """

        if name not in cls._HTTPServerInstances:
            _DefaultLogger.warning(f"HTTPServer instance {name} does not exist.")
            return
        cls._HTTPServerInstances.pop(name)

    @classmethod
    def getHTTPServerInstance(cls, name: str) -> Optional[HTTPServer]:
        """
        Retrieves a specific instance of HTTPServer by its name.

        :param name: A string representing the name of the HTTPServer instance to retrieve.
        :return: The HTTPServer instance associated with the given name, or None if the instance does not exist.
        setup:
            1. Check if the provided name exists in the class variable _HTTPServerInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return None.
            2. If the instance exists, return the corresponding HTTPServer instance from the _HTTPServerInstances dictionary.
        """

        if name not in cls._HTTPServerInstances:
            _DefaultLogger.warning(f"HTTPServer instance {name} does not exist.")
            return None
        return cls._HTTPServerInstances[name]

    @classmethod
    def getAllHTTPServerInstances(cls) -> Dict[str, HTTPServer]:
        """
        Retrieves all instances of HTTPServer currently available.

        :return: A dictionary where the keys are the names of the HTTP servers and the values are the corresponding HTTPServer instances.
        setup:
            1. Access the class variable _HTTPServerInstances, which holds all HTTPServer instances.
            2. Return this dictionary to provide access to all instances.
        """

        return cls._HTTPServerInstances

    @classmethod
    def registerWebSocketServer(cls, name: str, instance: WebSocketServer):
        """
        Registers a new WebSocketServer instance under a specified name.

        :param name: A string representing the name under which to register the WebSocketServer instance.
        :param instance: An instance of WebSocketServer to be registered.
        setup:
            1. Check if the provided name already exists in the class variable _WebSocketServerInstances:
                1.1. If the name exists, log a warning message indicating that the instance already exists and return.
            2. If the name does not exist, add the provided instance to the _WebSocketServerInstances dictionary using the specified name as the key.
        """

        if name in cls._WebSocketServerInstances:
            _DefaultLogger.warning(f"WebSocketServer instance {name} already exists.")
            return
        cls._WebSocketServerInstances[name] = instance

    @classmethod
    def unregisterWebSocketServer(cls, name: str):
        """
        Unregisters a WebSocketServer instance by its name, removing it from the list of available instances.

        :param name: A string representing the name of the WebSocketServer instance to unregister.
        setup:
            1. Check if the provided name exists in the class variable _WebSocketServerInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return.
            2. If the instance exists, remove it from the _WebSocketServerInstances dictionary using the pop method.
        """

        if name not in cls._WebSocketServerInstances:
            _DefaultLogger.warning(f"WebSocketServer instance {name} does not exist.")
            return
        cls._WebSocketServerInstances.pop(name)

    @classmethod
    def getWebSocketServerInstance(cls, name: str) -> Optional[WebSocketServer]:
        """
        Retrieves a specific instance of WebSocketServer by its name.

        :param name: A string representing the name of the WebSocketServer instance to retrieve.
        :return: The WebSocketServer instance associated with the given name, or None if the instance does not exist.
        setup:
            1. Check if the provided name exists in the class variable _WebSocketServerInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return None.
            2. If the instance exists, return the corresponding WebSocketServer instance from the _WebSocketServerInstances dictionary.
        """

        if name not in cls._WebSocketServerInstances:
            _DefaultLogger.warning(f"WebSocketServer instance {name} does not exist.")
            return None
        return cls._WebSocketServerInstances[name]

    @classmethod
    def getAllWebSocketServerInstances(cls) -> Dict[str, WebSocketServer]:
        """
        Retrieves all instances of WebSocketServer currently available.

        :return: A dictionary where the keys are the names of the WebSocket servers and the values are the corresponding WebSocketServer instances.
        setup:
            1. Access the class variable _WebSocketServerInstances, which holds all WebSocketServer instances.
            2. Return this dictionary to provide access to all instances.
        """

        return cls._WebSocketServerInstances

    @classmethod
    def registerWebSocketClient(cls, name: str, instance: WebSocketClient):
        """
        Registers a new WebSocketClient instance under a specified name.

        :param name: A string representing the name under which to register the WebSocketClient instance.
        :param instance: An instance of WebSocketClient to be registered.
        setup:
            1. Check if the provided name already exists in the class variable _WebSocketClientInstances:
                1.1. If the name exists, log a warning message indicating that the instance already exists and return.
            2. If the name does not exist, add the provided instance to the _WebSocketClientInstances dictionary using the specified name as the key.
        """

        if name in cls._WebSocketClientInstances:
            _DefaultLogger.warning(f"WebSocketClient instance {name} already exists.")
            return
        cls._WebSocketClientInstances[name] = instance

    @classmethod
    def unregisterWebSocketClient(cls, name: str):
        """
        Unregisters a WebSocketClient instance by its name, removing it from the list of available instances.

        :param name: A string representing the name of the WebSocketClient instance to unregister.
        setup:
            1. Check if the provided name exists in the class variable _WebSocketClientInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return.
            2. If the instance exists, remove it from the _WebSocketClientInstances dictionary using the pop method.
        """

        if name not in cls._WebSocketClientInstances:
            _DefaultLogger.warning(f"WebSocketClient instance {name} does not exist.")
            return
        cls._WebSocketClientInstances.pop(name)

    @classmethod
    def getWebSocketClientInstance(cls, name: str) -> Optional[WebSocketClient]:
        """
        Retrieves a specific instance of WebSocketClient by its name.

        :param name: A string representing the name of the WebSocketClient instance to retrieve.
        :return: The WebSocketClient instance associated with the given name, or None if the instance does not exist.
        setup:
            1. Check if the provided name exists in the class variable _WebSocketClientInstances:
                1.1. If the name does not exist, log a warning message indicating that the instance does not exist and return None.
            2. If the instance exists, return the corresponding WebSocketClient instance from the _WebSocketClientInstances dictionary.
        """

        if name not in cls._WebSocketClientInstances:
            _DefaultLogger.warning(f"WebSocketClient instance {name} does not exist.")
            return None
        return cls._WebSocketClientInstances[name]

    @classmethod
    def getAllWebSocketClientInstances(cls) -> Dict[str, WebSocketClient]:
        """
        Retrieves all instances of WebSocketClient currently available.

        :return: A dictionary where the keys are the names of the WebSocket clients and the values are the corresponding WebSocketClient instances.
        setup:
            1. Access the class variable _WebSocketClientInstances, which holds all WebSocketClient instances.
            2. Return this dictionary to provide access to all instances.
        """

        return cls._WebSocketClientInstances


class ViewsInstanceManager:
    ...
