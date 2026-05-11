/**
 * codeflow-shell main entry — v0.3.0-alpha (P4 sprint Day 1 — TASK-20260511-007).
 *
 * Reference:
 *   - design doc §11.2 + §11.3 (Layer 1 minimal entry)
 *   - TASK-20260510-002-PM-to-DEV §三 P1 §1 main.ts wiring (still in force)
 *   - TASK-20260510-007-PM-to-DEV §四 P2 §3 + §4 (P2 acceptance: spike + MT-2)
 *   - TASK-20260510-010-PM-to-DEV (MT-1 hotfix: defaultModel wire-through;
 *     adds banner WARNING block when live + local + no model)
 *   - TASK-20260510-012-PM-to-DEV (MT-2 hotfix: agent.send() carries
 *     local.force=true to expire wedged persisted runs; closes BUG-SDK-002.)
 *   - TASK-20260510-013-PM-to-DEV (MT-3 + MT-4 hotfixes: CURSOR_DEFAULT_MODEL
 *     default; ReviewEngine.extractText() walks content[] array.)
 *   - TASK-20260511-001-PM-to-DEV (MT-5 hotfix: Agent.create() no longer
 *     receives a `model` field — closes BUG-SDK-007.)
 *   - TASK-20260511-007-PM-to-DEV (P4 main sprint Day 1: introduce
 *     `FcopProjectClient` + banner PYTHON_BIN/fcop check + .env.example
 *     PYTHON_BIN entry. Day 2-5 will progressively swap TaskDispatcher /
 *     ReviewEngine / NeedsHumanGate / AgentRegistry over to fcop@1.1.0
 *     Python API via pythonia. v0.3.0-alpha.)
 *
 * Pipeline:
 *
 *   1. `loadConfig()` — merge defaults / config.json / .env / process.env / CLI args.
 *   2. Ensure data dirs exist (chokidar doesn't auto-create).
 *   3. Plant fixture skills if `<skillsDir>/fcop.json` is missing.
 *   4. **NEW (P4 Day 1.4)**: Probe pythonia + fcop@1.1.0 readiness via
 *      `assertFcopReady()`. Fail fast with actionable error if PYTHON_BIN
 *      points nowhere / Python < 3.10 / fcop@1.1.0 not installed.
 *   5. Pick the SDK adapter — real CursorSdkAdapter if cfg.cursor.apiKey
 *      resolves, else InMemorySdkAdapter (smoke-test fallback).
 *   6. Construct Runtime (synchronously runs RuntimeBootstrap).
 *   7. Register the default agent kit if `agents.json` is empty.
 *   8. Start dispatcher / review engine / status reconciler.
 *   9. Print banner with config provenance + adapter mode + watcher dir +
 *      PYTHON_BIN + fcop version + PID.
 *   10. Wait for SIGINT / SIGTERM → graceful stop (now also
 *       `disposeFcopBridge()` to kill the pythonia child Python process).
 *
 * What this file does NOT do (deferred to later v0.3 days / sprints):
 *
 *   - Day 2-5: swap TaskDispatcher / ReviewEngine.writeReview /
 *              NeedsHumanGate / AgentRegistry to FcopProjectClient.
 *   - Day 6:   bump version + CHANGELOG + release notes.
 *   - P3:      instantiate `RelayBridge` from `cfg.relay.*`.
 *   - P5:      install.ps1 auto-install Python + fcop.
 */

import { existsSync } from "node:fs";
import { join } from "node:path";

import {
  Runtime,
  assertFcopReady,
  disposeFcopBridge,
  FcopClientError,
  FcopProjectClient,
} from "@codeflow/runtime";

import {
  ensureDataDirs,
  plantSkillFixturesIfMissing,
  registerDefaultAgentKitIfEmpty,
} from "./bootstrap.ts";
import { loadConfig } from "./config.ts";
import {
  describeAdapterChoice,
  makeFakeCursorSdkAdapter,
  makeRealCursorSdkAdapter,
} from "./sdk-factory.ts";

