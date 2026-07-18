# solid-node

A Python framework for mechanical CAD projects. CLI entrypoint: `solid`
(`solid_node/cli.py`).

The development record lives in this repo: `openspec/specs/` (behavioral
contracts — deltas over them are the unit of ratifiable change),
`docs/adrs/` (decision log), `docs/architecture.md` (the synthesis —
read it first).

## The workbench lives in the shop

Development happens from a checkout of
[solid-node-shop](https://github.com/LibreSolid/solid-node-shop) — the
workspace that bootstraps the environment and this repo as a working
copy:

```
scripts/setup dev                 # framework clone + editable install
scripts/dev-env <name> setup      # isolated worktree bench at WTs/<name>
scripts/dev-env <name> teardown   # remove it (refuses if dirty)
```

Agents work in an isolated worktree bench, never the main clone. Rules
inside any worktree of this repo:

- Run everything from inside the worktree (`cd` into it), so its `.env`
  (per-bench `SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT`) is picked
  up — the `solid` CLI loads `.env` from the cwd at startup.
- The `solid` entrypoint resolves `solid_node` from where it's
  installed. To run the worktree's own code, use `PYTHONPATH="$PWD"`
  with the workspace venv's python/solid.
- The web app's `node_modules/` and `build/` are symlinked from the
  main clone — don't run `npm install` or `npm run build` inside a
  worktree (it would write through to the shared copy).
- Commit your work on the worktree's branch. Teardown refuses to remove
  a worktree with uncommitted changes and leaves the branch behind.
- The browser view for a worktree is `http://localhost:<SOLID_NODE_PORT>`.
