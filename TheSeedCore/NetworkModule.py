# -*- coding: utf-8 -*-
"""
TheSeedCore Network Services Module

# This module delivers robust implementations for HTTP and WebSocket servers and clients, facilitating the development of network services
# that support high concurrency and real-time data exchange. It's designed to enable quick setup and management of network communications
# for various scenarios including API services and real-time interactive applications.

# Key Components:
# 1. HTTPServer: Utilizes the aiohttp framework to offer an HTTP server capable of route management, request handling, and dynamic content responses.
# 2. WebSocketServer: Provides WebSocket services, handling connections, and real-time messaging with clients.
# 3. WebSocketClient: Allows communication with WebSocket services, supporting message sending and reception.

# Module Functions:
# - Facilitates the creation and management of HTTP services, including serving static pages and handling API requests.
# - Manages WebSocket server operations such as starting/stopping the server, and handling client connections and messaging.
# - Enables WebSocket clients to connect to services, supporting bidirectional communication.
# - Highly customizable, allowing for the easy addition of new routes and service handlers to meet evolving needs.

# Usage Scenarios:
# - Suitable for deploying web services or APIs accessible locally or across networks.
# - Ideal for applications requiring real-time interactions, like chat applications or live data feeds.
# - Can function as either server or client in WebSocket communications, facilitating versatile network solutions.

# Dependencies:
# - aiohttp: Empowers the HTTP server component with asynchronous request handling capabilities.
# - websockets: Provides foundational server and client capabilities for WebSocket communications.
# - ssl: Ensures secure WebSocket connections.
# - asyncio: Essential for asynchronous operations, enhancing responsiveness and scalability of network services.
# - LoggerModule: Integrates logging functionality, crucial for monitoring and troubleshooting network activities.

"""

from __future__ import annotations

__all__ = [
    "HTTPServer",
    "WebSocketServer",
    "WebSocketClient"
]

import asyncio
import json
import socket
import ssl
import traceback
from typing import TYPE_CHECKING, Callable, Any, Coroutine

import certifi
import websockets
from aiohttp import web

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger


