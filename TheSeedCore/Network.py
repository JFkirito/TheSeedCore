# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import multiprocessing
import socket
import ssl
import threading
from typing import TYPE_CHECKING, Callable, Coroutine, Any, Optional, Literal, Dict

from . import DEVELOPMENT_ENV
from .Logger import consoleLogger
from ._Common import _checkPackage  # noqa

if TYPE_CHECKING:
    pass

__all__ = [
    "WebSocketServer",
    "WebSocketClient",
    "HTTPServer",
    "AsyncFlask",
    "AsyncFastAPI"
]

_DEFAULT_LOGGER = consoleLogger("Network")
_HTTP_SERVER = {}
_WEB_SOCKET_SERVER = {}

# Define the WebSocketServer and WebSocketClient classes
try:
    # noinspection PyUnresolvedReferences
    import certifi
    # noinspection PyUnresolvedReferences
    import websockets


    class WebSocketServer:
        def __init__(self, name: str, host: str, port: str, web_socket_processor: Callable[..., Coroutine[Any, Any, Any]] = None):
            self._Name = name
            self._Host = host
            self._Port = port
            self._Server = None
            self._MsgProcessor: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
            self._WsProcessor = web_socket_processor if web_socket_processor is not None else self._wsProcessor
            self._Clients = {}
            self.IsClosed = False
            _WEB_SOCKET_SERVER[name] = self

        @property
        def name(self) -> str:
            return self._Name

        @property
        def host(self) -> str:
            return self._Host

        @property
        def port(self) -> str:
            return self._Port

        @property
        def server_address(self) -> str:
            return f"{self._Host}:{self._Port}"

        @property
        def all_clients(self) -> dict:
            return self._Clients

        def setMsgProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            self._MsgProcessor = processor

        def setWsProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            self._WsProcessor = processor

        async def startWebSocketServer(self):
            try:
                self._Server = await websockets.serve(self._wsProcessor, self._Host, int(self._Port), family=socket.AF_INET)
                _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] started at {self.server_address}")
            except Exception as e:
                _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] start error: {e}")

        async def stopWebSocketServer(self):
            if self._Server:
                self._Server.close()
                await self._Server.wait_closed()
            for ws in self._Clients.values():
                await ws.close()
            self._Clients.clear()
            self.IsClosed = True
            _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] turned off.")

        async def sendMsg(self, client_id, message):
            client = self._Clients.get(client_id, None)
            if client is not None:
                try:
                    await client.send(message)
                    _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] sent message to {client_id}: {message}")
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] send message error: {e}")
            else:
                _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] send message error: No such client: {client_id}")

        async def broadcast(self, message):
            for client_id, client in self._Clients.items():
                try:
                    await client.send(message)
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] broadcast message to {client_id} error : {e}")

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
                        _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] failed to decode JSON message.")
                        await ws.close(reason="Invalid JSON format")
                        break

                    client_id = json_msg.get("ClientID")
                    if client_id is not None:
                        self._cleanupClient(client_id, ws)
                        await ws.close(reason=f"WebSocketServer [{self._Name}] missing required parameter: ClientID")
                        _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] missing required parameter: ClientID, connection closed.")
                        break

                    msg_type = json_msg.get("type", "").lower()
                    if msg_type == "register":
                        await self._registerClient(client_id, ws)
                    elif msg_type == "unregister":
                        await self._unregisterClient(client_id, ws)
                    elif self._MsgProcessor is not None:
                        await self._MsgProcessor(json_msg)
                    _DEFAULT_LOGGER.info(f"WebSocketServer [{self._Name}] received message from {client_id}: {msg}")
            except websockets.ConnectionClosed as e:
                _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] connection closed for {client_id}: {e.reason}")
            except Exception as e:
                self._cleanupClient(client_id, ws)
                await ws.close()
                _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] processor error: {e}")

        async def _registerClient(self, client_id, ws):
            if client_id in self._Clients:
                _DEFAULT_LOGGER.info(f"WebSocketServer [{self._Name}] client {client_id} already registered. Updating connection.")
                await ws.send(json.dumps({"type": "info", "message": "Already registered. Connection updated."}))
            else:
                _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] client {client_id} registered successfully.")
                await ws.send(json.dumps({"type": "info", "message": "Registered successfully."}))
            self._Clients[client_id] = ws

        async def _unregisterClient(self, client_id, ws):
            if client_id in self._Clients:
                del self._Clients[client_id]
                _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] client {client_id} unregistered successfully.")
                await ws.send(json.dumps({"type": "info", "message": "Unregistered successfully."}))
            else:
                _DEFAULT_LOGGER.error(f"WebSocketServer [{self._Name}] attempted to unregister non-existent client: {client_id}")
                await ws.send(json.dumps({"type": "error", "message": "Client not found. Unregister failed."}))

        def _cleanupClient(self, client_id, ws):
            if client_id and client_id in self._Clients:
                self._unregisterClient(client_id, ws)
                _DEFAULT_LOGGER.debug(f"WebSocketServer [{self._Name}] cleaned up for {client_id}")


    class WebSocketClient:
        def __init__(self, client_id, url: str):
            self._ClientID = client_id
            self._Url = url
            self._Connection = None
            self._IsConnected = False
            self._MsgQueue = asyncio.Queue()
            self._ReceiveHandler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None

        @property
        def client_id(self):
            return self._ClientID

        def setReceiveProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            self._ReceiveHandler = processor

        async def connect(self):
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            try:
                self._Connection = await websockets.connect(self._Url, ssl=ssl_context)
                self._IsConnected = True
                _DEFAULT_LOGGER.debug(f"WebSocketClient [{self._ClientID}] connected to {self._Url}")
                await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "register"}))
                asyncio.create_task(self._sendMsgLoop())
                if self._ReceiveHandler:
                    asyncio.create_task(self._receiveMsgLoop())
            except Exception as e:
                _DEFAULT_LOGGER.error(f"WebSocketClient [{self._ClientID}] connection failed: {e}")
                self._IsConnected = False

        async def disconnect(self):
            if self._Connection:
                self._IsConnected = False
                try:
                    await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "unregister"}))
                    await self._Connection.close()
                    await asyncio.wait_for(self._Connection.wait_closed(), timeout=10)
                except asyncio.TimeoutError:
                    _DEFAULT_LOGGER.error(f"WebSocketClient [{self._ClientID}] close timeout")
                finally:
                    await self._Connection.close()
                    self._Connection = None

        async def sendMsg(self, msg):
            if not self._IsConnected:
                await self.connect()
            await self._MsgQueue.put(msg)

        async def _sendMsgLoop(self):
            while self._IsConnected:
                if not self._IsConnected:
                    return
                await asyncio.sleep(0.001)
                msg = await self._MsgQueue.get()
                try:
                    await self._Connection.send(msg)
                    _DEFAULT_LOGGER.debug(f"WebSocketClient [{self._ClientID}] sent message: {msg}")
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"WebSocketClient [{self._ClientID}] send message failed: {e}")
                    await self._MsgQueue.put(msg)
                    await asyncio.sleep(1)

        async def _receiveMsgLoop(self):
            while self._IsConnected:
                if not self._IsConnected:
                    return
                await asyncio.sleep(0.001)
                try:
                    msg = await self._Connection.recv()
                    if self._ReceiveHandler:
                        await self._ReceiveHandler(msg)
                    _DEFAULT_LOGGER.debug(f"WebSocketClient [{self._ClientID}] receive message: {msg}")
                except Exception as e:
                    _DEFAULT_LOGGER.error(f"WebSocketClient [{self._ClientID}] receive message failed : {e}")
