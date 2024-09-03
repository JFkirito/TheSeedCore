# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "NodeService"
]

import logging
import os
import subprocess
import threading
from typing import TYPE_CHECKING, Union

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger


def defaultLogger(debug_mode: bool = False) -> logging.Logger:
    """
    创建一个用于日志记录的 Logger 实例，提供控制台日志输出，并根据调试模式设置日志级别。

    参数：
        :param debug_mode: 布尔值，指示是否启用调试模式。默认为 False。调试模式下，日志级别设置为 DEBUG，否则设置为 WARNING 或更高。

    返回：
        :return - logging.Logger : 配置好的 Logger 实例，用于记录日志信息。

    执行过程：
        1. 创建一个新的 Logger 实例，名称为 'TheSeedCore - ExternalServices'。
        2. 设置 Logger 的日志级别为 DEBUG。
        3. 创建一个 StreamHandler，用于将日志输出到控制台。
        4. 根据 debug_mode 设置 StreamHandler 的日志级别。
        5. 创建一个自定义的日志格式化器，并将其应用于 StreamHandler。
        6. 将 StreamHandler 添加到 Logger 实例中。

    异常：
        1. 如果设置了无效的日志级别或格式化器，可能会导致日志无法正常输出。
    """

    logger = logging.getLogger(f'TheSeedCore - ExternalServices')
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


