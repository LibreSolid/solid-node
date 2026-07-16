# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import json
import asyncio
import uvicorn
import httpx
import logging
import subprocess
import traceback
from datetime import datetime
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.websockets import WebSocketDisconnect
from solid_node.core import load_node
from solid_node.core.logging import uvicorn_config
from solid_node.core.builder import get_errors_file


logger = logging.getLogger('viewer.web')
basedir = os.path.dirname(
    os.path.realpath(__file__)
)

# Ports are overridable so several checkouts (e.g. worktrees made by
# scripts/dev-env) can run side by side.
def backend_port():
    return int(os.environ.get('SOLID_NODE_PORT', 8000))

def frontend_port():
    return int(os.environ.get('SOLID_NODE_FRONTEND_PORT', 3000))

class WebDevServer:
    """For development purposes, run a "npm run start" command
    to be proxyed by WebViewer
    """
    def __init__(self, path):
        self.path = path
        self.app_dir = os.path.join(basedir, 'app')

    def start(self):
        proc = subprocess.Popen(
            ['npm', 'run', 'start'],
            cwd=self.app_dir,
            env=dict(os.environ, PORT=str(frontend_port())),
        )
        proc.communicate()


class WebViewer:
    """Starts a webserver that can serve either a built html app
    or make a proxy to WebDevServer instance.
    The react app is inside app/ in the same folder as this class' file.
    """
    def __init__(self, path, dev=True):
        self.path = path
        self.node = None

        self.frontend_dir = os.path.join(basedir, 'app/build')

        self.app = FastAPI()

        try:
            self.node = load_node(path)
            root_node = NodeAPI(self.node,
                                f'/{self.node.name}',
                                )
            self.app.mount(f'/node', root_node.app)
        except Exception:
            # A project broken at the moment the web viewer (re)starts
            # must not crash this server -- the browser depends on this
            # same process for the reload websocket and the
            # /_build_error endpoint below (fed by the builder's
            # errors.json) to recover once a fix lands and Develop
            # restarts this viewer with a working node. Don't duplicate
            # error reporting here: the builder subprocess already owns
            # writing errors.json for the exact same failure.
            logger.error(
                f'Failed to load node from {path} for web viewer:\n'
                f'{traceback.format_exc()}'
            )

        self._setup_build_error()

        self._setup_reload_websocket()

        if dev:
            self._setup_proxy_server()
        else:
            self._setup_frontend_server()

    def start(self):
        port = backend_port()
        logger.info(f"START - will listen on port {port}")
        uvicorn.run(self.app, host="0.0.0.0", port=port,
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
            errors_file = get_errors_file()
            if os.path.exists(errors_file):
                with open(errors_file, 'r') as f:
                    error = json.load(f)
                return JSONResponse(error)
            return JSONResponse({})

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
                response = await client.request('GET', f'http://localhost:{frontend_port()}{path}')
                return Response(
                    content=response.content,
                    media_type=response.headers.get('content-type'),
                )


class NodeAPI:
    """Recursively define an API to serve the node structure
    of a project to the web application"""

    def __init__(self, node, prefix):
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
            self.app.add_api_route(stl_path, self.stl)
            return

        children = self.node.render()
        if type(children) not in (list, tuple):
            # This is a leaf
            return

        for child in children:
            # NodeAPI walks render() output directly, never assemble(),
            # so it never goes through InternalNode.as_scad -- link and
            # derive the child's name here too (skill-repo
            # improvements.md #16), so the viewer tree and the
            # STL/test naming agree.
            self.node._link_child(child)
            child_path = f'/{child.name}'
            subapp = NodeAPI(child, child_path)
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
                return file_path
            await asyncio.sleep(0.1)
