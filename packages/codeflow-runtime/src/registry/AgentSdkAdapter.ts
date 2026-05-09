/**
 * AgentSdkAdapter — narrow seam between AgentRegistry and `@cursor/sdk`.
 *
 * Why an adapter at all:
 *
 * - `AgentRegistry` and `RuntimeBootstrap` need three SDK calls:
 *   `create`, `resume`, `list`. Anything else (send / cancel / artifacts)
 *   is outside the registry's contract — handled by `SessionManager` (S3
 *   Phase B+).
 * - Tests must run without a real `CURSOR_API_KEY` / network. The adapter
 *   abstraction lets us inject `InMemorySdkAdapter` so 11 unit-test
 *   scenarios (TASK-009 §必交付 6) cover behavior without touching SDK.
 * - The adapter is the ONLY place that imports `@cursor/sdk` types — keeps
 *   the registry / bootstrap files SDK-version-agnostic.
 *
 * Cross-link: `_ignore/spike_sdk_doorbell/sender.ts` validated the SDK
 * surface used here (Agent.create/resume/list signatures + asyncDispose).
 * Reproduced inline (NOT git-mv'd; spike folder is preserved as historical
 * evidence per HANDOFF + REPORT-002).
 */

import { Agent, CursorAgentError } from "@cursor/sdk";
import type { ListAgentsOptions } from "@cursor/sdk";

import type { AgentLayer, AgentRuntime } from "@codeflow/protocol";

import { SdkRunHandle, type SdkRunLike } from "../session/SdkRunHandle.ts";
import type { RunHandle } from "../types/state.ts";

/**
 * Spec used to call `Agent.create()`. Mirrors what `AgentRegistry.register`
 * extracts from a protocol-level `Agent`: enough to bootstrap an SDK agent
 * but not the whole FCoP record (avoids leaking governance fields into
 * SDK tooling that doesn't understand them).
 */
export interface AgentCreateSpec {
  /** FCoP role id, e.g. `"DEV-01"`. Used as the SDK agent's display name. */
  agentId: string;
  /** Mapped to `roles.yaml` `roles[].id`. Used for the role brief. */
  role: string;
  /** §0.9.1 layer; informs the SDK display name only. */
  layer: AgentLayer;
  /** Cursor SDK runtime mode. Currently `local` is the v0.1 reality. */
  runtime: AgentRuntime;
  /** For local agents: cwd path. For cloud agents: repo URL. */
  workspace?: string;
  /** Optional model hint forwarded to `Agent.create({ model })`. */
  modelId?: string;
}

/**
 * Spec used to call `agent.send()` on a freshly resumed SDK agent. Carries
 * the FCoP-side identifiers that `SessionManager` stamps onto the resulting
 * `RunHandle` (so transcript files / Mobile push events have the right
 * `session_id` / `agent_id` without the adapter having to invent them).
 */
export interface AgentSendSpec {
  /** Pattern: `^session-[a-z0-9-]+$`. Used as `RunHandle.session_id`. */
  sessionId: string;
  /** FCoP role id, e.g. `"DEV-01"`. Used as `RunHandle.agent_id`. */
  agentId: string;
  /** Plain text to forward to `agent.send(text)`. */
  text: string;
  /**
   * Optional model hint. Passed through to `Agent.resume({ model })`.
   * Defaults to the adapter's configured default model.
   */
  modelId?: string;
}

/**
 * Adapter contract — four methods, all narrow on purpose. Implementations
 * MUST be safe to call concurrently for `list`, but `create` / `resume`
 * / `send` may serialize at the implementation's discretion (the SDK
 * already enforces `409 agent_busy` server-side).
 *
 * Phase A shipped 3 methods (create / list / resume). Phase B added `send`
 * (TASK-20260509-013 §主交付 1 (c)). The reason `send` lives on the
 * adapter, not on `SessionManager` directly, is the §"adapter is the only
 * place that imports `@cursor/sdk`" rule from this file's docstring.
 */