except ImportError as _:
    class WebSocketServer:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("WebSocketServer is not available. Please install certifi and websockets package.")

        @property
        def name(self) -> str:
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        @property
        def host(self) -> str:
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        @property
        def port(self) -> str:
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        @property
        def server_address(self) -> str:
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        @property
        def all_clients(self) -> dict:
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        def setMsgProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        def setWsProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        async def startWebSocketServer(self):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        async def stopWebSocketServer(self):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        async def sendMsg(self, client_id, message):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")

        async def broadcast(self, message):
            raise NotImplementedError("WebSocketServer is not available. Please install certifi and websockets package.")


    class WebSocketClient:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("WebSocketClient is not available. Please install certifi and websockets package.")

        @property
        def client_id(self):
            raise ImportError("WebSocketClient is not available. Please install certifi and websockets package.")

        def setReceiveProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            raise ImportError("WebSocketClient is not available. Please install certifi and websockets package.")

        async def connect(self):
            raise ImportError("WebSocketClient is not available. Please install certifi and websockets package.")

        async def disconnect(self):
            raise ImportError("WebSocketClient is not available. Please install certifi and websockets package.")

        async def sendMsg(self, msg):
            raise ImportError("WebSocketClient is not available. Please install certifi and websockets package.")

# Define the HTTPServer class
try:
    # noinspection PyUnresolvedReferences
    from aiohttp import web


    class HTTPServer:
        def __init__(self, name: str, host: str, port: str):
            self._Name = name
            self._Host = host
            self._Port = port
            self._HTTPApplication = web.Application()
            self._Runner = None
            self._TCPSite = None
            self._IsRunning = False
            self.IsClosed = False
            self._initRoute()
            _HTTP_SERVER[name] = self

        def _initRoute(self):
            self._HTTPApplication.router.add_route("GET", "/", self._homeRequest)
            self._HTTPApplication.router.add_route("POST", "/change-address", self._addressChangedHandler)

        @property
        def name(self):
            return self._Name

        @property
        def host(self) -> str:
            return self._Host

        @property
        def port(self) -> str:
            return self._Port

        @property
        def server_address(self) -> str:
            return f"{self._Host}:{self._Port}"

        def checkRoute(self, method: Literal["POST", "GET"], path: str) -> bool:
            for route in self._HTTPApplication.router.routes():
                if route.method == method and route.resource.canonical == path:
                    return True
            return False

        def addRoute(self, method: Literal["POST", "GET"], path: str, processor: Callable[..., Coroutine[Any, Any, Any]]):
            self._HTTPApplication.router.add_route(method, path, processor)

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
                    _DEFAULT_LOGGER.debug(f"HTTPServer [{self._Name}] started at {self.server_address}")
                else:
                    _DEFAULT_LOGGER.debug(f"HTTPServer [{self._Name}] is already running")
            except Exception as e:
                _DEFAULT_LOGGER.error(f"HTTPServer [{self._Name}] startup failed : {e}")

        async def stopHTTPServer(self):
            if self._IsRunning and self._Runner:
                try:
                    await self._Runner.cleanup()
                    await self._Runner.shutdown()
                finally:
                    self._IsRunning = False
                    self._HTTPApplication = web.Application()
                    self._Runner = None
            _DEFAULT_LOGGER.debug(f"HTTPServer [{self._Name}] turned off.")
            self.IsClosed = True

        # noinspection PyUnusedLocal
        @staticmethod
        async def _homeRequest(request) -> web.Response:
            html_content = """
                    <html>
                    <head><title>TheSeedCore</title></head>
                    <body style="text-align:center; padding-top:50px;">
                    <pre style="color:black;">
                     _       __          __                                     __            ______  __           _____                   __   ______                        
                    | |     / /  ___    / /  _____  ____    ____ ___   ___     / /_  ____    /_  __/ / /_   ___   / ___/  ___   ___   ____/ /  / ____/  ____    _____  ___    
                    | | /| / /  / _ \  / /  / ___/ / __ \  / __ `__ \ / _ \   / __/ / __ \    / /   / __ \ / _ \  \__ \  / _ \ / _ \ / __  /  / /      / __ \  / ___/ / _ \   
                    | |/ |/ /  /  __/ / /  / /__  / /_/ / / / / / / //  __/  / /_  / /_/ /   / /   / / / //  __/ ___/ / /  __//  __// /_/ /  / /___   / /_/ / / /    /  __/   
                    |__/|__/   \___/ /_/   \___/  \____/ /_/ /_/ /_/ \___/   \__/  \____/   /_/   /_/ /_/ \___/ /____/  \___/ \___/ \__,_/   \____/   \____/ /_/     \___/    
                    </pre>
                    </body>
                    </html>
                    """
            return web.Response(text=html_content, content_type="text/html")

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
except ImportError as _:
    class HTTPServer:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("HTTPServer is not available. Please install aiohttp package.")

        @property
        def name(self):
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        @property
        def host(self) -> str:
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        @property
        def port(self) -> str:
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        @property
        def server_address(self) -> str:
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        def checkRoute(self, method: Literal["POST", "GET"], path: str) -> bool:
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        def addRoute(self, method: Literal["POST", "GET"], path: str, processor: Callable[..., Coroutine[Any, Any, Any]]):
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        async def setAddress(self, host: str, port: str):
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        async def startHTTPServer(self):
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

        async def stopHTTPServer(self):
            raise NotImplementedError("HTTPServer is not available. Please install aiohttp package.")