class HTTPServer:
    """
    TheSeedCore HTTP 服务器。

    参数:
        :param Host : 服务器主机地址。
        :param Port : 服务器端口号。
        :param Logger : 日志记录器。

    属性:
        _Logger : 日志记录器。
        _Host : 服务器主机地址。
        _Port : 服务器端口号。
        _HTTPApplication : aiohttp web 应用。
        _Runner : aiohttp 应用运行器。
        _IsRunning : 服务器运行状态标志。
        IsStopped : 服务器停止状态标志。
    """

    def __init__(self, Host: str, Port: str, Logger: TheSeedCoreLogger):
        self._Logger = Logger
        self._Host = Host
        self._Port = Port
        self._HTTPApplication = web.Application()
        self._Runner = None
        self._IsRunning = False
        self.IsClosed = False
        self._initRoute()

    def _initRoute(self):
        """初始化服务器路由。设置默认的路由处理函数。"""
        self._HTTPApplication.router.add_route("GET", "/", self._homeRequest)
        self._HTTPApplication.router.add_route("POST", "/change-address", self._addressChangedHandler)

    def checkRoute(self, method, path) -> bool:
        """
        检查指定的方法和路径是否已存在路由。

        参数:
            :param method : HTTP 方法（如 'GET', 'POST'）。
            :param path : 路由路径。

        返回:
            :return : 如果路由存在则返回 True，否则返回 False。
        """
        for route in self._HTTPApplication.router.routes():
            if route.method == method and route.resource.canonical == path:
                return True
        return False

    def addRoute(self, method, path, processor):
        """
        添加一个新的路由到服务器。

        参数:
            :param method : HTTP 方法。
            :param path : 路由路径。
            :param processor : 处理该路由的函数。
        """
        self._HTTPApplication.router.add_route(method, path, processor)

    def getHost(self) -> str:
        """
        获取服务器的主机地址。

        返回:
            :return : 服务器的主机地址。
        """
        return self._Host

    def getPort(self) -> str:
        """
        获取服务器的端口号。

        返回:
            :return : 服务器的端口号。
        """
        return self._Port

    def getServerAddress(self) -> str:
        """
        获取服务器的地址。

        返回:
            :return : 服务器的地址。
        """
        return f"{self._Host}:{self._Port}"

    @staticmethod
    async def _homeRequest(request) -> web.Response:
        """
        处理首页 GET 请求。

        参数:
            :param request : aiohttp 请求对象。

        返回:
            :return : 包含 HTML 内容的响应对象。
        """
        html_content = """
                <html>
                <head><title>TheSeedCore</title></head>
                <body style="text-align:center; padding-top:50px;">
                <pre style="color:black;">
                 _       __           __                                         __             ______   __               _____                        __
                | |     / /  ___     / /  _____   ____     ____ ___     ___     / /_   ____    /_  __/  / /_     ___     / ___/   ___     ___     ____/ /
                | | /| / /  / _ \   / /  / ___/  / __ \   / __ `__ \   / _ \   / __/  / __ \    / /    / __ \   / _ \    \__ \   / _ \   / _ \   / __  / 
                | |/ |/ /  /  __/  / /  / /__   / /_/ /  / / / / / /  /  __/  / /_   / /_/ /   / /    / / / /  /  __/   ___/ /  /  __/  /  __/  / /_/ /  
                |__/|__/   \___/  /_/   \___/   \____/  /_/ /_/ /_/   \___/   \__/   \____/   /_/    /_/ /_/   \___/   /____/   \___/   \___/   \__,_/  
                </pre>
                </body>
                </html>
                """
        return web.Response(text=html_content, content_type="text/html")

    async def setAddress(self, host: str, port: str):
        """
        设置服务器的新地址并重启服务。

        参数:
            :param host : 新的主机地址。
            :param port : 新的端口号。
        """
        await self.startHTTPServer()
        if self._Host != host:
            self._Host = host
        if self._Port != port:
            self._Port = port
        await self.stopHTTPServer()

    async def startHTTPServer(self):
        """
        启动 HTTP 服务器。

        异常:
            :exception 如果服务器启动失败，记录错误日志。
        """
        try:
            if not self._IsRunning:
                self._Runner = web.AppRunner(self._HTTPApplication)
                await self._Runner.setup()
                site = web.TCPSite(self._Runner, str(self._Host), int(self._Port))
                await site.start()
                self._IsRunning = True
                self._Logger.debug(f"HTTP server started at {self._Host}:{self._Port}")
            else:
                self._Logger.debug("HTTP server is already running")
        except Exception as e:
            self._Logger.error(f"HTTP server startup failed : {e}")

    async def stopHTTPServer(self):
        """停止 HTTP 服务器并清理资源。"""
        if self._IsRunning and self._Runner:
            try:
                await self._Runner.cleanup()
            finally:
                self._IsRunning = False
                self._HTTPApplication = web.Application()
                self._Runner = None
        self._Logger.debug("HTTP server is turned off.")
        self.IsClosed = True

    async def _addressChangedHandler(self, request) -> web.Response:
        """
        处理地址变更 POST 请求。

        参数:
            :param request : aiohttp 请求对象。

        返回:
            :return : 包含操作结果的响应对象。

        异常:
            :exception 如果处理请求过程中发生异常，返回错误信息。
        """
        try:
            data = await request.json()
            new_host = data['new_host']
            new_port = data['new_port']
            await self.setAddress(new_host, new_port)
            return web.Response(text=f"Address changed to http://{new_host}:{new_port}")
        except Exception as e:
            return web.Response(text=str(e), status=500)


