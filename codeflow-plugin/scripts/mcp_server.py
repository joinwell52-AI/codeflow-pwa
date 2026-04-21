"""Backwards-compat entrypoint for CodeFlow MCP.

This file exists so that ADMIN's existing Cursor `mcp.json` — which points at
an absolute path like ``D:\\Bridgeflow\\codeflow-plugin\\scripts\\mcp_server.py``
— keeps working after the packaging refactor in v0.2.0.

Preferred ways to run the MCP going forward:

    uvx codeflow-mcp              # zero-footprint, via uv
    pip install codeflow-mcp
    codeflow-mcp                  # console script

This shim simply puts the in-repo ``src/`` directory on ``sys.path`` and
dispatches to :func:`codeflow_mcp.server.main`. If the project is already
``pip install``-ed (e.g. via ``pip install -e codeflow-plugin``), the package
on ``sys.path`` takes precedence naturally.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, "..", "src"))
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from codeflow_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
