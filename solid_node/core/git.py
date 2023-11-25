import os
import asyncio
import logging
import websockets
from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError
from solid_node.core.broker import LOCK_URL

logger = logging.getLogger('core.git')


class GitRepo:
    def __init__(self, file_path):
        self.repo = _find_repo_root(file_path)
        self._ock = None

    def lock(self, source):
        self._lock = RepoLock(source)
        return self._lock

    @property
    def locked(self):
        return self._lock.locked

    async def add(self, file_path):
        self._debug('add')
        self.repo.git.add(file_path)

    async def commit(self):
        self._debug('commit')
        self.repo.index.commit(message)

    async def revert_last_commit(self):
        self._debug('revert')
        try:
            self.repo.git.revert('HEAD', no_edit=True)
            logger.info("Reverted the last commit.")
        except GitCommandError as e:
            logger.error(f"Failed to revert the last commit: {e}")

    def _debug(self, operation):
        assert self.locked
        logger.info(f'{operation} by {self._lock.source}')


class RepoLock:

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