class WebSocketServer:
    """
    TheSeedCore WebSocket服务器

    参数:
        :param Host : 服务器主机地址。
        :param Port : 服务器端口号。
        :param Logger : 日志记录器。
        :param WebSocketProcessor : WebSocket 连接处理函数。

    属性:
        _Host : 服务器主机地址。
        _Port : 服务器端口号。
        _Logger : 日志记录器。
        _Server : WebSocket 服务器实例。
        _WebSocketProcessor : WebSocket 连接处理函数。
        _MsgProcessor : 消息处理函数。
        _Clients : 当前连接的客户端列表。
    """

    def __init__(self, Host: str, Port: str, Logger: TheSeedCoreLogger, WebSocketProcessor: Callable[..., Coroutine[Any, Any, Any]] = None):
        self._Host = Host
        self._Port = Port
        self._Logger = Logger
        self._Server = None
        self._WsProcessor = WebSocketProcessor if WebSocketProcessor is not None else self._wsProcessor
        self._MsgProcessor = None
        self._Clients = {}
        self.IsClosed = False

    def setMsgProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
        self._MsgProcessor = processor

    def setWsProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
        self._WsProcessor = processor

    def getHost(self) -> str:
        """
        获取服务器的主机地址。

        返回:
            :return : 服务器的主机地址。
        """
        return self._Host

    def getPort(self) -> str:
        """
        获取服务器的端口号。

        返回:
            :return : 服务器的端口号。
        """
        return self._Port

    def getServerAddress(self) -> str:
        """
        获取服务器的地址。

        返回:
            :return : 服务器的地址。
        """
        return f"{self._Host}:{self._Port}"

    def getAllClients(self):
        """
        获取当前连接的客户端字典。

        返回:
            :return : 包含客户端名称和 WebSocket 连接实例的字典。
        """
        return self._Clients

    async def startWebSocketServer(self):
        """启动 WebSocket 服务器。"""
        self._Server = await websockets.serve(self._wsProcessor, self._Host, int(self._Port), family=socket.AF_INET)
        self._Logger.debug("WebSocketServer started at {}:{}".format(self._Host, self._Port))

    async def stopWebSocketServer(self):
        """停止 WebSocket 服务器并清理资源。"""
        if self._Server:
            self._Server.close()
            await self._Server.wait_closed()
        for ws in self._Clients.values():
            await ws.close()
        self._Logger.debug("WebSocket server is turned off.")
        self._Clients.clear()
        self.IsClosed = True

    async def sendMsg(self, client_id, message):
        """
        向指定的客户端发送消息。

        参数:
            :param client_id : 客户端标识。
            :param message : 消息内容。
        """
        client = self._Clients.get(client_id)
        if client:
            await client.send(message)
            self._Logger.debug(f"WebSocketServer Sent message to {client_id}: {message}")
        else:
            self._Logger.error(f"WebSocketServer No such client: {client_id}")

    async def broadcast(self, message):
        """
        向所有客户端广播消息。

        参数:
            :param message : 消息内容。
        """
        for client_id, client in self._Clients.items():
            try:
                await client.send(message)
            except Exception as e:
                self._Logger.error(f"WebSocketServer sending message to {client_id} error : {e}\n\n{traceback.format_exc()}")

    async def _wsProcessor(self, ws, path):
        client_id = None
        try:
            while True:
                await asyncio.sleep(0.01)
                msg = await ws.recv()
                try:
                    json_msg = json.loads(msg)
                except json.JSONDecodeError:
                    self._Logger.error("WebSocketServer failed to decode JSON message.")
                    await ws.close(reason="Invalid JSON format")
                    break

                client_id = json_msg.get("ClientID")
                if client_id is None:
                    self._cleanupClient(client_id, ws)
                    await ws.close(reason="Missing required parameter: ClientID")
                    self._Logger.error("WebSocketServer missing required parameter: ClientID, connection closed.")
                    break

                msg_type = json_msg.get("type", "").lower()
                if msg_type == "register":
                    await self._registerClient(client_id, ws)
                elif msg_type == "unregister":
                    await self._unregisterClient(client_id, ws)
                elif self._MsgProcessor is not None:
                    await self._MsgProcessor(json_msg)
                self._Logger.info(f"WebSocketServer received message from {client_id}: {msg}")
        except websockets.ConnectionClosed as e:
            self._Logger.debug(f"WebSocketServer connection closed for {client_id}: {e.reason}")
        except Exception as e:
            error_msg = f"WebSocketServer websocket processor error: {e}\n\n{traceback.format_exc()}"
            self._cleanupClient(client_id, ws)
            await ws.close()
            self._Logger.error(error_msg)

    async def _registerClient(self, client_id, ws):
        if client_id in self._Clients:
            self._Logger.info(f"Client {client_id} already registered. Updating connection.")
            await ws.send(json.dumps({"type": "info", "message": "Already registered. Connection updated."}))
        else:
            self._Logger.debug(f"Client {client_id} registered successfully.")
            await ws.send(json.dumps({"type": "info", "message": "Registered successfully."}))
        self._Clients[client_id] = ws

    async def _unregisterClient(self, client_id, ws):
        if client_id in self._Clients:
            del self._Clients[client_id]
            self._Logger.debug(f"Client {client_id} unregistered successfully.")
            await ws.send(json.dumps({"type": "info", "message": "Unregistered successfully."}))
        else:
            self._Logger.error(f"Attempted to unregister non-existent client: {client_id}")
            await ws.send(json.dumps({"type": "error", "message": "Client not found. Unregister failed."}))

    def _cleanupClient(self, client_id, ws):
        """如果客户端已注册，注销并关闭其WebSocket连接"""
        if client_id and client_id in self._Clients:
            self._unregisterClient(client_id, ws)
            self._Logger.debug(f"WebSocketServer cleaned up for {client_id}")


