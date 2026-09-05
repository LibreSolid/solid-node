## Context

Currency is mtime equality (ADR-006, ADR-050): an artifact is current when its
`st_mtime_ns` equals `node.mtime_ns`, the maximum over `node.files`. Beneath it
sits the content-verified fallback (ADR-060): when equality fails, the build
compares a digest recorded beside the artifact against a digest of the tracked
sources as they are now, and a match restamps rather than re-derives.

`node.files` is the node's own source plus the project-local import closure of
that source (ADR-033), and an internal node unions its children's sets while
assembling. Both `mtime_ns` and the digest are computed over exactly that set,
and the digest is a sorted sequence of `(project-relative path, sha256 of the
file's bytes)`.

The file is therefore the unit of both mechanisms. Two node classes in one file
share the file's mtime — so both fail equality when either is edited, which is
unavoidable and cheap — and share the file's digest, so the fallback cannot tell
them apart and both are re-derived. That second sharing is the only reason the
framework has asked project authors for one node class per file. The pilot has
withdrawn that ask: the framework must be efficient under whatever file layout a
project chooses.

Every stamping site already passes the node's `source_digest` through to
`currency.publish`/`record`; the sidecar is a single hex digest; the sweep keeps
a sidecar with its artifact. None of that needs to know what the digest covers.

## Goals / Non-Goals

**Goals:**

- Editing one node class in a file that defines several rebuilds that node's
  artifacts and the fusions above it, and leaves the other nodes' artifacts
  current.
- Editing anything in such a file that is not the body of another node class —
  imports, constants, helper functions, non-node classes, module-level
  statements — still rebuilds every node in the file.
- A node that refers to a sibling node class in the same file is still rebuilt
  when that sibling changes.
- The hit path is untouched: mtime equality still decides alone, with nothing
  opened, whenever it succeeds.
- The digest of a file that defines one node class or none is byte-for-byte
  what it is today, so no sidecar written by the current release is
  invalidated by upgrading.
- The framework's records stop stating one node per file as a premise, driver
  or recommendation of the cache.

**Non-Goals:**

- Sub-class granularity. A docstring or comment edit inside a node's own class
  rebuilds that node.
- Making a bare path to a multi-node file unambiguous for `solid build` and
  `solid snapshot`, or relieving companion test cases of `node = TheClass`.
  That is a node-reference change (`cli`, ADR-024) and a candidate follow-up.
- Changing the stamp, the sidecar's name, location or format, the sweep, or
  what publication means (ADR-030).
- Changing which files a node tracks (`source-closure-cost` requires that set
  unchanged) or what `solid develop` watches.

## Decisions

### The digest unit becomes a scoped file, not a file

A node carries, beside `self.files`, a **scope**: a mapping from the real path
of a Python source that defines node classes to the set of class names in that
file the node depends on. A leaf's scope is `{realpath(src): {ClassName}}`. An
internal node unions its children's scopes at the same point it unions their
files, so a fusion of two classes from one file has both names under that
file. Files in the import closure that are not a node's own source carry no
scope entry.

`currency.source_digest(files, root, scope)` produces the same sorted sequence
of `(relative path, digest)` entries as today. For a file with no scope entry
the digest is over its bytes, unchanged. For a file with a scope entry the
digest is over its **retained text**: the file's bytes with the line spans of
the *removable* top-level node classes deleted, where a class is removable when
it is a node class defined at the top level of that file, is not in the scope
set, and is not referred to by the retained text (below).

Because the entry format is unchanged and a file whose scope covers every node
class it defines removes nothing, a single-class file's entry is
byte-identical to today's. The recorded digest in every existing sidecar for a
conventional project stays valid — the property that makes this change safe to
ship without a rebuild. A multi-node file's nodes rebuild once after upgrade,
because their recorded whole-file digest no longer matches their scoped one;
that is the safe direction and is stated in the spec.

*Alternative — digest each class body separately and record a per-class
digest.* Rejected: it needs a new sidecar format and a migration, and it makes
the class body the unit, which is wrong — a class depends on everything around
it in the file except its siblings. Subtracting siblings from the file is the
minimal statement of what a node can see.

*Alternative — make the scope part of the stamp, so siblings do not fail
equality at all.* Rejected: the stamp is a filesystem timestamp and has one
value per file; there is nothing finer to store in it. Failing equality and
recovering through the digest is what ADR-060 exists for and costs one hash of
a small file.

### Which classes are removable is answered by the interpreter, not by parsing

