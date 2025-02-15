import asyncio
import websockets
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, Set
from solid_node.core.logging import logging, uvicorn_config


HOST = '127.0.0.1'
PORT = 4190
LOCK_PATH = '/lock'

BROKER_URL = f'ws://{HOST}:{PORT}'
LOCK_URL = f'{BROKER_URL}{LOCK_PATH}'

logger = logging.getLogger('core.broker')


class BrokerServer:
    """The broker is a persistent webserver process that
    implements locking to synchronize other processes and
    topics to exchange messages.
    """
    topics = []

    keys = [
        'build_error',
    ]

    data = {}

    def __init__(self):
        self.app = FastAPI()
        self.global_lock = asyncio.Event()
        self.global_lock.set()  # Initially, the lock is available
        self.topic_connections: Dict[str, Set[WebSocket]] = {topic: set() for topic in self.topics}
        self.data = {key: {} for key in self.keys}
        self.initialize_endpoints()

    def initialize_endpoints(self):
        @self.app.websocket(LOCK_PATH)
        async def lock_endpoint(websocket: WebSocket):
            await self.lock_handler(websocket)

        for key in self.keys:
            @self.app.put(f'/{key}')
            async def update_key(data: dict):
                self.data[key] = data

            @self.app.get(f'/{key}')
            async def get_key():
                return JSONResponse(self.data[key])

        for topic in self.topics:
            @self.app.websocket(f'/{topic}')
            async def topic_endpoint(websocket: WebSocket, topic=topic):
                await self.topic_handler(websocket, topic)

    async def lock_handler(self, websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                if data == 'acquire':
                    await self.global_lock.wait()
                    self.global_lock.clear()  # Lock is now held
                    await websocket.send_text('lock')
                elif data == 'release':
                    self.global_lock.set()  # Release the lock
                    await websocket.send_text('release')
        except WebSocketDisconnect:
            self.global_lock.set()  # Ensure lock is released if client disconnects

    async def topic_handler(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        self.topic_connections[topic].add(websocket)
        try:
            while True:
                message = await websocket.receive_text()
                await self.broadcast_message(topic, message, websocket)
        except WebSocketDisconnect:
            self.topic_connections[topic].discard(websocket)

    async def broadcast_message(self, topic: str, message: str, sender: WebSocket):
        for ws in self.topic_connections[topic]:
            if ws is not sender and ws.open:
                await ws.send_text(message)

    def start(self):
        import uvicorn
        logger.info("START")
        uvicorn.run(self.app, host=HOST, port=PORT,
                    log_config=uvicorn_config)

class BrokerClient:
    def __init__(self):
        self.lock_ws = None

    async def subscribe(self, topic):
        async with websockets.connect(f'{BROKER_URL}/{topic}') as websocket:
            return await websocket.recv()

    async def post(self, topic, message):
        async with websockets.connect(f'{BROKER_URL}/{topic}') as websocket:
            await websocket.send(message)

    async def put(self, key, data):
        async with httpx.AsyncClient() as client:
            response = await client.put((f'{BROKER_URL}/{key}'), json=data)
            return response.json()

    async def get(self, key):
        async with httpx.AsyncClient() as client:
            response = await client.get((f'{BROKER_URL}/{key}'))
            return response.json()

class AsyncLock:

    def __init__(self, source):
        self.source = source
        self.locked = False

    async def __aenter__(self):
        await self.acquire_lock()
        self.locked = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release_lock()
        self.locked = False

    async def acquire_lock(self):
        async with websockets.connect(LOCK_URL) as websocket:
            await websocket.send("acquire")
            await websocket.recv()
            logger.info(f'LOCK from {self.source} ')

    async def release_lock(self):
        async with websockets.connect(LOCK_URL) as websocket:
            await websocket.send("release")
            await websocket.recv()
            logger.info(f'RELEASE from {self.source} ')


class SyncLock:

    def __init__(self, source):
        self.source = source
        self.locked = False

    def __enter__(self):
        self.acquire_lock()
        self.locked = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_lock()
        self.locked = False

    def acquire_lock(self):
        # Synchronous code to acquire lock
        logger.info(f'SYNC LOCK from {self.source}')

    def release_lock(self):
        # Synchronous code to release lock
        logger.info(f'SYNC RELEASE from {self.source}')
