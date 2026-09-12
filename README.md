# repo-backup

## Run

```bash
uv run main.py
```

Then open http://127.0.0.1:8000

Layout:

```
main.py              dev entry point
app/
├── main.py          app assembly: routers + static mount
├── settings.py      settings from the environment
├── providers.py     objects injected into routes
├── rendering.py     the Jinja2 environment
├── routers/         pages.py (HTML) and api.py (JSON)
├── schemas/         Pydantic wire shapes
├── services/        logic, free of FastAPI imports
├── templates/
└── static/
```

`HOST`, `PORT`, `RELOAD` and `APP_NAME` override the defaults.

## Repository mirroring

`repo-backup.sh` mirrors, clones and forks upstream repositories into a tree
namespaced by forge host and owner, driven by a TOML manifest:

```bash
cp repos.example.toml repos.toml   # repos.toml is gitignored
./repo-backup.sh                   # process the manifest
./repo-backup.sh -n                # dry run — print what would happen
```

```toml
[defaults]
src_root     = "~/src"
patch_branch = "local/patches"

[[repo]]
url  = "https://github.com/junegunn/fzf"
mode = "fork"          # mirror | tree | both | fork   (default: mirror)
tags = ["cli"]
```

`tools/repos.py` reads and writes the manifest — the shell script uses it to
parse the TOML it cannot read itself:

```bash
python3 tools/repos.py list repos.toml            # reading: stdlib only
uv run python tools/repos.py add repos.toml \
    https://github.com/neovim/neovim --mode both  # writing: needs tomlkit
```

Adding from Python preserves comments and formatting:

```python
from pathlib import Path
import repos
repos.add(Path("repos.toml"), "https://github.com/neovim/neovim", "both", note="editor")
```

See [repo-backup.md](repo-backup.md) for a line-by-line explanation of the
script.