# Define the AsyncFlask class
try:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from flask import Flask, redirect


    class AsyncFlask(threading.Thread):
        def __new__(cls, *args, **kwargs):
            if multiprocessing.current_process().name != "MainProcess":
                return None
            return super().__new__(cls)

        def __init__(self, name: str, host: str, port: int, **config):
            super().__init__(name=name, daemon=True)
            self._Name = name
            self._Host = host
            self._Port = port
            self._DevelopmentEnv = DEVELOPMENT_ENV
            self._ServerOptions = {k: v for k, v in config.items() if k in {
                'load_dotenv', 'use_debugger', 'use_evalex', 'threaded', 'processes',
                'passthrough_errors', 'ssl_context'
            }}
            self._WaitressOptions = {k: v for k, v in config.items() if k in {
                'url_scheme', 'ident', 'threads', 'backlog', 'recv_bytes', 'send_bytes',
                'outbuf_overflow', 'inbuf_overflow', 'connection_limit', 'cleanup_interval',
                'channel_timeout', 'log_socket_errors', 'max_request_header_size', 'max_request_body_size',
                'expose_tracebacks', 'asyncore_use_poll'
            }}
            self._Debug = config.get("debug", True)
            self.Application = Flask(
                name,
                static_url_path=config.get("static_url_path", None),
                static_folder=config.get("static_folder", "static"),
                static_host=config.get("static_host", None),
                host_matching=config.get("host_matching", False),
                subdomain_matching=config.get("subdomain_matching", False),
                template_folder=config.get("template_folder", "templates"),
                instance_path=config.get("instance_path", None),
                instance_relative_config=config.get("instance_relative_config", False),
                root_path=config.get("root_path", None),
            )
            self._defaultRoute()

        def setDevelopmentEnv(self, status: bool):
            self._DevelopmentEnv = status

        def run(self):
            valid_flask_options = {
                'load_dotenv', 'use_debugger', 'use_evalex', 'threaded', 'processes',
                'passthrough_errors', 'ssl_context'
            }

            valid_waitress_options = {
                'url_scheme', 'ident', 'threads', 'backlog', 'recv_bytes', 'send_bytes',
                'outbuf_overflow', 'inbuf_overflow', 'connection_limit', 'cleanup_interval',
                'channel_timeout', 'log_socket_errors', 'max_request_header_size',
                'max_request_body_size', 'expose_tracebacks', 'asyncore_use_poll'
            }
            self._ServerOptions = self._validateOptions(self._ServerOptions, valid_flask_options, "Flask")
            self._WaitressOptions = self._validateOptions(self._WaitressOptions, valid_waitress_options, "Waitress")

            try:
                if self._DevelopmentEnv:
                    self.Application.run(host=self._Host, port=self._Port, debug=self._Debug, use_reloader=False, **self._ServerOptions)
                elif _checkPackage("waitress"):
                    # noinspection PyUnresolvedReferences,PyPackageRequirements
                    from waitress import serve
                    serve(self.Application, host=self._Host, port=self._Port, **self._WaitressOptions)
                else:
                    _DEFAULT_LOGGER.warning(f"AsyncFlask[{self._Name}]The current environment is a production environment, but AsyncFlask[{self._Name}] is running in a development environment.")
                    self.Application.run(host=self._Host, port=self._Port, debug=self._Debug, use_reloader=False, **self._ServerOptions)
            except Exception as e:
                _DEFAULT_LOGGER.error(f"AsyncFlask[{self._Name}] Runtime error: {e}", exc_info=True)

        def _defaultRoute(self):
            @self.Application.route("/TheSeedCore")
            def _defaultRoute():
                return redirect("https://ns-cloud-backend.site")

        @staticmethod
        def _validateOptions(options: Dict[str, str], valid_options: set[str], server_name: str):
            invalid_options = [k for k in options if k not in valid_options]
            if invalid_options:
                _DEFAULT_LOGGER.warning(f"AsyncFlask{server_name} ignored invalid options: {invalid_options}")
            return {k: v for k, v in options.items() if k in valid_options}
