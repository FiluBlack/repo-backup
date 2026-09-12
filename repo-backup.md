# repo-backup.sh — annotated

A line-by-line reading of the mirror-and-fork script: what each block does,
which git semantics it leans on, and the three places where a small change
would quietly break it.

Line numbers refer to `repo-backup.sh` as committed.

The manifest is TOML. Bash cannot parse TOML, so `tools/repos.py` flattens it
into lines the script reads — see [The TOML bridge](#the-toml-bridge).

- [What it builds](#what-it-builds)
- [The TOML bridge](#the-toml-bridge)
- [Configuration](#configuration-lines-2840) — 28–40
- [The dry-run gate: `run`](#the-dry-run-gate-run-lines-6268) — 62–68
- [`parse_url`](#parse_url-lines-7291) — 72–91
- [Remote helpers](#remote-helpers-lines-94109) — 94–109
- [`ensure_mirror`](#ensure_mirror-lines-111125) — 111–125
- [`ensure_tree`](#ensure_tree-lines-127158) — 127–158
- [`ensure_mine`](#ensure_mine-lines-160179) — 160–179
- [`process`](#process-lines-194228) — 194–228
- [Main body](#main-body-lines-230294) — 230–294
- [Two bash mechanics](#two-bash-mechanics)
- [Known limits](#known-limits)

## What it builds

Every repository in the manifest becomes up to three sibling directories under
a tree namespaced by forge host and owner. The suffix tells you what a
directory is without looking inside, and alphabetical sorting keeps the set
adjacent.

```text
~/src/github.com/junegunn/
├── fzf                working tree — build, read, patch
├── fzf.git            bare mirror — archival, never push
└── fzf.mine.git       bare repo — your own commits
```

Which of the three you get is each entry's `mode`:

| Mode | Result |
| --- | --- |
| `mirror` | Bare archival mirror only. The default when `mode` is omitted. |
| `tree` | Working tree only, not archived. |
| `both` | Mirror plus working tree. |
| `fork` | All three, including a branch for your own patches. |

The script is a manifest loop wrapped around three idempotent `ensure_*`
functions. Nothing else in it is load-bearing.

| Stage | What happens |
| --- | --- |
| **read** | One emitted line at a time: URL plus mode. |
| **process** | URL to three paths; mode to three flags. |
| **ensure** | Create what's missing, refresh what exists. |

## The TOML bridge

The manifest looks like this:

```toml
[defaults]
src_root     = "~/src"
patch_branch = "local/patches"

[[repo]]
url  = "https://github.com/junegunn/fzf"
mode = "fork"
note = "fuzzy finder"
tags = ["cli"]
```

Bash has no TOML parser, so `tools/repos.py` reads it with `tomllib` (standard
library, Python 3.11+) and prints one TAB-separated line per repo. The script
consumes that instead of a file:

```bash
manifest_defaults=$(python3 "$REPOS_PY" defaults "$MANIFEST") || exit 1
apply_manifest_defaults "$manifest_defaults"
SRC_ROOT=${SRC_ROOT:-$HOME/src}
PATCH_BRANCH=${PATCH_BRANCH:-local/patches}

manifest_lines=$(python3 "$REPOS_PY" emit "$MANIFEST") || exit 1
```

Two deliberate choices here.

**Command substitution, not process substitution.** `$( ... )` propagates the
exit status, so a TOML syntax error or an unknown mode stops the script at line
270 or 275. With `done < <(python3 ...)` a crashed reader yields empty input
and the run reports a cheerful "0 ok, 0 failed" — a silent no-op is the worst
possible failure for a backup tool.

**Validation lives in Python.** `tools/repos.py` rejects an unknown `mode` and
a `[[repo]]` with no `url` before the shell sees anything, where the error
message can name the file, the field and the valid choices.

`apply_manifest_defaults` (line 183) fills in any setting not already supplied,
giving the precedence **flag > environment > `[defaults]` > built-in**. It also
expands a leading `~`, which TOML stores as a literal character.

> [!NOTE]
> This is the one place the script depends on something other than git and
> bash. `emit` and `defaults` need only `tomllib`, so any system `python3`
> 3.11+ works with nothing installed. Writing the manifest from Python uses
> `tomlkit` (to preserve comments), but the shell path never imports it.

## Configuration (lines 28–40)

```bash
set -uo pipefail

SRC_ROOT=${SRC_ROOT:-}
PATCH_BRANCH=${PATCH_BRANCH:-}
NO_PUSH=no-push # sentinel push URL; any push to it fails loudly

self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
```

`-u` makes an unset variable fatal, catching typos. `pipefail` fails a pipeline
if any stage fails. **`-e` is deliberately absent** — one unreachable forge
shouldn't abort a forty-line manifest, so errors are checked explicitly
instead. There is a second reason, in [Two bash mechanics](#two-bash-mechanics).

`${VAR:-default}` takes the environment's value when set and non-empty,
otherwise the default. Every knob follows this shape, so env vars and flags
both work without extra code.

`SRC_ROOT` and `PATCH_BRANCH` start **empty** rather than at their defaults.
That is what lets `[defaults]` in the manifest fill them in: the built-in
fallbacks are applied at lines 272–273, after the manifest has had its turn.

`NO_PUSH` is not a real URL, and that is exactly its job. Git tries to resolve
it, fails, and prints an error instead of writing into an archival repository.

`BASH_SOURCE[0]` is the script's own path — unlike `$0`, which can be the
caller's. Wrapping it in `cd` and `pwd` makes it absolute, so the default
manifest resolves next to the script whatever directory you run it from.

## The dry-run gate: `run` (lines 62–68)

```bash
run() {
    if ((DRY_RUN)); then
        printf '  + %s\n' "$*"
        return 0
    fi
    "$@"
}
```

`"$@"` re-expands the arguments as a command with word boundaries intact —
`"$*"`, used for the printed form, would flatten them into one string.

The discipline matters more than the function: **every mutating call goes
through `run`**. A command that skipped it would show up as an unexplained
change during `-n`. There are two deliberate exceptions in `ensure_mine`,
handled by an early return.

## `parse_url` (lines 72–91)

```bash
    case $url in
        *://*)
            rest=${url#*://}
            rest=${rest#*@}
            ;;
        *@*:*)
            rest=${url#*@}
            rest=${rest/:/\/}
            ;;
        *) rest=$url ;;
    esac
    rest=${rest%/}
    rest=${rest%.git}
    host=${rest%%/*}
    path=${rest#*/}
    host=${host%%:*} # drop any :port
    [[ -n $host && -n $path && $path == */* ]]
```

`${url#*://}` strips the shortest leading match through `://`, turning
`https://github.com/o/r` into `github.com/o/r`. `${rest#*@}` then drops any
`user@` prefix — harmless when absent, since a non-matching `#` leaves the
string untouched.

The second branch handles scp-style `git@github.com:owner/repo`: strip through
the `@`, then `${rest/:/\/}` replaces the *first* colon with a slash,
normalising it to the same shape as the others.

`%` and `%%` strip from the end, `#` and `##` from the front; the doubled form
takes the longest match. So `%%/*` on `github.com/o/r` removes `/o/r` and
leaves the host.

The bare `[[ ... ]]` on the last line is the return value — a function's exit
status is that of its final command, so no explicit `return` is needed. This is
the validation that makes `not-a-url` fail cleanly rather than producing a
nonsense path.

Because `path` keeps every remaining segment rather than just two, GitLab
subgroups such as `gitlab.com/group/sub/repo` nest correctly instead of being
flattened.

## Remote helpers (lines 94–109)

```bash
    if git -C "$dir" remote get-url "$name" >/dev/null 2>&1; then
        run git -C "$dir" remote set-url "$name" "$url"
    else
        run git -C "$dir" remote add "$name" "$url"
    fi
```

`git remote add` fails when the remote already exists; `set-url` fails when it
doesn't. Probing with `get-url` chooses between them, which makes the operation
idempotent and self-healing at once — a remote you edited by hand is corrected
on the next run.

`block_push` uses `git remote set-url --push`, which sets a *separate* push URL
and leaves fetching entirely normal.

## `ensure_mirror` (lines 111–125)

```bash
    if [[ -d $mirror ]]; then
        log "refresh mirror $mirror"
        run git --git-dir="$mirror" remote update --prune || return 1
    else
        log "clone mirror $mirror"
        run mkdir -p -- "$(dirname -- "$mirror")" || return 1
        run git clone --mirror -- "$url" "$mirror" || return 1
    fi
```

`--mirror` sets the refspec `+refs/*:refs/*`, fetching every branch, tag and
note. A plain clone gets one branch and whatever tags come with it, which is
not a backup.

`--git-dir=` rather than `-C`: a bare repository has no working tree, so `-C`
would rely on git's directory-walk discovery. Naming the git dir outright is
unambiguous and unaffected by `safe.bareRepository` settings.

The two `config` calls after the branch run on **every** invocation, not only
at creation — that's what makes the settings self-healing.

> [!WARNING]
> **Sharp edge.** That same `+refs/*:refs/*` refspec is what makes `--prune`
> destructive here: the mirror treats every local ref as a copy of upstream and
> deletes anything upstream no longer has. Bare repositories also keep no
> reflog by default, so a dropped ref would leave nothing to recover from.
>
> Line 123 sets `core.logAllRefUpdates true` for exactly that reason.
> Filesystem snapshots remain the real backstop.

## `ensure_tree` (lines 127–158)

```bash
    if [[ ! -e $tree ]]; then
        run mkdir -p -- "$(dirname -- "$tree")" || return 1
        if ((have_mirror)); then
            # Local clone: git hardlinks the objects, so this is nearly free.
            log "clone tree $tree (from mirror)"
            run git clone -- "$mirror" "$tree" || return 1
            run git -C "$tree" remote rename origin mirror
```

The `elif` that follows catches a path that exists but is not a working tree,
warns, and returns failure. Testing with `-e` rather than `-d` means a stray
file trips the guard too — the script refuses to touch anything it didn't
create.

When a mirror exists the tree is cloned *from the mirror*, not over the
network. Git hardlinks the object files for a local clone, so the second copy
costs almost nothing on disk.

> [!WARNING]
> **Sharp edge.** `remote rename origin mirror` also rewrites
> `branch.<name>.remote`. Your checked-out `main` now tracks the mirror, so a
> bare `git push` resolves to it — the one repository that must never be pushed
> to. Git only falls back to `origin` when no tracking remote is set, so an
> absent `origin` is not a safeguard.
>
> That's what `block_push` on line 151 is for. With the push URL pointed at the
> sentinel, the push fails loudly instead.

```bash
    # Fetch only. Updating the checkout is a decision for you, not a cron job.
    run git -C "$tree" fetch --prune --tags upstream || return 1
```

New commits land in `upstream/main` for you to inspect; your checkout doesn't
move and uncommitted work is untouched. `--prune` is safe in this direction —
it only removes stale remote-tracking refs. It's the mirror's refspec that
makes pruning destructive, not pruning itself.

## `ensure_mine` (lines 160–179)

`git init --bare` creates an ordinary bare repository — **not** a mirror, so
nothing prunes it. That is the entire reason it exists as a separate directory
rather than a branch in the mirror. It is wired up as `origin`, the one remote
that keeps push enabled.

```bash
    if ((DRY_RUN)); then
        printf '  + ensure branch %s exists and is pushed to origin\n' "$PATCH_BRANCH"
        return 0
    fi
    if git -C "$tree" rev-parse --verify -q "refs/heads/$PATCH_BRANCH" >/dev/null; then
```

The early return is necessary because the code below it inspects a working tree
that does not exist during a dry run. `rev-parse --verify -q` is the
branch-existence test, and spelling the ref out in full as `refs/heads/...`
stops it matching a tag or a remote branch of the same name.

The branch is created **only when missing**. On later runs the script leaves it
alone — after a rebase your patches need `--force-with-lease`, and that is not
a decision a scheduled job should be making.

## `process` (lines 194–228)

```bash
    local base=$SRC_ROOT/$host/$path
    local mirror=$base.git tree=$base mine=$base.mine.git
```

This is the layout in two lines. A project changing role — read-only clone
becomes a fork — needs no `mv` and breaks no path you referenced elsewhere.

The `case` below maps a mode word onto three flags, with `*)` rejecting typos
rather than silently defaulting to something destructive.

```bash
    head_ "$host/$path  [$mode]"
    ((want_mirror)) && { ensure_mirror "$url" "$mirror" || return 1; }
    ((want_tree)) && { ensure_tree "$url" "$mirror" "$tree" "$want_mirror" || return 1; }
    ((want_mine)) && { ensure_mine "$tree" "$mine" || return 1; }
    return 0
```

A false `((...))` yields exit status 1. Without the explicit `return 0` on line 227, a
`mirror`-mode repository — which leaves the last two flags unset — would
succeed and then report itself as failed.

## Main body (lines 230–294)

`getopts ':f:r:nh'` — the leading colon selects silent error mode, so the
script prints its own messages through the `:` and `*` cases instead of
getopts' built-in ones. Trailing colons mark the flags that take an argument.

```bash
while read -r url mode _rest; do
    [[ -z ${url//[[:space:]]/} ]] && continue # blank (an empty manifest)
    if process "$url" "${mode:-mirror}"; then
        ((ok++))
    else
        ((failed++))
        failed_names+=("$url")
    fi
done <<<"$manifest_lines"
```

`read` splits on whitespace into exactly those three variables, with anything
left over landing in `_rest`. `-r` stops backslashes being interpreted.

The input is a **here-string** over the already-captured `$manifest_lines`, not
a pipe, and that distinction is load-bearing: a piped `while` runs in a
subshell, and the `ok` and `failed` counters would vanish when it exited.

The blank-line guard remains because a manifest with no `[[repo]]` entries
emits an empty string, and `<<<""` still feeds the loop one empty line.

At the end, `printf '   failed: %s\n' "${failed_names[@]}"` prints one line per
failure with no loop — `printf` reuses its format string until the arguments
run out.

## Two bash mechanics

### Dynamic scoping returns two values

`parse_url` assigns `host` and `path` without `local`, yet they don't leak into
the global namespace — because `process` declares `local host path` on line 195
before calling it. In bash a `local` is visible to everything the function
calls, which is how one function here returns two values.

### Arithmetic exit status

`((ok++))` uses *post*-increment: it evaluates to the old value, so on the
very first success it evaluates to `0`, which is arithmetic false, which is
exit status 1.

> [!WARNING]
> **Sharp edge.** Harmless as written, but under `set -e` the script would exit
> on its first successful repository. That is the second reason `-e` is absent
> — worth remembering if you ever add it. `((++ok))` or `ok=$((ok + 1))`
> would be safe under either setting.

## Known limits

- `--tags` fetches tags but does not prune them, so a tag deleted upstream
  lingers in the working tree. `--prune-tags` would change that, at the cost of
  being able to delete tags you care about.
- Positional arguments after the flags are ignored — a URL can only be passed
  through a manifest, never directly.
- Repositories are processed serially. Fine for a handful; a large manifest
  over slow links would benefit from parallelism.
- A mirror reproduces upstream deletions and force-pushes faithfully. It
  protects against a project disappearing, not against one rewriting its
  history.
- Reading the manifest needs `python3` 3.11 or newer on PATH. On a minimal
  host where only git and bash are guaranteed, that is a new prerequisite.
