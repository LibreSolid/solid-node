# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Private coherent reads and strong identities for built artifacts."""

import os
import shutil
import tempfile
from dataclasses import asdict, dataclass


class ArtifactChanged(RuntimeError):
    """An artifact stopped naming the open identity being consumed."""


@dataclass(frozen=True)
class ArtifactObservation:
    """The observable filesystem identity of one built artifact."""

    realpath: str
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def from_stat(cls, realpath, stat):
        return cls(
            realpath=os.path.realpath(realpath),
            device=stat.st_dev,
            inode=stat.st_ino,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            ctime_ns=stat.st_ctime_ns,
        )

    @classmethod
    def from_record(cls, value):
        if not isinstance(value, dict):
            raise ValueError('artifact observation is not an object')
        expected = {field.name for field in cls.__dataclass_fields__.values()}
        if set(value) != expected:
            raise ValueError('artifact observation has unknown fields')
        if not isinstance(value['realpath'], str):
            raise ValueError('artifact realpath is not text')
        for key in expected - {'realpath'}:
            if not isinstance(value[key], int) or isinstance(value[key], bool):
                raise ValueError(f'artifact {key} is not an integer')
        return cls(**value)

    def record(self):
        return asdict(self)


def observe_artifact(path):
    """Observe one path without retaining its contents."""
    spelling = os.path.abspath(os.fspath(path))
    real_before = os.path.realpath(spelling)
    stat = os.stat(spelling)
    real_after = os.path.realpath(spelling)
    if real_before != real_after:
        raise ArtifactChanged(
            f'Artifact path changed while observed: {spelling}')
    return ArtifactObservation.from_stat(real_before, stat)


def artifact_cache_key(path):
    """A process-cache key invalidated by ordinary preserved-mtime edits."""
    return os.fspath(path), observe_artifact(path)


class ArtifactSnapshot:
    """An open artifact identity validated around every byte consumption."""

    def __init__(self, path):
        self.path = os.path.abspath(os.fspath(path))
        self._stream = open(self.path, 'rb')
        try:
            real = os.path.realpath(self.path)
            self.observation = ArtifactObservation.from_stat(
                real, os.fstat(self._stream.fileno()))
            self.validate()
        except Exception:
            self._stream.close()
            raise

    @property
    def closed(self):
        return self._stream.closed

    def validate(self):
        """Require both the open file and its path to keep one identity."""
        if self.closed:
            raise ValueError('artifact snapshot is closed')
        opened = ArtifactObservation.from_stat(
            self.observation.realpath, os.fstat(self._stream.fileno()))
        try:
            current = observe_artifact(self.path)
        except OSError:
            current = None
        if opened != self.observation or current != self.observation:
            raise ArtifactChanged(
                f'Artifact changed while consumed: {self.path}')
        return self.observation

    def read_bytes(self):
        """Read the complete pinned payload, validating before and after."""
        self.validate()
        self._stream.seek(0)
        data = self._stream.read()
        self.validate()
        if len(data) != self.observation.size:
            raise ArtifactChanged(
                f'Artifact size changed while consumed: {self.path}')
        return data

    def copy_to(self, target):
        """Atomically copy bytes from this identity, never from its path."""
        self.validate()
        directory = os.path.dirname(os.path.abspath(target)) or '.'
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f'.{os.path.basename(target)}.', suffix='.tmp',
            dir=directory)
        try:
            self._stream.seek(0)
            with os.fdopen(descriptor, 'wb') as output:
                shutil.copyfileobj(self._stream, output)
            self.validate()
            if os.path.getsize(temporary) != self.observation.size:
                raise ArtifactChanged(
                    f'Artifact copy is incomplete: {self.path}')
            os.chmod(temporary, os.fstat(self._stream.fileno()).st_mode)
            os.utime(temporary, ns=(self.observation.mtime_ns,
                                    self.observation.mtime_ns))
            os.replace(temporary, target)
        except Exception:
            if os.path.exists(temporary):
                os.remove(temporary)
            raise

    def close(self):
        self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

