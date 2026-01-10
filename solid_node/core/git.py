# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import asyncio
import logging
import websockets
from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError
from solid_node.core.broker import AsyncLock, SyncLock

logger = logging.getLogger('core.git')


class GitRepo:
    """Manages a git repository for user's project.
    It was used for browser's code editor, now it's
    not in use.
    """
    def __init__(self, file_path):
        self.repo = _find_repo_root(file_path)
        self._lock = None

    def async_lock(self, source):
        self._lock = AsyncLock(source)
        return self._lock

    def sync_lock(self, source):
        self._lock = SyncLock(source)
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
