#!/usr/bin/env python3
"""Read and write the repo-backup manifest.

The manifest is TOML; repo-backup.sh is bash and cannot parse it. This module
is the bridge, and is also the supported way to edit the file from Python.

    emit      one TAB-separated "url<TAB>mode" line per repo, for the shell
    defaults  one TAB-separated "key<TAB>value" line per default setting
    add       add or update a repo, preserving comments and formatting
    list      human-readable summary

Reading uses tomllib from the standard library, so `emit` and `defaults` run
under any python3 >= 3.11 with nothing installed. Only `add` needs tomlkit,
imported lazily so the shell path never depends on it.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_MODE = "mirror"
VALID_MODES = ("mirror", "tree", "both", "fork")


def load(path: Path) -> dict[str, Any]:
    """Parse the manifest. Raises on malformed TOML or an unknown mode."""
    with path.open("rb") as fh:
        cfg = tomllib.load(fh)

    for entry in cfg.get("repo", []):
        if "url" not in entry:
            raise ValueError(f"{path}: a [[repo]] entry has no url")
        mode = entry.get("mode", DEFAULT_MODE)
        if mode not in VALID_MODES:
            raise ValueError(
                f"{path}: unknown mode {mode!r} for {entry['url']} "
                f"(use {', '.join(VALID_MODES)})"
            )
    return cfg


def repos(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    return cfg.get("repo", [])


def defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("defaults", {})


def add(path: Path, url: str, mode: str = DEFAULT_MODE, **extra: Any) -> bool:
    """Add a repo, or update it if the url is already present.

    Uses tomlkit so comments, spacing and key order survive the round trip.
    Returns True if a new entry was added, False if an existing one changed.
    """
    try:
        import tomlkit
    except ImportError as exc:  # only the write path needs it
        raise RuntimeError(
            "writing the manifest needs tomlkit (comment-preserving TOML).\n"
            "  install it:  uv add tomlkit\n"
            "  or run via:  uv run python tools/repos.py ..."
        ) from exc

    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode {mode!r} (use {', '.join(VALID_MODES)})")

    doc = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.document()
    table_array = doc.setdefault("repo", tomlkit.aot())

    for entry in table_array:
        if entry.get("url") == url:
            entry["mode"] = mode
            for key, value in extra.items():
                entry[key] = value
            path.write_text(tomlkit.dumps(doc))
            return False

    entry = tomlkit.table()
    if len(table_array) or path.exists():
        entry.trivia.indent = "\n"   # blank line between entries
    entry["url"] = url
    entry["mode"] = mode
    for key, value in extra.items():
        entry[key] = value
    table_array.append(entry)
    path.write_text(tomlkit.dumps(doc))
    return True


def _cmd_emit(cfg: dict[str, Any]) -> None:
    for entry in repos(cfg):
        print(f"{entry['url']}\t{entry.get('mode', DEFAULT_MODE)}")


def _cmd_defaults(cfg: dict[str, Any]) -> None:
    for key, value in defaults(cfg).items():
        print(f"{key}\t{value}")


def _cmd_list(cfg: dict[str, Any]) -> None:
    for entry in repos(cfg):
        tags = ",".join(entry.get("tags", []))
        print(
            f"{entry.get('mode', DEFAULT_MODE):<7} {entry['url']}"
            + (f"  [{tags}]" if tags else "")
            + (f"  {entry['note']}" if "note" in entry else "")
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("emit", "defaults", "list", "add"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("url", nargs="?")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=VALID_MODES)
    parser.add_argument("--note")
    parser.add_argument("--tag", action="append", dest="tags")
    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            if not args.url:
                parser.error("add requires a url")
            extra: dict[str, Any] = {}
            if args.note:
                extra["note"] = args.note
            if args.tags:
                extra["tags"] = args.tags
            created = add(args.manifest, args.url, args.mode, **extra)
            print(f"{'added' if created else 'updated'} {args.url}", file=sys.stderr)
            return 0

        cfg = load(args.manifest)
    except FileNotFoundError:
        print(f"manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    except (tomllib.TOMLDecodeError, ValueError, RuntimeError) as exc:
        print(f"{exc}", file=sys.stderr)
        return 1

    {"emit": _cmd_emit, "defaults": _cmd_defaults, "list": _cmd_list}[args.command](cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
