# -*- coding: utf-8 -*-
"""
TheSeed External Services Module


# This module specializes in managing and operating external services, with a focus on Node.js-related functionalities.
# It offers tools for installing Node.js packages and managing Node.js application services, making it ideal for environments
# that require integration with Node.js, such as launching Node.js-based API services or managing Node.js tools and libraries.

# Key Components:
# 1. NodeService: Manages the installation of Node.js packages and the starting/stopping of Node.js application services.
#    It performs service operations asynchronously using subprocesses and threads, and includes integrated logging for tracking operations.

# Module Functions:
# - Installs Node.js packages to a specified path.
# - Starts and stops Node.js application services, allowing for concurrent operations.
# - Automatically logs detailed information about all operations, including outputs from installations and service activities.
# - Checks the local installation status of Node.js, ensuring system readiness for Node.js operations.

# Usage Scenarios:
# - Integrating Node.js package management within Python applications.
# - Controlling backend services written in Node.js through a Python interface.
# - Monitoring and logging the operational status of Node.js services within a system.

# Dependencies:
# - subprocess: Handles the creation and management of subprocesses for executing Node.js commands.
# - threading: Enables parallel thread execution, allowing the main application to operate without interruption.
# - os: Manages file and directory operations, essential for handling installation paths.
# - LoggerModule: Provides logging functionalities, crucial for operation tracking and auditing.

"""

from __future__ import annotations

__all__ = ["NodeService"]

import os
import subprocess
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger


