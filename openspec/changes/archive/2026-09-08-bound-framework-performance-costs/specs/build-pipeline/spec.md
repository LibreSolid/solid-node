## ADDED Requirements

### Requirement: One fresh builder owns one stable source generation

The build supervisor SHALL start a builder in a fresh interpreter and SHALL allow that builder to perform every artifact pass needed to complete one stable source generation. A source generation SHALL be identified by the complete observable metadata identity of the loader entry/facade, imported project-module closure, and recursively discovered node source set, not by the maximum source mtime alone.

The loader SHALL bracket source execution: it SHALL observe the entry/facade and every project-local module before Python reads or executes it and SHALL require an uncached post-load observation to match after instantiation. A module discovered during import SHALL join through that same pre/post handshake. Project-local module execution SHALL NOT accept timestamp-and-size bytecode freshness as sufficient: it SHALL compile coherently observed source bytes or validate bytecode against a source content identity that rejects a same-size edit with restored mtime. External-library bytecode behavior is unchanged. A changed identity SHALL abandon the loaded classes and retry in a fresh interpreter; a first observation taken only after load SHALL NOT certify them.

Artifact-producing phases SHALL likewise compare an uncached observation before and after work for the contributors known to that producer. The agreed recursively assembled source set, including foreign geometry sources, SHALL then be sealed as the generation. One generation SHALL own one loaded root instance and one full assembly; retained artifact continuation SHALL resume the same memoized tree without re-import, reinstantiation, structural re-render, reassembly, or fusion reordering. The builder SHALL compare one fresh distinct-path census with that generation before every retained artifact pass, immediately before and after an asynchronous renderer wait, and immediately before publication. All node checks within one phase SHALL share its census instead of restatting the same closure per node. A changed, replaced, missing, newly selected, or newly imported contributor SHALL stop geometry work with the source-changed outcome before stale work is published. The next attempt SHALL begin in another fresh interpreter.

The project build lock SHALL continue to cover every artifact-producing phase and publication, while watches, callbacks, and project tests remain outside it. Every subprocess the supervisor does start SHALL retain the fresh-native-state and plain reconstructable-input guarantees of the build-isolation contract. A one-shot failure and an initial development failure SHALL end with their existing failed outcomes. A watch-reload failure SHALL record its error, release the build lock, perform no further geometry, wait under the existing recovery watcher, and exit source-changed after an edit so the next load is fresh; it SHALL NOT cause an immediate failed-child respawn loop.

#### Scenario: A multi-artifact generation pays one builder startup

- **WHEN** a stable cold model requires twenty-four sequential artifact render passes before its document is current
- **THEN** one spawned builder process performs those passes and reaches the complete current outcome without twenty-four fresh imports, and every published artifact equals the ordinary per-pass result

#### Scenario: A same-maximum edit ends the retained worker

- **WHEN** a contributing source is replaced during a retained builder's artifact passes while another contributor preserves the same maximum mtime
- **THEN** the per-contributor generation observation disagrees, the retained process publishes no document for its stale classes, reports source-changed, and a fresh process loads the edit

#### Scenario: Replacement during import cannot bless stale classes

- **WHEN** a project-local module is atomically replaced after Python read its old bytes but before loading and instantiation finish
- **THEN** the loader's pre/post identity handshake disagrees and the child retries fresh rather than sealing the replacement's disk identity around the old live classes

#### Scenario: Restored-mtime source cannot enter through stale bytecode

- **WHEN** a project module has a valid timestamp-and-size `.pyc` and its source is changed to different same-size bytes with restored mtime
- **THEN** the builder executes the current source or rejects the load generation, and never publishes geometry produced by the stale bytecode

#### Scenario: Artifact continuation keeps one assembled tree

- **WHEN** one stable generation needs several artifact passes
- **THEN** its root constructor, structural render, full assembly, and exact-fusion order occur once, and later passes continue pending artifacts on that same linked tree

#### Scenario: One-shot failure recovery gets a new interpreter

- **WHEN** a one-shot retained builder renders one artifact and a later artifact or document step fails
- **THEN** the failure is reported through the existing error outcome, the process exits, and a subsequent repair is loaded by a new spawned interpreter

#### Scenario: A watch reload failure waits instead of spinning

- **WHEN** a retained development worker fails during a reload after the initial build succeeded
- **THEN** it writes the error, releases the lock, waits without geometry for a relevant edit, exits source-changed on that edit, and causes neither an immediate respawn loop nor repeated viewer restart

#### Scenario: Lock contention does not widen

- **WHEN** a second process attempts to build while the retained worker is producing a stable generation
- **THEN** it waits on the same project lock until artifact work and publication finish, while a callback or source-change wait holds no lock

### Requirement: Stable-generation work is shared without redundant writes

Within one sealed source generation, the system SHALL maintain a request-local metadata census. One census SHALL observe each distinct tracked contributor once and SHALL serve overlapping node source-fingerprint and digest work only for that observation. A later currency or publication boundary SHALL take a fresh census before deciding that the generation is still stable. No census SHALL survive the builder process or a generation change.

Rigid base SCAD generation SHALL occur at most once for the currently published full source/currency identity at a canonical artifact path in an assembly, regardless of how many repeated instances reference that artifact. A different identity at the same path SHALL replace what is current; a later return to an earlier identity SHALL NOT be reused merely because that identity appeared historically.