export interface AgentSdkAdapter {
  /**
   * Create an SDK agent and return its (cloud or local) `agentId`.
   * Mirrors `Agent.create({...})` — the registry takes the returned id
   * verbatim and stores it as `record.protocol.sdk_agent_id`.
   */
  create(spec: AgentCreateSpec): Promise<{ sdk_agent_id: string }>;

  /**
   * Enumerate `sdk_agent_id`s currently visible to the SDK. Used by
   * `RuntimeBootstrap` to detect orphaned / foreign records.
   *
   * Implementations MAY filter by runtime/cwd; `RuntimeBootstrap` calls
   * with the runtime's configured cwd to scope local-runtime listings.
   */
  list(): Promise<string[]>;

  /**
   * Re-bind to an existing SDK agent. Equivalent to `Agent.resume(id)`,
   * but adapter-shaped so tests don't need a real SDK.
   *
   * MUST throw if the SDK no longer recognizes the id; callers translate
   * that into the `orphan_local` reconciliation strategy.
   *
   * Implementations MUST dispose the agent before resolving — this method
   * is for "is the agent still live" probes only. Do NOT use it to keep
   * an agent reference alive for `send`; that flow belongs to `send` itself.
   */
  resume(sdkAgentId: string): Promise<void>;

  /**
   * Resume the SDK agent and immediately call `agent.send(text)`, returning
   * a `RunHandle` that owns the resulting Run's stream / cancel / dispose
   * lifecycle. Each call is an independent SDK conversation — the adapter
   * does NOT pool agents (decision N: SDK pattern is "resume → send →
   * settled → dispose", concurrent sessions per agent live in §3.2 future
   * work, not Phase B).
   *
   * MUST throw if the SDK rejects the resume / send. Caller (SessionManager)
   * translates that into a `runtime.session_failed` event.
   */
  send(spec: AgentSendSpec, sdkAgentId: string): Promise<RunHandle>;
}

// ───────────────────────────────────────────────────────────────────────────
// Cursor SDK-backed implementation
// ───────────────────────────────────────────────────────────────────────────

/** Construction options for `CursorSdkAdapter`. */
export interface CursorSdkAdapterOptions {
  /**
   * `CURSOR_API_KEY` to forward to every SDK call. Falls back to
   * `process.env.CURSOR_API_KEY` at call time if omitted.
   */
  apiKey?: string;
  /**
   * Default cwd for local-runtime agents. Tests override this; production
   * uses the runtime's working directory.
   */
  defaultCwd?: string;
  /**
   * `runtime` filter passed to `Agent.list()`. Defaults to `local` to
   * scope reconciliation to the current machine. Set to `undefined` for
   * a cross-runtime listing (rarely useful; only the runtime owner knows
   * which scope is correct).
   */
  listScope?: "local" | "cloud" | undefined;
}

/**
 * Real `@cursor/sdk` adapter. Thin wrapper — no caching, no retries.
 * The registry layer owns retry / failure semantics so they're observable
 * in the same place.
 */
export class CursorSdkAdapter implements AgentSdkAdapter {
  private readonly _opts: CursorSdkAdapterOptions;

  constructor(opts: CursorSdkAdapterOptions = {}) {
    this._opts = opts;
  }

  async create(spec: AgentCreateSpec): Promise<{ sdk_agent_id: string }> {
    const apiKey = this._resolveApiKey();

    let agent;
    try {
      agent = await Agent.create({
        apiKey,
        name: `CodeFlow ${spec.agentId}`,
        ...(spec.modelId ? { model: { id: spec.modelId } } : {}),
        local: { cwd: spec.workspace ?? this._opts.defaultCwd ?? process.cwd() },
      });
    } catch (err) {
      if (err instanceof CursorAgentError) {
        throw new Error(
          `Agent.create failed for agent_id="${spec.agentId}": ${err.message} ` +
            `(code=${err.code}, isRetryable=${err.isRetryable})`,
        );
      }
      throw err;
    }

    const sdkAgentId = agent.agentId;
    await agent[Symbol.asyncDispose]();
    return { sdk_agent_id: sdkAgentId };
  }

