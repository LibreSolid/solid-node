## 1. Red: the failing tests

- [x] 1.1 `tests/test_simulate_split.py`: `simulate()` runs after `render()` under the current binding and its operations compose innermost (a child translated at rest and rotated in `simulate()` lands where rotate-then-translate puts it)
- [x] 1.2 A render that read nothing runs once per instance across bindings; its operation objects persist and are never swept; `simulate()` operations are swept and re-applied per binding without accumulating
- [x] 1.3 With nothing bound, `simulate()` produces symbolic `$t` expressions; `set_keyframe` makes them numeric; `clear_keyframe` restores the symbolic form
- [x] 1.4 Two assemblies simulating one node keep their operations apart
- [x] 1.5 A `render()` that reads a driver, `time`, or a port keeps today's behaviour (re-render per binding, tagged and swept) and emits one `FutureWarning` per class naming the read
- [x] 1.6 `omit()` inside `simulate()` raises `StructureError`; `omit()` in a once-only `render()` holds across bindings
- [x] 1.7 `__init__` placement still survives and sits before rest placement; a methodless assembly and a subclass delegating to `super().simulate()` both work

## 2. Green: the framework

- [x] 2.1 `solid_node/node/phase.py`: the phase stack (assembly, phase, applied operations, read record) and the read reporter
- [x] 2.2 `base.py`: `rotate()`/`translate()` place through the phase (append vs. motion-region insert, tag); `omit()` refuses the simulate phase; keep `_render_stack` importable
- [x] 2.3 `assembly.py`: `simulate()` no-op; the wrapper sweeps, renders once or legacy, decides on the first run, warns, runs `simulate()`; `time` reports reads
- [x] 2.4 `qualified.py` `DriverDeclaration.__get__` and `ports.py` `BoundPort.value` report reads
- [x] 2.5 Full framework suite, flake8 against the base, sphinx build clean

## 3. Records

- [x] 3.1 `docs/declaring.rst`: replace "Where placement goes" with the render/simulate split; migration bullets
- [x] 3.2 `docs/animation.rst`, `docs/driving.rst`, `docs/assemblies.rst`, `docs/testing.rst`, `docs/api-reference.rst`: drivers, time and ports are read in `simulate()`; the deprecation
- [x] 3.3 `docs/changelog.rst`, `HISTORY.rst`
- [x] 3.4 ADR-066 (render at rest, simulate per instant); notes on ADR-023, ADR-064, ADR-065's neighbour ADR list; `docs/adrs/README.md`; `docs/architecture.md`
- [x] 3.5 Sync delta specs, archive the change, validate
