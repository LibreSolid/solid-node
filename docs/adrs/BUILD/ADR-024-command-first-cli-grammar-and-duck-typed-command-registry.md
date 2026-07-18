# ADR-024: Command-First CLI Grammar and Duck-Typed Command Registry

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-005: Path-Based Dynamic Module Loading](./ADR-005-path-based-dynamic-module-loading.md)

**Related to:**
- [ADR-007: Watchdog Library for Filesystem Monitoring](./ADR-007-watchdog-library-filesystem-monitoring.md)
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](../EXPORT/ADR-020-static-export-and-embeddable-viewer-widget.md)
- [ADR-021: Snapshot CLI Command for AI Agent Autonomy](./ADR-021-snapshot-cli-command-for-agent-autonomy.md)
- ADR-019: Solid-Builder Autonomous CAD Agent System *(historical — the solid-builder predecessor of the solid-node-shop agents; its record lives with the agent tooling, not in this framework log)*

## Context and Problem Statement

`solid` is the single entry point (`cli.py:manage()`) through which every framework action runs: `develop`, `test`, `snapshot`, `export`, and project scaffolding via `new`. The CLI needed a grammar for how a user names an action and its target, a mechanism for registering and dispatching the growing set of commands, and a way to bootstrap a new project without a network fetch. No ADR previously recorded any of these decisions.

Two forces shaped the design:

- **A grammar reversal, driven by agent ergonomics.** The CLI originally used **path-first** ordering, `solid <path> <command>`. In 0.4 it flipped to **command-first**, `solid <command> <path>`. The origin of this flip was empirical, not a first-principles design exercise: while looking for ways to make the AI agents that drive the framework more efficient, an agent that uses the CLI surfaced command-first ordering as an optimization, and it was adopted for that reason. This ties the CLI directly to the framework's agent-autonomy theme (the `snapshot` command exists "for AI Agent Autonomy," ADR-021; the solid-builder system, ADR-019, drives `solid` commands programmatically). Because reordering silently changes the meaning of old muscle-memory invocations, the change needed an explicit migration path.
- **Heterogeneous commands.** Most commands operate on a node and want a `path` positional (with directory→`__init__.py` resolution, feeding the ADR-005 loader). But `new` operates on a *name*, not an existing node, and must not demand a node path. The dispatch mechanism had to accommodate both without ceremony.

## Decision Drivers

- **Agent-driving ergonomics and efficiency (primary).** The framework is increasingly driven by AI agents that construct and run `solid` commands; command-first ordering was an empirically-adopted optimization surfaced by an agent using the CLI, aligned with the agent-autonomy direction of ADR-021 and ADR-019.
- **No silent misinterpretation on upgrade.** Old path-first invocations must fail loudly with guidance, not silently treat a path as an unknown command.
- **Low-ceremony command authoring.** Adding a command should mean writing a small plain class and appending one list entry — no base-class boilerplate, no registration decorators.
- **Node vs non-node commands.** The `path` positional and its `__init__.py` resolution must be automatic for node commands and absent for `new`.
- **Offline, self-contained scaffolding.** `solid new` must create a runnable project from resources shipped inside the package, with no template download.
- **Dev-env worktree support.** Script-created worktrees need per-worktree ports via `.env`, with real environment variables taking precedence.
- **Convention and argparse fit (secondary/supporting).** Command-first also happens to match the familiar `git`/`docker`-style `verb target` convention and maps cleanly onto argparse subparsers (per-command help and options). This is a welcome corroborating benefit, not the reason the flip was made.

## Considered Options

**Grammar:**
1. Command-first `solid <command> <path>` on argparse subparsers, with a migration guard (chosen).
2. Path-first `solid <path> <command>` (the prior 0.4-and-earlier grammar).

**Command dispatch:**
1. Duck-typed command classes in a module-level list, no base class (chosen).
2. A shared abstract `Command` base class enforcing the interface.
3. A third-party CLI framework (click / typer).

## Decision Outcome

**Grammar: command-first with a migration guard.** `manage()` builds one argparse subparser per command (`solid <command> ...`), each carrying the command's `__doc__` as help. Before parsing, a guard inspects `sys.argv`: if `argv[1]` is *not* a known command but `argv[2]` *is*, it recognizes an old path-first invocation and exits with code 2 and the message "The CLI grammar changed in 0.4: commands come first. Try: solid {command} {path} [options]" rather than letting argparse emit a confusing "invalid choice" for the path.

**Dispatch: duck-typed command registry.** Commands are a module-level list, `commands = [Develop(), Test(), Snapshot(), New(), Export()]`. There is **no base class**. Each command is a plain class exposing:
- `__doc__` — used as the subparser help;
- an optional `needs_node` attribute (read via `getattr(command, 'needs_node', True)`, defaulting to True);
- `add_arguments(parser)` — registers its own options;
- `handle(args)` — executes.

`manage()` iterates the list, creates a subparser per command, and — **only when `needs_node`** — adds the shared `path` positional. After parsing, again only for `needs_node` commands, it resolves a directory argument to its package entry point (`if os.path.isdir(args.path): args.path = join(args.path, '__init__.py')`) before handing off to the ADR-005 loader, then calls `command.handle(args)`. `New` sets `needs_node = False` and declares its own `name` positional instead.

