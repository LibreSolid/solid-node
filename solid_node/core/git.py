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
        self._lock = None

    def async_lock(self, source):
        self._lock = RepoAsyncLock(source)
        return self._lock

    def sync_lock(self, source):
        self._lock = RepoSyncLock(source)
        return self._lock

    @property
    def locked(self):
        return self._lock.locked

    def add(self, file_path):
        self._assert_lock('add')
        self.repo.git.add(file_path)

    def commit(self, message):
        self._assert_lock('commit')
        self.repo.index.commit(message)

    def revert_last_commit(self):
        self._assert_lock('revert')
        try:
            self.repo.git.revert('HEAD', no_edit=True)
            logger.info("Reverted the last commit.")
        except GitCommandError as e:
            logger.error(f"Failed to revert the last commit: {e}")

    def _assert_lock(self, operation):
        assert self.locked
        logger.debug(f'{operation} by {self._lock.source}')


class RepoAsyncLock:

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


class RepoSyncLock:

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