class NodeService:
    """
    TheSeed NodeService 管理 Node.js 包的安装和服务的启动和停止。

    参数:
        :param DefaultInstallPath : 默认的 Node.js 包安装路径。
        :param Logger : 用于记录日志的对象。

    属性:
        - _INSTANCE : 单例实例。
        - _DefaultInstallPath : 默认的 Node.js 包安装路径。
        - _TaskManager : TheSeed 任务管理器。
        - _Logger : 用于记录日志的对象。
        - _InstallPackageSubProcess : 安装包的子进程。
        - _InstallPackageThread : 安装包的线程。
        - _ServiceSubProcess : 服务的子进程。
        - _ServiceThread : 服务的线程。
    """
    _INSTANCE = None

    def __new__(cls, DefaultInstallPath: str, Logger: TheSeedCoreLogger):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(NodeService, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, DefaultInstallPath: str, Logger: TheSeedCoreLogger):
        self._DefaultInstallPath = DefaultInstallPath
        self._Logger = Logger
        self._InstallPackageSubProcess = None
        self._InstallPackageThread = None
        self._ServiceSubProcess = {}
        self._ServiceThread = {}
        self.IsClosed = False

    def installPackage(self, package_name: str, package_version: str = None, install_path: str = None, basic_logger=None):
        """
        执行 Node.js 包的安装过程。

        参数:
            :param package_name : 要安装的包名。
            :param package_version : 包的版本。
            :param install_path : 安装路径。
            :param basic_logger : 用于记录安装过程的日志对象。
        """
        if basic_logger is None:
            logger = self._Logger
        else:
            logger = basic_logger
        try:
            if install_path is None:
                _basic_path = self._DefaultInstallPath
            else:
                _basic_path = install_path
            _path = os.path.join(_basic_path, package_name)
            if not os.path.exists(_basic_path):
                os.makedirs(_basic_path)
            if package_version is None:
                _basic_version = "latest"
            else:
                _basic_version = str(package_version)
            command = f"npm.cmd install {package_name}@{_basic_version}"
            self._InstallPackageSubProcess = subprocess.Popen(
                command,
                cwd=_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
            )
            self._InstallPackageThread = threading.Thread(target=self._installOutput)
            self._InstallPackageThread.start()
            logger.info(f"NodeService install package success : {package_name} has been installed")
            self._InstallPackageThread.join()
        except Exception as e:
            logger.error(f"NodeService install {package_name} package error : {str(e)}")

    def startService(self, package_name: str, application: str, application_path: str = None, node_path: str = None, basic_logger=None, *args, **kwargs):
        """
        启动指定的 Node.js 应用服务。

        参数:
            :param package_name : 包名。
            :param application : 应用名称。
            :param application_path : 应用的具体路径。
            :param node_path : Node.js的执行路径。
            :param basic_logger : 日志记录器。
        """
        try:
            if application_path is None:
                _app_path = os.path.join(self._DefaultInstallPath, package_name, "node_modules", package_name, application)
            else:
                _app_path = os.path.join(application_path, application)
            if node_path is None:
                _node_path = "node"
            else:
                _node_path = node_path
            self._ServiceSubProcess[package_name] = subprocess.Popen(
                [_node_path, _app_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                *args,
                **kwargs
            )
            self._ServiceThread[package_name] = threading.Thread(target=self._serviceOutput, args=(package_name, basic_logger))
            self._ServiceThread[package_name].start()
        except Exception as e:
            self._Logger.error(f"NodeService start {package_name} service error : {str(e)}")

    def stopService(self, package_name: str, basic_logger=None):
        """
        停止指定的 Node.js 服务。

        参数:
            :param package_name : 包名。
            :param basic_logger : 日志记录器。
        """
        if basic_logger is None:
            logger = self._Logger
        else:
            logger = basic_logger
        try:
            self._ServiceSubProcess[package_name].terminate()
            self._ServiceThread[package_name].join()
            self._ServiceSubProcess.pop(package_name)
            self._ServiceThread.pop(package_name)
            logger.info(f"NodeService {package_name} service has been stopped")
        except Exception as e:
            logger.error(f"NodeService stop {package_name} service error : {str(e)}")

    def stopAllNodeService(self):
        """停止所有的 Node.js 服务。"""
        try:
            if self._ServiceSubProcess:
                for package_name in self._ServiceSubProcess.keys():
                    self._ServiceSubProcess[package_name].terminate()
                    self._ServiceThread[package_name].join()
            self._ServiceSubProcess.clear()
            self._ServiceThread.clear()
            self.IsClosed = True
            self._Logger.info("NodeService stop all service success : all services have been stopped")
        except Exception as e:
            self._Logger.error(f"NodeService stop all service error : {str(e)}")

    @staticmethod
    def _checkNodeInstalled():
        """
        检查系统中是否已安装 Node.js。

        返回:
            :return : 如果已安装 Node.js，则返回 True，否则返回 False。
        """
        try:
            result = subprocess.run(["node", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                return True
            else:
                return False
        except FileNotFoundError:
            return False

    def _installOutput(self, basic_logger=None):
        """
        监听和记录安装过程中的输出。

        参数:
            :param basic_logger : 用于记录安装输出的日志对象，如果未提供，则使用默认日志记录器。
        """
        if basic_logger is None:
            logger = self._Logger
        else:
            logger = basic_logger
        try:
            while self._InstallPackageSubProcess and self._InstallPackageSubProcess.poll() is None:
                line = self._InstallPackageSubProcess.stdout.readline()
                if line:
                    logger.info(line.strip())
        except Exception as e:
            logger.error(f"install output thread error : {str(e)}")
        finally:
            if self._InstallPackageSubProcess:
                self._InstallPackageSubProcess.stdout.close()
                self._InstallPackageSubProcess = None
            logger.info("install output thread has been closed")
            self._InstallPackageThread = None

    def _serviceOutput(self, package_name: str, basic_logger=None):
        """
        处理和记录服务运行时的输出。

        参数:
            :param package_name : 包名。
            :param basic_logger : 日志记录器。
        """
        if basic_logger is None:
            logger = self._Logger
        else:
            logger = basic_logger
        try:
            while self._ServiceSubProcess[package_name] and self._ServiceSubProcess[package_name].poll() is None:
                line = self._ServiceSubProcess[package_name].stdout.readline()
                if line:
                    logger.info(line.strip())
        except Exception as e:
            logger.error(f"NodeService {package_name} service output thread error : {str(e)}")
        finally:
            if self._ServiceSubProcess[package_name]:
                self._ServiceSubProcess[package_name].stdout.close()
            logger.info(f"NodeService {package_name} service output thread has been closed")
            self._ServiceThread[package_name] = None
