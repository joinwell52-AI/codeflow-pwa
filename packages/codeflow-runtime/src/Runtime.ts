/**
 * Runtime — high-level composition root for the CodeFlow AI Runtime.
 *
 * Sprint S3 Phase C shipped the first 8 subsystems; Sprint S4 added
 * three more (review layer + the AgentStatusReconciler integration hook
 * resolving REPORT-018 §五决策 B'); Sprint S5 Phase E now adds three
 * more for Skill Runtime + fcop hard-dependency enforcement. The full
 * v0.1 stack is now:
 *
 *   PersistentStore (agents.json)
 *     → SkillRegistry (.codeflow/state/skills/)              ★ S5
 *     → KernelDependencyValidator (fcop hard-dep gate)       ★ S5
 *     → MCPInjector (stub mode v0.1)                         ★ S5
 *     → AgentRegistry (with optional kernel + mcp hooks)
 *     → RuntimeBootstrap (run once + kernel-dep gate)        ★ S5
 *     → SessionStore (per-session JSON)
 *     → TranscriptWriter (per-run markdown)
 *     → SessionManager
 *     → InboxWatcher (chokidar)
 *     → StateHistoryWriter
 *     → TaskDispatcher (glue)
 *     → ReviewWriter (.codeflow/state/reviews/)              ★ S4
 *     → NeedsHumanGate (v0.1 sink="cli")                     ★ S4
 *     → ReviewEngine (subscribes to SessionManager.onEvent)  ★ S4
 *     → AgentStatusReconciler (B' integration hook)          ★ S4
 *
 * Reference:
 *   - TASK-20260509-018 §主交付 5b (this file, original Phase C version)
 *   - TASK-20260509-022 §主交付 5a (this file, S4 update)
 *   - TASK-20260509-024 §主交付 5b (this file, S5 update)
 *   - design doc §0.5 + §0.7.5 (fcop hard-dep) + §0.8.3 + §10.2
 *
 * What this file deliberately is NOT:
 *
 *   - A long-lived daemon entry point. That's `codeflow-shell` (S6).
 *     Runtime.ts is a building block; the daemon binary will import it
 *     and add SIGTERM/SIGINT trapping, log routing, etc.
 *   - A multi-tenant orchestrator. v0.1 = single PC, single workspace.
 *   - A CLI argument parser. Caller passes options as a typed object.
 */

import { join } from "node:path";

import type { FcopProjectClient } from "./_external/fcop-client.ts";
import { AgentRegistry } from "./registry/AgentRegistry.ts";
import type { AgentSdkAdapter } from "./registry/AgentSdkAdapter.ts";
import { AgentStatusReconciler } from "./registry/AgentStatusReconciler.ts";
import {
  JsonFileStore,
  type PersistentStore,
} from "./registry/PersistentStore.ts";
import { RuntimeBootstrap } from "./registry/RuntimeBootstrap.ts";
import {
  NeedsHumanGate,
  ReviewEngine,
  ReviewWriter,
  type ReviewPolicy,
} from "./review/index.ts";
import {
  InboxWatcher,
  StateHistoryWriter,
  TaskDispatcher,
  type TaskDispatcherLogger,
  TaskParser,
} from "./scheduler/index.ts";
import { SessionManager } from "./session/SessionManager.ts";
import { SessionStore } from "./session/SessionStore.ts";
import { TranscriptWriter } from "./session/TranscriptWriter.ts";
import {
  KernelDependencyValidator,
  MCPInjector,
  SkillRegistry,
} from "./skill/index.ts";
import type { ReconciliationReport } from "./types/state.ts";

