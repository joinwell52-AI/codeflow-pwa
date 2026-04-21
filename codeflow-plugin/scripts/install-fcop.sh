#!/usr/bin/env bash
# Install fcop MCP into Cursor on macOS / Linux.
#
# Idempotent one-shot installer:
#   1. Installs `uv` (via official script) if missing
#   2. Merges fcop entry into ~/.cursor/mcp.json (preserves other MCP servers)
#   3. Prints restart instructions
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.sh | bash

set -euo pipefail

echo ""
echo "=== fcop MCP installer ==="
echo ""

# --- 1. Ensure uv ------------------------------------------------------------
if command -v uvx >/dev/null 2>&1; then
    echo "[1/3] uv already installed: $(uvx --version)"
else
    echo "[1/3] Installing uv via https://astral.sh/uv/install.sh ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source uv env for current shell
    if [ -f "$HOME/.local/bin/env" ]; then
        # shellcheck disable=SC1091
        . "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
        # shellcheck disable=SC1091
        . "$HOME/.cargo/env"
    fi
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uvx >/dev/null 2>&1; then
        echo "ERROR: uv installed but uvx not on PATH. Restart shell and re-run." >&2
        exit 1
    fi
    echo "    uv installed: $(uvx --version)"
fi

# --- 2. Prepare mcp.json -----------------------------------------------------
CURSOR_DIR="$HOME/.cursor"
MCP_PATH="$CURSOR_DIR/mcp.json"
mkdir -p "$CURSOR_DIR"

# Merge via Python (ships with uv's managed interpreter if needed, but system
# python3 is almost always present on macOS/Linux)
PY_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PY_BIN" ]; then
    # Fallback: use uv's ephemeral python
    PY_BIN="uv run --with-requirements /dev/null python"
fi

$PY_BIN - "$MCP_PATH" <<'PYEOF'
import json, os, shutil, sys, time
path = sys.argv[1]
cfg = {}
if os.path.exists(path) and os.path.getsize(path) > 0:
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        backup = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy(path, backup)
        print(f"[!] Invalid existing mcp.json. Backed up to: {backup}")
        cfg = {}
cfg.setdefault("mcpServers", {})
had = "fcop" in cfg["mcpServers"]
cfg["mcpServers"]["fcop"] = {"command": "uvx", "args": ["fcop"]}
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("    fcop entry " + ("refreshed" if had else "added") + " in: " + path)
PYEOF

echo "[2/3] mcp.json ready."

# --- 3. Done -----------------------------------------------------------------
echo ""
echo "[3/3] All done."
echo ""
echo "Next step: completely quit Cursor and restart it."
echo "First tool call will lazy-download fcop from PyPI (~30-90s), then cached."
echo ""
