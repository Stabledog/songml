# `songml` -- text-first music composition tool

[![CI](https://github.com/stabledog/songml/workflows/CI/badge.svg)](https://github.com/stabledog/songml/actions)
[![codecov](https://codecov.io/gh/stabledog/songml/branch/main/graph/badge.svg)](https://codecov.io/gh/stabledog/songml)

See [docs/songml_design_manifesto.md]

## Development Setup

After cloning the repository:

```bash
cd songml-utils
pip install -e ".[dev]" --break-system-packages --user
pre-commit install
```

Run tests:
```bash
cd songml-utils
pytest
```

The pre-commit hooks will automatically format and lint your code before each commit. CI will run the same checks on push.

## Viewing SongML files

`songml-serve` starts a local web server that lists `.songml` files under a
directory and renders them as beat-grid chord charts in the browser, with a
MIDI download link on each chart.

```bash
cd songml-utils
songml-serve --root ../samples
```

Then open http://localhost:8000/ in a browser. Useful flags:

- `--port N` — listen on a different port (default: 8000)
- `--bars-per-row N` — bars per display row (default: 8)
- `--reload` — auto-restart and re-render on file changes, handy while editing a `.songml` file live

### On the Stablebeast Coder workspace

On the `music-tools` Coder workspace (host: Stablebeast, `192.168.1.99`),
`songml-serve` is started automatically on every workspace boot by
[`.myspaces/init`](../.myspaces/init) — no manual step needed. It serves the
real chord sheets from `/host_home/Dropbox/AbletonLive/Sheets` (a read-only
host bind mount) on port **8080**, which is this workspace's `dev_port` —
the one port number the Coder template publishes identically inside and
outside the container (see `dev_port` in `workspaces.conf` and the `ports`
block in `main.tf`). The router forwards that same port to Stablebeast, so
it's reachable from anywhere on the LAN or internet at:

```
http://coder-stablehome.ddns.net:8080/
```

If it's not responding, check `/tmp/songml-serve.log` inside the workspace,
or re-run `.myspaces/init` from the `music-tools` repo root to restart it
(it's idempotent — a no-op if port 8080 is already listening). This gets a
fresh container to a valid baseline state; it's not meant to be re-run
while actively developing (see below).

`.myspaces/init`'s instance runs the songml-utils install under
`~/workarea/songml` (a separate clone from this dev tree — see `CLAUDE.md`'s
"Two Clones" section). There's no separate dev/production split here in
practice: while working on songml-utils, run `make serve-bounce` from the
repo root to kill whatever's on :8080 and replace it with **this dev tree's**
code (via `uv run`, with `--reload` watching this tree's own source files —
so most edits reflect automatically; re-run `make serve-bounce` if a change
doesn't seem to have taken). That instance then stays the live one at
`coder-stablehome.ddns.net:8080` until the container itself is recycled.
`make serve-status` / `make serve-stop` / `make serve-start` are also
available — see `make help`.