export interface RuntimeCreateOptions {
  /**
   * SDK adapter (real `CursorSdkAdapter` for production, `InMemorySdkAdapter`
   * for the Phase C E2E demo). Caller owns construction so they can plant
   * a fixture roster ahead of time.
   */
  sdkAdapter: AgentSdkAdapter;
  /**
   * Directory that owns runtime persistence (agents.json + sessions/ +
   * transcripts/). Default: `.codeflow/state` rooted at process.cwd().
   *
   * Sub-paths derived from this:
   *   <persistDir>/agents.json
   *   <persistDir>/sessions/<session_id>.json
   *   <persistDir>/transcripts/<run_id>.md
   */
  persistDir: string;
  /**
   * Directory the InboxWatcher monitors. Default: `docs/agents/tasks/`
   * relative to process.cwd().
   */
  inboxDir: string;
  /**
   * Directory the `ReviewWriter` writes `REVIEW-*.md` files into.
   * Default: `<persistDir>/reviews`. Sprint S4 addition.
   */
  reviewsDir?: string;
  /**
   * Override the review policy. Default: `DefaultReviewPolicy` (always
   * review, always pick `"REVIEW"` role). Sprint S4 addition.
   */
  reviewPolicy?: ReviewPolicy;
  /**
   * Directory the `SkillRegistry` scans for `<skill_id>.json` files.
   * Default: `<persistDir>/skills`. Sprint S5 addition.
   *
   * If absent or empty, the kernel-dep validator will reject every
   * non-trivial agent (no fcop@.+ resolvable) — the demo opts out of
   * this by registering only agents with `skills: []` and not wiring
   * the validator. Production deployments MUST plant at least one
   * fcop-providing skill file here before starting.
   */
  skillsDir?: string;
  /**
   * v0.1 = "stub". Setting "live" makes `Runtime.create` eager-throw
   * `MCPInjectorLiveModeNotImplementedError` — see decision T in
   * REPORT-024. Sprint S5 addition.
   */
  mcpInjectorMode?: "stub" | "live";
  /** Optional logger override forwarded to TaskDispatcher + Bootstrap. */
  logger?: TaskDispatcherLogger;
  /**
   * Optional fcop@1.1.0 client (P4 sprint Day 2 — TASK-20260511-009).
   *
   * When provided, `Runtime` wires a `TaskParser` instance configured to
   * delegate to `fcopClient.readTask(filename)` instead of doing
   * in-process YAML parsing. fcop validates the front-matter against the
   * official `task.schema` and returns a typed `FcopTask`, which the
   * parser then shapes back into CodeFlow's existing `ParsedTask`
   * interface — TaskDispatcher / SessionManager / state-history paths
   * downstream are untouched.
   *
   * When omitted (CODEFLOW_SKIP_FCOP_PROBE=1 path, unit tests, demo),
   * Runtime keeps the legacy static yaml parser. This preserves backward
   * compat with all pre-Day-2 callers and the 4 existing TaskParser
   * tests.
   */
  fcopClient?: FcopProjectClient;
}

export interface RuntimeBootstrapResult {
  report: ReconciliationReport;
}

/**
 * Composed runtime. Opaque-ish to callers: most code only needs
 * `.start()` / `.stop()`. The public sub-systems are exposed as
 * read-only fields for tests and for the demo to register agents.
 */
export class Runtime {
  /** Reconciliation report from the constructor's RuntimeBootstrap.run(). */
  public readonly bootstrap: RuntimeBootstrapResult;

  public readonly store: PersistentStore;
  public readonly skillRegistry: SkillRegistry;
  public readonly kernelValidator: KernelDependencyValidator;
  public readonly mcpInjector: MCPInjector;
  public readonly registry: AgentRegistry;
  public readonly sessionStore: SessionStore;
  public readonly transcriptWriter: TranscriptWriter;
  public readonly sessionManager: SessionManager;
  public readonly historyWriter: StateHistoryWriter;
  public readonly watcher: InboxWatcher;
  public readonly dispatcher: TaskDispatcher;
  public readonly reviewWriter: ReviewWriter;
  public readonly needsHumanGate: NeedsHumanGate;
  public readonly reviewEngine: ReviewEngine;
  public readonly statusReconciler: AgentStatusReconciler;

  private constructor(parts: {
    bootstrap: RuntimeBootstrapResult;
    store: PersistentStore;
    skillRegistry: SkillRegistry;
    kernelValidator: KernelDependencyValidator;
    mcpInjector: MCPInjector;
    registry: AgentRegistry;
    sessionStore: SessionStore;
    transcriptWriter: TranscriptWriter;
    sessionManager: SessionManager;
    historyWriter: StateHistoryWriter;
    watcher: InboxWatcher;
    dispatcher: TaskDispatcher;
    reviewWriter: ReviewWriter;
    needsHumanGate: NeedsHumanGate;
    reviewEngine: ReviewEngine;
    statusReconciler: AgentStatusReconciler;
  }) {
    this.bootstrap = parts.bootstrap;
    this.store = parts.store;
    this.skillRegistry = parts.skillRegistry;
    this.kernelValidator = parts.kernelValidator;
    this.mcpInjector = parts.mcpInjector;
    this.registry = parts.registry;
    this.sessionStore = parts.sessionStore;
    this.transcriptWriter = parts.transcriptWriter;
    this.sessionManager = parts.sessionManager;
    this.historyWriter = parts.historyWriter;
    this.watcher = parts.watcher;
    this.dispatcher = parts.dispatcher;
    this.reviewWriter = parts.reviewWriter;
    this.needsHumanGate = parts.needsHumanGate;
    this.reviewEngine = parts.reviewEngine;
    this.statusReconciler = parts.statusReconciler;
  }