**Scaffolding: `solid new` from packaged resources.** `New.handle()` copies a template tree shipped inside the package (`solid_node.manager/templates/project/`: `root/__init__.py`, `gitignore`) using `importlib.resources` (`resources.files(...)` + `resources.as_file(...)`), guards against overwriting an existing directory (`exit(1)`), and prints next-steps. No network access; the template travels with the wheel.

**`.env` loading.** `manage()` calls `load_dotenv()` first, reading `KEY=value` lines from `./.env` into `os.environ` via `setdefault` so **real environment variables win**. This is how `scripts/dev-env` worktrees get their own `SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT`.

Rationale for the chosen options:

### Grammar — command-first with migration guard (chosen)
- Good: adopted as an agent-ergonomics optimization for the AI agents that construct and run `solid` commands (ADR-021, ADR-019).
- Good: the guard turns a breaking reorder into a one-line, actionable error instead of silent misbehavior.
- Good (secondary): matches `git`/`docker`-style `verb target` convention and argparse subparser design; each command gets clean `-h` and scoped options.
- Bad: the guard is heuristic (argv position inspection) and only covers the common two-token case.

### Grammar — path-first (prior)
- Good: no migration needed; it was the status quo.
- Bad: less ergonomic for the agents driving the CLI (the reason it was replaced); awkward to express per-command options and help in argparse. Deliberately abandoned in `2d8b3f0`.

### Dispatch — duck-typed classes, no base (chosen)
- Good: minimal ceremony — a command is a small class plus one list entry; `needs_node` is a single attribute.
- Good: no inheritance coupling; commands stay independent and trivially testable.
- Good: the `getattr` default keeps the common (node) case zero-config.
- Bad: the contract (`__doc__`, `needs_node`, `add_arguments`, `handle`) is implicit — a typo or missing method fails only at runtime.
- Bad: no compile-time or import-time guarantee that a command conforms.

### Dispatch — abstract `Command` base class
- Good: explicit, discoverable interface; could enforce methods via `abc`.
- Good: a natural home for shared behavior (path resolution, common options).
- Bad: boilerplate for a handful of commands; the shared behavior already lives cleanly in `manage()`.
- Bad: little practical gain over the duck-typed list at this scale.

### Dispatch — third-party CLI framework (click / typer)
- Good: decorators, rich help, validation, shell completion out of the box.
- Bad: a new runtime dependency for a framework that values a lean footprint (cf. ADR-018 direction); argparse is stdlib.
- Note: there is no evidence this was actually evaluated at decision time; it is listed as a standard alternative for completeness, not as a weighed-and-rejected option.

## Consequences

- **Adding a command is cheap and uniform.** Write a class with `__doc__` / `add_arguments` / `handle` (and `needs_node = False` if it is not node-scoped), then append an instance to `commands`. `snapshot` (ADR-021) and `export` (ADR-020) are exactly this shape, as is `develop`.
- **The implicit contract is the cost.** Because there is no base class, a malformed command (missing `handle`, misspelled `needs_node`) surfaces only when invoked. This is an accepted trade for low ceremony at the current command count; a base class or a registration check could be introduced if the set grows large.
- **The migration guard is a temporary courtesy.** It eases the 0.4 path-first→command-first transition and can be removed once the old grammar is long gone. It is heuristic and does not cover every malformed invocation, only the recognizable old ordering.
- **The CLI is an agent-facing surface.** Because the grammar was tuned for the agents that drive it, changes to command naming or ordering should weigh agent ergonomics alongside human ergonomics; this couples the CLI's evolution to the agent-autonomy work (ADR-021, ADR-019).
- **`needs_node` is the single seam between node and non-node commands.** It governs both the `path` positional and the directory→`__init__.py` resolution that feeds the ADR-005 loader. `new` is the sole current non-node command; the convention scales to future ones (e.g. project-wide utilities).
- **Scaffolding is offline and versioned with the package.** Templates ship in the wheel via `importlib.resources`, so `solid new` works with no network and stays in lockstep with the installed version. Template changes require a release.
- **`.env` loading couples the CLI to the dev-env worktree workflow.** The precedence rule (real env over `.env`) is deliberate so CI/production env always wins; the feature primarily serves `scripts/dev-env` port isolation and is otherwise inert when no `.env` is present.
- **Empirical hardening.** `solid test` was fixed to accept the test path and fail clearly instead of raising a bare `TypeError` (`3a0a625`, `2a2ee15`), reflecting that the duck-typed dispatch benefits from each command validating its own inputs since the framework enforces little.

## References

- `solid_node/cli.py` — `manage()` entry point, migration guard, subparser construction, `needs_node` dispatch, `load_dotenv`
- `solid_node/manager/new.py` — `New` scaffolding from packaged template resources
- `solid_node/manager/develop.py` — representative duck-typed command (`needs_node`, `add_arguments`, `handle`)
- `solid_node/manager/templates/project/` — packaged project template (`root/__init__.py`, `gitignore`)
- Commits: `2d8b3f0` (flip to command-first), `e1f2105` (`solid new` scaffolding), `1caa1f7` (docs), `3a0a625` / `2a2ee15` (`solid test` path handling)