class WebSocketClient:
    """
    TheSeedCore WebSocket 客户端

    参数:
        :param ClientID : 客户端标识。
        :param Logger : 日志记录器。
        :param Url : WebSocket 服务器地址。

    属性:
        _ClientID : 客户端标识。
        _Logger : 日志记录器。
        _Url : WebSocket 服务器地址。
        _Connection : WebSocket 连接实例。
        _IsConnected : 连接状态标志。
        _MsgQueue : 发送消息队列。
        _ReceiveHandler : 消息接收处理函数。
    """

    def __init__(self, ClientID, Logger: TheSeedCoreLogger, Url: str):
        self._ClientID = ClientID
        self._Logger = Logger
        self._Url = Url
        self._Connection = None
        self._IsConnected = False
        self._MsgQueue = asyncio.Queue()
        self._ReceiveHandler = None

    def setReceiveProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
        """
        设置消息接收处理函数。

        参数:
            :param processor : 处理接收到的消息的函数。
        """
        self._ReceiveHandler = processor

    async def connect(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            self._Connection = await websockets.connect(self._Url, ssl=ssl_context)
            self._IsConnected = True
            self._Logger.debug(f"WebSocketClient {self._ClientID} connected to {self._Url}")
            await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "register"}))
            asyncio.ensure_future(self._sendMsgLoop())
            if self._ReceiveHandler:
                asyncio.ensure_future(self._receiveMsgLoop())
        except Exception as e:
            self._Logger.error(f"WebSocketClient {self._ClientID} connection failed: {e}")
            self._IsConnected = False

    async def disconnect(self):
        if self._Connection:
            self._IsConnected = False
            try:
                await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "unregister"}))
                await self._Connection.close()
                await asyncio.wait_for(self._Connection.wait_closed(), timeout=10)
            except asyncio.TimeoutError:
                self._Logger.error(f"WebSocketClient {self._ClientID} close timeout")
            finally:
                await self._Connection.close()
                self._Connection = None

    async def sendMsg(self, msg):
        """将消息加入发送队列。"""
        if not self._IsConnected:
            await self.connect()
        await self._MsgQueue.put(msg)

    async def _sendMsgLoop(self):
        while self._IsConnected:
            await asyncio.sleep(0.01)
            msg = await self._MsgQueue.get()
            if not self._IsConnected:
                return
            try:
                await self._Connection.send(msg)
                self._Logger.debug(f"WebSocketClient {self._ClientID} sent message: {msg}")
            except Exception as e:
                self._Logger.error(f"WebSocketClient {self._ClientID} send message failed: {e}")
                await self._MsgQueue.put(msg)
                await asyncio.sleep(1)

    async def _receiveMsgLoop(self):
        """循环接收消息并调用接收处理函数。"""
        while self._IsConnected:
            await asyncio.sleep(0.01)
            try:
                msg = await self._Connection.recv()
                if self._ReceiveHandler:
                    await self._ReceiveHandler(msg)
                self._Logger.debug(f"WebSocketClient {self._ClientID} receive message: {msg}")
            except Exception as e:
                self._Logger.error(f"WebSocketClient {self._ClientID} receive message failed : {e}")