  async list(): Promise<string[]> {
    const apiKey = this._resolveApiKey();
    const listOptions = this._buildListOptions(apiKey);

    let result;
    try {
      result = await Agent.list(listOptions);
    } catch (err) {
      if (err instanceof CursorAgentError) {
        throw new Error(
          `Agent.list failed: ${err.message} (code=${err.code}, isRetryable=${err.isRetryable})`,
        );
      }
      throw err;
    }
    return result.items.map((item) => item.agentId);
  }

  async resume(sdkAgentId: string): Promise<void> {
    const apiKey = this._resolveApiKey();
    let agent;
    try {
      agent = await Agent.resume(sdkAgentId, {
        apiKey,
        local: { cwd: this._opts.defaultCwd ?? process.cwd() },
      });
    } catch (err) {
      if (err instanceof CursorAgentError) {
        throw new Error(
          `Agent.resume failed for sdk_agent_id="${sdkAgentId}": ${err.message} ` +
            `(code=${err.code}, isRetryable=${err.isRetryable})`,
        );
      }
      throw err;
    }
    await agent[Symbol.asyncDispose]();
  }

  async send(spec: AgentSendSpec, sdkAgentId: string): Promise<RunHandle> {
    const apiKey = this._resolveApiKey();

    let agent;
    try {
      agent = await Agent.resume(sdkAgentId, {
        apiKey,
        ...(spec.modelId ? { model: { id: spec.modelId } } : {}),
        local: { cwd: this._opts.defaultCwd ?? process.cwd() },
      });
    } catch (err) {
      if (err instanceof CursorAgentError) {
        throw new Error(
          `Agent.resume failed for sdk_agent_id="${sdkAgentId}" (during send): ` +
            `${err.message} (code=${err.code}, isRetryable=${err.isRetryable})`,
        );
      }
      throw err;
    }

    let run;
    try {
      run = await agent.send(spec.text);
    } catch (err) {
      // Dispose the resumed agent if send failed — we never got to a usable
      // state. Best-effort: a failing dispose adds noise but doesn't change
      // the failure semantics for the caller.
      try {
        await agent[Symbol.asyncDispose]();
      } catch {
        // best-effort
      }
      if (err instanceof CursorAgentError) {
        throw new Error(
          `agent.send failed for sdk_agent_id="${sdkAgentId}": ${err.message} ` +
            `(code=${err.code}, isRetryable=${err.isRetryable})`,
        );
      }
      throw err;
    }

    // SdkRunHandle owns dispose from here; see SdkRunHandle._driveStream.
    return new SdkRunHandle({
      agent,
      run: run as unknown as SdkRunLike,
      sessionId: spec.sessionId,
      agentId: spec.agentId,
    });
  }

  private _resolveApiKey(): string {
    const apiKey = this._opts.apiKey ?? process.env["CURSOR_API_KEY"];
    if (!apiKey) {
      throw new Error(
        "CursorSdkAdapter: missing CURSOR_API_KEY (set process.env.CURSOR_API_KEY or pass apiKey in constructor)",
      );
    }
    return apiKey;
  }

  private _buildListOptions(apiKey: string): ListAgentsOptions {
    if (this._opts.listScope === "cloud") {
      return { runtime: "cloud", apiKey };
    }
    if (this._opts.listScope === "local") {
      return {
        runtime: "local",
        cwd: this._opts.defaultCwd ?? process.cwd(),
      };
    }
    return {};
  }
}

// ───────────────────────────────────────────────────────────────────────────
// In-memory test double
// ───────────────────────────────────────────────────────────────────────────

