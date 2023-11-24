import asyncio
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from solid_node.core.logging import logging, uvicorn_config


HOST = '127.0.0.1'
PORT = 4190
LOCK_PATH = '/lock'

BROKER_URL = f'ws://{HOST}:{PORT}'
LOCK_URL = f'{BROKER_URL}{LOCK_PATH}'

logger = logging.getLogger('core.broker')


class BrokerServer:
    # Static declaration of topics
    topics = ['compile']

    def __init__(self):
        self.app = FastAPI()
        self.global_lock = asyncio.Event()
        self.global_lock.set()  # Initially, the lock is available
        self.topic_connections: Dict[str, Set[WebSocket]] = {topic: set() for topic in self.topics}
        self.initialize_endpoints()

    def initialize_endpoints(self):
        @self.app.websocket(LOCK_PATH)
        async def lock_endpoint(websocket: WebSocket):
            await self.lock_handler(websocket)

        for topic in self.topic_connections.keys():
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
