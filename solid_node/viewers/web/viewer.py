import os
import json
import asyncio
import threading
import uvicorn
import httpx
import logging
import subprocess
from datetime import datetime
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.websockets import WebSocketDisconnect
from solid_node.core import load_node
from solid_node.core.logging import uvicorn_config
from solid_node.core.broker import BrokerClient


logger = logging.getLogger('viewer.web')
basedir = os.path.dirname(
    os.path.realpath(__file__)
)

class WebDevServer:
    """For development purposes, run a "npm run start" command
    to be proxyed by WebViewer
    """
    def __init__(self, path, dev=True):
        self.path = path
        self.app_dir = os.path.join(basedir, 'app')

    def start(self):
        proc = subprocess.Popen(
            ['npm', 'run', 'start'],
            cwd=self.app_dir,
        )
        proc.communicate()


class WebViewer:
    """Starts a webserver that can serve either a built html app
    or make a proxy to WebDevServer instance.
    The react app is inside app/ in the same folder as this class' file.
    """
    def __init__(self, path, dev=True):
        self.path = path
        self.node = load_node(path)

        self.frontend_dir = os.path.join(basedir, 'app/build')

        self.stl_index = {}
        self.app = FastAPI()

        root_node = NodeAPI(self.node,
                            self.stl_index,
                            f'/{self.node.name}',
                            )

        self.app.mount(f'/node', root_node.app)

        self.broker = BrokerClient()

        self._setup_build_error()

        self._setup_reload_websocket()

        if dev:
            self._setup_proxy_server()
        else:
            self._setup_frontend_server()

    def start(self):
        logger.info("START - will listen on port 8000")
        uvicorn.run(self.app, host="0.0.0.0", port=8000,
                    log_config=uvicorn_config)

    def _setup_reload_websocket(self):
        @self.app.websocket("/ws/reload")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("reload")
            monitoring = set()
            try:
                while True:
                    path = await websocket.receive_text()
                    monitoring.add(path)
            except WebSocketDisconnect:
                return

    def _setup_build_error(self):
        @self.app.get("/_build_error")
        async def get_status():
            error = await self.broker.get('build_error')
            return JSONResponse(error)

    def _setup_frontend_server(self):
        # Serve a static application.
        # It's generated with "npm run build" inside app/ application
        @self.app.get("/")
        async def read_root():
            return FileResponse(os.path.join(self.frontend_dir, 'index.html'))

        self.app.mount(f'/',
                       StaticFiles(directory=self.frontend_dir),
                       name="frontend")


    def _setup_proxy_server(self):
        # This makes a proxy to a running "npm start" development server
        # inside app/ application.
        @self.app.get('/')
        async def proxy_root():#, request: Request):
            return await _proxy('/')

        @self.app.get('/{path}')
        async def proxy_path(path: str):
            return await _proxy(f'/{path}')

        @self.app.get('/static/js/{path}')
        async def proxy_static_js(path: str):
            return await _proxy(f'/static/js/{path}')

        async def _proxy(path: str):
            async with httpx.AsyncClient() as client:
                response = await client.request('GET', f'http://localhost:3000{path}')
                return Response(
                    content=response.content,
                    media_type=response.headers.get('content-type'),
                )


class NodeAPI:
    """Recursively define an API to serve the node structure
    of a project to the web application"""

    def __init__(self, node, stl_index, prefix):
        self.node = node
        self.name = self.node.name

        logger.info(f'Prefix {prefix} to {node.name}')
        self.app = FastAPI()

        self.app.add_api_route('/', self.state, methods=["GET"])

        self.operations = [
            op.serialized for op in self.node.operations
        ]

        self.subapps = []
        self.children = []

        if self.node.rigid:
            stl_path = f'/{self.name}.stl'
            key = f'{prefix}{stl_path}'
            stl_index[key] = self.node.stl
            self.app.add_api_route(stl_path, self.stl)
            return

        children = self.node.render()
        if type(children) not in (list, tuple):
            # This is a leaf
            return

        for child in children:
            child_path = f'/{child.name}'
            subapp = NodeAPI(child, stl_index, child_path)
            logger.info(f'Mounting node {child_path}')
            self.app.mount(child_path, subapp.app)
            self.subapps.append(subapp)
            self.children.append(child.name)

    async def state(self):
        state =  {
            'operations': self.operations,
            'type': self.node._type,
            'name': self.node.name,
            'color': self.node.color
        }
        if self.children:
            state['children'] = self.children
        else:
            state['model'] = f'{self.name}.stl'

        state['mtime'] = self.node.mtime
        op = json.dumps(self.operations)
        return state

    async def stl(self, request: Request):
        stl = self.node.stl
        if not stl:
            logger.info(f'Waiting for {self.node.stl_file} to be available')
            stl = await self.wait_for_file(self.node.stl_file)
            logger.info(f'Got {self.node.stl_file}')

        last_modified_time = datetime.utcfromtimestamp(os.path.getmtime(stl))

        # Check 'If-Modified-Since' header in the request
        if_modified_since = request.headers.get('if-modified-since')
        if if_modified_since:
            if_modified_since_time = datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT")
            if last_modified_time <= if_modified_since_time:
                return Response(status_code=304)

        response = FileResponse(
            stl,
            media_type='application/octet-stream',
            filename=f'{self.name}.stl',
        )

        last_modified_str = last_modified_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers['Last-Modified'] = last_modified_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        return response

    async def wait_for_file(self, file_path):
        while True:
            if os.path.exists(file_path):
                return
            await asyncio.sleep(0.1)