class NodeService:
    _INSTANCE = None

    def __new__(cls, DefaultInstallPath: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(NodeService, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, DefaultInstallPath: str, Logger: Union[TheSeedCoreLogger, logging.Logger], DebugMode: bool = False):
        self._DefaultInstallPath = DefaultInstallPath
        self._Logger = defaultLogger(DebugMode) if Logger is None else Logger
        self._InstallPackageSubProcess = None
        self._InstallPackageThread = None
        self._ServiceSubProcess = {}
        self._ServiceThread = {}
        self.IsClosed = False

    def installPackage(self, package_name: str, package_version: str = None, install_path: str = None, basic_logger=None):
        """
        安装指定的 npm 包，并支持设置版本、安装路径和自定义日志记录器。支持异步处理安装输出。

        参数：
            :param package_name: 要安装的 npm 包的名称。
            :param package_version: 要安装的 npm 包的版本。如果为 None，则安装最新版本。默认为 None。
            :param install_path: 安装路径。如果为 None，则使用默认安装路径。默认为 None。
            :param basic_logger: 用于记录日志的 Logger 实例。如果为 None，则使用类实例的默认 Logger。默认为 None。

        返回：
            无

        执行过程：
            1. 根据是否提供基本日志记录器选择使用默认 Logger 或提供的 Logger。
            2. 确定安装路径，如果未提供，则使用默认安装路径。
            3. 创建安装路径目录（如果不存在的话）。
            4. 确定包的版本，如果未提供，则默认为 "latest"。
            5. 构造安装命令，并通过 subprocess.Popen 启动安装进程。
            6. 启动一个线程处理安装过程的输出。
            7. 等待安装线程完成。
            8. 记录安装成功的日志信息。

        异常：
            1. 如果安装过程中发生异常，则记录错误信息。
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
            self._InstallPackageThread.join()
            logger.info(f"NodeService install package success : {package_name} has been installed")
        except Exception as e:
            logger.error(f"NodeService install {package_name} package error : {str(e)}")

    def startService(self, package_name: str, application: str, application_path: str = None, node_path: str = None, basic_logger=None, *args, **kwargs):
        """
        启动指定的 Node.js 服务进程，并支持设置应用程序路径、Node.js 路径以及自定义日志记录器。支持异步处理服务输出。

        参数：
            :param package_name: 要启动服务的 npm 包的名称。
            :param application: 要启动的 Node.js 应用程序的名称。
            :param application_path: 应用程序的路径。如果为 None，则使用默认安装路径。默认为 None。
            :param node_path: Node.js 的路径。如果为 None，则使用默认的 "node"。默认为 None。
            :param basic_logger: 用于记录日志的 Logger 实例。如果为 None，则使用类实例的默认 Logger。默认为 None。
            :param args: 传递给 subprocess.Popen 的额外位置参数。
            :param kwargs: 传递给 subprocess.Popen 的额外关键字参数。

        返回：
            无

        执行过程：
            1. 确定应用程序路径，如果未提供，则使用默认路径。
            2. 确定 Node.js 路径，如果未提供，则默认为 "node"。
            3. 启动一个 subprocess 进程来运行 Node.js 服务，并将其输出重定向到管道。
            4. 启动一个线程来处理服务进程的输出。

        异常：
            1. 如果启动服务过程中发生异常，则记录错误信息。
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
        停止指定的 Node.js 服务进程，并清理相关资源。

        参数：
            :param package_name: 要停止服务的 npm 包的名称。
            :param basic_logger: 用于记录日志的 Logger 实例。如果为 None，则使用类实例的默认 Logger。默认为 None。

        返回：
            无

        执行过程：
            1. 终止指定的服务进程。
            2. 等待服务线程结束。
            3. 从内部字典中移除服务进程和服务线程的记录。

        异常：
            1. 如果停止服务过程中发生异常，则记录错误信息。
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
        """
        停止所有正在运行的 Node.js 服务进程，并清理相关资源。

        参数：
            无

        返回：
            无

        执行过程：
            1. 终止所有在 `_ServiceSubProcess` 字典中记录的服务进程。
            2. 等待所有服务线程结束。
            3. 清空 `_ServiceSubProcess` 和 `_ServiceThread` 字典。
            4. 设置 `IsClosed` 为 `True`。

        异常：
            1. 如果在停止服务过程中发生异常，则记录错误信息。
        """

        try:
            if self._ServiceSubProcess:
                for package_name in self._ServiceSubProcess.keys():
                    self._ServiceSubProcess[package_name].terminate()
                    self._ServiceThread[package_name].join()
            self._ServiceSubProcess.clear()
            self._ServiceThread.clear()
            self.IsClosed = True
            self._Logger.debug("NodeService all services has been stopped.")
        except Exception as e:
            self._Logger.error(f"NodeService stop all service error : {str(e)}")

    @staticmethod
    def _checkNodeInstalled():
        """
        检查 Node.js 是否已安装在系统中。

        参数：
            无

        返回：
            bool: 如果 Node.js 已安装，返回 `True`；否则返回 `False`。

        执行过程：
            1. 使用 `subprocess.run` 执行 `node --version` 命令检查 Node.js 的版本。
            2. 如果命令成功执行（返回码为 0），则返回 `True`。
            3. 如果命令执行失败或文件未找到，则返回 `False`。

        异常：
            1. 如果系统无法找到 `node` 命令，会捕捉 `FileNotFoundError` 异常，并返回 `False`。
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
        处理并记录安装过程的输出。

        参数：
            basic_logger (logging.Logger, 可选): 自定义的日志记录器。如果为 `None`，则使用默认日志记录器。

        返回：
            无

        执行过程：
            1. 检查是否提供了自定义日志记录器，使用自定义日志记录器或默认日志记录器。
            2. 持续读取并记录安装进程的标准输出，直到进程结束。
            3. 捕捉并记录处理输出过程中出现的异常。
            4. 在安装输出线程结束时，关闭标准输出流，并将 `self._InstallPackageSubProcess` 设为 `None`。
            5. 将 `self._InstallPackageThread` 设为 `None`，并记录安装输出线程已关闭。

        异常：
            1. 捕捉并记录读取或处理输出时发生的异常。
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
        处理并记录服务进程的标准输出。

        参数：
            :param package_name: 服务的包名称，用于从 `_ServiceSubProcess` 中获取相应的进程。
            :param basic_logger: 自定义的日志记录器。如果为 `None`，则使用默认日志记录器。

        返回：
            无

        执行过程：
            1. 检查是否提供了自定义日志记录器，使用自定义日志记录器或默认日志记录器。
            2. 持续读取并记录指定服务进程的标准输出，直到进程结束。
            3. 捕捉并记录处理输出过程中出现的异常。
            4. 在服务输出线程结束时，关闭标准输出流，并将 `self._ServiceThread[package_name]` 设为 `None`。

        异常：
            1. 捕捉并记录读取或处理输出时发生的异常。
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
