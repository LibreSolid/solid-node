# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import subprocess
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Response, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from solid_node.core.builder import get_build_dir, get_errors_file
from solid_node.core.logging import uvicorn_config
from solid_node.viewers.bundle import (
    api_version, bundle_path, has_bundle, missing_bundle_remedy,
)


logger = logging.getLogger('viewer.web')
basedir = os.path.dirname(os.path.realpath(__file__))


def backend_port():
    return int(os.environ.get('SOLID_NODE_PORT', 8000))


def frontend_port():
    return int(os.environ.get('SOLID_NODE_FRONTEND_PORT', 3000))


class WebDevServer:
    """Run the development React server proxied by :class:`WebViewer`."""
    def __init__(self, path):
        self.path = path
        self.app_dir = os.path.join(basedir, 'app')

    def start(self):
        proc = subprocess.Popen(
            ['npm', 'run', 'start'], cwd=self.app_dir,
            env=dict(os.environ, PORT=str(frontend_port())),
        )
        proc.communicate()


class WebViewer:
    """Serve the published build snapshot and the shared viewer bundle."""
    def __init__(self, path, dev=True):
        self.path = path
        self.frontend_dir = os.path.join(basedir, 'app/build')
        self.app = FastAPI()

        self._setup_build_error()
        self._setup_build_snapshot()
        self._setup_viewer_bundle()
        self._setup_reload_websocket()

        if dev:
            self._setup_proxy_server()
        else:
            self._setup_frontend_server()

    def start(self):
        port = backend_port()
        logger.info('START - will listen on port %s', port)
        uvicorn.run(self.app, host='0.0.0.0', port=port,
                    log_config=uvicorn_config)

    def _setup_reload_websocket(self):
        @self.app.websocket('/ws/reload')
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text('reload')
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                return

    def _setup_build_error(self):
        @self.app.get('/_build_error')
        async def get_status():
            errors_file = get_errors_file()
            if os.path.exists(errors_file):
                with open(errors_file, 'r') as stream:
                    return JSONResponse(json.load(stream))
            return JSONResponse({})

    def _setup_build_snapshot(self):
        @self.app.get('/build/{requested_path:path}')
        async def get_build_file(requested_path: str):
            build_dir = Path(get_build_dir()).resolve()
            candidate = (build_dir / requested_path).resolve()
            try:
                candidate.relative_to(build_dir)
            except ValueError:
                raise HTTPException(status_code=404)
            if not candidate.is_file():
                raise HTTPException(status_code=404, detail='Published build artifact not found')
            return FileResponse(candidate)

    def _setup_viewer_bundle(self):
        @self.app.get('/_viewer')
        async def get_viewer_status():
            available = has_bundle()
            return {
                'available': available,
                'apiVersion': api_version(),
                'remedy': None if available else missing_bundle_remedy(),
            }

        @self.app.get('/_viewer/bundle.js')
        async def get_viewer_bundle():
            if not has_bundle():
                return JSONResponse({
                    'remedy': missing_bundle_remedy(),
                }, status_code=503)
            return FileResponse(bundle_path(), media_type='application/javascript')

    def _setup_frontend_server(self):
        @self.app.get('/')
        async def read_root():
            return FileResponse(os.path.join(self.frontend_dir, 'index.html'))

        self.app.mount('/', StaticFiles(directory=self.frontend_dir), name='frontend')

    def _setup_proxy_server(self):
        @self.app.get('/')
        async def proxy_root():
            return await self._proxy('/')

        @self.app.get('/{path:path}')
        async def proxy_path(path: str):
            return await self._proxy('/' + path)

    async def _proxy(self, path: str):
        async with httpx.AsyncClient() as client:
            response = await client.request(
                'GET', f'http://localhost:{frontend_port()}{path}')
        return Response(content=response.content,
                        media_type=response.headers.get('content-type'))
