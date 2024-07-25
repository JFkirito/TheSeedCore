# -*- coding: utf-8 -*-
"""TheSeedCore Config Module."""

from __future__ import annotations

__all__ = [
    "BASIC_SYSTEM_PATH",
    "EXTERNAL_LIBRARY",
    "LoggerConfig",
    "SQLiteDatabaseConfig",
    "MySQLDatabaseConfig",
    "RedisDatabaseConfig",
    "EncryptorConfig",
    "ConcurrencySystemConfig",
    "TheSeedCoreConfig"
]

import logging
import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, Literal

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger
    from .EncryptionModule import TheSeedCoreEncryptor

BASIC_SYSTEM_PATH = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTERNAL_LIBRARY = os.path.join(BASIC_SYSTEM_PATH, "ExternalLibrary")


@dataclass
class LoggerConfig:
    Name: str
    Path: str
    BackupCount: int
    Level: int
    Debug: bool

    def __post_init__(self):
        if not isinstance(self.Name, str):
            raise ValueError("The logger name must be a string.")
        if not isinstance(self.Path, str):
            raise ValueError("The logger path must be a string.")
        if not isinstance(self.BackupCount, int):
            raise ValueError("The logger backup count must be an integer.")
        if not isinstance(self.Level, int):
            raise ValueError("The logger level must be an integer.")
        if not isinstance(self.Debug, bool):
            raise ValueError("The logger debug mode must be a boolean.")


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
    Logger: Union[TheSeedCoreLogger, logging.Logger]
    Encryptor: TheSeedCoreEncryptor
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
    MySQL数据库配置。

    属性:
        - Host : MySQL主机地址。
        - Port : MySQL端口。
        - User : MySQL用户名。
        - Password : MySQL密码。
        - Database : 数据库名称。
        - Logger : 日志记录器。
    """
    Host: str
    Port: int
    User: str
    Password: str
    Database: str
    Logger: Union[TheSeedCoreLogger, logging.Logger]

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
    Redis数据库配置。

    属性:
        - Host : Redis主机地址。
        - Port : Redis端口。
        - Password : Redis密码。
        - Num : 数据库编号。
        - Logger : 日志记录器。
        - Encryptor : 加密器。
    """
    Host: str
    Port: int
    Password: str
    Num: int
    Logger: Union[TheSeedCoreLogger, logging.Logger]
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


@dataclass
class EncryptorConfig:
    """
    加密器配置。

    属性:
        - AESName : AES加密器的名称。
        - Logger : 日志记录器。
        - KeyringIdentifier : 密钥环标识符。
    """
    AESName: str
    Logger: Union[TheSeedCoreLogger, logging.Logger]
    KeyringIdentifier: Union[None, str]

    def __post_init__(self):
        if not isinstance(self.AESName, str):
            raise ValueError("The encryptor AES name must be a string.")
        if not isinstance(self.KeyringIdentifier, (str, type(None))):
            raise ValueError("The encryptor keyring identifier must be a string or None.")