/**
 * Version stays `0.2.0-beta.3` until P4 Day 6 (PM TASK-20260511-007 §四 Day
 * 6.6 "版本号 bump"). Day 1-5 work is **on top of** beta.3 — the banner
 * already shows the per-day P4 progress in the new "fcop bridge" line.
 */
const VERSION = "0.2.0-beta.3";

interface ShellLogger {
  info: (msg: string) => void;
  warn: (msg: string) => void;
  error: (msg: string) => void;
}

const consoleLogger: ShellLogger = {
  info: (msg) => console.log(msg),
  warn: (msg) => console.warn(msg),
  error: (msg) => console.error(msg),
};

/**
 * Result of {@link probeFcopBridge}. We discriminate three states so the
 * banner can print the right thing and tests can drive each branch:
 *
 *   - `ok`       fcop@1.1.0 reachable + version captured.
 *   - `failed`   probe threw. `probeFcopBridge` already printed actionable
 *                  errors to stderr and called `process.exit(1)` — this
 *                  variant exists so TS knows the branch is unreachable in
 *                  production, but the type stays sound for tests / sandbox.
 *   - `skipped`  user explicitly opted out via `CODEFLOW_SKIP_FCOP_PROBE=1`.
 *                  Used during integration tests that pre-stub fcop and
 *                  during early P4 dev when Python isn't yet on the box.
 */
type FcopProbeResult =
  | {
      status: "ok";
      fcopVersion: string;
      pythonVersion: string;
      pythonExecutable: string;
    }
  | {
      status: "skipped";
      reason: string;
    }
  | {
      status: "failed";
      message: string;
    };

/**
 * Probe pythonia + fcop@1.1.0 readiness. **Side-effect: kills the process
 * with exit code 2 on failure** (after printing actionable hints to
 * stderr). Returns a structured result for the banner if the probe
 * succeeds or was skipped.
 *
 * Why exit code **2** (not 1)? `main().catch` already uses exit code 1
 * for unexpected fatals. Splitting "config / env failure" → 2 from
 * "uncaught exception" → 1 lets ops scripts (Day 6 smoke tests; later
 * install.ps1 / EXE bundler) distinguish them.
 */
async function probeFcopBridge(): Promise<FcopProbeResult> {
  if (process.env["CODEFLOW_SKIP_FCOP_PROBE"] === "1") {
    return {
      status: "skipped",
      reason: "CODEFLOW_SKIP_FCOP_PROBE=1 in env",
    };
  }
  // PRE-flight check: pythonia's StdioCom synchronously cp.spawn()s
  // `process.env.PYTHON_BIN || 'python3'` the first time something from
  // the pythonia module is imported. `cp.spawn()` returns synchronously
  // even when the target doesn't exist — the ENOENT surfaces as an
  // async 'error' event on the child process, which pythonia doesn't
  // listen for, so Node crashes with exit code 1 BEFORE assertFcopReady's
  // try/catch can ever run.
  //
  // Therefore we verify PYTHON_BIN points to an existing file BEFORE we
  // touch any code path that transitively imports pythonia. The check is
  // intentionally only "file exists" (not "is a Python interpreter +
  // version + has fcop") — the deeper checks live in assertFcopReady().
  const pythonBin = process.env["PYTHON_BIN"];
  if (pythonBin && !existsSync(pythonBin)) {
    printFcopProbeFailure(
      `PYTHON_BIN points at a path that does not exist: ${pythonBin}`,
      [
        "Check the spelling, escape backslashes properly in .env, or unset",
        "PYTHON_BIN to let pythonia fall back to PATH `python3` / `python`.",
        "",
        "Find a valid path with:",
        "  Windows: where.exe python  OR  py -3 -c \"import sys; print(sys.executable)\"",
        "  macOS:   which python3      OR  python3 -c \"import sys; print(sys.executable)\"",
        "  Linux:   which python3      OR  python3 -c \"import sys; print(sys.executable)\"",
      ],
    );
  }
  try {
    const info = await assertFcopReady();
    return {
      status: "ok",
      fcopVersion: info.fcopVersion,
      pythonVersion: info.pythonVersion,
      pythonExecutable: info.pythonExecutable,
    };
  } catch (err) {
    const isClientError = err instanceof FcopClientError;
    const message = err instanceof Error ? err.message : String(err);
    if (isClientError) {
      // assertFcopReady already builds a multi-line actionable message.
      printFcopProbeFailure(message, []);
    } else {
      printFcopProbeFailure("Unexpected error during fcop bridge probe:", [
        message,
        "",
        "Hints:",
        "  - Set PYTHON_BIN to a Python 3.10+ executable that has fcop installed.",
        `    Current PYTHON_BIN = ${process.env["PYTHON_BIN"] ?? "<unset>"}`,
        "  - Install fcop: `py -3 -m pip install fcop` (or `pip install fcop`",
        "    on the same interpreter PYTHON_BIN points to).",
      ]);
    }
  }
  // Unreachable but TS requires a return.
  return { status: "failed", message: "unreachable" };
}

