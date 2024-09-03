# -*- coding: utf-8 -*-
"""
TheSeedCore NetworkServiceModule

######################################################################################################################################
# This module provides networking services, including an HTTP server, WebSocket server,
# and WebSocket client. It is designed to handle asynchronous communication over the network,
# enabling real-time data exchange and interaction between clients and servers.

# Main functionalities:
# 1. HTTP server for handling HTTP requests and serving web content.
# 2. WebSocket server for managing real-time communication with multiple clients.
# 3. WebSocket client for connecting to WebSocket servers and exchanging messages.
# 4. Support for SSL/TLS encryption to secure WebSocket connections.
# 5. Integration with custom logging for monitoring network service operations.

# Main components:
# 1. HTTPServer - Manages an HTTP server capable of handling GET and POST requests.
# 2. WebSocketServer - Manages a WebSocket server that handles client connections and message processing.
# 3. WebSocketClient - A client that connects to WebSocket servers and manages communication.
# 4. defaultLogger - Provides custom logging functionality for network services.

# Design thoughts:
# 1. Asynchronous communication:
#    a. The module leverages asyncio to handle multiple concurrent network connections efficiently,
#       ensuring that servers and clients can process requests and messages without blocking.
#    b. The HTTPServer and WebSocketServer are designed to handle high volumes of requests by processing
#       each connection in an independent coroutine.
#
# 2. Real-time data exchange:
#    a. WebSocket support enables real-time, bidirectional communication between clients and servers,
#       making the module suitable for applications requiring live updates or interactions.
#    b. The WebSocketClient allows seamless integration with WebSocket servers, facilitating the
#       development of real-time applications.
#
# 3. Secure communication:
#    a. SSL/TLS encryption is supported for WebSocket connections, ensuring that data exchanged over
#       the network is secure and protected from interception.
#    b. The module uses Python's ssl library and certifi to manage SSL certificates and establish
#       secure connections.
#
# 4. Modular and extensible design:
#    a. The module is structured to allow easy customization and extension of its functionality.
#       Developers can add new routes to the HTTP server or modify the message processing logic
#       in the WebSocket server and client.
#    b. The use of callable processors in WebSocketServer and WebSocketClient enables dynamic handling
#       of messages, allowing developers to tailor the behavior to specific application needs.
#
# 5. Comprehensive logging and error handling:
#    a. The module integrates with a custom logging system to provide detailed logs of network service
#       activities, aiding in monitoring and debugging.
#    b. Extensive error handling is implemented to manage connection issues, message processing errors,
#       and other runtime exceptions, ensuring the robustness of network operations.

# Required dependencies:
# 1. Python libraries: asyncio, json, logging, socket, ssl, traceback, typing.
# 2. External libraries: aiohttp (for HTTP server), websockets (for WebSocket server and client), certifi (for SSL certificate management).
######################################################################################################################################
"""
from __future__ import annotations

__all__ = [
    "HTTPServer",
    "WebSocketServer",
    "WebSocketClient",
    "NetWorkServiceSupport"
]

import asyncio
import json
import logging
import socket
import ssl
import traceback
from typing import TYPE_CHECKING, Callable, Any, Coroutine, Literal, Union

from . import _ColoredFormatter

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger

NetWorkServiceSupport = False


def defaultLogger(service_type: Literal["HttpServer", "WebSocketServer", "WebSocketClient"], debug_mode: bool = False) -> logging.Logger:
    logger = logging.getLogger(f'TheSeedCore - {service_type}')
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


# Try defining the network service classes:
try:
    import certifi
    import websockets
    from aiohttp import web
