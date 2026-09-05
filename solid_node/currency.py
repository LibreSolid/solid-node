# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The content-verified fallback beneath the mtime-equality rule.

Currency is mtime equality (ADR-006), and this module does not change
that: when an artifact's stamp equals the node's mtime nothing here is
read, computed or opened. What it adds is what happens when the equality
FAILS.

It fails constantly for a reason that has nothing to do with the model. A
clone, a branch switch, a stash pop, a `git restore`, a copy, an agent or
a formatter rewriting a file with identical bytes -- all of them stamp a
source with the time it was written and none of them change what it says.
Measured on a 22-part CadQuery project, rewriting every source mtime with
zero content change turned a 6.05 s settled rebuild into 35.66 s of
re-deriving geometry that was already on disk and provably identical.

So when the stamp disagrees, the build asks the question the stamp was
standing in for: are the sources that produced this artifact the sources
that are here now? The digest below answers it over `node.files` -- the
exact set `mtime_ns` is the maximum of -- as a sorted sequence of
(project-relative path, sha256 of bytes). Project-RELATIVE because the
case this exists for is a project that moved: a fresh clone in a new
directory must recognise its own artifacts.

ADR-006 considered content hashing as a REPLACEMENT for the mtime check
and rejected it on cost ("expensive I/O ... slower cache checks ...
overkill"). That judgement holds and is not disturbed: hashing is paid
only where a full render would otherwise run, and never on the hit path.

The direction of failure is the whole safety argument. A digest match is
a strictly stronger claim than the mtime equality it stands behind -- it
says the bytes are identical, not merely that a number matches -- so this
can only ever spare a rebuild that would have reproduced the same
artifact. Everything else says "not current": a mismatch, a missing
record, an unreadable source, a sidecar that was swept. A stale model
reported as fresh is the one failure the system cannot survive, and every
uncertain path here resolves toward rebuilding.
"""

import ast
import hashlib
import logging
import os
import tempfile
import time


logger = logging.getLogger('currency')


#: Appended to the artifact's own name, so the record for `part.stl` is
#: `part.stl.sources`. It lives inside the build directory, is never
#: named by `viewer.json`, and changes nothing about what publication
#: means (ADR-030). The suffix deliberately keeps the artifact's own
#: extension in the middle of the name, so a `*.stl` glob -- the build
#: directory is full of them -- does not match a sidecar.
SIDECAR_SUFFIX = '.sources'


# Per-file digests, keyed on (path, mtime, size) so an edited file is
# re-read and its stale entry evicted -- the same shape as the base mesh
# cache in node/base.py and the import cache in node/sources.py. Without
# it a tree's digests are quadratic: an internal node's file set is the
# union of its children's, so the root re-reads every source in the
# project once per node.
_file_digests = {}


def _file_digest(path):
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    cached = _file_digests.get(key)
    if cached is None:
        for stale in [k for k in _file_digests if k[0] == path]:
            del _file_digests[stale]
        with open(path, 'rb') as stream:
            cached = _file_digests[key] = hashlib.file_digest(
                stream, 'sha256').hexdigest()
    return cached


# Per-file structure for scoping, keyed like _file_digests: the file's
# lines, and for each top-level statement the node-class span it defines
# (if it is one) and every name and string the statement mentions. None
# when the file cannot be scoped -- unparseable, or the interpreter cannot
# say which of its classes are nodes -- so it is digested whole.
_analyses = {}

# Digests of retained text, keyed on the file key plus the classes kept.
# A tree asks for the same (file, scope) once per node that shares it, so
# without this an internal node's digest re-reads its children's files.
_scoped_digests = {}


def _analysis(path):
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key not in _analyses:
        for stale in [k for k in _analyses if k[0] == path]:
            del _analyses[stale]
        with open(path, 'rb') as stream:
            _analyses[key] = _analyse(path, stream.read())
    return _analyses[key]


def _analyse(path, data):
    # Local import avoids the node.base -> currency -> sources cycle.
    from solid_node.node.sources import node_classes_in

    try:
        tree = ast.parse(data, filename=path)
    except (SyntaxError, ValueError):
        return None
    node_classes = node_classes_in(path)
    if not node_classes:
        return None

    statements = []
    for statement in tree.body:
        mentions = set()
        for inner in ast.walk(statement):
            if isinstance(inner, ast.Name):
                mentions.add(inner.id)
            elif (isinstance(inner, ast.Constant)
                    and isinstance(inner.value, str)):
                mentions.add(inner.value)
        span = None
        if (isinstance(statement, ast.ClassDef)
                and statement.name in node_classes):
            first = min([statement.lineno]
                        + [d.lineno for d in statement.decorator_list])
            span = (statement.name, first, statement.end_lineno)
        statements.append((span, frozenset(mentions)))

    # bytes.splitlines breaks where the tokenizer does -- \n, \r\n and a
    # lone \r -- so line numbers from the AST index these lines.
    return data.splitlines(keepends=True), statements


def _removed_spans(statements, keep):
    """The (name, first, last) spans of the node classes a node whose
    scope is `keep` does not see.

    Start from every top-level node class not in `keep`; then put back
    any of them the retained statements mention, by identifier or as a
    string, and repeat until the retained text refers to nothing removed.
    A base class, a helper that instantiates a sibling, `getattr(module,
    'Sibling')` -- all of them keep the sibling in. Only a class the rest
    of the file never names is left out.
    """
    removed = {span[0] for span, _ in statements
               if span is not None and span[0] not in keep}
    while removed:
        mentioned = set()
        for span, mentions in statements:
            if span is None or span[0] not in removed:
                mentioned |= mentions
        restored = removed & mentioned
        if not restored:
            break
        removed -= restored
    return [span for span, _ in statements
            if span is not None and span[0] in removed]


def _scoped_digest(path, keep):
    """The digest of `path` as a node whose scope there is `keep` sees it.

    Identical to `_file_digest` whenever nothing is removed, which is the
    single-class file, the file with no node classes, and every file this
    cannot analyse. That equality is what keeps a digest recorded before
    scoping existed valid under it.
    """
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size, frozenset(keep))
    cached = _scoped_digests.get(key)
    if cached is None:
        for stale in [k for k in _scoped_digests if k[0] == path]:
            del _scoped_digests[stale]
        analysis = _analysis(path)
        removed = _removed_spans(analysis[1], keep) if analysis else []
        if not removed:
            cached = _file_digest(path)
        else:
            lines = analysis[0]
            skipped = set()
            for _, first, last in removed:
                skipped.update(range(first - 1, last))
            digest = hashlib.sha256()
            for number, line in enumerate(lines):
                if number not in skipped:
                    digest.update(line)
            cached = digest.hexdigest()
        _scoped_digests[key] = cached
    return cached


def source_digest(files, root, scope=None):
    """One digest over a node's tracked sources, or None if any is unreadable.

    `files` is the node's own source together with its project-local
    import closure -- the set `node.mtime_ns` is the maximum over -- and
    `root` is the project root every path is expressed against. `scope`
    maps the real path of a source that defines node classes to the names
    of the classes this node depends on there; such a file contributes
    only the text those classes can see (see `_scoped_digest`), so a
    sibling class edited in the same file leaves this digest alone. A
    file with no scope entry contributes its bytes.

    None is not an error to report: it is the answer "cannot vouch for
    anything", and every caller treats it as not current. A source that
    vanished or cannot be read is a build about to fail on its own terms,
    and until it does, its artifact must not be certified.

    Most of what this reads is a handful of small text files. A leaf whose
    source IS its geometry (an `StlNode`'s mesh, a `JScadNode`'s script)
    is bigger, but it is still bounded by the render this replaces.
    """
    scope = scope or {}
    try:
        # Keyed on the relative path, so the same file reached under two
        # spellings -- the loader adds the reference it was given beside
        # the closure's own realpath -- is one entry and not two.
        entries = {}
        for path in files:
            real = os.path.realpath(path)
            keep = scope.get(real)
            entries[os.path.relpath(real, root)] = (
                _file_digest(path) if keep is None
                else _scoped_digest(real, keep))
    except OSError as error:
        logger.debug('No source digest: %s', error)
        return None

    digest = hashlib.sha256()
    for relative, content in sorted(entries.items()):
        digest.update(os.fsencode(relative))
        digest.update(b'\0')
        digest.update(content.encode('ascii'))
        digest.update(b'\n')
    return digest.hexdigest()


def sidecar(artifact):
    """The path of the record vouching for `artifact`."""
    return f'{artifact}{SIDECAR_SUFFIX}'


def describes(name):
    """The artifact a sidecar belongs to, or None if `name` is not one.

    Takes and returns whatever spelling it is given -- a bare name or a
    path -- so a caller can ask about either.

    The sweep needs this: a sidecar is not an artifact of its own and is
    never referenced by the published document, so it lives or dies with
    the file it describes rather than on its own merits.
    """
    if not name.endswith(SIDECAR_SUFFIX):
        return None
    return name[:-len(SIDECAR_SUFFIX)]


def recorded_digest(artifact):
    """The digest recorded when `artifact` was written, or None."""
    try:
        with open(sidecar(artifact)) as stream:
            return stream.read().strip() or None
    except OSError:
        return None


def drop(artifact):
    """Forget whatever was recorded for `artifact`."""
    try:
        os.remove(sidecar(artifact))
    except FileNotFoundError:
        pass
    except OSError as error:
        logger.debug('Could not drop the source record for %s: %s',
                     artifact, error)


def record(artifact, digest):
    """Vouch for `artifact` with `digest`, or for nothing when it is None.

    Always drops first, so a failure anywhere in here leaves no record
    rather than a record from a different source state. No record costs a
    rebuild; a wrong one serves a stale model.
    """
    drop(artifact)
    if digest is None:
        return
    directory = os.path.dirname(artifact) or '.'
    path = sidecar(artifact)
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
        try:
            with os.fdopen(descriptor, 'w') as output:
                output.write(f'{digest}\n')
            os.replace(temporary, path)
        except Exception:
            if os.path.exists(temporary):
                os.remove(temporary)
            raise
    except OSError as error:
        # The artifact is already published and correct; only the record
        # of what produced it was lost. The next build rebuilds it.
        logger.debug('Could not record the sources of %s: %s', artifact, error)


def publish(temporary, artifact, digest):
    """Move a finished artifact into place, with the record that vouches
    for it.

    The ordering is the contract: the old record goes BEFORE the new
    artifact appears, and the new record only after it is in place. An
    interruption at any point therefore leaves an artifact with no record
    -- which rebuilds -- and never an artifact carrying a record from the
    source state that produced the previous one, which would certify a
    stale file the moment those sources came back.
    """
    drop(artifact)
    os.replace(temporary, artifact)
    record(artifact, digest)


def restamp(artifact, mtime_ns):
    """Give a content-verified artifact the current node mtime, so the
    fast path serves every later build.

    Best effort on purpose. Where the artifact filesystem cannot store the
    exact stamp -- the coarse-resolution case build-pipeline already
    covers -- this will not achieve equality, and that is not a failure:
    the artifact is current on the strength of the digest for this build,
    and the fallback is simply consulted again next time. It must not, and
    does not, loop or reconsider.
    """
    try:
        os.utime(artifact, ns=(time.time_ns(), mtime_ns))
    except OSError as error:
        logger.debug('Could not restamp %s: %s', artifact, error)
