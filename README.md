# repo-backup

## Run

```bash
uv run main.py
```

Then open http://127.0.0.1:8000

Pages are Jinja2 templates in `templates/`; `templates/index.html` is
rendered at `/`. Static assets live in `static/` and are served under
`/static`.

## Repository mirroring

`repo-backup.sh` mirrors, clones and forks upstream repositories into a tree
namespaced by forge host and owner, driven by `repo-urls.txt`:

```bash
./repo-backup.sh        # process the manifest into ~/src
./repo-backup.sh -n     # dry run — print what would happen, change nothing
```

See [repo-backup.md](repo-backup.md) for a line-by-line explanation of the
script.
