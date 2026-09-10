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
namespaced by forge host and owner, driven by `repo-urls.txt`:

```bash
./repo-backup.sh        # process the manifest into ~/src
./repo-backup.sh -n     # dry run — print what would happen, change nothing
```

See [repo-backup.md](repo-backup.md) for a line-by-line explanation of the
script.
