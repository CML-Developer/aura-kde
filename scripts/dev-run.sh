#!/usr/bin/env bash
# Development launcher — runs the locally compiled binary with the bridge pointing to this tree.
# Production use: install with scripts/install.py and run aura-kde-lab from PATH.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
binary="${repo}/../aura/target-kde/release/aura"
if [[ ! -f "$binary" ]]; then
    echo "Binary not found at $binary" >&2
    echo "Build Aura with: cargo build --features kde --locked --release --target-dir target-kde" >&2
    exit 1
fi
marker="$("$binary" --kde-info 2>/dev/null || true)"
if [[ "$marker" != "aura-kde-lab: KDE adapter, both screens" ]]; then
    echo "Binary is not the KDE build. Compile with --features kde." >&2
    exit 1
fi
export AURA_KDE_BRIDGE="$repo/tools/aura_kde_bridge.py"
exec "$binary" "$@"