  /**
   * Compose all sub-systems and run RuntimeBootstrap.
   *
   * After this resolves the runtime is "ready" but NOT yet listening for
   * inbox events — call `.start()` to engage the dispatcher.
   *
   * @throws `RuntimeBootstrapError` if `agents.json` is corrupt or
   *   `SDK.list()` fails (HARD FAIL per crash-recovery.md decision 2).
   */
  static async create(opts: RuntimeCreateOptions): Promise<Runtime> {
    const agentsJsonPath = join(opts.persistDir, "agents.json");
    const sessionsDir = join(opts.persistDir, "sessions");
    const transcriptsDir = join(opts.persistDir, "transcripts");
    const reviewsDir = opts.reviewsDir ?? join(opts.persistDir, "reviews");
    const skillsDir = opts.skillsDir ?? join(opts.persistDir, "skills");

    // --- skill layer (Sprint S5) — must come BEFORE registry so the
    //     registry's kernel-dep hook has a non-null validator. The
    //     mcpInjector ctor eager-throws on mode="live" (decision T)
    //     before any other side effect runs.
    const skillRegistry = new SkillRegistry({
      skillsDir,
      ...(opts.logger ? { logger: opts.logger } : {}),
    });
    await skillRegistry.load();
    const kernelValidator = new KernelDependencyValidator({
      skillRegistry,
      ...(opts.logger ? { logger: opts.logger } : {}),
    });
    const mcpInjector = new MCPInjector({
      skillRegistry,
      sdkAdapter: opts.sdkAdapter,
      mode: opts.mcpInjectorMode ?? "stub",
      ...(opts.logger ? { logger: opts.logger } : {}),
    });

    // --- registry layer ---
    const store = new JsonFileStore({ path: agentsJsonPath });
    const registry = new AgentRegistry({
      store,
      sdk: opts.sdkAdapter,
      kernelValidator,
      mcpInjector,
    });
    const bootstrap = new RuntimeBootstrap({
      store,
      sdk: opts.sdkAdapter,
      registry,
      kernelValidator,
      mcpInjector,
    });
    const report = await bootstrap.run();

    // --- session layer ---
    const sessionStore = new SessionStore({ dir: sessionsDir });
    const transcriptWriter = new TranscriptWriter({ dir: transcriptsDir });
    const sessionManager = new SessionManager({
      registry,
      sdk: opts.sdkAdapter,
      sessionStore,
      transcriptWriter,
    });

    // --- scheduler layer ---
    const historyWriter = new StateHistoryWriter();
    const watcher = new InboxWatcher({ dir: opts.inboxDir });
    // P4 sprint Day 2: when a fcop client is supplied, wire a TaskParser
    // instance whose `.parse(filepath)` delegates to fcop's typed
    // `read_task(filename_or_id)`. Otherwise leave dispatcher on the
    // legacy static parser (back-compat + CODEFLOW_SKIP_FCOP_PROBE=1
    // escape hatch).
    const parserOverride = opts.fcopClient
      ? (() => {
          const inst = new TaskParser({ fcopClient: opts.fcopClient });
          return { parse: inst.parse.bind(inst) };
        })()
      : undefined;
    const dispatcher = new TaskDispatcher({
      watcher,
      historyWriter,
      registry,
      sessionManager,
      ...(parserOverride ? { parser: parserOverride } : {}),
      ...(opts.logger ? { logger: opts.logger } : {}),
    });

    // --- review + B' integration layer (Sprint S4) ---
    const reviewWriter = new ReviewWriter({ reviewsDir });
    const needsHumanGate = new NeedsHumanGate({
      sink: "cli",
      ...(opts.logger ? { logger: opts.logger } : {}),
    });
    const reviewEngine = new ReviewEngine({
      sessionManager,
      registry,
      sessionStore,
      historyWriter,
      reviewWriter,
      needsHumanGate,
      inboxDir: opts.inboxDir,
      ...(opts.reviewPolicy ? { policy: opts.reviewPolicy } : {}),
      ...(opts.logger ? { logger: opts.logger } : {}),
    });
    const statusReconciler = new AgentStatusReconciler({
      sessionManager,
      registry,
      store,
      ...(opts.logger ? { logger: opts.logger } : {}),
    });

    return new Runtime({
      bootstrap: { report },
      store,
      skillRegistry,
      kernelValidator,
      mcpInjector,
      registry,
      sessionStore,
      transcriptWriter,
      sessionManager,
      historyWriter,
      watcher,
      dispatcher,
      reviewWriter,
      needsHumanGate,
      reviewEngine,
      statusReconciler,
    });
  }

  /**
   * Start the dispatcher (which starts the watcher under the hood) plus
   * the review engine + status reconciler. Subscribers are wired in this
   * order:
   *
   *   1. AgentStatusReconciler (so session_started promotes status BEFORE
   *      the dispatcher's listener can pick up the next dropped task)
   *   2. ReviewEngine          (subject session_ended → reviewer flow)
   *   3. TaskDispatcher        (inbox → startSession)
   *
   * Sprint S4: order matters for correctness — the reconciler must be
   * up first so the doorbell `reject_busy` path is reachable.
   */
  async start(): Promise<void> {
    this.statusReconciler.start();
    this.reviewEngine.start();
    await this.dispatcher.start();
  }

  /**
   * Gracefully stop everything in reverse order. Does NOT cancel running
   * sessions — callers wanting that should call
   * `runtime.sessionManager.cancelAllForEmergencyStop()` first.
   */
  async stop(): Promise<void> {
    await this.dispatcher.stop();
    await this.reviewEngine.stop();
    await this.statusReconciler.stop();
  }
}
