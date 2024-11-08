# -*- coding: utf-8 -*-
from __future__ import annotations

__all__ = [
    "WebSocketServer",
    "WebSocketClient",
    "HTTPServer"
]

import asyncio
import json
import socket
import ssl
from typing import TYPE_CHECKING, Callable, Coroutine, Any, Optional, Literal

from .InstanceManager import NetworkInstanceManager
from .Logger import consoleLogger

if TYPE_CHECKING:
    pass

_DefaultLogger = consoleLogger("Network")
try:
    # noinspection PyUnresolvedReferences
    import certifi
    # noinspection PyUnresolvedReferences
    import websockets


    class WebSocketServer:
        """
        WebSocketServer class for managing WebSocket server operations and client connections.

        The class manages WebSocket server operations, including handling client connections, receiving and broadcasting messages, and managing server lifecycle events.
        It provides methods for configuring message processing, managing connected clients, and broadcasting data to all or individual clients.

        ClassAttributes:
            _Name: Name of the WebSocket server.
            _Host: Host address for the server.
            _Port: Port number for the server.
            _Server: Active WebSocket server instance.
            _MsgProcessor: Optional callback function for processing incoming messages.
            _WsProcessor: WebSocket processor for handling WebSocket events.
            _Clients: Dictionary holding connected clients.
            IsClosed: Flag indicating whether the server is closed.

        InstanceAttributes:
            name: The name of the WebSocket server.
            host: The host address of the WebSocket server.
            port: The port number of the WebSocket server.
            server_address: The combined host and port address of the server.
            all_clients: A dictionary of all connected clients.

        Methods:
            setMsgProcessor: Sets the callback function for processing incoming messages.
            setWsProcessor: Sets the WebSocket processor function for handling WebSocket events.
            startWebSocketServer: Starts the WebSocket server and listens for connections.
            stopWebSocketServer: Stops the WebSocket server and disconnects all clients.
            sendMsg: Sends a message to a specific client.
            broadcast: Sends a message to all connected clients.
            _wsProcessor: Handles incoming WebSocket connections and messages.
            _registerClient: Registers a new client connection.
            _unregisterClient: Unregisters a client connection.
            _cleanupClient: Cleans up resources associated with a disconnected client.
        """

        def __init__(self, name: str, host: str, port: str, web_socket_processor: Callable[..., Coroutine[Any, Any, Any]] = None):
            self._Name = name
            self._Host = host
            self._Port = port
            self._Server = None
            self._MsgProcessor: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
            self._WsProcessor = web_socket_processor if web_socket_processor is not None else self._wsProcessor
            self._Clients = {}
            self.IsClosed = False

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
            """
            Sets the message processor function to handle incoming messages from connected clients.

            This method allows the user to define a custom processing function that will be called
            whenever a message is received from a client.

            :param processor: A callable that takes the received message as input and returns a coroutine.
            :return: None
            :raise: None

            setup:
                1. Assign the provided processor function to the internal _MsgProcessor attribute.
                2. Ensure that the processor is a callable that can handle client messages.
            """

            self._MsgProcessor = processor

        def setWsProcessor(self, processor: Callable[..., Coroutine[Any, Any, Any]]):
            """
            Sets the WebSocket processor function to handle incoming WebSocket messages.

            This method allows the user to define a custom processing function that will be called
            whenever a message is received by the WebSocket server.

            :param processor: A callable that takes the received message as input and returns a coroutine.
            :return: None
            :raise: None

            setup:
                1. Assign the provided processor function to the internal _WsProcessor attribute.
                2. Ensure that the processor is a callable that can handle WebSocket messages.
            """

            self._WsProcessor = processor

        async def startWebSocketServer(self):
            """
            Starts the WebSocket server and begins listening for incoming connections.

            This asynchronous method performs the following actions:
            1. Attempts to create and start a WebSocket server that listens on the specified host and port.
            2. Calls the _wsProcessor method to handle incoming WebSocket connections.
            3. Logs a debug message indicating that the server has successfully started and displays the server address.

            :return: None
            :raise: None

            setup:
                1. Attempt to start the WebSocket server using the websockets.serve method.
                    1.1. Specify the handler (_wsProcessor) to manage incoming messages and connections.
                    1.2. Use the provided host and port for the server.
                    1.3. Set the family to socket.AF_INET for IPv4 connections.
                2. If successful, log a debug message with the server address.
                3. If an error occurs during server startup, log the error message.
            """

            try:
                self._Server = await websockets.serve(self._wsProcessor, self._Host, int(self._Port), family=socket.AF_INET)
                _DefaultLogger.debug(f"WebSocketServer [{self._Name}] started at {self.server_address}")
            except Exception as e:
                _DefaultLogger.error(f"WebSocketServer [{self._Name}] start error: {e}")

        async def stopWebSocketServer(self):
            """
            Stops the WebSocket server and closes all active client connections.

            This asynchronous method performs the following actions:
            1. Closes the WebSocket server if it is currently running.
            2. Waits for the server to fully close.
            3. Iterates through all connected clients and closes their connections.
            4. Clears the list of clients.
            5. Marks the server as closed and logs a debug message indicating that the server has been turned off.

            :return: None
            :raise: None

            setup:
                1. Check if the server instance exists and is running.
                    1.1. If running, close the server and wait for it to close.
                2. Iterate through the _Clients dictionary:
                    2.1. Close each client's WebSocket connection.
                3. Clear the _Clients dictionary to remove all references to clients.
                4. Set the IsClosed attribute to True to indicate that the server is no longer active.
                5. Log a debug message indicating that the WebSocket server has been turned off.
            """

            if self._Server:
                self._Server.close()
                await self._Server.wait_closed()
            for ws in self._Clients.values():
                await ws.close()
            self._Clients.clear()
            self.IsClosed = True
            _DefaultLogger.debug(f"WebSocketServer [{self._Name}] turned off.")

        async def sendMsg(self, client_id, message):
            """
            Sends a message to a specific WebSocket client identified by client_id.

            This asynchronous method checks if the specified client is connected. If the client exists, it attempts to send the provided message.
            If the message is sent successfully, it logs a debug message. If any error occurs during the sending process or if the client does not exist,
            it logs an error message.

            :param client_id: The ID of the client to whom the message should be sent.
            :param message: The message to be sent to the specified client.
            :return: None
            :raise: None

            setup:
                1. Retrieve the client associated with the given client_id from the _Clients dictionary.
                2. If the client exists:
                    2.1. Attempt to send the provided message to the client.
                    2.2. Log a debug message upon successful sending.
                3. If the client does not exist or an error occurs, log an appropriate error message.
            """

            client = self._Clients.get(client_id, None)
            if client is not None:
                try:
                    await client.send(message)
                    _DefaultLogger.debug(f"WebSocketServer [{self._Name}] sent message to {client_id}: {message}")
                except Exception as e:
                    _DefaultLogger.error(f"WebSocketServer [{self._Name}] send message error: {e}")
            else:
                _DefaultLogger.error(f"WebSocketServer [{self._Name}] send message error: No such client: {client_id}")

        async def broadcast(self, message):
            """
            Sends a message to all connected WebSocket clients.

            This asynchronous method iterates over all registered clients and attempts to send the specified message to each one.
            If an error occurs while sending the message to a client, it logs an error message indicating which client failed.

            :param message: The message to be sent to all clients.
            :return: None
            :raise: None

            setup:
                1. Loop through all clients in the _Clients dictionary.
                2. Attempt to send the provided message to each client.
                    2.1. If an error occurs during the sending process, log the error with the client ID.
            """

            for client_id, client in self._Clients.items():
                try:
                    await client.send(message)
                except Exception as e:
                    _DefaultLogger.error(f"WebSocketServer [{self._Name}] broadcast message to {client_id} error : {e}")

        # noinspection PyUnusedLocal
        async def _wsProcessor(self, ws, path):
            """
            Processes incoming WebSocket messages from a client.

            This asynchronous method runs in a loop, continuously receiving messages from the WebSocket connection. It attempts to
            decode each message as a JSON object. If the message cannot be decoded, it logs an error and closes the connection
            with a specific reason. If a valid message is received, it checks for a client ID and processes the message based on
            its type, such as registering or unregistering the client. If a critical error occurs, it cleans up the client and
            closes the connection.

            :param ws: The WebSocket connection from which to receive messages.
            :param path: The path of the WebSocket connection (not used in this method).
            :return: None
            :raise: None

            setup:
                1. Enter a loop to continuously check for incoming messages.
                2. Receive a message from the WebSocket connection.
                3. Attempt to decode the received message as JSON; if it fails, log an error and close the connection.
                4. Extract the ClientID from the JSON message.
                    4.1. If ClientID is present, call _cleanupClient and close the connection if missing.
                5. Determine the message type from the JSON message.
                    5.1. If the message type is "register", call _registerClient.
                    5.2. If the message type is "unregister", call _unregisterClient.
                    5.3. If the message type is unrecognized and a message processor exists, call it.
                6. Log the received message.
                7. Handle connection closure and any other exceptions gracefully.
            """

            client_id = None
            try:
                while True:
                    await asyncio.sleep(0.01)
                    msg = await ws.recv()
                    try:
                        json_msg = json.loads(msg)
                    except json.JSONDecodeError:
                        _DefaultLogger.error(f"WebSocketServer [{self._Name}] failed to decode JSON message.")
                        await ws.close(reason="Invalid JSON format")
                        break

                    client_id = json_msg.get("ClientID")
                    if client_id is not None:
                        self._cleanupClient(client_id, ws)
                        await ws.close(reason=f"WebSocketServer [{self._Name}] missing required parameter: ClientID")
                        _DefaultLogger.error(f"WebSocketServer [{self._Name}] missing required parameter: ClientID, connection closed.")
                        break

                    msg_type = json_msg.get("type", "").lower()
                    if msg_type == "register":
                        await self._registerClient(client_id, ws)
                    elif msg_type == "unregister":
                        await self._unregisterClient(client_id, ws)
                    elif self._MsgProcessor is not None:
                        await self._MsgProcessor(json_msg)
                    _DefaultLogger.info(f"WebSocketServer [{self._Name}] received message from {client_id}: {msg}")
            except websockets.ConnectionClosed as e:
                _DefaultLogger.debug(f"WebSocketServer [{self._Name}] connection closed for {client_id}: {e.reason}")
            except Exception as e:
                self._cleanupClient(client_id, ws)
                await ws.close()
                _DefaultLogger.error(f"WebSocketServer [{self._Name}] processor error: {e}")

        async def _registerClient(self, client_id, ws):
            """
            Registers a client with the server.

            This asynchronous method checks if the specified client ID is already registered. If it is, it updates the connection
            and informs the client that their connection has been updated. If the client ID is not registered, it adds the client
            to the server's client list and sends a success message to the client.

            :param client_id: The ID of the client to be registered.
            :param ws: The WebSocket connection associated with the client.
            :return: None
            :raise: None

            setup:
                1. Check if the client ID is already present in the _Clients dictionary.
                2. If present, log an info message and send a message to the client indicating that their connection has been updated.
                3. If not present, log a debug message and send a message to the client confirming successful registration.
                4. Add the client ID and its associated WebSocket connection to the _Clients dictionary.
            """

            if client_id in self._Clients:
                _DefaultLogger.info(f"WebSocketServer [{self._Name}] client {client_id} already registered. Updating connection.")
                await ws.send(json.dumps({"type": "info", "message": "Already registered. Connection updated."}))
            else:
                _DefaultLogger.debug(f"WebSocketServer [{self._Name}] client {client_id} registered successfully.")
                await ws.send(json.dumps({"type": "info", "message": "Registered successfully."}))
            self._Clients[client_id] = ws

        async def _unregisterClient(self, client_id, ws):
            """
            Unregisters a client from the server.

            This asynchronous method checks if the specified client ID exists in the server's client list.
            If it exists, the client is removed from the list, and a confirmation message is sent to the client.
            If the client ID does not exist, an error message is sent back to the client indicating the failure.

            :param client_id: The ID of the client to be unregistered.
            :param ws: The WebSocket connection associated with the client.
            :return: None
            :raise: None

            setup:
                1. Check if the client ID is present in the _Clients dictionary.
                2. If present, delete the client ID from the _Clients dictionary and log a debug message.
                3. Send a success message to the client via the WebSocket connection.
                4. If the client ID is not present, log an error message and send an error message to the client.
            """

            if client_id in self._Clients:
                del self._Clients[client_id]
                _DefaultLogger.debug(f"WebSocketServer [{self._Name}] client {client_id} unregistered successfully.")
                await ws.send(json.dumps({"type": "info", "message": "Unregistered successfully."}))
            else:
                _DefaultLogger.error(f"WebSocketServer [{self._Name}] attempted to unregister non-existent client: {client_id}")
                await ws.send(json.dumps({"type": "error", "message": "Client not found. Unregister failed."}))

        def _cleanupClient(self, client_id, ws):
            """
            Cleans up the specified client from the server.

            This method checks if the given client ID exists in the server's list of clients.
            If it exists, the client will be unregistered and a debug message will be logged to indicate the cleanup.

            :param client_id: The ID of the client to be cleaned up.
            :param ws: The WebSocket connection associated with the client.
            :return: None
            :raise: None

            setup:
                1. Check if the client ID is valid and exists in the _Clients dictionary.
                2. Call the _unregisterClient method to remove the client from the server's client list.
                3. Log a debug message confirming the cleanup for the specified client ID.
            """

            if client_id and client_id in self._Clients:
                self._unregisterClient(client_id, ws)
                _DefaultLogger.debug(f"WebSocketServer [{self._Name}] cleaned up for {client_id}")


    class WebSocketClient:
        """
        WebSocketClient class for managing WebSocket connections and message handling.

        The class is designed to manage WebSocket connections and handle message sending and receiving.
        It provides a straightforward interface for connecting to a WebSocket server, sending messages,
        and processing incoming messages with an optional callback function.

        ClassAttributes:
            _ClientID: Unique identifier for the WebSocket client.
            _Url: URL of the WebSocket server.
            _Connection: Active WebSocket connection.
            _IsConnected: Flag indicating the connection status.
            _MsgQueue: Queue for managing outgoing messages.
            _ReceiveHandler: Optional callback function for processing received messages.

        InstanceAttributes:
            client_id: The unique identifier of the WebSocket client.

        Methods:
            setReceiveProcessor: Sets the callback function to handle received messages.
            connect: Establishes a connection to the WebSocket server.
            disconnect: Closes the connection to the WebSocket server.
            sendMsg: Puts a message into the outgoing message queue.
            _sendMsgLoop: Continuously sends messages from the queue.
            _receiveMsgLoop: Continuously listens for incoming messages from the server.
        """

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
            """
            Sets the processor function for handling received messages.

            This method assigns a callable processor that will be invoked whenever a message is received by the WebSocket client.
            The processor should be a coroutine function capable of handling the incoming message asynchronously.

            :param processor: A callable that processes the received message, must be a coroutine.
            :return: None
            :raise: None

            setup:
                1. Assign the provided processor to the _ReceiveHandler attribute.
            """

            self._ReceiveHandler = processor

        async def connect(self):
            """
            Establishes a connection to the WebSocket server.

            This asynchronous method creates an SSL context and attempts to connect to the specified WebSocket URL.
            Upon successful connection, it sends a registration message to the server and starts message loops for sending and receiving messages.

            :return: None
            :raise: None

            setup:
                1. Create an SSL context using the default certificate authority.
                2. Attempt to connect to the WebSocket server.
                    2.1 If successful, set the connection status to true and log the connection.
                    2.2 Send a registration message to the server.
                    2.3 Start asynchronous loops for handling outgoing and incoming messages.
                3. Handle any exceptions during the connection process.
            """

            ssl_context = ssl.create_default_context(cafile=certifi.where())
            try:
                self._Connection = await websockets.connect(self._Url, ssl=ssl_context)
                self._IsConnected = True
                _DefaultLogger.debug(f"WebSocketClient [{self._ClientID}] connected to {self._Url}")
                await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "register"}))
                asyncio.create_task(self._sendMsgLoop())
                if self._ReceiveHandler:
                    asyncio.create_task(self._receiveMsgLoop())
            except Exception as e:
                _DefaultLogger.error(f"WebSocketClient [{self._ClientID}] connection failed: {e}")
                self._IsConnected = False

        async def disconnect(self):
            """
            Disconnects the WebSocket client from the server.

            This asynchronous method attempts to send an unregistration message to the server before closing the connection.
            It sets the connection status to false and handles potential timeout errors during the closing process.

            :return: None
            :raise: None

            setup:
                1. Check if there is an active connection.
                    1.1 If connected, set the connection status to false.
                    1.2 Send an unregistration message to the server.
                    1.3 Close the WebSocket connection and wait for it to close.
                2. Handle any timeout errors during the close process.
            """

            if self._Connection:
                self._IsConnected = False
                try:
                    await self._Connection.send(json.dumps({"ClientID": self._ClientID, "type": "unregister"}))
                    await self._Connection.close()
                    await asyncio.wait_for(self._Connection.wait_closed(), timeout=10)
                except asyncio.TimeoutError:
                    _DefaultLogger.error(f"WebSocketClient [{self._ClientID}] close timeout")
                finally:
                    await self._Connection.close()
                    self._Connection = None

        async def sendMsg(self, msg):
            """
            Sends a message through the WebSocket connection.

            This asynchronous method checks if the WebSocket connection is established; if not, it attempts to connect. It then
            places the message in the message queue for sending.

            :param msg: The message to be sent through the WebSocket connection.
            :return: None
            :raise: None

            setup:
                1. Check if the client is connected.
                    1.1 If not connected, initiate a connection.
                2. Add the message to the message queue for processing.
            """

            if not self._IsConnected:
                await self.connect()
            await self._MsgQueue.put(msg)

        async def _sendMsgLoop(self):
            """
            Asynchronously sends messages from the message queue over the WebSocket connection.

            This method continuously checks the message queue for new messages while the client is connected.
            If a message is available, it is sent over the WebSocket connection.
            If sending fails, the message is requeued for later sending.

            setup:
                1. Continuously run while the client is connected (_IsConnected is True):
                    1.1. Sleep for 0.01 seconds to prevent busy-waiting.
                    1.2. Retrieve a message from the message queue.
                    1.3. Check if the client is still connected. If not, exit the loop.
                    1.4. Attempt to send the message over the WebSocket connection:
                        1.4.1. If successful, log the sent message at the debug level.
                        1.4.2. If an exception occurs during sending:
                            1.4.2.1. Log the error.
                            1.4.2.2. Requeue the message for later sending.
                            1.4.2.3. Sleep for 1 second before trying again.
            """

            while self._IsConnected:
                await asyncio.sleep(0.01)
                msg = await self._MsgQueue.get()
                if not self._IsConnected:
                    return
                try:
                    await self._Connection.send(msg)
                    _DefaultLogger.debug(f"WebSocketClient [{self._ClientID}] sent message: {msg}")
                except Exception as e:
                    _DefaultLogger.error(f"WebSocketClient [{self._ClientID}] send message failed: {e}")
                    await self._MsgQueue.put(msg)
                    await asyncio.sleep(1)

        async def _receiveMsgLoop(self):
            """
            Asynchronously receives messages from the WebSocket connection in a loop.

            This method continuously listens for incoming messages while the client is connected.
            If a message is received, it is passed to the specified receive handler if one exists.
            Any exceptions encountered during the message receiving process are logged.

            setup:
                1. Continuously run while the client is connected (_IsConnected is True):
                    1.1. Sleep for 0.01 seconds to prevent busy-waiting.
                    1.2. Attempt to receive a message from the WebSocket connection:
                        1.2.1. If successful and a receive handler is defined, call the handler with the received message.
                        1.2.2. Log the received message at the debug level.
                    1.3. If an exception occurs during the message reception, log the error.
            """

            while self._IsConnected:
                await asyncio.sleep(0.01)
                try:
                    msg = await self._Connection.recv()
                    if self._ReceiveHandler:
                        await self._ReceiveHandler(msg)
                    _DefaultLogger.debug(f"WebSocketClient [{self._ClientID}] receive message: {msg}")
                except Exception as e:
                    _DefaultLogger.error(f"WebSocketClient [{self._ClientID}] receive message failed : {e}")
