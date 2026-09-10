#!/usr/bin/env bash
#
# repo-backup.sh — mirror, clone and fork upstream repositories into a tree
# namespaced by forge host and owner:
#
#   $SRC_ROOT/github.com/junegunn/fzf           working tree
#   $SRC_ROOT/github.com/junegunn/fzf.git       bare mirror (archival)
#   $SRC_ROOT/github.com/junegunn/fzf.mine.git  bare repo for your own commits
#
# Driven by a manifest (default: repo-urls.txt next to this script):
#
#   # url                                       mode
#   https://github.com/junegunn/fzf             fork
#   https://github.com/syncthing/syncthing      mirror
#   https://codeberg.org/forgejo/forgejo
#
# Modes: mirror (default) | tree | both | fork
#
# Safe to re-run: missing pieces are created, existing ones refreshed.
# Working trees are never merged or rebased — only fetched.

set -uo pipefail

SRC_ROOT=${SRC_ROOT:-$HOME/src}
PATCH_BRANCH=${PATCH_BRANCH:-local/patches}
NO_PUSH=no-push   # sentinel push URL; any push to it fails loudly

self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MANIFEST=${MANIFEST:-$self_dir/repo-urls.txt}
DRY_RUN=0

ok=0; failed=0; failed_names=()

usage() {
    cat <<EOF
Usage: ${0##*/} [-f manifest] [-r src_root] [-n] [-h]

  -f FILE  manifest of repository URLs (default: $MANIFEST)
  -r DIR   root of the repository tree (default: $SRC_ROOT)
  -n       dry run — print what would be done, change nothing
  -h       this help

Environment: SRC_ROOT, MANIFEST, PATCH_BRANCH (default: $PATCH_BRANCH)
EOF
}

log()  { printf '  %s\n' "$*"; }
warn() { printf '  !! %s\n' "$*" >&2; }
head_() { printf '\n== %s\n' "$*"; }

run() {
    if (( DRY_RUN )); then
        printf '  + %s\n' "$*"
        return 0
    fi
    "$@"
}

# Split a repo URL into host + path. Handles https://, http://, ssh://,
# git://, scp-style git@host:owner/repo, with or without a .git suffix.
parse_url() {
    local url=$1 rest
    case $url in
        *://*)   rest=${url#*://}; rest=${rest#*@} ;;
        *@*:*)   rest=${url#*@}; rest=${rest/:/\/} ;;
        *)       rest=$url ;;
    esac
    rest=${rest%/}
    rest=${rest%.git}
    host=${rest%%/*}
    path=${rest#*/}
    host=${host%%:*}   # drop any :port
    [[ -n $host && -n $path && $path == */* ]]
}

# set_remote DIR NAME URL — add or correct a remote, idempotently.
set_remote() {
    local dir=$1 name=$2 url=$3
    if git -C "$dir" remote get-url "$name" >/dev/null 2>&1; then
        run git -C "$dir" remote set-url "$name" "$url"
    else
        run git -C "$dir" remote add "$name" "$url"
    fi
}

# Point a remote's push URL at a sentinel so an accidental `git push` fails
# instead of writing into an archival repo. Renaming origin -> mirror moves
# branch.<name>.remote with it, so a bare `git push` would otherwise target
# the mirror.
block_push() {
    run git -C "$1" remote set-url --push "$2" "$NO_PUSH"
}

ensure_mirror() {
    local url=$1 mirror=$2
    if [[ -d $mirror ]]; then
        log "refresh mirror $mirror"
        run git --git-dir="$mirror" remote update --prune || return 1
    else
        log "clone mirror $mirror"
        run mkdir -p -- "$(dirname -- "$mirror")" || return 1
        run git clone --mirror -- "$url" "$mirror" || return 1
    fi
    # Bare repos keep no reflog by default, so a prune that drops a ref is
    # unrecoverable in-repo. Turn it on.
    run git --git-dir="$mirror" config core.logAllRefUpdates true
    run git --git-dir="$mirror" remote set-url --push origin "$NO_PUSH"
}

ensure_tree() {
    local url=$1 mirror=$2 tree=$3 have_mirror=$4

    if [[ ! -e $tree ]]; then
        run mkdir -p -- "$(dirname -- "$tree")" || return 1
        if (( have_mirror )); then
            # Local clone: git hardlinks the objects, so this is nearly free.
            log "clone tree $tree (from mirror)"
            run git clone -- "$mirror" "$tree" || return 1
            run git -C "$tree" remote rename origin mirror
        else
            log "clone tree $tree (from upstream)"
            run git clone -- "$url" "$tree" || return 1
            run git -C "$tree" remote rename origin upstream
        fi
    elif [[ ! -d $tree/.git ]]; then
        warn "$tree exists but is not a git working tree — skipping"
        return 1
    else
        log "tree $tree present"
    fi

    (( have_mirror )) && set_remote "$tree" mirror "$mirror"
    set_remote "$tree" upstream "$url"
    (( have_mirror )) && block_push "$tree" mirror
    block_push "$tree" upstream

    # Fetch only. Updating the checkout is a decision for you, not a cron job.
    run git -C "$tree" fetch --prune --tags upstream || return 1
    (( have_mirror )) && run git -C "$tree" fetch --prune mirror
    return 0
}

ensure_mine() {
    local tree=$1 mine=$2
    if [[ ! -d $mine ]]; then
        log "create patch repo $mine"
        run git init -q --bare -- "$mine" || return 1
    fi
    set_remote "$tree" origin "$mine"

    if (( DRY_RUN )); then
        printf '  + ensure branch %s exists and is pushed to origin\n' "$PATCH_BRANCH"
        return 0
    fi
    if git -C "$tree" rev-parse --verify -q "refs/heads/$PATCH_BRANCH" >/dev/null; then
        log "patch branch $PATCH_BRANCH present"
    else
        log "create patch branch $PATCH_BRANCH"
        git -C "$tree" switch -q -c "$PATCH_BRANCH" || return 1
        git -C "$tree" push -q -u origin "$PATCH_BRANCH" || return 1
    fi
}

process() {
    local url=$1 mode=$2 host path
    if ! parse_url "$url"; then
        warn "cannot parse URL: $url"
        return 1
    fi

    local base=$SRC_ROOT/$host/$path
    local mirror=$base.git tree=$base mine=$base.mine.git
    local want_mirror=0 want_tree=0 want_mine=0

    case $mode in
        mirror) want_mirror=1 ;;
        tree)   want_tree=1 ;;
        both)   want_mirror=1; want_tree=1 ;;
        fork)   want_mirror=1; want_tree=1; want_mine=1 ;;
        *) warn "unknown mode '$mode' for $url (use mirror|tree|both|fork)"; return 1 ;;
    esac

    head_ "$host/$path  [$mode]"
    (( want_mirror )) && { ensure_mirror "$url" "$mirror" || return 1; }
    (( want_tree ))   && { ensure_tree "$url" "$mirror" "$tree" "$want_mirror" || return 1; }
    (( want_mine ))   && { ensure_mine "$tree" "$mine" || return 1; }
    return 0
}

while getopts ':f:r:nh' opt; do
    case $opt in
        f) MANIFEST=$OPTARG ;;
        r) SRC_ROOT=$OPTARG ;;
        n) DRY_RUN=1 ;;
        h) usage; exit 0 ;;
        :) printf 'missing argument to -%s\n' "$OPTARG" >&2; exit 2 ;;
        *) usage >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

command -v git >/dev/null || { echo "git not found" >&2; exit 1; }
[[ -r $MANIFEST ]] || { printf 'manifest not readable: %s\n' "$MANIFEST" >&2; exit 1; }

printf 'manifest: %s\nroot:     %s%s\n' "$MANIFEST" "$SRC_ROOT" \
    "$( (( DRY_RUN )) && printf '\ndry run:  no changes will be made')"

while read -r url mode _rest; do
    [[ -z ${url//[[:space:]]/} ]] && continue   # blank
    [[ $url == \#* ]] && continue               # comment
    if process "$url" "${mode:-mirror}"; then
        (( ok++ ))
    else
        (( failed++ )); failed_names+=("$url")
    fi
done < "$MANIFEST"

printf '\n== done: %d ok, %d failed\n' "$ok" "$failed"
if (( failed )); then
    printf '   failed: %s\n' "${failed_names[@]}"
    exit 1
fi