/**
 * Thrown by `InMemorySdkAdapter` when a planted error fires during
 * `create` / `resume` / `list` / `send`. Tests use this class identity
 * to assert that the SDK call was the one that threw (vs. a registry- or
 * session-layer validation).
 */
export class InMemorySdkPlantedError extends Error {
  override readonly name = "InMemorySdkPlantedError";
}

/**
 * In-memory `RunHandle` for tests. Default behavior:
 *
 *   - All planted events fire synchronously via `microtask` scheduling
 *     once a listener subscribes (so `attach + emit + assert` works
 *     without timer trickery).
 *   - `whenSettled()` resolves with `status: "finished"` after one
 *     microtask, unless `settleStatus` / `settleError` are planted.
 *   - `cancel()` is idempotent and flips the eventual `whenSettled`
 *     status to `"cancelled"` if called before the natural settle.
 *
 * Tests that need fine-grained control over event timing can use
 * `emit(...)` and `settle(...)` directly.
 */
export interface InMemoryRunHandleOptions {
  sessionId: string;
  agentId: string;
  runId?: string;
  /** Auto-emit these events to subscribers in order, then auto-settle. */
  emitEvents?: import("../types/state.ts").RuntimeEvent[];
  /** Default `"finished"`. */
  settleStatus?: import("@codeflow/protocol").SessionRun["status"];
  /** When set, `whenSettled` rejects with this error instead of resolving. */
  settleError?: Error;
  /** Disable the auto-settle behavior; tests drive `settle()` manually. */
  manualSettle?: boolean;
}

let _inMemoryRunSeq = 0;

export class InMemoryRunHandle implements RunHandle {
  readonly run_id: string;
  readonly session_id: string;
  readonly agent_id: string;

  private readonly _listeners = new Set<
    (event: import("../types/state.ts").RuntimeEvent) => void
  >();
  private readonly _eventBuffer: import("../types/state.ts").RuntimeEvent[] = [];
  private readonly _settlePromise: Promise<
    import("@codeflow/protocol").SessionRun
  >;
  private _resolveSettle!: (
    run: import("@codeflow/protocol").SessionRun,
  ) => void;
  private _rejectSettle!: (err: Error) => void;
  private _settled = false;
  private _cancelled = false;
  private readonly _opts: InMemoryRunHandleOptions;
  private readonly _startedAt: string;

  constructor(opts: InMemoryRunHandleOptions) {
    this._opts = opts;
    this.run_id = opts.runId ?? `run-mem-${(++_inMemoryRunSeq).toString(36)}`;
    this.session_id = opts.sessionId;
    this.agent_id = opts.agentId;
    this._startedAt = new Date().toISOString();
    this._settlePromise = new Promise((resolve, reject) => {
      this._resolveSettle = resolve;
      this._rejectSettle = reject;
    });

    if (!opts.manualSettle) {
      // Schedule auto-settle on the macrotask queue (`setImmediate`), NOT
      // the microtask queue. `SessionManager.startSession` does several
      // `await` hops between `_sdk.send()` returning a handle and the
      // caller's `onEvent` listener being wired up; microtasks run inside
      // those `await` hops, so a microtask-scheduled emit would land
      // BEFORE the listener attaches. `setImmediate` defers to after the
      // surrounding async operation fully unwinds.
      //
      // Race-defense complement: `emit()` buffers events when no
      // listeners are present yet, so even if a setImmediate winner
      // races a not-yet-completed `await`-hop, no events are lost.
      setImmediate(() => this._autoDrive());
    }
  }

  isActive(): boolean {
    return !this._settled;
  }

  async cancel(reason: string): Promise<void> {
    void reason;
    this._cancelled = true;
    if (!this._settled && !this._opts.manualSettle) {
      // Force-settle as cancelled.
      this.settle({ status: "cancelled" });
    }
  }

