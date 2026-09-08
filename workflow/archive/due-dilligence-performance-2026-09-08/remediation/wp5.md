# WP5 — Bounded flexible faceted geometry (P04)

## Scope

WP5 changes only the flexible faceted-geometry seam:

- `solid_node/test.py` owns an access-ordered `OrderedDict` working set with
  the internal initial limit of 64 entries;
- `solid_node/node/flexible.py` supplies a narrow private coherent snapshot
  for that seam; and
- `tests/test_flexible_cache_performance.py` proves the bounded behavior and
  identity separation.

The cache holds only an evaluated base mesh long enough to derive local bounds
and an admitted Manifold, then retains the latter two objects.  It does not
persist anything.  Eviction drops the mapping's least-recently-used Python
references.  It does not cache flexible Boolean verdicts and does not change
`FlexibleNode._exact_solid()`'s existing per-instance, last-binding memo.
The public zero-argument `base_mesh()` override seam remains unchanged. The
stock `FlexibleNode.base_mesh()` path uses the private coherent snapshot so a
cache miss renders exactly once. An overriding subclass may define geometry the
serialized molejo spec cannot certify, so it continues through its public
override uncached rather than silently receiving stock geometry or an unsafe
cache hit.

## Identity and coherent evaluation

The private snapshot key uses full values, not a shortened artifact/display
hash: technology; defining module and real source path; current full source
fingerprint and content digest; the full canonical constructor/declarative
identity that produced `uniq_id`; exact sorted binding `repr` values; and a
SHA-256 over canonical serialized shape spec.  An unobservable source causes
a coherent uncached evaluation rather than a hit.

`_faceted_cache_snapshot()` renders one current shape and serializes that very
shape for the identity. On the stock path the test-framework seam passes that
shape and its values to `_snapshot_mesh`, so the mesh cannot come from a
second, potentially different `current_shape()` call. Existing currency digest
memoization remains the source-byte reuse mechanism; WP5 adds none.

## Red/green proof

The red run in [wp5-red.log](wp5-red.log) recorded the legacy failure: 80
interleaved reads across three useful bindings constructed 80 meshes, and its
one-entry key conflated forced short hashes and source/spec changes.  The
focused green commands and results are recorded in
[wp5-green.log](wp5-green.log).

The new structural coverage proves:

- 80 interleaved reads across three bindings construct exactly three meshes
  and admitted Manifolds, while returning each binding's original bounds and
  volume;
- source/module and forced structural-id collisions do not share;
- a forced shortened binding-hash collision, a source identity change, and a
  serialized-spec change each miss;
- an unobservable source is never retained, signed zero remains a distinct
  canonical binding value, and one cache miss renders once before evaluating
  exactly that rendered shape;
- a three-entry test limit retains at most three entries, promotes a hit by
  access order, evicts the least-recent entry, and recomputes it correctly on
  revisit;
- 128 distinct structural identities exercise the default 64-entry limit;
  every insertion remains bounded and a revisit of the first evicted identity
  reproduces its bounds and Manifold volume;
- a subclass overriding public `base_mesh()` supplies its translated geometry
  on every faceted read and remains uncached, rather than being replaced by the
  stock private snapshot;
- flexible Booleans still run twice for two comparisons after geometry reuse;
  exact geometry remains one memo per instance and replaces only that
  instance's last binding.

## Provenance and limits

- Planning source: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on branch
  `performance-analysis`.
- Interpreter: `/home/asa/devel/libresolid-studio/.venv/bin/python`, invoked
  from this framework worktree with `PYTHONPATH="$PWD"`.
- Candidate source/test SHA-256 after the green run:
  - `solid_node/node/flexible.py`:
    `d8c0bd62df8f204d2fe674c42865fb1cd2a107752cc57e4a17509e76ba77d76c`
  - `solid_node/test.py`:
    `9cd23a3e39dd1bc0891e6dd673fb9f5f6002df7f1772f34c794bf83539feea16`
  - `tests/test_flexible_cache_performance.py`:
    `dfbfba45267d397270fb14f603057534ab1221974444427941c818355bbc64ea`
  - `tests/test_molejo_adapter.py`:
    `a21bf6917f6e37c5c906975e9d7d46397dc9b171b2737abd4e90ef5df3372d02`
- This is a structural correctness proof, not a universal wall-clock or RSS
  claim.  A long trajectory may recompute evicted bindings by design.
- No original catalogue project, historical audit asset, OpenSpec task,
  progress record, spec, or ADR was edited by WP5.
