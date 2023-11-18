import os
import threading
import uvicorn
import httpx
import inspect
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pyinotify import WatchManager, EventsCodes, Notifier, ProcessEvent
from solid_node.core import load_node


class WebViewer:
    def __init__(self, path, dev=True):
        self.path = path
        self.node = load_node(path)

        self.basedir = os.path.dirname(
            os.path.realpath(__file__)
        )
        self.frontend_dir = os.path.join(self.basedir, 'app/build')

        self.app = FastAPI()
        self.root = NodeAPI(self.node)

        self.app.mount(f'/api/{self.root.name}', self.root.app)

        if dev:
            self._setup_proxy_server()
        else:
            self._setup_frontend_server()


    def start(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)

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
        # It's cumbersome because FastAPI was not meant for this. Couldn't find
        # a way to get full URI with it.

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

    def __init__(self, node):
        self.node = node
        self.name = self.node.name

        self.app = FastAPI()

        self.app.add_api_route('/', self.state, methods=["GET"])
        self.app.add_api_route('/', self.save_source_code, methods=["POST"])

        self.operations = [
            op.serialized for op in self.node.operations
        ]

        self.subapps = []
        self.children = []

        if self.node.rigid:
            self.app.add_api_route(f'/{self.name}.stl', self.stl)
            return

        children = self.node.render()
        if type(children) not in (list, tuple):
            # This is a leaf
            return

        for child in children:
            subapp = NodeAPI(child)
            self.app.mount(f'/{child.name}', subapp.app)
            self.subapps.append(subapp)
            self.children.append(child.name)

    async def state(self):
        state =  {
            'operations': self.operations,
        }
        if self.children:
            state['children'] = self.children
        else:
            state['model'] = f'{self.name}.stl'

        state['code'] = inspect.getsource(inspect.getmodule(self.node))

        return state

    async def save_source_code(self, request: Request):
        body = await request.body()
        source = inspect.getfile(inspect.getmodule(self.node))
        bak = f'{source}.bak'
        open(bak, 'wb').write(open(source, 'rb').read())
        open(source, 'wb').write(body)
        return Response(status_code=201)

    async def stl(self, request: Request):
        stl = self.node.stl
        if not stl:
            stl = await self.wait_for_file(stl)

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
        future = asyncio.Future()
        wm = WatchManager()
        mask = EventsCodes.ALL_FLAGS['IN_CREATE']
        handler = EventHandler(future, file_path)
        notifier = Notifier(wm, default_proc_fun=handler)
        wm.add_watch(os.path.dirname(file_path), mask)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, notifier.loop)
        await future

        notifier.stop()

        return file_path


class EventHandler(ProcessEvent):
    def __init__(self, future, filename):
        self.future = future
        self.filename = filename

    def process_IN_CREATE(self, event):
        if event.pathname == self.filename:
            self.future.set_result(True)