  whenSettled(): Promise<import("@codeflow/protocol").SessionRun> {
    return this._settlePromise;
  }

  onEvent(
    listener: (event: import("../types/state.ts").RuntimeEvent) => void,
  ): import("../types/state.ts").Unsubscribe {
    const wasEmpty = this._listeners.size === 0;
    this._listeners.add(listener);
    // If this is the first listener, replay any buffered events.
    if (wasEmpty && this._eventBuffer.length > 0) {
      const buffered = this._eventBuffer.splice(0);
      for (const event of buffered) {
        this._deliverToListeners(event);
      }
    }
    return () => {
      this._listeners.delete(listener);
    };
  }

  /**
   * Manually emit an event to all subscribers. If no subscribers are
   * present yet, the event is buffered and replayed when the first one
   * subscribes (`onEvent`).
   *
   * Buffering is the correct mock semantics for "plant events should be
   * received" — the alternative (drop events emitted before `onEvent`)
   * would race with `SessionManager.startSession`, which has fs-IO
   * macrotasks (`SessionStore.save`) between `_sdk.send()` returning a
   * handle and the caller's `onEvent` being wired. SDK's real `Run.stream()`
   * has equivalent behavior — events are buffered until consumed.
   */
  emit(event: import("../types/state.ts").RuntimeEvent): void {
    if (this._listeners.size === 0) {
      this._eventBuffer.push(event);
      return;
    }
    this._deliverToListeners(event);
  }

  private _deliverToListeners(
    event: import("../types/state.ts").RuntimeEvent,
  ): void {
    for (const listener of [...this._listeners]) {
      try {
        listener(event);
      } catch (err) {
        this._listeners.delete(listener);
        // eslint-disable-next-line no-console -- mirrors SdkRunHandle contract
        console.error(
          `[InMemoryRunHandle] listener threw on run_id="${this.run_id}"; unsubscribed: ${
            err instanceof Error ? err.message : String(err)
          }`,
        );
      }
    }
  }

  /** Manually settle with explicit terminal status. */
  settle(opts: {
    status?: import("@codeflow/protocol").SessionRun["status"];
    error?: Error;
  }): void {
    if (this._settled) return;
    this._settled = true;
    if (opts.error) {
      this._rejectSettle(opts.error);
      return;
    }
    const status =
      opts.status ?? (this._cancelled ? "cancelled" : "finished");
    this._resolveSettle({
      run_id: this.run_id,
      started_at: this._startedAt,
      ended_at: new Date().toISOString(),
      status,
      tool_calls_count: 0,
    });
  }

  private _autoDrive(): void {
    for (const event of this._opts.emitEvents ?? []) {
      this.emit(event);
    }
    if (this._opts.settleError) {
      this.settle({ error: this._opts.settleError });
      return;
    }
    this.settle({
      status:
        this._opts.settleStatus ?? (this._cancelled ? "cancelled" : "finished"),
    });
  }
}

/**
 * In-memory `AgentSdkAdapter` for tests. Records every call so `assert.deepEqual`
 * can compare the exact spy trace, and supports planting failures to exercise
 * registry / bootstrap error paths.
 *
 * Usage (test scenario 4 from TASK-009):
 *
 * ```ts
 * const sdk = new InMemorySdkAdapter();
 * sdk.failNextCreateWith("simulated SDK outage");
 * await assert.rejects(() => registry.register(spec));
 * assert.equal(sdk.calls.create.length, 1); // SDK was hit, write was rolled back
 * ```
 */
export class InMemorySdkAdapter implements AgentSdkAdapter {
  /** Set of sdk_agent_ids the SDK currently "knows about". */
  private readonly _known = new Set<string>();
  private _nextCreateId = 1;
  private _failNextCreate: string | null = null;
  private _failNextResume: string | null = null;
  private _failNextList: string | null = null;

