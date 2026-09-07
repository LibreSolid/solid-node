# ADR-071: Node-Scoped Content Currency

**Status:** Accepted
**Date:** 2026-09-05
**Amends:**
- [ADR-060: Content-Verified Currency Beneath the Mtime Rule](./ADR-060-content-verified-currency-beneath-the-mtime-rule.md)
- [ADR-033: Import-Closure Source Set and Up-To-Date Leaf Path](./ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
**Amended by:** [ADR-081: Per-Contributor Metadata Guards Aggregate-Mtime Currency](./ADR-081-per-contributor-metadata-guards-aggregate-mtime-currency.md) — source-set metadata guards the path above the scoped digest
**Depends on:**
- [ADR-058: Indexed Package Lookup for Source Closures](./ADR-058-indexed-package-lookup-for-source-closures.md)
- [ADR-067: Fresh-Interpreter Build Subprocesses](../BUILD/ADR-067-fresh-interpreter-build-subprocesses.md)

## Context and Problem Statement

Currency is mtime equality (ADR-006, ADR-050), and beneath it ADR-060 placed a
content-verified fallback: when an artifact's stamp does not match the node's
source mtime, a digest of the node's tracked sources is compared with the digest
recorded when the artifact was written, and a match restamps instead of
re-deriving. That digest was a sorted sequence of `(project-relative path,
sha256 of the file's bytes)` over `node.files`.

The file was therefore the unit of both mechanisms. Two node classes defined in
one file share the file's mtime — unavoidable, and cheap, since it only sends
both to the fallback — and shared the file's digest, so the fallback could not
tell them apart: editing either re-derived both, and every fusion above them,
at leaf-tessellation cost.

That second sharing was the whole reason the framework asked project authors to
keep one node class per file. ADR-033 recorded it as a decision driver
("solid-node's premise is one node per file, so that editing one file rebuilds
one node"), and the shop's machining and API skills stated it as "the
framework's premise, not a style preference." The pilot has withdrawn the
premise: the framework does not get to impose a file layout on a project in
order to cache well. It must be efficient under whatever layout the project
chooses.

## Decision Drivers

- The hit path must not change. `exists`, then `stat == mtime_ns`, opening
  nothing, is taken for every node of every build.
- Currency may fail in only one direction. A source a node depends on that
  changed must never be reported current — the failure ADR-006 says the
  system cannot survive.
- Nothing recorded by the current release may become invalid. A conventional
  project must not pay a migration rebuild for a change that does not
  concern it.
- No new sidecar format, no change to the stamp, the sweep or publication
  (ADR-030).

## Considered Options

1. **Subtract the sibling node classes from the file before digesting it**
   (chosen)
2. Digest each class body separately and record a per-class digest
3. Carry the scope in the stamp so siblings never fail equality
4. Keep the file as the unit and keep the one-node-per-file discipline

## Decision Outcome

Chosen: **the digest unit is the file as one node sees it**, not the file.

A node carries a *scope* beside `node.files`: the real path of its own Python
source mapped to the set containing its own class name. An internal node unions
its children's scopes at the point it already unions their files, so a fusion of
two classes from one file has both names under that file.

`currency.source_digest(files, root, scope)` produces the same sorted sequence
of entries as before. A file with no scope entry — every module in the import
closure that is not a node's own source, and every non-Python source — is
digested by its bytes, unchanged. A file with a scope entry is digested as its
**retained text**: the file's bytes with the line spans of the *removable*
top-level node classes deleted, where a class is removable when it is a node
class defined as a top-level statement of that file, is not in the scope set,
and is not referred to by the retained text. Module-level statements, imports,
constants, functions and non-node classes are never removed, so an edit to
anything the classes share still invalidates every node in the file.

**Which classes are node classes is answered by the interpreter, not by
parsing.** The module is already imported when any node is constructed — the
node is an instance of a class from it — so the loader's enumeration of the
node classes a file defines is consulted through the loaded-module index
ADR-058 already maintains, extended to keep the module name beside the package.
Bases can be aliased, re-exported or built; the source cannot say reliably what
the module object can.

**A sibling the retained text refers to stays in.** After the initial removal,
every retained top-level statement is scanned for the removed classes' names,
as `ast.Name` identifiers or as string constants, and any so mentioned is put
back; the scan repeats until nothing changes. A base class, a module-level
helper that instantiates a sibling and is called from a node's `render()`, and
`getattr(module, 'Sibling')` are all caught. Only a class the rest of the file
never names is left out.

**Every uncertainty keeps more text.** A file whose module cannot be found,
whose text does not parse, or that defines no node class the interpreter
recognises is digested whole. A node class that is not a top-level statement is
not removable. A file that removes nothing digests to exactly the value it did
before — the raw bytes, split on the tokenizer's line boundaries and rejoined
without normalisation — which is what makes the change safe to ship: every
sidecar recorded by the previous release for a single-class file is still
valid, and only the nodes of multi-node files rebuild once, because their
recorded whole-file digest no longer matches their scoped one.

The scope is not recorded in the sidecar. A node whose scope changes — it starts
naming a sibling, or a sibling is added to or removed from the file — digests
differently and rebuilds once, which is the safe direction and costs no format
change.

The analysis is one AST walk per file, cached on `(path, mtime_ns, size)` like
the import cache and the per-file digest cache, and the retained-text digest is
cached on that key plus the frozen set of retained names, so a tree's digests
stay linear in its files. All of it runs on the miss path only.

### Why not per-class digests (option 2)

A class body is the wrong unit: a class depends on everything around it in the
file except its siblings. Subtracting siblings is the minimal statement of what
a node can see, and it needs no new sidecar format and no migration.

### Why not scope in the stamp (option 3)

The stamp is a filesystem timestamp with one value per file; there is nothing
finer to store in it. Failing equality and recovering through the digest is what
ADR-060 exists for, and costs one hash of a small file.

### Why not keep the discipline (option 4)

Because it was the cache dictating the project's architecture, and the pilot
has said it may not.

## Consequences

- The one-node-per-file layout is no longer a premise, driver or
  recommendation of the cache. ADR-033's driver is withdrawn; its decision —
  the import-closure source set and the up-to-date leaf path — stands
  unchanged. ADR-060's mechanism stands; its unit changes from the file to
  the file as one node sees it.
- What remains true of a multi-node file is a property of node *references*,
  not of currency: a bare path to such a file is ambiguous for `solid build`
  and `solid snapshot` because there is no way to declare a main class
  (ADR-024, the `cli` capability), and each companion test case must name its
  class. That is owned by the reference grammar and is a separate decision.
- The blind spot is a sibling reached with no identifier or literal naming it
  — a registry filled by a decorator and read under a different key, a name
  computed at runtime. It is the boundary ADR-033 already draws for
  `importlib`, computed names and runtime data files: the static walk cannot
  see it, and the framework says so rather than executing project code to find
  out. The conventional single-class file removes nothing and has no such
  window.
- Measured on v8-engine (46 exact parts, 119 recorded rigid artifacts): every
  sidecar recorded by the previous release still matched under the scoped
  digest, and a settled rebuild re-derived nothing. With `Piston` and
  `WristPin` moved into one file: editing `Piston`'s body re-derived Piston's
  `.stl` and `.brep` and nothing else; editing `WristPin`'s body re-derived
  WristPin's and nothing else; editing a line both can see re-derived both.
- The test fixture for in-process rebuilds must evict the scratch project's
  modules between builds, which a real build gets for free from ADR-067's
  fresh interpreter; without that the rebuilt class is the one first imported
  and an edit is invisible to geometry. The existing currency fixture now does
  so and is stronger for it.

## References

- `solid_node/currency.py` — `_analysis`, `_removed_spans`, `_scoped_digest`,
  `source_digest`
- `solid_node/node/sources.py` — `source_scope`, `node_classes_in`, the
  extended loaded-module index
- `solid_node/node/base.py` — `scope`, `source_digest`
- `solid_node/node/internal.py` — scope union beside the file union
- `tests/test_node_scoped_currency.py`
- OpenSpec change `node-scoped-currency`, capability `build-pipeline`
