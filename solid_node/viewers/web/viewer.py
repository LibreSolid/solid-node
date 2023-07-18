import threading
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


class WebViewer:
    def __init__(self, path):
        self.path = path
        self.node = load_node(path)

        self.basedir = os.path.dirname(
            os.path.realpath(__file__)
        )
        self.frontend_dir = os.path.join(self.basedir, 'frontend')

        self.app = FastAPI()
        self.root = NodeAPI(self.node)

        self.app.mount(f'/api/{self.root.name}', self.root)
        self.app.mount(f'/',
                       StaticFiles(directory=self.frontend_dir),
                       name="frontend")

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)

    def start(self):
        threading.Thread(target=self.run).start()


class NodeAPI:

    def __init__(self, node):
        self.node = node
        self.name = self.node.name

        self.app = FastAPI()

        self.app.add_api_route('/', self.state)

        self.operations = [
            op.serialized for op in self.node.operations
        ]

        self.subapps = []
        self.children = None

        if self.node.rigid:
            self.app.add_api_route(f'/{self.name}.stl', self.stl)
            return

        children = self.node.render()
        if type(children) not in (list, tuple):
            # This is a leaf
            return

        for child in children:
            subapp = NodeAPI(child)
            self.app.mount(f'/{child.name}', subapp)
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
        return state

    async def stl(self):
        stl = self.node.stl
        if not stl:
            stl = await self.wait_for_file(stl)

        return FileResponse(
            stl,
            media_type='application/octet-stream',
            filename=f'{self.name}.stl',
        )

    async def wait_for_file(self, file_path)
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