except ImportError:
    class HTTPServer:
        # noinspection PyUnusedLocal
        def __init__(self, Host: str, Port: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            raise ImportError("The aiohttp is not installed. Please install it using 'pip install aiohttp'.")


    class WebSocketServer:
        # noinspection PyUnusedLocal
        def __init__(self, Host: str, Port: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, WebSocketProcessor: Callable[..., Coroutine[Any, Any, Any]] = None):
            raise ImportError("The websockets is not installed. Please install it using 'pip install websockets'.")


    class WebSocketClient:
        # noinspection PyUnusedLocal
        def __init__(self, ClientID, Url: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, ):
            raise ImportError("The websockets and certifi are not installed. Please install them using 'pip install websockets certifi'.")
else:
    NetWorkServiceSupport = True


    class HTTPServer:
        def __init__(self, Host: str, Port: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False):
            self._Logger = defaultLogger("HttpServer", DebugMode) if Logger is None else Logger
            self._Host = Host
            self._Port = Port
            self._HTTPApplication = web.Application()
            self._Runner = None
            self._TCPSite = None
            self._IsRunning = False
            self.IsClosed = False
            self._initRoute()

        def _initRoute(self):
            self._HTTPApplication.router.add_route("GET", "/", self._homeRequest)
            self._HTTPApplication.router.add_route("POST", "/change-address", self._addressChangedHandler)

        def checkRoute(self, method, path) -> bool:
            for route in self._HTTPApplication.router.routes():
                if route.method == method and route.resource.canonical == path:
                    return True
            return False

        def addRoute(self, method, path, processor):
            self._HTTPApplication.router.add_route(method, path, processor)

        def getHost(self) -> str:
            return self._Host

        def getPort(self) -> str:
            return self._Port

        def getServerAddress(self) -> str:
            return f"{self._Host}:{self._Port}"

        # noinspection PyUnusedLocal
        @staticmethod
        async def _homeRequest(request) -> web.Response:
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
            await self.startHTTPServer()
            if self._Host != host:
                self._Host = host
            if self._Port != port:
                self._Port = port
            await self.stopHTTPServer()

        async def startHTTPServer(self):
            try:
                if not self._IsRunning:
                    self._Runner = web.AppRunner(self._HTTPApplication)
                    await self._Runner.setup()
                    self._TCPSite = web.TCPSite(self._Runner, str(self._Host), int(self._Port))
                    await self._TCPSite.start()
                    self._IsRunning = True
                    self._Logger.debug(f"HTTP server started at {self._Host}:{self._Port}")
                else:
                    self._Logger.debug("HTTP server is already running")
            except Exception as e:
                self._Logger.error(f"HTTP server startup failed : {e}")

        async def stopHTTPServer(self):
            if self._IsRunning and self._Runner:
                try:
                    await self._Runner.cleanup()
                    await self._Runner.shutdown()
                finally:
                    self._IsRunning = False
                    self._HTTPApplication = web.Application()
                    self._Runner = None
            self._Logger.debug("HTTP server is turned off.")
            self.IsClosed = True

        async def _addressChangedHandler(self, request) -> web.Response:
            try:
                data = await request.json()
                new_host = data['new_host']
                new_port = data['new_port']
                await self.setAddress(new_host, new_port)
                # noinspection HttpUrlsUsage
                return web.Response(text=f"Address changed to http://{new_host}:{new_port}")
            except Exception as e:
                return web.Response(text=str(e), status=500)


    class WebSocketServer:
        def __init__(self, Host: str, Port: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, WebSocketProcessor: Callable[..., Coroutine[Any, Any, Any]] = None):
            self._Host = Host
            self._Port = Port
            self._Logger = defaultLogger("WebSocketServer", DebugMode) if Logger is None else Logger
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
            return self._Host

        def getPort(self) -> str:
            return self._Port

        def getServerAddress(self) -> str:
            return f"{self._Host}:{self._Port}"

        def getAllClients(self):
            return self._Clients

        async def startWebSocketServer(self):
            self._Server = await websockets.serve(self._wsProcessor, self._Host, int(self._Port), family=socket.AF_INET)
            self._Logger.debug(f"Started at {self._Host}:{self._Port}")

        async def stopWebSocketServer(self):
            if self._Server:
                self._Server.close()
                await self._Server.wait_closed()
            for ws in self._Clients.values():
                await ws.close()
            self._Logger.debug("Server is turned off.")
            self._Clients.clear()
            self.IsClosed = True

        async def sendMsg(self, client_id, message):
            client = self._Clients.get(client_id)
            if client:
                await client.send(message)
                self._Logger.debug(f"Sent message to {client_id}: {message}")
            else:
                self._Logger.error(f"No such client: {client_id}")

        async def broadcast(self, message):
            for client_id, client in self._Clients.items():
                try:
                    await client.send(message)
                except Exception as e:
                    self._Logger.error(f"Sending message to {client_id} error : {e}\n\n{traceback.format_exc()}")

        # noinspection PyUnusedLocal
        async def _wsProcessor(self, ws, path):
            client_id = None
            try:
                while True:
                    await asyncio.sleep(0.01)
                    msg = await ws.recv()
                    try:
                        json_msg = json.loads(msg)
                    except json.JSONDecodeError:
                        self._Logger.error("Failed to decode JSON message.")
                        await ws.close(reason="Invalid JSON format")
                        break

                    client_id = json_msg.get("ClientID")
                    if client_id is None:
                        self._cleanupClient(client_id, ws)
                        await ws.close(reason="Missing required parameter: ClientID")
                        self._Logger.error("Missing required parameter: ClientID, connection closed.")
                        break

                    msg_type = json_msg.get("type", "").lower()
                    if msg_type == "register":
                        await self._registerClient(client_id, ws)
                    elif msg_type == "unregister":
                        await self._unregisterClient(client_id, ws)
                    elif self._MsgProcessor is not None:
                        await self._MsgProcessor(json_msg)
                    self._Logger.info(f"Received message from {client_id}: {msg}")
            except websockets.ConnectionClosed as e:
                self._Logger.debug(f"Connection closed for {client_id}: {e.reason}")
            except Exception as e:
                self._cleanupClient(client_id, ws)
                await ws.close()
                self._Logger.error(f"Websocket processor error: {e}\n\n{traceback.format_exc()}")

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
            if client_id and client_id in self._Clients:
                self._unregisterClient(client_id, ws)
                self._Logger.debug(f"Cleaned up for {client_id}")


    class WebSocketClient:
        def __init__(self, ClientID, Url: str, Logger: Union[None, TheSeedCoreLogger, logging.Logger] = None, DebugMode: bool = False, ):
            self._ClientID = ClientID
            self._Logger = defaultLogger("WebSocketClient", DebugMode) if Logger is None else Logger
            self._Url = Url
            self._Connection = None
            self._IsConnected = False
            self._MsgQueue = asyncio.Queue()
            self._ReceiveHandler = None

        def setReceiveProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            self._ReceiveHandler = processor

        async def connect(self):
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            try:
                self._Connection = await websockets.connect(self._Url, ssl=ssl_context)
                self._IsConnected = True
                self._Logger.debug(f"{self._ClientID} connected to {self._Url}")
                await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "register"}))
                asyncio.ensure_future(self._sendMsgLoop())
                if self._ReceiveHandler:
                    asyncio.ensure_future(self._receiveMsgLoop())
            except Exception as e:
                self._Logger.error(f"{self._ClientID} connection failed: {e}")
                self._IsConnected = False

        async def disconnect(self):
            if self._Connection:
                self._IsConnected = False
                try:
                    await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "unregister"}))
                    await self._Connection.close()
                    await asyncio.wait_for(self._Connection.wait_closed(), timeout=10)
                except asyncio.TimeoutError:
                    self._Logger.error(f"{self._ClientID} close timeout")
                finally:
                    await self._Connection.close()
                    self._Connection = None

        async def sendMsg(self, msg):
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
                    self._Logger.debug(f"{self._ClientID} sent message: {msg}")
                except Exception as e:
                    self._Logger.error(f"{self._ClientID} send message failed: {e}")
                    await self._MsgQueue.put(msg)
                    await asyncio.sleep(1)

        async def _receiveMsgLoop(self):
            while self._IsConnected:
                await asyncio.sleep(0.01)
                try:
                    msg = await self._Connection.recv()
                    if self._ReceiveHandler:
                        await self._ReceiveHandler(msg)
                    self._Logger.debug(f"{self._ClientID} receive message: {msg}")
                except Exception as e:
                    self._Logger.error(f"{self._ClientID} receive message failed : {e}")
