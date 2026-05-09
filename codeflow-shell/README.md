# CodeFlow Shell — v0.2.0-alpha (sprint 0 P1)

> ⚠️ **Internal preview release.** Not published to npm/PyPI/GitHub Releases. For ADMIN test only.
>
> **What's new since v0.1.0-rc.1**:
> - 🆕 Real `CursorSdkAdapter` wiring (no longer hard-stubbed to `InMemorySdkAdapter`).
> - 🆕 `ConfigLoader` — 6-tier merge (`defaults` → `~/.codeflow/v2/config.json` → `./codeflow.config.json` → `~/.codeflow/v2/.env` → `./.env` → `process.env` → CLI args).
> - 🆕 `.env.example` whitelisted env vars.
> - Fallback to `InMemorySdkAdapter` is **still** the default when `CURSOR_API_KEY` is absent — first launch with no setup remains a smoke-test friendly experience.
>
> **v1.0 alignment pending**: This release implements CodeFlow protocol v0.1
> (5 schemas: agent / task / review / session / skill) with `Review.decision`
> including `needs_human` and `human_approval` sub-structure. **These will be
> deprecated in v0.2** — see [FCoP issue #2](https://github.com/joinwell52-AI/FCoP/issues/2#issuecomment-4412811192)
> for the upstream v1.0 charter (7 abstractions, Boundary capability, etc.).
> CodeFlow v0.2 sprint 0 will fully align to `fcop@>=1.0,<2.0`.

---

The minimal executable wrapper around `@codeflow/runtime`. The shell is a **thin Layer-1 entry point** (design doc §11.2-§11.5) that:

1. Resolves `dataDir` (defaults to `~/.codeflow/v2/`).
2. Plants fixture kernel skills (`fcop` / `git` / `review`) on first launch.
3. Constructs `Runtime` (synchronously runs `RuntimeBootstrap`).
4. Registers `DEV-01` + `REVIEW-01` if `agents.json` is empty.
5. Starts the dispatcher / review engine / status reconciler.
6. Waits for `SIGINT` → graceful stop.

What it does **not** do (deferred to v0.2 — see [TASK-20260509-028 §二](../docs/agents/tasks/TASK-20260509-028-PM-to-DEV.md)):

- ❌ tray icon (system tray)
- ❌ web panel (Express + PWA)
- ❌ relay bridge (Mobile PWA over WebSocket)
- ❌ macOS / Linux packaging
- ❌ self-startup registration / single-instance mutex
- ❌ real `@cursor/sdk` (uses `InMemorySdkAdapter` in v0.1 — see `src/sdk-factory.ts`)

---

## Quick start

> ⚠️ **v0.1.0-rc.1 SEA/EXE status**: `pack.cmd` is **not currently green** on Node 24.14.0 + esbuild bundle. The bundler hits `@cursor/sdk` internal `.d.ts.map` references and `import.meta.url` in `@codeflow/protocol`'s validator (`cjs` format incompatibility). The PM `TASK-028 §三` explicitly accepted this fallback: **v0.1 ADMIN test runs via `npm start` (Option A); EXE bundling is rolled to v0.2 sprint 0** alongside the real `@cursor/sdk` adapter wiring (which itself blocks on Cursor's doorbell primitive). See [REPORT-20260509-028-DEV-to-PM.md](../docs/agents/tasks/REPORT-20260509-028-DEV-to-PM.md) §决策栏 for the full root cause + retry plan.

### Option A — npm script (works today, recommended fallback)

```powershell
cd codeflow-shell
npm install
npm start
```

You should see a banner like:

```text
===========================================================
CodeFlow v0.1.0-rc.1 — internal preview
===========================================================
Data dir       : C:\Users\me\.codeflow\v2
Inbox          : C:\Users\me\.codeflow\v2\inbox
Reviews        : C:\Users\me\.codeflow\v2\reviews
Skills loaded  : 3 (fcop, git, review)
MCP injector   : mode="stub" (2 agents mounted)
(planted 3 fixture skill(s) on first launch)
(registered 2 default agent(s) on first launch)
Bootstrap      : success=2, failed=0, kernel_failures=0
Status         : running. Drop TASK-*-XXX-to-AGENT.md to inbox.
Stop           : Ctrl+C
PID            : 12345
===========================================================
```

In another PowerShell window:

```powershell
copy codeflow-shell\examples\hello-world\sample-task.md "$env:USERPROFILE\.codeflow\v2\inbox\"
```

The main window's stdout will stream the full governance loop. See [`examples/hello-world/README.md`](examples/hello-world/README.md) for the expected log lines.

### Option B — single-EXE (Node SEA, Windows) — **DEFERRED to v0.2**

```powershell
cd codeflow-shell
npm install
.\pack.cmd
```

**Status (v0.1.0-rc.1): not green.** The pack pipeline (tsc typecheck → esbuild bundle → SEA blob → postject inject) currently fails at the esbuild step on three fronts:

1. `@cursor/sdk`'s ESM bundle references `.d.ts.map` files which esbuild has no loader for.
2. `@codeflow/protocol/src/validator.ts` uses `import.meta.url`, which is empty under esbuild's `--format=cjs` output.
3. `@cursor/sdk` re-exports from `@anysphere/cursor-sdk-shared/core-adapter`, which esbuild cannot resolve from the bundle root.

These are **bundler-tooling issues in the v0.1 dependency tree**, not Node SEA limitations per se — they require either (a) external-marking the cursor SDK + its sub-shared module + a `--format=esm` switch + a `.map` loader stub, or (b) a different bundler (`@vercel/ncc` looks promising; PM `TASK-028 §三` blesses this swap).

