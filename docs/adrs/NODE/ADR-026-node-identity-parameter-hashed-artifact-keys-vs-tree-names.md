# ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs. Tree-Addressing Names

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-001: Composite Pattern for Node Tree Architecture](./ADR-001-composite-pattern-node-tree-architecture.md)
- [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)

**Related to:**
- [ADR-005: Path-Based Dynamic Module Loading](../BUILD/ADR-005-path-based-dynamic-module-loading.md)
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)

## Context and Problem Statement

Every node needs two different kinds of identity that had been conflated into one:

1. A **build-artifact identity** — the key that names its `.scad`/`.stl` files in the build tree, and which the mtime cache (ADR-006) uses to decide whether a rebuild is needed. Two nodes that would render *different geometry* must have different artifact keys, or one serves the other's stale STL.
2. A **tree/test addressing name** — how a node is referred to in the assembly hierarchy, in the web NodeAPI (ADR-014), and in tests. This is a human/tree concern with no bearing on geometry.

Conflating these produced two real bugs:

- **Stale geometry (#3).** Passing `name=` used to *replace* the parameter-based artifact key. Two instances of the same class with the *same name* but *different parameters* then collided on a single STL file, and one silently served the other's geometry.
- **`OSError: File name too long` (#13).** The artifact key was the constructor parameters serialized *verbatim* into the filename. A single long list-valued kwarg blew past the filesystem's per-component name limit.

Two adjacent identity problems surfaced alongside:

- **Child names were unstable/unhelpful (#16).** A child's name defaulted to its class name, so an assembly with three `Wheel()` children gave three identically-named nodes, useless for addressing in the tree/API/tests.
- **Ambiguous class resolution (#14).** Loading a file by path returned the *first* `AbstractBaseNode` subclass defined in it — an unenforced "main class first" convention that silently loaded the wrong node when a file legitimately defined several.

The framework needed to separate build identity from addressing cleanly, and to make both the child-name assignment and the which-class-is-the-node resolution explicit and correct.

## Decision Drivers

- **Geometry-faithful artifact keys.** Any parameter change — even one buried deep in a long value — must produce a different artifact key, so the cache (ADR-006) never serves stale geometry.
- **Bounded filenames.** The artifact key must not grow without limit with parameter size; basenames must stay within filesystem limits.
- **Name must not affect geometry.** Addressing (`name`) must be fully decoupled from build identity (`uniq_id`); naming a node must never change which artifact it builds.
- **Useful, stable child names.** Children should get meaningful names derived from how the parent refers to them, while an explicit `name=` always wins.
- **Unambiguous class resolution.** When a file defines several node classes, which one is "the node" must be explicit, failing loudly rather than silently guessing.
- **Backward-compatible common case.** Single-node files should keep working with no marker. (An earlier driver — that a *no-argument* node should keep its bare-script basename — was deliberately given up; see the "no-arg special case removed" note in the Decision Outcome.)
- **Class-distinct artifact keys.** Two *different* no-arg node classes must not collide on one artifact. Serializing parameters only, they both produced the empty canonical string and shared a single bare-script-name STL — the same silent stale-geometry failure mode as #3, now between distinct classes rather than distinct parameters — so identity must fold in the node class itself.

## Considered Options

**Artifact key:**
1. Hash of the canonical serialization of the node class plus its parameters, with a decorative readable prefix (chosen).
2. Verbatim parameter serialization embedded in the filename (the prior behavior).
3. Name-derived key (the prior conflation, where `name=` replaced the parameter key).

**Which-class-is-the-node resolution:**
1. Explicit module-level `NODE = MyClass` marker, ambiguity fails loudly (chosen).
2. First-`BaseClass`-subclass-in-file convention (the prior, unenforced behavior).

**Child naming:**
1. Derive from the parent attribute holding the child; explicit `name=` wins (chosen).
2. Class-name-only default.
3. Explicit `name=` required for every child.

## Decision Outcome

**Artifact key = class + parameter hash, name = addressing (the split).** In `AbstractBaseNode.__init__`:
- `self.uniq_id = _build_uniq_id(self.__class__, args, kwargs)` — **always** derived from the node's class plus its constructor parameters, never from `name=`.
- `self.name = name or self.__class__.__name__` — purely tree/test addressing; it never influences `uniq_id`.
- `self._explicit_name = name is not None` — records whether `name=` was actually passed, so a derived child name only ever overrides the class-name default, never an explicit name.

`_build_uniq_id(klass, args, kwargs)` is **always** `<readable-prefix>-<shorthash>` — every node gets a non-empty, class-derived key (the earlier no-arg special case is gone; see below):
- `_canonical_serialization(klass, args, kwargs)` builds an order-stable string that **leads with the class's `__qualname__`**, then positional args in call order, then kwargs **sorted by key** (so kwarg order is irrelevant), comma-joined. This full string is **never truncated**. Leading with the class is what makes two *different* node classes called with identical (possibly empty) args get distinct ids.
- `<shorthash>` = first `_HASH_LEN` (12) hex digits of the sha256 of that full serialization, so any parameter change — including one deep inside a long value — or a **different class** changes the id.
- `<readable-prefix>` = the same serialization sanitized to filesystem-safe characters (`_UNSAFE_PREFIX_CHARS`) and truncated to `_PREFIX_LEN` (60). It is decoration only; identity lives entirely in the hash, so **basename length is bounded** regardless of parameter size (fixes #13). Because `uniq_id` is now never empty, the basename is **always** `f'{script}-{self.uniq_id}'`.

**No-arg special case removed (`e254601`).** The ADR originally kept a no-argument node's bare-script basename (`_build_uniq_id` returning `''`). Empirical evidence retired that: two *different* no-arg node classes defined in the same source file both serialized to the empty canonical string and collided on one bare-script-name STL — whichever built second silently served its geometry to both. This is the exact silent stale-geometry failure mode of the #3 story, now between distinct classes rather than distinct parameters (discovered via `FlushPeg`/`FlushSlot` fixtures that had needed a `part=` workaround kwarg to dodge it). Folding the class `__qualname__` into the canonical serialization makes every node's key non-empty and class-distinct, which is what makes the special case safe to drop.

A related fix (`6ea4622`) ensures positional and keyword forms of the *same* call no longer collide, by serializing positionals and sorted kwargs distinctly.

**Child name = parent-attribute-derived.** `_link_child(child)` sets the child's `_parent` and, **unless the child has an explicit name** (`_explicit_name`), derives `child.name` via `_attr_name_for`: the parent attribute referencing the child (`self.wheel` → `"wheel"`), or `<attr>-<index>` for a list/tuple member. A plain attribute is preferred over a list membership (two passes), private `_`-prefixed attributes are skipped, and the derivation is **idempotent** (a second assemble recomputes the identical name — overwrites, never stacks). It is called both from `InternalNode.as_scad` and from the web NodeAPI (ADR-014), which walks `render()` output without a full assemble.

**Class resolution = explicit `NODE` marker.** `find_class` still returns the sole `AbstractBaseNode` subclass in a single-node file, but when a file defines **several** node classes it must set module-level `NODE = MyClass` to name the node; otherwise it raises `AmbiguousNodeError` instead of silently picking the first. The marker must name a class **defined in that same file** (an imported class is rejected). `TestCase` resolution (`load_test`) is unaffected — the marker rule is for node classes only.

Rationale:

### Artifact key — class + parameter hash + decorative prefix (chosen)
- Good: any parameter change (even deep in a long value) yields a new key — the cache (ADR-006) never serves stale geometry.
- Good: leading with the class `__qualname__` (`e254601`) makes two different no-arg classes distinct, closing the same-file collision where they shared one bare-script STL.
- Good: bounded basename length regardless of parameter size (fixes #13).
- Good: readable prefix keeps filenames glance-friendly without carrying identity.
- Good: kwarg-order-independent and positional/keyword-consistent (`6ea4622`).
- Bad: the hash makes basenames less directly human-readable than a full serialization.
- Bad: even a no-arg node now carries a `-<prefix>-<shorthash>` suffix rather than a bare script basename — the readability of the old special case was traded for its safety.
- Bad: a 12-hex-digit truncation is not collision-proof in principle (practically negligible for one project's build tree).

### Artifact key — verbatim serialization in filename
- Good: fully human-readable; no hashing.
- Bad: unbounded filename length — a long list kwarg raised `OSError: File name too long` (#13). Abandoned.

### Artifact key — name-derived
- Good: short, human-chosen filenames.
- Bad: conflates addressing with geometry — same-named, differently-parameterized instances collided and served stale STLs (#3). Abandoned.

### Class resolution — explicit `NODE` marker (chosen)
- Good: unambiguous; multi-class files fail loudly with an actionable message.
- Good: single-node files need no marker (backward compatible); marker must be same-file (rejects imported-class mistakes).
- Bad: authors of multi-class files must remember to add the marker.

### Class resolution — first-class-in-file convention
- Good: zero ceremony.
- Bad: unenforced ordering silently loaded the wrong node (#14). Abandoned.

### Child naming — parent-attribute-derived (chosen)
- Good: meaningful, stable names (`self.wheel` → `"wheel"`; list members indexed) without manual naming.
- Good: explicit `name=` always wins; idempotent; skips private attrs.
- Bad: a child held only by a private attribute or not referenced by any attribute falls back to the class-name default.
- Bad: `<attr>-<index>` names shift if the list order changes.

### Child naming — class-name-only / explicit-only
- Class-name-only: simple but non-unique for repeated types (#16). Explicit-only: precise but tedious and error-prone. Both rejected in favor of derive-with-override.

## Consequences

- **Build identity and addressing are now orthogonal axes.** `uniq_id` answers "is this the same artifact?"; `name` answers "how do I refer to this node?". Neither leaks into the other — the root fix for both #3 and #13.
- **The cache contract (ADR-006) is sound.** Because the key is a hash of the class plus the full parameter serialization, cache hits imply identical geometry inputs; differently-parameterized nodes — and now differently-*classed* nodes — can never share an STL. Two instances of the **same class with the same args** still share one cached artifact (that intended dedup is unchanged), and `name=` still never influences `uniq_id`.
- **Filenames are bounded and stable.** Basename length no longer depends on parameter size; the readable prefix aids debugging without affecting identity. Every artifact basename now carries a `<readable-prefix>-<shorthash>` suffix — including no-arg nodes, which no longer keep a bare script basename.
- **Child names are useful for the tree, API, and tests.** Derivation runs both under `as_scad` and in the NodeAPI, so the web viewer and tests see the same names; explicit `name=` remains authoritative.
- **Multi-class node files are now first-class and safe.** A file may legitimately define several node classes; the `NODE` marker makes the choice explicit and same-file-scoped, which is also what makes the "one file, several node classes" pattern viable at all — this is the loader-side (ADR-005) extension of the identity model.
- **Small author-facing obligations.** Multi-class files need a `NODE` marker; children needing a specific name still pass `name=`. Both fail-safe (loud error, or class-name fallback) rather than silently misbehaving.
- **Hash truncation is a bounded risk.** 12 hex digits is not cryptographically collision-proof, but is more than sufficient for a single project's artifact set; it can be widened via `_HASH_LEN` if ever needed.

## References

- `solid_node/node/base.py:66-116` — `_canonical_serialization`, `_build_uniq_id` (class-led hash + decorative prefix, both taking `klass` first), `_UNSAFE_PREFIX_CHARS`, `_PREFIX_LEN`, `_HASH_LEN`
- `solid_node/node/base.py:145-210` — `AbstractBaseNode.__init__` name/uniq_id split (`_build_uniq_id(self.__class__, args, kwargs)`), always-suffixed basename construction
- `solid_node/node/base.py:396-417` — `_link_child`, `_attr_name_for` (parent-attribute-derived child names)
- `solid_node/core/loader.py:48-102` — `find_class`, `NODE_MARKER`, `AmbiguousNodeError`, `_resolve_marker`
- Commits: `915bfd0` (decouple `uniq_id` from `name=`, hash the key; #3 + #13), `57e8a4a` (`NODE` marker for multi-class files; #14), `350ef2f` (derive child name from parent attribute; #16), `6ea4622` (fix positional/keyword collision in `_build_uniq_id`), `e254601` (fold the node class into the artifact-key hash; improvements.md #22)
