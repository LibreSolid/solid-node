# solid-node

A Python framework for mechanical CAD projects. CLI entrypoint: `solid`
(`solid_node/cli.py`), dev environment uses the venv at `.venv/`.

## Working in worktrees

Agents should do their work in an isolated git worktree, not in the main
checkout. Create and destroy them with `scripts/dev-env`:

```
scripts/dev-env <name> setup      # create WTs/<name> on branch <name>
scripts/dev-env <name> teardown   # remove it (refuses if dirty)
```

Setup picks the lowest free slot N (recorded in `WTs/manifest` as `name:N`
lines) and writes a `.env` in the worktree root with that slot's ports:

- backend (web viewer): `SOLID_NODE_PORT` = 8000 + PORT_BASE + N
- frontend (npm dev server): `SOLID_NODE_FRONTEND_PORT` = 3000 + PORT_BASE + N

`PORT_BASE` comes from the repo root `.env` (default 0). The main checkout
is slot 0. The `solid` CLI loads `.env` from the cwd at startup, so each
worktree's servers come up on its own ports automatically — several
worktrees (and the main checkout) can run side by side.

Rules for agents:

- Run everything from inside the worktree (`cd WTs/<name>`), so its `.env`
  is picked up.
- The `solid` entrypoint resolves `solid_node` from where it's installed.
  To run the worktree's own code, use `PYTHONPATH="$PWD"`, e.g.:
  `PYTHONPATH="$PWD" ../../.venv/bin/python -m pytest tests/`
  `PYTHONPATH="$PWD" ../../.venv/bin/solid develop <node.py> --web-dev`
- The web app's `node_modules/` and `build/` are symlinked from the main
  checkout — don't run `npm install` or `npm run build` inside a worktree
  (it would write through to the shared copy).
- Commit your work on the worktree's branch. Teardown refuses to remove a
  worktree with uncommitted changes and leaves the branch behind.
- The browser view for a worktree is `http://localhost:<SOLID_NODE_PORT>`.