except ImportError as _:
    class AsyncFlask:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("AsyncFlask is not available. Please install flask package.")
            self.Application = None

        def setDevelopmentEnv(self, status: bool):
            raise NotImplementedError("AsyncFlask is not available. Please install flask package.")

        def start(self):
            raise NotImplementedError("AsyncFlask is not available. Please install flask package.")

# Define the AsyncFastAPI class
try:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from fastapi import FastAPI
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from starlette.responses import RedirectResponse
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import uvicorn


    class AsyncFastAPI(threading.Thread):
        def __new__(cls, *args, **kwargs):
            if multiprocessing.current_process().name != "MainProcess":
                return None
            return super().__new__(cls)

        def __init__(self, name: str, host: str, port: int, **config):
            super().__init__(name=name, daemon=True)
            self._Name = name
            self._Host = host
            self._Port = port
            self._DevelopmentEnv = DEVELOPMENT_ENV
            self._ApplicationOptions = {k: v for k, v in config.items() if k in {
                "debug", "routes", "title", "summary", "description", "version", "openapi_url", "openapi_tags",
                "servers", "dependencies", "default_response_class", "redirect_slashes", "docs_url", "redoc_url",
                "swagger_ui_oauth2_redirect_url", "swagger_ui_init_oauth", "middleware", "exception_handlers",
                "on_startup", "on_shutdown", "lifespan", "terms_of_service", "openapi_prefix", "root_path", "root_path_in_servers",
                "responses", "callbacks", "webhooks", "deprecated", "include_in_schema", "swagger_ui_parameters",
                "generate_unique_id_function", "separate_input_output_schemas"
            }}
            self._UvicornOptions = {k: v for k, v in config.items() if k in {
                "uds", "fd", "loop", "http", "ws", "ws_max_size", "ws_max_queue", "ws_ping_interval", "ws_ping_timeout",
                "ws_per_message_deflate", "lifespan", "interface", "reload", "reload_dirs", "reload_includes", "reload_excludes",
                "reload_delay", "workers", "env_file", "log_config", "log_level", "access_log", "proxy_headers", "server_header",
                "date_header", "forwarded_allow_ips", "root_path", "limit_concurrency", "backlog", "limit_max_requests", "timeout_keep_alive",
                "timeout_graceful_shutdown", "ssl_keyfile", "ssl_certfile", "ssl_keyfile_password", "ssl_version", "ssl_cert_reqs", "ssl_ca_certs",
                "ssl_ciphers", "headers", "use_colors", "app_dir", "factory", "h11_max_incomplete_event_size"
            }}
            self.Application = FastAPI(**self._ApplicationOptions)
            self._defaultRoute()

        def _defaultRoute(self):
            @self.Application.get("/TheSeedCore")
            def _defaultRoute():
                return RedirectResponse("https://ns-cloud-backend.site")

        def run(self):
            uvicorn.run(self.Application, host=self._Host, port=self._Port, **self._UvicornOptions)
except ImportError as _:
    class AsyncFastAPI:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DEFAULT_LOGGER.warning("AsyncFastAPI is not available. Please install fastapi and uvicorn package.")

        def start(self):
            raise NotImplementedError("AsyncFastAPI is not available. Please install fastapi and uvicorn package.")


def _closeNetworkService():
    from Backup.Concurrent import submitThreadTask
    for http_server_instance in _HTTP_SERVER.values():
        submitThreadTask(http_server_instance.stopHTTPServer)
    for websocket_server_instance in _WEB_SOCKET_SERVER.values():
        submitThreadTask(websocket_server_instance.stopWebSocketServer)
    while True:
        if all([http_server_instance.IsClosed for http_server_instance in _HTTP_SERVER.values()]):
            break
    while True:
        if all([websocket_server_instance.IsClosed for websocket_server_instance in _WEB_SOCKET_SERVER.values()]):
            break