When non-rigid, non-flexible assembly instances produce several desired SCAD states for one canonical path during an assembly, every instance SHALL retain its distinct in-memory composition, placement, node address, and parent-document contribution. Only the last desired text, timestamp, digest, and fingerprint for that path SHALL reach artifact comparison at successful assembly completion, in the order of the paths' last occurrences. The resulting file SHALL match the historical last-occurrence value. Flexible publication and direct generation outside an assembly phase SHALL retain their existing immediate behavior.

The system SHALL verify the complete source generation immediately before and after making final coalesced values visible, while the assembly remains inside the project build lock. A body or pre-publication source failure SHALL discard the pending values. A write failure SHALL follow the existing assembly failure path; a post-publication source mismatch SHALL prevent viewer-document publication and end the generation source-changed.

Atomic text and currency publication SHALL compare the desired state with the state on disk. When SCAD bytes, timestamp, and currency record already match, the system SHALL replace none of them. When source metadata changes but node-scoped contents remain equal, the system SHALL perform the required restamp and currency-record refresh without rewriting identical SCAD bytes. Write suppression SHALL NOT bypass source-fingerprint comparison, content verification, lock ownership, generation checks, or atomic replacement of changed content.

#### Scenario: Repeated rigid parts generate one SCAD artifact

- **WHEN** many rigid instances share one artifact identity in a stable assembly
- **THEN** their one base SCAD artifact is generated at most once for that source/currency identity, while every instance retains its own tree name and placement in the published document

#### Scenario: Repeated non-rigid path publishes its final value once

- **WHEN** non-rigid, non-flexible assembly instances produce different SCAD text at one canonical path under one stable source generation
- **THEN** every instance contributes its own in-memory composition, only the last desired path value reaches comparison in last-occurrence order, and a second and third unchanged build replace neither that SCAD nor its currency record

#### Scenario: Historical identity is not current identity

- **WHEN** one rigid canonical path is produced under full source/currency identities A, then B, then A in one generation
- **THEN** all three desired states reach publication in order and the final A is not skipped because an earlier A was remembered

#### Scenario: Coalesced publication cannot certify a changed generation

- **WHEN** assembly fails before final publication or a contributor changes immediately before or during coalesced publication
- **THEN** pending values are discarded before publication when possible, no viewer document certifies stale work, and a detected source mismatch ends the generation source-changed

#### Scenario: Flexible and direct generation remain immediate

- **WHEN** flexible bindings emit several snapshot imports at one SCAD path or a caller generates SCAD without an assembly phase
- **THEN** each call retains its existing immediate publication behavior and is not folded into non-rigid assembly coalescing

#### Scenario: A shared source is observed once per census

- **WHEN** hundreds of nodes' source closures contain the same project file
- **THEN** one generation census performs one filesystem metadata observation of that file and each node receives the same observation, while the next generation boundary observes it afresh

#### Scenario: Unchanged text is not replaced

- **WHEN** a complete build computes SCAD bytes, timestamp, and a currency record identical to those already on disk
- **THEN** the existing SCAD and currency files retain their inode, mtime, and ctime

#### Scenario: Metadata-only source change keeps currency correct

- **WHEN** a tracked source's metadata changes while its node-scoped content stays byte-identical
- **THEN** content verification refreshes the artifact stamp and currency record as required, without rewriting byte-identical SCAD content or reporting stale geometry current

## MODIFIED Requirements

### Requirement: Superseded and redundant builds do not publish

Having acquired the build lock, a builder SHALL re-evaluate whether its work is still needed before rendering or publishing, using the complete per-contributor source-generation observation together with the mtime-equality and source-fingerprint rules already governing artifact currency.

- When any source identity on disk differs from the source generation represented by the builder's loaded classes, the builder SHALL publish nothing and SHALL report the same source-changed outcome an ordinary edit produces, so its lifecycle loop rebuilds from current source. Equality of the aggregate maximum mtime SHALL NOT override a contributor disagreement.
- When the published artifact set is already current for the loaded node, the builder SHALL publish nothing. A one-shot build SHALL report the model current; a watching builder SHALL go on waiting for the next source change rather than ending.

Currency SHALL be judged where a consumer reads artifacts — the build directory itself, which is now the only place a builder writes. Persistent artifact currency SHALL remain derived from source/artifact timestamps, the source fingerprint, and the node-scoped content fallback; the system SHALL NOT record a generation counter or source identity inside a published viewer document. The source-generation observation is process-local and certifies only whether the live classes may continue working.

#### Scenario: The newest source wins

- **WHEN** a build against older source finishes after a build against newer source has published the same project
- **THEN** the older build publishes nothing and the published model matches the newer source

#### Scenario: A contributor changes beneath the same maximum

- **WHEN** a retained builder's contributor changes while the source set's maximum mtime remains equal
- **THEN** the changed contributor's metadata identity invalidates that process-local generation and the builder publishes nothing from the old classes

#### Scenario: A redundant build publishes nothing

- **WHEN** a builder acquires the lock and the published artifact set is already current for its sources
- **THEN** no artifact is rendered, no publication occurs, and the outcome reports the model current

#### Scenario: A watching builder finds nothing to do

- **WHEN** a builder that watches for source changes acquires the lock and the published set is already current
- **THEN** it publishes nothing and keeps watching, and the development loop does not respawn it

#### Scenario: An ordinary change still builds

- **WHEN** a builder acquires the lock, its complete source generation is the newest on disk, and the published set is not current for it
- **THEN** it renders and publishes exactly as it does without contention