/**
 * Print a structured FATAL banner with hints and exit with code 2.
 *
 * **never returns** — the function is typed `never` so TS knows control flow
 * after a call to it can't reach further statements (we still write a
 * sentinel `return` after the `process.exit(2)` for runtime sanity).
 */
function printFcopProbeFailure(headline: string, lines: string[]): never {
  console.error("===========================================================");
  console.error("FATAL: pythonia + fcop@1.1.0 bridge is not ready.");
  console.error("===========================================================");
  console.error(headline);
  for (const line of lines) console.error(line);
  console.error("");
  console.error(
    "To run codeflow-shell without the fcop bridge (Day 1 development only),",
  );
  console.error("set CODEFLOW_SKIP_FCOP_PROBE=1 and the probe will be skipped.");
  console.error("===========================================================");
  process.exit(2);
}

function describeSources(sources: ReturnType<typeof loadConfig>["sources"]): string {
  const order = [
    sources.userConfig ? "user-config" : null,
    sources.projectConfig ? "project-config" : null,
    sources.userEnvFile ? "user-env" : null,
    sources.projectEnvFile ? "project-env" : null,
    sources.processEnv ? "process.env" : null,
    sources.cliArgs ? "cli-args" : null,
  ].filter(Boolean);
  return order.length === 0 ? "defaults only" : order.join(" → ");
}