except ImportError as _:
    class WebSocketServer:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DefaultLogger.warning("WebSocketServer is not available. Please install certifi and websockets package.")


    class WebSocketClient:
        # noinspection PyUnusedLocal
        def __init__(self, *args, **kwargs):
            _DefaultLogger.warning("WebSocketClient is not available. Please install certifi and websockets package.")
try:
    # noinspection PyUnresolvedReferences
    from aiohttp import web


    class HTTPServer:
        """
        HTTPServer class for managing HTTP server operations, routing, and client requests.

        The class manages HTTP server operations, including routing, client requests, and server lifecycle management.
        It provides a flexible framework for defining routes, processing requests, and handling server start and stop operations.

        ClassAttributes:
            _Name: Name of the HTTP server.
            _Host: Host address for the server.
            _Port: Port number for the server.
            _HTTPApplication: The HTTP application instance.
            _Runner: Application runner for managing server lifecycle.
            _TCPSite: The TCP site for handling requests.
            _IsRunning: Flag indicating whether the server is currently running.
            IsClosed: Flag indicating whether the server has been closed.

        InstanceAttributes:
            name: The name of the HTTP server.
            host: The host address of the HTTP server.
            port: The port number of the HTTP server.
            server_address: The combined host and port address of the server.

        Methods:
            checkRoute: Checks if a specific route exists in the HTTP application.
            addRoute: Adds a new route to the HTTP application with the specified method and processor.
            startHTTPServer: Starts the HTTP server and listens for incoming requests.
            stopHTTPServer: Stops the HTTP server and cleans up resources.
            setAddress: Changes the host and port of the server while managing server state.
            _homeRequest: Handles requests to the home route.
            _addressChangedHandler: Processes requests to change the server address.
            _initRoute: Initializes the routes for the HTTP application.
        """

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
            NetworkInstanceManager.registerHTTPServer(self._Name, self)

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
            """
            Checks if a specific route exists in the HTTP application.

            This method iterates through the existing routes in the HTTP application to determine if a route with the specified method and path is registered.

            :param method: The HTTP method to check for (e.g., "POST" or "GET").
            :param path: The path to check for in the routes.

            :return: True if the route exists; otherwise, False.
            :raise: None

            setup:
                1. Access the HTTP application's router to retrieve the list of routes.
                2. Compare each route's method and canonical path with the provided parameters.
            """

            for route in self._HTTPApplication.router.routes():
                if route.method == method and route.resource.canonical == path:
                    return True
            return False

        def addRoute(self, method: Literal["POST", "GET"], path: str, processor: Callable[..., Coroutine[Any, Any, Any]]):
            """
            Adds a new route to the HTTP application.

            This method allows for the dynamic registration of routes to the HTTP server, specifying the HTTP method, path, and the corresponding request handler (processor).

            :param method: The HTTP method for the route (e.g., "POST" or "GET").
            :param path: The path for the route, which determines the endpoint URL.
            :param processor: The asynchronous function that will handle requests to this route.

            :return: None
            :raise: None

            setup:
                1. Use the HTTP application’s router to add a route.
                2. Specify the method, path, and processor for the new route.
            """

            self._HTTPApplication.router.add_route(method, path, processor)

        # noinspection PyUnusedLocal
        @staticmethod
        async def _homeRequest(request) -> web.Response:
            """
            Handles the home request and responds with an HTML page displaying the application title and ASCII art.

            This static asynchronous method serves as the entry point for the home page of the application.
            When a request is made to the home endpoint, it returns a simple HTML response containing a title and a styled ASCII art banner.

            :param request: The incoming HTTP request object.
            :return: A web.Response containing the HTML content.
            :raise: None

            setup:
                1. Define the HTML content for the response, including the title and ASCII art.
                2. Return the HTML content as a web.Response object with the appropriate content type.
            """

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

        async def setAddress(self, host: str, port: str):
            """
            Sets the host and port for the HTTP server and restarts the server.

            This asynchronous method updates the server's address by changing the host and/or port.
            It starts the server if it is not already running, updates the host and port values,
            and then stops the server to apply the new settings.

            :param host: The new host address for the HTTP server.
            :param port: The new port number for the HTTP server.
            :return: None
            :raise: Any exceptions during server start or stop operations will be logged.

            setup:
                1. Start the HTTP server if it is not already running.
                2. Update the host value if it differs from the current one.
                3. Update the port value if it differs from the current one.
                4. Stop the HTTP server to apply the new address settings.
            """

            await self.startHTTPServer()
            if self._Host != host:
                self._Host = host
            if self._Port != port:
                self._Port = port
            await self.stopHTTPServer()

        async def startHTTPServer(self):
            """
            Starts the HTTP server.

            This asynchronous method initializes and starts the HTTP server if it is not already running.
            It sets up the application runner, creates a TCP site for the server, and starts the server.

            :return: None
            :raise: Any exceptions that occur during the startup process will be logged.

            setup:
                1. Check if the server is already running.
                2. If not running, initialize the AppRunner with the HTTP application.
                3. Set up the AppRunner.
                4. Create a TCP site with the specified host and port.
                5. Start the TCP site and set the running state to True.
            """

            try:
                if not self._IsRunning:
                    self._Runner = web.AppRunner(self._HTTPApplication)
                    await self._Runner.setup()
                    self._TCPSite = web.TCPSite(self._Runner, str(self._Host), int(self._Port))
                    await self._TCPSite.start()
                    self._IsRunning = True
                    _DefaultLogger.debug(f"HTTPServer [{self._Name}] started at {self.server_address}")
                else:
                    _DefaultLogger.debug(f"HTTPServer [{self._Name}] is already running")
            except Exception as e:
                _DefaultLogger.error(f"HTTPServer [{self._Name}] startup failed : {e}")

        async def stopHTTPServer(self):
            """
            Stops the HTTP server if it is currently running.

            This asynchronous method performs cleanup and shutdown operations for the HTTP server.
            It sets the server's running state to false, clears the HTTP application, and nullifies the runner instance.

            :return: None
            :raise: Any exceptions that occur during the cleanup or shutdown process will be logged.

            setup:
                1. Check if the server is running and the runner instance exists.
                2. Call the cleanup method on the runner to clean up resources.
                3. Call the shutdown method on the runner to stop the server.
                4. Set the server's running state to False and reset the HTTP application and runner instance.
            """

            if self._IsRunning and self._Runner:
                try:
                    await self._Runner.cleanup()
                    await self._Runner.shutdown()
                finally:
                    self._IsRunning = False
                    self._HTTPApplication = web.Application()
                    self._Runner = None
            _DefaultLogger.debug(f"HTTPServer [{self._Name}] turned off.")
            self.IsClosed = True

        async def _addressChangedHandler(self, request) -> web.Response:
            """
            Handles changes to the server's address based on client requests.

            This asynchronous method receives an HTTP request containing the new host and port
            for the server. It updates the server's address accordingly and sends a response
            indicating the new address.

            :param request: The HTTP request object containing the new address information in JSON format.
            :return: web.Response indicating the status of the address change.
            :raise: Exception if there is an error in processing the request or changing the address.

            setup:
                1. Extract the new_host and new_port from the request JSON data.
                2. Call the setAddress method to update the server's address.
                3. Return a web.Response with the confirmation message or an error status.
            """

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
            _DefaultLogger.warning("HTTPServer is not available. Please install aiohttp package.")
