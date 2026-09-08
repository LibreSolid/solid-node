# MM2 manifest digest diagnosis

The `current-candidate-v4` MM2 manifest mismatch is fully explained by
serialized source timestamps, not geometry, model/piece references, P06
naming, or the AR08 import-path correction.

The formal v4 record retained `f9f904f826eca8fce579fb6cb440f22342609f3ca8215ef9ac8d4d3be2598919`
(173,857 bytes), while the immutable planning baseline and v3 record retained
`d1ba8ddfdfc993b1d56f180877a3715a77e0e536dd6817a5e573928df88ec338`
(173,799 bytes). The project's selected input bytes, Git HEAD
`a81f86267329754243b292a8ce83ca6ff8e8d438`, and clean status remained the
same. The catalogue identity did not retain source mtimes and intentionally
excluded `_build`.

A fresh disposable current build reproduced the formal v4 `f9f9...8919`
digest. Starting from that current JSON document, a read-only reconstruction
replaced only recursively aligned `mtime` values in its `root` tree with the
values preserved by the original project's older version-3
`_build/viewer.json` (`70c4f5165bd74ee5463570f9667a78875d2d43d2eb2ba9ea0be86e0004108c08`).
All other v4 fields were retained. Of 576 `mtime` fields, 226 changed. Python's
default `json.dumps(document).encode()` then produced exactly 173,799 bytes
with SHA-256 `d1ba...c338`, the digest retained by both the planning baseline
and v3.

The formal v3 and v4 complete STL filename/SHA maps are equal, and their
aggregate artifact values are equal: 105 STL files, 47,946,420 STL bytes,
99 distinct pieces, and 443 piece instances. The baseline did not retain a
complete STL filename/SHA map, so this does not remove that cross-baseline
map-level blind spot. It does establish that the available manifest-digest
exception is metadata-only.

The machine-readable record
`mm2-manifest-mtime-diagnostic.json` contains every changed JSON path and both
timestamp values, the formal identities, and the independently resolved
4bc/current `solid_node.__file__` and serializer/builder/loader/base/pieces
hashes. `mm2-manifest-mtime-reconstruction.txt` preserves the exact
reconstruction command and observed output. These are separate diagnostic
records: no formal v4 raw record was changed and no section was cherry-picked.