**v0.1 RC fallback (PM-blessed)**: ADMIN uses Option A (`npm start`). EXE bundling will be re-attempted in v0.2 sprint 0 alongside the real `@cursor/sdk` adapter wiring. `pack.cmd` is committed for v0.2's starting point.

If you want to experiment with EXE locally: `pack.cmd` is the recipe. If it succeeds, double-click `dist\CodeFlow-v0.1.0-rc.1.exe`.

---

## Configuration

The shell merges configuration from **six** layers (later layers override earlier):

1. **Built-in defaults** — `dataDir=~/.codeflow/v2/`, `listScope=local`, `defaultAgentKit=["DEV-01","REVIEW-01"]`.
2. `~/.codeflow/v2/config.json` — per-user persistent (recommended for personal Cursor key).
3. `./codeflow.config.json` (project root) — per-project pinned.
4. `~/.codeflow/v2/.env` + `./.env` — limited to a whitelist of `CURSOR_*` and `CODEFLOW_*` keys.
5. `process.env` — same whitelist.
6. CLI args — `--api-key`, `--relay-url`, `--room-key`, `--data-dir`.

### Whitelisted env vars

| Var | Purpose | Default |
|---|---|---|
| `CURSOR_API_KEY` | Activates real `CursorSdkAdapter`. **Without this, the shell uses `InMemorySdkAdapter` (smoke-test fallback)**. | unset |
| `CURSOR_DEFAULT_MODEL` | Default model hint (recorded for forward compat — not yet wired through SDK calls). | unset |
| `CURSOR_LIST_SCOPE` | `local` (per-cwd) or `cloud` (cross-machine). | `local` |
| `CODEFLOW_DATA_DIR` | Override `dataDir` (skills/, inbox/, reviews/, transcripts/, sessions/, agents.json). | `~/.codeflow/v2/` |
| `CODEFLOW_RELAY_URL` | WebSocket URL for Mobile PWA bridge (P3, not yet active). | unset |
| `CODEFLOW_ROOM_KEY` | Relay room key. | unset |
| `CODEFLOW_RELAY_AUTOCONNECT` | `true`/`1` to auto-connect; auto-set when both URL + room key present. | unset |

### `config.json` schema

```jsonc
{
  "cursor": {
    "apiKey": "ck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "defaultModel": "claude-sonnet-4",
    "listScope": "local"
  },
  "relay": {
    "url": "wss://ai.chedian.cc/codeflow/ws/",
    "roomKey": "codeflow-replace-with-your-id",
    "autoConnect": true
  },
  "dataDir": "~/.codeflow/v2",
  "defaultAgentKit": ["DEV-01", "REVIEW-01"]
}
```

Every key is optional. The `~` prefix expands to `homedir()` for `dataDir`. Place the file at `~/.codeflow/v2/config.json` for a per-user pin, or at `./codeflow.config.json` for a project pin (commit-proof — `.env` and `codeflow.config.json` are both `.gitignore`d).

### Quick start: getting a Cursor API key

1. Open [https://cursor.com/settings](https://cursor.com/settings) → **Account** → **API keys**.
2. Click **Create new key**. Copy the value (starts with `ck_`).
3. Pick **one** of the following options:
   - Easiest: `cp codeflow-shell/.env.example ~/.codeflow/v2/.env` then edit the file and set `CURSOR_API_KEY`.
   - Per-project: same but copy to `codeflow-shell/.env`.
   - Per-shell: `set CURSOR_API_KEY=ck_xxx` then `npm start` in the same window (PowerShell: `$env:CURSOR_API_KEY="ck_xxx"`).
4. Re-launch the shell. Banner should show:
   ```text
   Cursor SDK     : live (CursorSdkAdapter; apiKey from process.env.CURSOR_API_KEY, listScope="local")
   ```
   instead of the v0.1 fallback line.

If the banner still shows `fake (InMemorySdkAdapter; ...)`, the key didn't reach the shell — the most common cause on Windows is forgetting to relaunch after editing `.env`. The shell reads config exactly once, at startup.

---

## File layout

```
codeflow-shell/
├── src/
│   ├── main.ts              ← entry point — orchestrates 1-7 above
│   ├── bootstrap.ts         ← skill / agent fixture planters
│   └── sdk-factory.ts       ← real ?? fake SDK adapter chain
├── examples/
│   └── hello-world/
│       ├── sample-task.md   ← demo TASK to drop into inbox/
│       └── README.md        ← expected stdout + run instructions
├── sea-config.json          ← Node SEA config (Node 22+ stable, 24+ recommended)
├── pack.cmd                 ← Windows SEA pack script
├── package.json             ← name=codeflow-shell, private=true, deps on @codeflow/{runtime,protocol}
├── tsconfig.json            ← strict, ES2022 / NodeNext
├── README.md                ← (this file)
└── .gitignore               ← node_modules, dist, *.log
```

---

## v0.2 roadmap (not in this release)

| feature | tracking |
|---|---|
| tray + web panel + relay bridge | v0.2 sprint 1+ |
| macOS / Linux pack scripts | v0.2 sprint 1 |
| Real `@cursor/sdk` adapter | v0.2 sprint 0 (waits on `@cursor/sdk` doorbell primitive — see Cursor forum #158480) |
| Drop `Review.decision="needs_human"` enum | v0.2 sprint 0 (FCoP issue #2 alignment) |
| Boundary capability schema | v0.2 sprint 0 |
| Mobile PWA pairing | v0.2 sprint 1 |

---

## License

MIT. Same as the rest of the CodeFlow tree.