Whether a top-level `ClassDef` is a *node* class cannot be read reliably from
the source (bases can be aliased, re-exported or built). The module is already
imported by the time a node is constructed — the node *is* an instance of a
class from it — so the answer comes from the module object, exactly as
ADR-033 resolves the import closure through `sys.modules` rather than by
reimplementing import. The loader's existing `_defined_classes(path, module,
AbstractBaseNode)` names the node classes a file defines; the module for a real
path is found through the same one-shot loaded-module index ADR-058 already
maintains, extended to keep the module name beside the package.

Only node classes are ever removed. A non-node class — a dataclass of
dimensions, a helper — is shared code and stays in every node's retained text.
A node class that is not a top-level statement (defined inside a function or
an `if`) is not removable either, and a file whose module cannot be found, or
whose text does not parse, is digested whole. Every uncertainty resolves to
"keep more text", which can only cause a rebuild.

### A sibling the retained text refers to stays in

After the initial removal, the retained text is scanned for references to any
removed class: an `ast.Name` whose id is the class name, or a string constant
equal to it (which catches `getattr(module, 'Pin')` and registry keys spelled
as the class name). Any removed class so referenced is put back, and the scan
repeats until nothing changes. This is a fixpoint over at most the number of
node classes in the file, on an AST that was already parsed for the import
closure.

It covers the cases that matter: a leaf calling a sibling's static helper, a
node class inheriting from a sibling node class (the base is a `Name` in the
`ClassDef`), a module-level factory that instantiates a sibling and is called
from a node's `render`. A fusion whose children are in the same file is covered
twice — its scope already names them, and its body refers to them.

*Alternative — scan only the node's own class body.* Rejected: a reference
routed through module-level code (`def make_pin(): return Pin()`) would be
missed. Scanning everything retained is both simpler and stricter.

The remaining blind spot is a sibling reached with no identifier or literal
naming it — through a decorator registering into a module-level table that
another node reads by a different key, or a name computed at runtime. That is
the same boundary ADR-033 already draws for `importlib`, computed names and
runtime data files: the static walk cannot see it, and the framework says so
rather than executing project code to find out.

### Spans are lines, and removal is subtraction from the bytes

A class's span runs from the first line of its first decorator (or its `class`
line) through `end_lineno`, inclusive; both are available from the AST on the
supported Python versions. Retained text is the file's raw bytes split into
lines with their endings kept, with those line ranges deleted, and joined. No
re-encoding, no normalisation: when nothing is removed the result is the input,
which is what keeps single-class files' digests unchanged.

The scope set is not recorded in the sidecar. If a node's scope changes — it
starts referring to a sibling, or a sibling is added to or removed from the
file — its digest changes and it rebuilds once. Recording the scope would only
let the build recognise that it *could* have skipped, at the cost of a format
change; the direction of failure is already the safe one.

### One analysis per file, cached like everything else here

The per-file analysis — the top-level node-class spans, and each top-level
statement's referenced identifiers and string constants — is computed once and
cached on `(path, mtime_ns, size)`, the key the import cache and the per-file
digest cache already use, and evicted the same way. The retained-text digest is
cached on that key plus the frozen set of retained class names. An internal
node asking for the digest of a file its children already digested therefore
pays a dictionary lookup, which is what keeps a tree's digests linear, the
concern ADR-060 recorded for the per-file cache.

All of this runs only on the miss path. The hit path — `exists`, then
`stat == mtime_ns` — is not touched by this change, and the test that no source
is read on a hit stays.

### The premise is withdrawn in a new ADR, not by editing old ones

ADR-033 names "one node per file" as a decision driver and ADR-060 digests
whole files. Neither is rewritten; a new ADR records this decision, amends both,
states that the one-node-per-file layout is no longer a premise, driver or
recommendation of the cache, and points at the node-reference ambiguity as the
one remaining property of multi-node files, owned elsewhere.
`docs/architecture.md`'s node-model summary is updated to describe scoped
digests. The shop's skills, which carry the discipline for project agents, are
outside this repository and are corrected in a shop change after this
integrates; the proposal names them so the two changes stay paired.

## Risks / Trade-offs

- **A sibling the node depends on is removed from its digest, so editing the
  sibling leaves a stale artifact current** — the one failure the system cannot
  survive → only node classes are removable; any identifier or string literal
  naming a removed class in the retained text puts it back; a fusion's scope
  names its children regardless; and the tests include a leaf that reaches a
  sibling through a module-level helper and must still rebuild.
- **A dynamic reference the scan cannot see** → the boundary is the one
  ADR-033 already states for computed names and `importlib`; the new ADR and
  the architecture summary say so. This is not widened for the conventional
  project, whose files define one node class and remove nothing.
- **Existing sidecars invalidated by the upgrade, costing every project one
  full rebuild** → a file that removes nothing digests to exactly today's
  value, verified by a test comparing the two; only multi-node files, which
  today rebuild together on every edit anyway, rebuild once.
- **The retained-text analysis costing more than the render it saves** → it is
  one AST walk per file per `(mtime, size)`, on a file already parsed for the
  import closure, and it runs only where a render would otherwise start.
- **Line spans mis-attributing a decorator or a trailing comment** → decorators
  are included from their own `lineno`; a comment between classes belongs to
  the retained text, which at worst keeps more. A `ClassDef` without
  `end_lineno` cannot occur on the supported interpreters.

## Migration Plan

None required. Conventional projects see identical digests. A project with
multi-node files rebuilds those nodes once on the first build after upgrade,
after which they are scoped. Rollback is a downgrade: an older release reads
the same sidecar format and simply rebuilds multi-node files on the first
edit, as it does today.

## Open Questions

None blocking. Whether multi-node files should also gain a declared main
class, so bare-path references stop being ambiguous, is a separate decision for
the pilot and is listed in the proposal as the natural follow-up.
