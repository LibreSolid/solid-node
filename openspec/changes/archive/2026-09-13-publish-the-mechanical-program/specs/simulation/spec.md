## MODIFIED Requirements

### Requirement: A running root's simulation owns every driver and joint coordinate

Under a root assembly declaring `time = Time.running()` the simulation
SHALL own a BANK holding every driver AND every joint coordinate of the
linked tree — on assemblies and leaves alike, class-declared and
site-declared joints alike — keyed by the qualified id the driver
enumeration and the port enumeration produce: the instance path joined
with the driver's name, the joint's name, or `<joint>.<coordinate>` for a
joint owning several. `sim.state` SHALL return the whole bank by id, as a
fresh mapping. Plain ports and derived coordinates SHALL NOT be in the
bank: they are computed by the ordinary enumeration from the bank on
every tick. There SHALL be no separate memory bank, and the author SHALL
declare no state. An id two declarations of one node would both claim
SHALL be refused at construction naming both.

The initial bank SHALL be the untimed rest pose at the requested driver
values: construction SHALL bind the driver values (the declared defaults,
overridden by `state=`) with `time` at zero, enumerate the tree once
exactly as an untimed root is enumerated — the author's `simulate()` and
every relation solving as they do today — and read every joint coordinate
off the tree. A joint coordinate that rest render leaves unbound SHALL be
refused at construction naming the node path and the coordinate and
saying that the run owns every joint coordinate and needs a rest value for
each.

From the moment construction completes, every bank coordinate SHALL be
bound by the run — through `set_state` with the whole bank and `time`,
the run recorded as the binder — so that `render()` and `simulate()` stay
pure functions of the bound snapshot: rendering, inspecting, or binding
the same snapshot again SHALL advance nothing and change no value. An
author's `simulate()` that binds a run-owned coordinate SHALL be refused
as doubly bound naming the class and the coordinate, at construction; a
binding written under a guard that finds the coordinate already bound is
not a binding and SHALL keep working.

`sim.time` SHALL remain `tick * dt`, and every instant, duration and
period SHALL keep the whole-tick rule.

ONE simulation SHALL own a tree at a time, and the newest SHALL take it.
Constructing a simulation over a tree a previous run owns SHALL RELEASE that
ownership before the rest render: the run's claim on the tree and on every
joint coordinate it bound is dropped, so the rest render finds a tree no run
owns and poses it exactly as it would a tree no run ever touched. A released
run SHALL REFUSE to advance, naming both simulations and saying its bank no
longer describes the tree, rather than binding over the simulation that now
owns it. This is what makes a fresh simulation per call possible over a node
built once and shared — the contract the scenario base states — and it does
not weaken the doubly-bound refusal: an author's `simulate()` binding of a
run-owned coordinate is still refused, because a release happens only before
the rest render of a NEW simulation and never during one.

A declared driver or joint coordinate whose qualified id is `time` SHALL be
REFUSED at construction, naming the id and the reservation: `time` is the one
snapshot entry that is global by contract, the run binds it beside the whole
bank on every tick, and a bank entry under that id would be silently
overwritten.

#### Scenario: The bank lists joint coordinates by qualified id

- **WHEN** a simulation is constructed over a running root declaring
  drivers `crank` and `lever`, its own joint `spindle` wired into a
  child's plain port `wheel.turn`, children `first` and `second` each
  owning a `turn` joint on a leaf, and a child `slide` owning a `travel`
  joint
- **THEN** `sim.state` has exactly the keys `crank`, `lever`, `spindle`,
  `first.turn`, `second.turn` and `slide.travel` — the plain port
  `wheel.turn` among them nowhere

#### Scenario: The initial bank is the rest pose

- **WHEN** the same root states `crank.drives(first.turn, ratio=2.0)`,
  `first.turn.drives(second.turn, ratio=-1.5)` and
  `lever.drives(slide.travel, law=tooth_window)`, and the simulation is
  constructed with `state={'crank': 10.0}`
- **THEN** the initial bank reads `first.turn == 20.0`,
  `second.turn == -30.0` and `slide.travel` equal to the law at the
  lever's default — the values the untimed root poses at

#### Scenario: Rendering and rebinding advance nothing

- **WHEN** a running simulation has moved its crank for ten ticks and the
  caller then renders the node, reads every coordinate, and calls
  `set_state` with `sim.state` and `time=sim.time` once more
- **THEN** `sim.state`, `sim.tick` and every joint coordinate on the tree
  are unchanged, and the next tick continues from the same bank

#### Scenario: An author binding of a run-owned coordinate is refused

- **WHEN** a running root's `simulate()` binds `self.first.turn` from its
  crank unconditionally
- **THEN** construction is refused naming that class and `first.turn` as
  doubly bound, saying the running simulation owns it and a law belongs
  in a relation

#### Scenario: A guarded rest default keeps working

- **WHEN** a running root's `simulate()` reads `self.slide.travel.value`,
  finds it `None` and binds `4.0`
- **THEN** construction succeeds, the bank reads `slide.travel == 4.0`, and
  the guard never binds again while the run owns the coordinate

#### Scenario: An unbound joint coordinate is refused at construction

- **WHEN** a running root's rest render leaves a joint coordinate unbound —
  nothing drives it and no `simulate()` binds it
- **THEN** construction is refused naming its qualified id and saying the
  run needs a rest value for every joint coordinate

#### Scenario: A joint on a leaf is owned like any other

- **WHEN** the joint `turn` is declared on a leaf class held as `first`
- **THEN** `first.turn` is in the bank, the run binds it on every tick, and
  the leaf's body is placed by the bound value

#### Scenario: A second simulation over one tree starts fresh

- **WHEN** a simulation over a running root has moved its crank for twenty
  ticks and a second simulation is constructed over the SAME node
- **THEN** construction succeeds, the second simulation's bank is the rest
  pose — identical to the first's initial snapshot — and nothing is refused
  as doubly bound

#### Scenario: A released simulation refuses to advance

- **WHEN** a simulation whose tree a later simulation has taken over is
  stepped
- **THEN** it refuses naming both simulations and saying its bank no longer
  describes the tree, and the tree is left as the owning simulation posed it

#### Scenario: An author binding is still refused

- **WHEN** a running root's `simulate()` binds a run-owned coordinate
  unconditionally
- **THEN** construction is refused as doubly bound, naming the class and the
  coordinate, exactly as before

#### Scenario: A driver named for the clock is refused

- **WHEN** a running root declares a driver whose qualified id is `time`
- **THEN** construction is refused naming the id and saying `time` is
  reserved for the simulation clock