@dataclass
class ConcurrencySystemConfig:
    """
    数据类：用于配置并发系统的参数。

    属性:
        - DebugMode: 调试模式。
        - CoreProcessCount: 核心进程数。
        - CoreThreadCount: 核心线程数。
        - MaximumProcessCount: 最大进程数。
        - MaximumThreadCount: 最大线程数。
        - TaskThreshold: 任务阈值，用于控制任务的处理和调度。
        - GlobalTaskThreshold: 全局任务阈值，用于整个系统的任务管理。
        - TaskRejectionPolicy: 任务拒绝策略，定义当任务超出处理能力时的行为。
        - RejectionPolicyTimeout: 任务拒绝策略的超时设置，用于某些拒绝策略的时间控制。
        - ExpandPolicy: 扩展策略，定义系统如何增加资源以处理更多任务。
        - ShrinkagePolicy: 收缩策略，定义系统如何减少资源以适应较低的任务负载。
        - ShrinkagePolicyTimeout: 收缩策略的超时设置，用于控制资源减少的时机。
    """
    DebugMode: bool
    CoreProcessCount: Union[None, int]
    CoreThreadCount: Union[None, int]
    MaximumProcessCount: Union[None, int]
    MaximumThreadCount: Union[None, int]
    TaskThreshold: Union[None, int]
    GlobalTaskThreshold: Union[None, int]
    TaskRejectionPolicy: Literal[None, "Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]
    RejectionPolicyTimeout: Union[None, int]
    ExpandPolicy: Literal[None, "NoExpand", "AutoExpand", "BeforehandExpand"]
    ShrinkagePolicy: Literal[None, "NoShrink", "AutoShrink", "TimeoutShrink"]
    ShrinkagePolicyTimeout: Union[None, int]

    def __post_init__(self):
        if self.CoreProcessCount is not None and not isinstance(self.CoreProcessCount, int):
            raise ValueError("The core process count must be an integer.")
        if self.CoreThreadCount is not None and not isinstance(self.CoreThreadCount, int):
            raise ValueError("The core thread count must be an integer.")
        if self.MaximumProcessCount is not None and not isinstance(self.MaximumProcessCount, int):
            raise ValueError("The maximum process count must be an integer.")
        if self.MaximumThreadCount is not None and not isinstance(self.MaximumThreadCount, int):
            raise ValueError("The maximum thread count must be an integer.")
        if self.TaskThreshold is not None and not isinstance(self.TaskThreshold, int):
            raise ValueError("The task threshold must be an integer.")
        if self.GlobalTaskThreshold is not None and not isinstance(self.GlobalTaskThreshold, int):
            raise ValueError("The global task threshold must be an integer.")
        if self.TaskRejectionPolicy not in [None, "Abandonment", "ExceptionAbandonment", "EarliestAbandonment", "CallerExecution", "TimeoutAbandonment"]:
            raise ValueError("The task rejection policy must be one of None, 'Abandonment', 'ExceptionAbandonment', 'EarliestAbandonment', 'CallerExecution', 'TimeoutAbandonment'.")
        if self.RejectionPolicyTimeout is not None and not isinstance(self.RejectionPolicyTimeout, int):
            raise ValueError("The rejection policy timeout must be an integer.")
        if self.ExpandPolicy not in [None, "NoExpand", "AutoExpand", "BeforehandExpand"]:
            raise ValueError("The expand policy must be one of None, 'NoExpand', 'AutoExpand', 'BeforehandExpand'.")
        if self.ShrinkagePolicy not in [None, "NoShrink", "AutoShrink", "TimeoutShrink"]:
            raise ValueError("The shrinkage policy must be one of None, 'NoShrink', 'AutoShrink', 'TimeoutShrink'.")
        if self.ShrinkagePolicyTimeout is not None and not isinstance(self.ShrinkagePolicyTimeout, int):
            raise ValueError("The shrinkage policy timeout must be an integer.")


@dataclass
class TheSeedCoreConfig:
    Application: type
    ConcurrencySystemConfig: ConcurrencySystemConfig
    BasicSystemPath: Union[None, str]
    BannerMode: Literal["Solid", "Gradient"]
    DebugMode: bool
    Args: Union[None, list, tuple]
    KwArgs: Union[None, dict]

    def __post_init__(self):
        if not isinstance(self.Application, type):
            raise ValueError("The application must be a class.")
        if self.BasicSystemPath is not None and not isinstance(self.BasicSystemPath, str):
            raise ValueError("The basic system path must be a string.")
        if self.BannerMode not in ["Solid", "Gradient"]:
            raise ValueError("The banner mode must be one of 'Solid' or 'Gradient'.")
        if not isinstance(self.DebugMode, bool):
            raise ValueError("The debug mode must be a boolean.")
        if self.Args is not None and not isinstance(self.Args, (list, tuple)):
            raise ValueError("The arguments must be a list or a tuple.")
        if self.KwArgs is not None and not isinstance(self.KwArgs, dict):
            raise ValueError("The keyword arguments must be a dictionary.")
