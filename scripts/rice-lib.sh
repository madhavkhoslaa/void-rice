#!/bin/sh
# Shared POSIX-shell paths. Installed next to the executable scripts.
RICE_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/rice"
RICE_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/rice"
RICE_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/rice"
RICE_SRC="$HOME/.local/src/rice"
# DISPLAY is deliberately part of PID/lock paths; never signal another X server.
rice_display=$(printf '%s' "${DISPLAY:-headless}" | tr -c 'a-zA-Z0-9_-' '_')
RICE_RUNTIME="${XDG_RUNTIME_DIR:-$RICE_CACHE/runtime}/rice-$rice_display"
export RICE_CONFIG RICE_CACHE RICE_DATA RICE_SRC RICE_RUNTIME
