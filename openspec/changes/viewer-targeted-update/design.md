## Context

`mount()` builds a `WidgetTree` from the fetched document and adds its group to
the scene. `reload()` calls the same `replaceTree()` the initial mount used: it
fetches the document, constructs an entirely new tree, awaits every mesh, then
removes and disposes the old one and reframes the camera from the captured view.
Nothing in the widget can update less than everything.

Two facts make targeted updating cheap. The document is small — 13 KB on
`v8-engine` against 113 MB of geometry — so refetching it in full costs nothing
worth optimising. And every node already carries `mtime` in both published
documents; the widget's `ManifestNode` type simply omits the field.

The consumers differ in what they know. `solid develop`'s reload channel says
only "something changed", so it needs the document-level update. The shop's
floor will forward the path of one completed artifact (S1), so it needs the
artifact-level update. Both are the same reconciliation seen from different
sides, which is why this lives in the framework rather than in the shop.

## Goals / Non-Goals

**Goals:**

- Update exactly what changed: one artifact's geometry, or one document's worth
  of structural difference.
- Preserve the canvas, the camera, the orbit target, the animation clock and
  every untouched mesh across an update.
- Refetch geometry only when `(model path, mtime)` differs from what a node
  already holds.
- Survive a failed fetch with the previous model still on screen and the handle
  still usable.
- Give `solid develop` the benefit immediately, in this repository, rather than
  waiting for the shop.

**Non-Goals:**

- Changing what the viewer can render, or the document schema (PRD section 8).
- Deciding when updates happen. The viewer is told; watching, event forwarding
  and coalescing belong to the host — the floor in S1, the reload channel here.
- Handling deletions as events. The document is authoritative for existence
  (PRD D4); an artifact-level update never removes a node.
- Diffing geometry bytes. The staleness key answers this without reading a mesh.

## Decisions

**D-1 — Two update entry points, not one.**
`artifactChanged(path)` and `manifestChanged()` do different work with different
inputs, and collapsing them would force one to guess. An artifact event names a
file and implies no structural change: the viewer refetches that mesh and swaps
it. A document event implies structure and no particular geometry: the viewer
reconciles the tree and lets the staleness key decide what to fetch. Alternative:
a single `update(hint?)`, rejected because the two paths share no logic beyond
"keep the camera" and a union-typed argument hides which invariants hold.

**D-2 — `(model path, mtime)` is the geometry identity, held per node.**
Each tree node records the `(model, mtime)` pair it loaded. On reconciliation a
node refetches only when the incoming pair differs. Both halves are load-bearing:
builds are parameter-keyed, so a parameter change moves the `model` path without
touching source mtime, while an ordinary edit moves the mtime under an unchanged
path. A touched-but-unedited source causes one harmless refetch; the reverse —
serving a stale mesh — would be silent and wrong. Alternative: an ETag or
content hash per artifact, rejected because it needs a request per node to
learn anything, and the document already carries both fields for free.

**D-3 — Reconciliation is positional within a parent, keyed by node name.**
The document's nodes carry names that are already stable and unique among
siblings (the framework derives them from the parent's attribute holding the
child). Matching incoming children to existing ones by name lets a node keep its
mesh, its group and its identity across a structural edit; unmatched incoming
nodes are built, unmatched existing nodes are removed and disposed. Alternative:
matching by index, rejected because inserting a child at the front would
renumber every sibling and refetch the whole subtree.

**D-4 — Operations and colour are applied in place, with no fetch.**
Operations already recompute from scratch on every frame, so a changed operation
list needs only assignment. Colour changes replace the material, which is cheap
and does not touch geometry. This is what makes a placement edit free, and it is
directly PRD acceptance criterion 6.

**D-5 — A failed update is contained.**
Both methods reject on a failed fetch and leave the scene exactly as it was: no
node is removed before its replacement geometry has arrived, and a rejected
promise never leaves the tree half-reconciled. The handle stays usable, so the
next update recovers on its own. This is the framework half of PRD acceptance
criterion 3; the shop half — not unmounting the host on error — is S2.

**D-6 — The API version is raised to 2.**
The existing rule raises the version when the handle changes incompatibly. This
change is additive, so an unmodified host keeps working, but a host that
*requires* targeted updates needs to detect them, and reading a declared version
is what the package already offers for that. Raising it beats feature-sniffing
methods on a handle. The rule itself is restated to cover a capability addition,
so the next reader is not left thinking a bump implies breakage. Alternative:
staying at 1 and letting hosts test `typeof handle.artifactChanged`, rejected as
an interface contract expressed by duck-typing where a declared one exists.

**D-7 — The development shell adopts `manifestChanged()` now.**
`solid develop`'s reload channel carries no artifact identity, so the document
update is the one it can use, and it is a strict improvement: unchanged meshes
are no longer refetched or re-uploaded. It also means the new path is exercised
by the framework's own e2e tests before the shop ever calls it. `reload()`
remains for hosts that want a full rebuild, and the reload channel's protocol is
untouched.

## Risks / Trade-offs

- **Name-keyed matching inherits the framework's naming rules.** Two siblings
  that resolve to the same name would collide during reconciliation → mitigation:
  the framework already derives sibling-unique names and tests them; the viewer
  falls back to rebuilding a subtree it cannot match unambiguously rather than
  guessing.
- **In-place mutation is harder to reason about than replacement.** A partially
  applied update is a class of bug `replaceTree()` cannot have → mitigation:
  D-5's ordering (fetch, then mutate) and unit tests that assert object identity
  of untouched nodes, not just rendered output.
- **`mtime` is a float from the filesystem.** JSON round-tripping and
  filesystem resolution differences could make equal artifacts compare unequal →
  mitigation: compare the raw values as the document carries them; a spurious
  inequality costs one refetch, which the design already accepts.
- **The e2e proof needs a real browser.** The assertion that matters — the
  canvas element survives — cannot be made in jsdom → mitigation: the widget e2e
  suite already drives headless chromium through playwright and skips cleanly
  where it is unavailable.
- **The shop is not ready to consume this.** Nothing breaks — the shop still
  calls `reload()` until S2 — but the capability sits unused until then →
  accepted; F3 is deliberately independent so it can land while F2 proceeds.