async function main(): Promise<void> {
  // ── 1. Resolve config (5-tier merge) ───────────────────────────────
  const cfg = loadConfig();
  const dataDir = cfg.dataDir;
  const inboxDir = join(dataDir, "inbox");
  const skillsDir = join(dataDir, "skills");

  // ── 2. Ensure all data dirs exist BEFORE Runtime.create ────────────
  await ensureDataDirs(dataDir);

  // ── 3. Plant fixture skills BEFORE Runtime.create ──────────────────
  const skillResult = await plantSkillFixturesIfMissing(skillsDir);

  // ── 4. fcop bridge readiness probe (P4 sprint Day 1.4) ─────────────
  //
  // BUG-SDK-001 taught us: silent feature-flags that surface as obscure
  // failures 30 seconds into a task dispatch waste user time. The fcop
  // bridge has THREE common ways to be misconfigured on Windows:
  //
  //   1. `PYTHON_BIN` env var not set, and PATH `python3` / `python` is a
  //      Python that doesn't have fcop installed (Windows defaults to
  //      python.org PATH installer which is often a separate interpreter
  //      from the one with fcop).
  //   2. Python < 3.10 (fcop requires 3.10+; DEV-005 §五 S2).
  //   3. fcop@1.1.0 missing (`pip install fcop` was never run, or run on
  //      the wrong interpreter — see #1).
  //
  // We probe NOW (before Runtime.create) so users see the error at the
  // banner stage with actionable hints, not after the first task drop.
  const fcopReady = await probeFcopBridge();

  // ── 5. Pick the SDK adapter ────────────────────────────────────────
  const sdkAdapter =
    makeRealCursorSdkAdapter(cfg.cursor) ?? makeFakeCursorSdkAdapter();
  const adapterDescription = describeAdapterChoice(cfg.cursor, sdkAdapter);

  // ── 6. Construct runtime (bootstrap runs synchronously) ────────────
  // P4 sprint Day 2: when the fcop probe succeeded, build a
  // FcopProjectClient bound to the data dir and inject it into Runtime
  // so TaskDispatcher's parser walks fcop @1.1.0 instead of in-process
  // yaml. When the probe was skipped or fcop is otherwise unavailable,
  // omit the client — Runtime then keeps the legacy yaml parser
  // (back-compat + CODEFLOW_SKIP_FCOP_PROBE=1 escape hatch).
  //
  // Note: we pass `workspaceDir: "docs/agents"` to keep CodeFlow's v0.x
  // task layout (`docs/agents/tasks/`) — TASK-20260511-007 §五 P1-1 +
  // DEV-005 §S8 escape hatch. `ensureInitialized: false` because fcop
  // init writes 12+ files and we want full control over when that
  // happens; the demo / shell startup just READS the existing tree.
  let fcopClient: FcopProjectClient | undefined;
  if (fcopReady.status === "ok") {
    try {
      fcopClient = await FcopProjectClient.create({
        projectRoot: process.cwd(),
        workspaceDir: "docs/agents",
        ensureInitialized: false,
      });
    } catch (err) {
      // The probe passed but the actual Project construction failed —
      // this should be rare (e.g. projectRoot points at a place fcop
      // refuses), but it's not worth crashing the shell. Log a warning
      // and proceed with the legacy yaml parser.
      consoleLogger.warn(
        `[shell] FcopProjectClient.create failed: ${
          err instanceof Error ? err.message : String(err)
        } — falling back to in-process yaml parser`,
      );
      fcopClient = undefined;
    }
  }

  const runtime = await Runtime.create({
    sdkAdapter,
    persistDir: dataDir,
    inboxDir,
    skillsDir,
    logger: consoleLogger,
    ...(fcopClient ? { fcopClient } : {}),
  });

  // ── 7. Register default agent kit ──────────────────────────────────
  const agentResult = await registerDefaultAgentKitIfEmpty({
    dataDir,
    runtime,
  });

  // ── 8. Start ───────────────────────────────────────────────────────
  await runtime.start();

  // ── 9. Banner ──────────────────────────────────────────────────────
  console.log("===========================================================");
  console.log(`CodeFlow v${VERSION} — internal preview`);
  console.log("===========================================================");
  console.log(`Data dir       : ${dataDir}`);
  console.log(`Inbox          : ${runtime.watcher.dir}`);
  console.log(`Reviews        : ${runtime.reviewWriter.reviewsDir}`);
  console.log(`Config sources : ${describeSources(cfg.sources)}`);
  console.log(`Cursor SDK     : ${adapterDescription}`);
  // P4 Day 1.4: surface fcop bridge state in the banner. When the probe
  // skipped (FAKE_PYTHONIA env / probe disabled), show "(skipped)".
  if (fcopReady.status === "ok") {
    const parserMode = fcopClient
      ? "TaskParser=fcop"
      : "TaskParser=yaml fallback (FcopProjectClient.create failed)";
    console.log(
      `fcop bridge    : fcop ${fcopReady.fcopVersion} via pythonia ` +
        `(Python at ${fcopReady.pythonExecutable})`,
    );
    console.log(`Task parser    : ${parserMode}`);
  } else if (fcopReady.status === "skipped") {
    console.log(`fcop bridge    : (skipped — ${fcopReady.reason})`);
    console.log(`Task parser    : yaml fallback (no fcop client)`);
  } else {
    console.log(`fcop bridge    : FAILED — see message above`);
    console.log(`Task parser    : yaml fallback`);
  }
  // MT-1 friendly hint: live adapter without a default model + local
  // listScope = nothing actually wrong yet, but every task drop will
  // fail at `agent.send()` with `Local SDK agents require an explicit
  // model.` We surface that up-front instead of letting users hit it
  // after a 30-second governance loop. (BUG-SDK-001 / TASK-007 §3.5)
  const listScope = cfg.cursor.listScope ?? "local";
  const liveAdapterPicked = adapterDescription.startsWith("live ");
  if (
    liveAdapterPicked &&
    listScope === "local" &&
    !cfg.cursor.defaultModel
  ) {
    console.warn(
      "WARNING        : live SDK + local mode + no CURSOR_DEFAULT_MODEL set.",
    );
    console.warn(
      "                 First task drop will fail with 'Local SDK agents",
    );
    console.warn(
      "                 require an explicit model.' Set CURSOR_DEFAULT_MODEL",
    );
    console.warn(
      "                 in ~/.codeflow/v2/.env (e.g. `default`, `claude-sonnet-4`)",
    );
    console.warn(
      "                 or per-task `spec.modelId`. See README §Cursor API key.",
    );
  }
  console.log(
    `Skills loaded  : ${runtime.skillRegistry.size()} ` +
      `(${runtime.skillRegistry.list().map((s) => s.skill_id).join(", ") || "(none)"})`,
  );
  console.log(
    `MCP injector   : mode="${runtime.mcpInjector.mode}" ` +
      `(${runtime.mcpInjector.listMounted().length} agents mounted)`,
  );
  if (cfg.relay.autoConnect && cfg.relay.url && cfg.relay.roomKey) {
    console.log(
      `Relay (P3)     : ${cfg.relay.url} (room=${cfg.relay.roomKey}) — wiring deferred to v0.2.0-rc.1`,
    );
  } else {
    console.log(`Relay (P3)     : not configured (set CODEFLOW_RELAY_URL + CODEFLOW_ROOM_KEY to enable in P3)`);
  }
  if (skillResult.planted > 0) {
    console.log(
      `(planted ${skillResult.planted} fixture skill(s) on first launch)`,
    );
  }
  if (agentResult.registered > 0) {
    console.log(
      `(registered ${agentResult.registered} default agent(s) on first launch)`,
    );
  }
  console.log(
    `Bootstrap      : success=${runtime.bootstrap.report.success.length}, ` +
      `failed=${runtime.bootstrap.report.failed.length}, ` +
      `kernel_failures=${runtime.bootstrap.report.kernel_failures.length}`,
  );
  console.log(`Status         : running. Drop TASK-*-XXX-to-AGENT.md to inbox.`);
  console.log(`Stop           : Ctrl+C`);
  console.log(`PID            : ${process.pid}`);
  console.log("===========================================================");

  // ── 10. Graceful stop ──────────────────────────────────────────────
  let stopping = false;
  const stop = async (signal: string): Promise<void> => {
    if (stopping) return;
    stopping = true;
    console.log(`\n[shell] received ${signal}, stopping runtime...`);
    try {
      await runtime.stop();
      // P4 Day 1.4: tear down pythonia child Python process. Without this
      // Node would hang on shutdown because pythonia keeps a stdio-piped
      // child alive (see fcop-client.ts `__killRealPythonChildForTests`
      // JSDoc for the same hazard surfaced in tests).
      await disposeFcopBridge();
      console.log("[shell] runtime stopped cleanly. Goodbye.");
      process.exit(0);
    } catch (err) {
      console.error(
        "[shell] error during stop:",
        err instanceof Error ? err.message : err,
      );
      process.exit(1);
    }
  };
  process.on("SIGINT", () => void stop("SIGINT"));
  process.on("SIGTERM", () => void stop("SIGTERM"));
}

main().catch((err) => {
  console.error("[shell] fatal:", err);
  process.exit(1);
});