  /** Spy trace; tests assert on this. */
  readonly calls: {
    create: AgentCreateSpec[];
    list: number;
    resume: string[];
    send: { spec: AgentSendSpec; sdk_agent_id: string }[];
  } = { create: [], list: 0, resume: [], send: [] };

  /**
   * Optional factory for `send` return values. Tests that need a richer
   * RunHandle (e.g. with planted events) inject a factory here; otherwise
   * `send` returns a default `InMemoryRunHandle` that auto-settles.
   */
  sendHandleFactory?: (
    spec: AgentSendSpec,
    sdkAgentId: string,
  ) => InMemoryRunHandle;

  /** Plant a failure for the very next `send` call. */
  private _failNextSend: string | null = null;

  /** Plant a failure for the very next `create` call. */
  failNextCreateWith(reason: string): void {
    this._failNextCreate = reason;
  }

  /** Plant a failure for the very next `resume` call. */
  failNextResumeWith(reason: string): void {
    this._failNextResume = reason;
  }

  /**
   * Plant a failure for the very next `list` call. Used by Phase B test
   * scenario 12 (TS-2.8 B-path) to verify that `RuntimeBootstrap` translates
   * an uncaught SDK error into a `RuntimeBootstrapError` HARD FAIL.
   */
  failNextListWith(reason: string): void {
    this._failNextList = reason;
  }

  /**
   * Plant a failure for the very next `send` call. Used by Phase B
   * SessionManager tests to verify the `runtime.session_failed` path.
   */
  failNextSendWith(reason: string): void {
    this._failNextSend = reason;
  }

  /** Pre-populate sdk_agent_ids the SDK should claim to know. */
  seedKnown(...ids: string[]): void {
    for (const id of ids) this._known.add(id);
  }

  /** Inspect what the SDK currently believes (read-only). */
  knownIds(): string[] {
    return [...this._known];
  }

  async create(spec: AgentCreateSpec): Promise<{ sdk_agent_id: string }> {
    this.calls.create.push(spec);
    if (this._failNextCreate !== null) {
      const reason = this._failNextCreate;
      this._failNextCreate = null;
      throw new InMemorySdkPlantedError(`create failed: ${reason}`);
    }
    const id = `sdk-fake-${String(this._nextCreateId++).padStart(4, "0")}`;
    this._known.add(id);
    return { sdk_agent_id: id };
  }

  async list(): Promise<string[]> {
    this.calls.list += 1;
    if (this._failNextList !== null) {
      const reason = this._failNextList;
      this._failNextList = null;
      throw new InMemorySdkPlantedError(`list failed: ${reason}`);
    }
    return [...this._known];
  }

  async resume(sdkAgentId: string): Promise<void> {
    this.calls.resume.push(sdkAgentId);
    if (this._failNextResume !== null) {
      const reason = this._failNextResume;
      this._failNextResume = null;
      throw new InMemorySdkPlantedError(`resume failed: ${reason}`);
    }
    if (!this._known.has(sdkAgentId)) {
      throw new InMemorySdkPlantedError(
        `resume failed: sdk_agent_id="${sdkAgentId}" is not in the SDK's known set`,
      );
    }
  }

  async send(spec: AgentSendSpec, sdkAgentId: string): Promise<RunHandle> {
    this.calls.send.push({ spec, sdk_agent_id: sdkAgentId });
    if (this._failNextSend !== null) {
      const reason = this._failNextSend;
      this._failNextSend = null;
      throw new InMemorySdkPlantedError(`send failed: ${reason}`);
    }
    if (!this._known.has(sdkAgentId)) {
      throw new InMemorySdkPlantedError(
        `send failed: sdk_agent_id="${sdkAgentId}" is not in the SDK's known set`,
      );
    }
    if (this.sendHandleFactory) {
      return this.sendHandleFactory(spec, sdkAgentId);
    }
    return new InMemoryRunHandle({
      sessionId: spec.sessionId,
      agentId: spec.agentId,
    });
  }
}
