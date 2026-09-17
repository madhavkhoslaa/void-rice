#!/usr/bin/env bash
# User-side file/source operations shared by install.sh and its isolated tests.
backup() {
    local path=$1 relative
    if [[ -e $path || -L $path ]]; then
        relative=${path#/}
        if [[ ! -e $BACKUP/$relative && ! -L $BACKUP/$relative ]]; then
            mkdir -p "$BACKUP/$(dirname "$relative")"
            cp -a -- "$path" "$BACKUP/$relative"
        fi
    fi
}

copy_file() {
    if [[ -f $2 ]] && cmp -s "$1" "$2"; then return 0; fi
    backup "$2"
    install -D -m "${3:-0644}" "$1" "$2"
}

checkout() {
    local url=$1 revision=$2 directory=$3 remote
    if [[ ! -d $directory/.git ]]; then
        [[ ! -e $directory ]] || { echo "Not a managed checkout: $directory" >&2; return 1; }
        git init -q "$directory"
    fi
    # A cancelled initial run may leave .git with no origin or no HEAD.
    if ! git -C "$directory" rev-parse --verify HEAD >/dev/null 2>&1; then
        remote=$(git -C "$directory" remote get-url origin 2>/dev/null || :)
        if [[ -z $remote ]]; then
            git -C "$directory" remote add origin "$url"
        elif [[ $remote != "$url" ]]; then
            echo "Unexpected source remote: $directory" >&2; return 1
        fi
        git -C "$directory" fetch -q --depth 1 origin "$revision" ||
            git -C "$directory" fetch -q origin
        git -C "$directory" checkout -q --detach "$revision"
    fi
    [[ $(git -C "$directory" rev-parse HEAD) == "$revision" ]] || {
        echo "Source revision differs from the pinned build: $directory" >&2; return 1;
    }
}
