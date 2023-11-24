import os
import asyncio
import websockets
from git import Repo, InvalidGitRepositoryError, NoSuchPathError
from solid_node.core.broker import LOCK_URL


class GitRepo:
    def __init__(self, file_path):
        self.repo = _find_repo_root(file_path)

    def lock(self):
        return RepoLock()

    async def add(self, file_path):
        """
        Adds the specified file to the staging area
        """
        self.repo.git.add(file_path)

    async def commit(self, message="AUTO-COMMIT"):
        self.repo.index.commit(message)

    async def discard_changes(self):
        """
        Discards all changes from repository
        """
        async with RepoLock():
            self.repo.git.reset('--hard')


class RepoLock:

    async def __aenter__(self):
        await self.acquire_lock()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release_lock()

    async def acquire_lock(self):
        async with websockets.connect(LOCK_URL) as websocket:
            await websocket.send("acquire")
            await websocket.recv()

    async def release_lock(self):
        async with websockets.connect(LOCK_URL) as websocket:
            await websocket.send("release")
            await websocket.recv()


def _find_repo_root(file_path):
    """
    Find the root of the Git repository starting from the given file path.
    """
    try:
        path = os.path.abspath(file_path)
        while not os.path.isdir(os.path.join(path, '.git')):
            parent = os.path.dirname(path)
            if parent == path:
                raise InvalidGitRepositoryError(f"No git repository found for {file_path}")
            path = parent
        return Repo(path)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        raise e
