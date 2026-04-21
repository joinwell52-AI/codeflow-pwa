# Cursor / VS Code Shortcuts and “This Project Only”

## Bottom Line (Read This First)

1. **Shortcut rules live in user config by default**: `%APPDATA%\Cursor\User\keybindings.json` (Windows), watched and merged by Cursor with built-in rules. Official docs’ “advanced customization” refers to this **user** `keybindings.json`, **not** `.vscode/keybindings.json` in the repo.
2. **Unlike `settings.json`**: workspaces may have `.vscode/settings.json`; **VS Code does not ship a standard, automatic workspace-only `keybindings.json` loader** that mirrors that (common community approach: user-level rules + `when` clauses).
3. **If an online guide puts rules in “project root `.vscode/keybindings.json`”**: **verify on your local Cursor build** whether they are loaded; **do not assume** that checking a file into the repo limits shortcuts to that repo only.
4. **“This project only” in the official model** usually relies on **`when` clauses**: rules stay in **user** `keybindings.json`, and use `workspaceFolderPath`, `resourceDirname`, `config.xxx`, etc. to decide whether the current context is this project.

## Practical Options for “Only Respond to Ctrl+Alt+1–4 in This Project”

| Approach | Notes |
|----------|--------|
| **User keybindings + `when`** | Add rules in **user** `keybindings.json`, e.g. `when` with `workspaceFolderPath =~ /your-project-path-fragment/` (path varies per machine; update when switching machines or use a more stable match). |
| **User keybindings + workspace toggle** | Set a custom flag in `.vscode/settings.json`, e.g. `codeflow.keybindings.enabled: true`, and in user `keybindings.json` use `when: config.codeflow.keybindings.enabled`; only applies when this project is open and enabled. |
| **Multiple windows** | `when` depends on the active window’s workspace; wrong rules may look “global” or “never fire” — use **Developer: Inspect Context Keys** to debug. |

## Relation to 码流（CodeFlow）

- **CodeFlow Desktop (patrol / nudge)** sends **Ctrl+Alt+1–4** via **pyautogui** as **OS-level keys to the foreground window**; it does **not** automatically “pick which repo” inside Cursor — it depends on the user having the **correct Cursor window** focused.
- **Therefore**, if the product goal is “**no reliance on global shortcut setup**” and “**no accidental binding to other projects**”, more reliable options are:
  - **Sidebar tab + OCR / click** (path already supported by patrol), or  
  - **MCP tools** (explicit invocation inside Cursor; tools can focus windows or use the command palette), or  
  - **Accept “user keybindings + `when`”** as optional advanced setup, document how to write `when`, and **do not** treat “project `.vscode/keybindings.json` exists” as a preflight pass condition.

## Alternatives If You “Give Up on Cursor Shortcuts”

1. **Desktop patrol**: keep using shortcuts or click paths; CodeFlow drives pacing; users can reduce global bindings in Cursor.
2. **Cursor extension**: e.g. `codeflow-desktop/cursor-extension/` (`codeflow-panel-launcher`) opens the panel via the VS Code extension API, or write your own MCP for other capabilities.
3. **Fully manual**: click Agent in the sidebar; preflight only needs to verify you “can switch to” the right place.

## References

- [VS Code: Keyboard shortcuts](https://code.visualstudio.com/docs/getstarted/keybindings) (user `keybindings.json`, `when` clauses)
- [When clause contexts](https://code.visualstudio.com/api/references/when-clause-contexts)

---

*This document describes product boundaries; it does not replace behavior differences across Cursor versions — validate on your machine.*
