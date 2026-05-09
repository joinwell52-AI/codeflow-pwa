/**
 * SessionManager — the runtime's process-scheduler analogue at the
 * session layer. Owns the question "which agent is running which task
 * via which run, and how do we drive / cancel / observe it".
 *
 * Sprint S2 shipped only the surface (every method threw
 * `[S2 skeleton]`). Sprint S3 Phase B (TASK-20260509-013 §主交付 1)
 * ships the full implementation. This file replaces the S2 throws but
 * keeps the surface contract — JSDoc invariants are unchanged.
 *
 * Reference:
 * - design doc `docs/design/codeflow-v2-on-fcop-sdk.md` §2.1 subsystem 1,
 *   §3.5 Session Schema, §0.9.5 Mobile Emergency Stop
 * - TASK-20260509-013 §主交付 1 (six method specs)
 * - crash-recovery.md decision 4 (transcript split)
 */

import type { Session, SessionRun } from "@codeflow/protocol";

import type { AgentRegistry } from "../registry/AgentRegistry.ts";
import type { AgentSdkAdapter } from "../registry/AgentSdkAdapter.ts";
import {
  AgentNotFoundError,
  InvalidAgentStatusError,
  SessionNotFoundError,
} from "../registry/errors.ts";
import type {
  RunHandle,
  RuntimeEvent,
  SessionRecord,
  Unsubscribe,
} from "../types/state.ts";
import type { SessionStore } from "./SessionStore.ts";
import type { TranscriptWriter } from "./TranscriptWriter.ts";

/**
 * Payload passed into `Agent.send()` for a freshly started session.
 *
 * S2 leaves this loosely typed — concrete payload schema is part of S3
 * Task Scheduler design (the bridge from `Task.md` front-matter to the
 * SDK send call). For Phase B we just need a name to thread through.
 */
export interface SessionStartPayload {
  /** Plain text body sent to the SDK (Task.md body, typically). */
  text: string;
  /**
   * Optional structured context (schema decided in Phase C). MUST NOT
   * carry any FCoP protocol field as a top-level key; protocol fields
   * live in `Task` proper, which is referenced via `task_id`, not
   * duplicated here.
   */
  context?: Record<string, unknown>;
}

/** Result of `cancelAllForEmergencyStop()`. */
export interface EmergencyStopResult {
  /** The session_ids that were running and got cancelled. */
  cancelled: string[];
  /**
   * Sessions that failed to cancel cleanly (e.g. SDK call timed out).
   * In v0.1 these are surfaced for the operator to investigate; the
   * runtime does NOT retry automatically (that's S6+ behavior).
   */
  failed_to_cancel: { session_id: string; reason: string }[];
}

/** Constructor options for `SessionManager`. */
export interface SessionManagerOptions {
  /** AgentRegistry — for `get(agentId)` agent lookup. */
  registry: AgentRegistry;
  /** SDK adapter — `send` is the only method SessionManager calls. */
  sdk: AgentSdkAdapter;
  /** Persistence layer for SessionRecord. */
  sessionStore: SessionStore;
  /** Transcript layer (decision 4 right-half). */
  transcriptWriter: TranscriptWriter;
  /**
   * ID minter for new `session_id`s. Default = monotonic `session-mem-N`.
   * Tests inject a deterministic minter to make assertions readable.
   */
  newSessionId?: () => string;
  /** Wall clock; tests inject a controlled clock. */
  now?: () => Date;
}

/**
 * SessionHandle — short-lived handle returned by `startSession`.
 *
 * Encapsulates the active RunHandle for callers that want to cancel /
 * await without going through the SessionManager again. The persisted
 * form remains `SessionRecord`.
 */
export interface SessionHandle {
  readonly session_id: string;
  readonly agent_id: string;
  readonly task_id: string;
  /** The currently in-flight run, if any. */
  readonly activeRun: RunHandle | null;
  /** Convenience: latest snapshot of the persisted record. */
  snapshot(): Promise<SessionRecord>;
}

let _sessionSeq = 0;
function defaultMintSessionId(): string {
  // Pattern `^session-[a-z0-9-]+$` (per Session.session_id schema regex).
  return `session-${(++_sessionSeq).toString(36)}-${Date.now().toString(36)}`;
}

const ALLOWED_START_STATUSES: readonly Session["status"][] = [
  // §3.5 SessionStatus = running | completed | failed | cancelled
  // — we do NOT treat any of those as legal "start" states. The check
  // operates on Agent.status (idle | running | error) per §3.2.
];

const ALLOWED_AGENT_START_STATUSES: readonly string[] = ["idle", "error"];

/**
 * SessionManager — central coordinator for agent×task×run sessions.
 *
 * Lifecycle (Phase B impl):
 *
 * 1. `startSession(agentId, taskId, payload)` → resolve agent record →
 *    `_sdk.send(sdk_agent_id, payload)` → wrap in `SessionHandle` +
 *    persist `SessionRecord` + attach `TranscriptWriter`.
 * 2. `getSession(sessionId)` / `listActive()` → store-backed query.
 * 3. `cancelSession(sessionId, reason)` → SDK `run.cancel()` first,
 *    then update SessionRecord + transcript line + emit
 *    `runtime.session_cancelled`.
 * 4. `cancelAllForEmergencyStop()` → §0.9.5 red button: cancel everything
 *    via `Promise.allSettled` (one failing cancel does NOT block peers).
 * 5. `onEvent(handler)` → subscribe to all 12 RuntimeEventType (see
 *    decision M for the spike-aligned 8 sdk.* + 4 runtime.* set).
 *
 * Invariants enforced at this layer (TASK-013 §"关键不变量"):
 *
 * - `startSession` validates agent record + agent status BEFORE calling
 *   the SDK (so a rejected attempt costs no SDK quota).
 * - `cancelSession` calls SDK `run.cancel()` BEFORE updating the store
 *   ("取消生效" 先于 "持久化记录").
 * - `cancelAllForEmergencyStop` continues even when individual cancels
 *   fail — `Promise.allSettled` semantics.
 * - All transcript writes go through `TranscriptWriter`; SessionManager
 *   never writes a transcript file directly.
 * - Errors are named classes (Phase A `errors.ts` + Phase B additions).
 */
export class SessionManager {
  private readonly _opts: SessionManagerOptions;
  private readonly _registry: AgentRegistry;
  private readonly _sdk: AgentSdkAdapter;
  private readonly _sessionStore: SessionStore;
  private readonly _transcriptWriter: TranscriptWriter;
  private readonly _now: () => Date;
  private readonly _newSessionId: () => string;
  private readonly _activeRuns = new Map<string, RunHandle>();
  /**
   * Promise per-session for the post-settle "natural settle" pipeline
   * (run.whenSettled → store.save(status=completed/failed) → emit
   * session_ended). Tests `await` this to deterministically observe the
   * end state without having to chain `setImmediate`s.
   *
   * Public via `awaitSettled(sessionId)` — kept private here so the
   * field is the test seam, the method is the explicit API.
   */
  private readonly _settlementChain = new Map<string, Promise<void>>();
  private readonly _eventListeners = new Set<
    (event: RuntimeEvent) => void
  >();

  constructor(opts: SessionManagerOptions) {
    this._opts = opts;
    this._registry = opts.registry;
    this._sdk = opts.sdk;
    this._sessionStore = opts.sessionStore;
    this._transcriptWriter = opts.transcriptWriter;
    this._now = opts.now ?? (() => new Date());
    this._newSessionId = opts.newSessionId ?? defaultMintSessionId;
    void this._opts; // retained for future-deprecation diagnostics
    void ALLOWED_START_STATUSES; // retained as a documentation anchor
  }

  /**
   * Start a new agent×task session. See class doc for full lifecycle.
   *
   * @throws `AgentNotFoundError` if `agentId` is unknown to the registry.
   * @throws `InvalidAgentStatusError` if the agent is not in `{idle, error}`.
   * @throws on SDK `send` failure — bubbled with the SDK adapter's
   *   translation already applied.
   */
  async startSession(
    agentId: string,
    taskId: string,
    payload: SessionStartPayload,
  ): Promise<SessionHandle> {
    // Step (a): resolve agent record.
    const record = await this._registry.get(agentId);
    if (!record) {
      throw new AgentNotFoundError(agentId);
    }

    // Step (b): validate agent status. Phase B = serial sessions per agent.
    const status = record.protocol.status;
    if (!ALLOWED_AGENT_START_STATUSES.includes(status)) {
      throw new InvalidAgentStatusError(
        agentId,
        status,
        ALLOWED_AGENT_START_STATUSES,
      );
    }

    const sdkAgentId = record.protocol.sdk_agent_id;
    if (!sdkAgentId) {
      throw new InvalidAgentStatusError(
        agentId,
        `(no sdk_agent_id; status="${status}")`,
        ALLOWED_AGENT_START_STATUSES,
      );
    }

    // Step (c): mint identifiers + call SDK.send.
    const sessionId = this._newSessionId();
    const startedAt = this._now().toISOString();

    const handle = await this._sdk.send(
      {
        sessionId,
        agentId,
        text: payload.text,
      },
      sdkAgentId,
    );

    this._activeRuns.set(sessionId, handle);

    // Step (d): construct SessionRecord with the in-flight run.
    const sessionProto: Session = {
      session_id: sessionId,
      agent_id: agentId,
      task_id: taskId,
      started_at: startedAt,
      ended_at: null,
      status: "running",
      runs: [
        {
          run_id: handle.run_id,
          started_at: startedAt,
          ended_at: null,
          status: "running",
          tool_calls_count: 0,
        },
      ],
    };
    const sessionRecord: SessionRecord = {
      protocol: sessionProto,
      runtime_last_event_at: startedAt,
      runtime_active_run_id: handle.run_id,
    };

    // Step (e): attach TranscriptWriter + bridge events to onEvent fan-out
    // BEFORE awaiting the persistence write. The SDK Run can start
    // streaming events any time after `send()` returned the handle; if
    // we awaited persistence first, those early events would race into
    // a void on fast SDK paths (the in-memory test mock makes this race
    // observable: a `setImmediate`-scheduled emit would land DURING the
    // fs-IO macrotask of `sessionStore.save` and find zero listeners).
    //
    // If `save` fails, the transcript file is harmless (orphan one-line
    // header), the handle.onEvent listener is harmless (manager's
    // dispatcher fans out to listeners that don't care about the record
    // either), and `_activeRuns` is rolled back. The Phase A
    // `RegistryWriteError` semantics still apply: original on-disk
    // state is untouched on a failed atomic write.
    this._transcriptWriter.attach(handle.run_id, handle);
    handle.onEvent((event) => this._dispatchToListeners(event));

    // Step (f): persist. If this throws, roll back the in-memory state.
    try {
      await this._sessionStore.save(sessionRecord);
    } catch (saveErr) {
      this._activeRuns.delete(sessionId);
      // Best-effort: close transcript so the file ends gracefully.
      await this._transcriptWriter.close(handle.run_id).catch(() => undefined);
      // Best-effort: cancel the SDK run so we don't leak a runaway agent.
      await handle.cancel("startSession persistence failed").catch(() => undefined);
      throw saveErr;
    }

    // Emit runtime.session_started after everything is durable.
    this._emit({
      event_id: `${sessionId}-started`,
      at: startedAt,
      event_type: "runtime.session_started",
      session_id: sessionId,
      run_id: handle.run_id,
      agent_id: agentId,
      payload: { task_id: taskId },
    });

    // Step (g): wire settlement to update record.status when the run ends
    // naturally (success / failure). cancelSession drives the cancelled
    // path explicitly — see invariants. The settlement chain is exposed
    // via `awaitSettled(sessionId)` so callers (and tests) can observe
    // end state without polling.
    const settlementChain = handle
      .whenSettled()
      .then((settledRun) => this._handleNaturalSettle(sessionId, settledRun))
      .catch((err) =>
        this._handleNaturalSettle(
          sessionId,
          {
            run_id: handle.run_id,
            started_at: startedAt,
            ended_at: this._now().toISOString(),
            status: "failed",
            tool_calls_count: 0,
            tokens_used: null,
            transcript_path: null,
          },
          err instanceof Error ? err : new Error(String(err)),
        ),
      )
      .finally(() => {
        this._settlementChain.delete(sessionId);
      });
    this._settlementChain.set(sessionId, settlementChain);

    // Construct the handle returned to the caller. snapshot() always
    // re-loads from the store so the caller sees the latest persisted
    // state (e.g. after a cancel-in-flight).
    const self = this;
    const returned: SessionHandle = {
      session_id: sessionId,
      agent_id: agentId,
      task_id: taskId,
      get activeRun() {
        return self._activeRuns.get(sessionId) ?? null;
      },
      async snapshot() {
        const r = await self._sessionStore.load(sessionId);
        if (!r) {
          throw new SessionNotFoundError(sessionId);
        }
        return r;
      },
    };
    return returned;
  }

  /**
   * Single-record lookup by `session_id`. Returns `null` for absent —
   * does NOT throw (symmetric with `AgentRegistry.get`).
   */
  async getSession(sessionId: string): Promise<SessionRecord | null> {
    return this._sessionStore.load(sessionId);
  }

  /**
   * List sessions whose `protocol.status === "running"`.
   *
   * Backed by `SessionStore.listAll` so we always reflect on-disk truth
   * (no in-memory cache that can drift across SessionManager restarts).
   */
  async listActive(): Promise<SessionRecord[]> {
    const all = await this._sessionStore.listAll();
    return all.filter((r) => r.protocol.status === "running");
  }

  /**
   * Graceful cancellation of a running session.
   *
   * Order is invariant (TASK-013 §"关键不变量"):
   *   1. SDK cancel  ← actually stops the run
   *   2. Append cancel-reason to transcript
   *   3. Update SessionRecord.status = "cancelled" + persist
   *   4. Emit `runtime.session_cancelled`
   *
   * Idempotent — calling twice succeeds; the second call is a no-op
   * + warning-line in the transcript.
   *
   * @throws `SessionNotFoundError` if the session is not in the store.
   */
  async cancelSession(sessionId: string, reason: string): Promise<void> {
    const record = await this._sessionStore.load(sessionId);
    if (!record) {
      throw new SessionNotFoundError(sessionId);
    }

    // Idempotency: already-terminal sessions get a transcript note + return.
    if (record.protocol.status !== "running") {
      const handle = this._activeRuns.get(sessionId);
      if (handle) {
        // best-effort detach; transcript may already be closed
        await this._transcriptWriter
          .append(handle.run_id, "warning", `cancel after ${record.protocol.status}: ${reason}`)
          .catch(() => undefined);
      }
      return;
    }

    const handle = this._activeRuns.get(sessionId);
    const runId =
      handle?.run_id ??
      record.runtime_active_run_id ??
      record.protocol.runs[record.protocol.runs.length - 1]?.run_id;

    // Step 1: SDK cancel (must come BEFORE persistence per invariant).
    if (handle && handle.isActive()) {
      await handle.cancel(reason);
    }

    // Step 2: transcript line.
    if (runId) {
      await this._transcriptWriter
        .append(runId, "session_cancelled", `reason: ${reason}`)
        .catch(() => undefined);
    }

    // Step 3: update + persist record.
    const cancelledAt = this._now().toISOString();
    const updated: SessionRecord = {
      ...record,
      protocol: {
        ...record.protocol,
        status: "cancelled",
        ended_at: cancelledAt,
        runs: record.protocol.runs.map((r, i, arr) =>
          i === arr.length - 1 && r.status === "running"
            ? { ...r, status: "cancelled" as const, ended_at: cancelledAt }
            : r,
        ),
      },
      runtime_last_event_at: cancelledAt,
    };
    await this._sessionStore.save(updated);

    this._activeRuns.delete(sessionId);

    // Step 4: emit runtime.session_cancelled.
    this._emit({
      event_id: `${sessionId}-cancelled`,
      at: cancelledAt,
      event_type: "runtime.session_cancelled",
      session_id: sessionId,
      run_id: runId ?? undefined,
      agent_id: record.protocol.agent_id,
      payload: { reason },
    });
  }

  /**
   * §0.9.5 Mobile Emergency Stop ⛔ — cancel every running session.
   *
   * Uses `Promise.allSettled` so one failing cancel does NOT block the
   * rest (TASK-013 §"关键不变量"). Phase B leaves the EMERGENCY-{ts}.md
   * write hook unimplemented (v0.2 S10 scope) — the JSDoc captures the
   * contract for the future implementer.
   *
   * AUTHORIZATION: this method itself does NOT check for admin layer —
   * the caller (CLI handler, mobile bridge) is responsible. The method
   * name is intentionally explicit as a code-review tripwire.
   */
  async cancelAllForEmergencyStop(): Promise<EmergencyStopResult> {
    const active = await this.listActive();
    const results = await Promise.allSettled(
      active.map((r) =>
        this.cancelSession(r.protocol.session_id, "emergency_stop").then(
          () => ({ session_id: r.protocol.session_id }) as const,
        ),
      ),
    );

    const cancelled: string[] = [];
    const failed_to_cancel: EmergencyStopResult["failed_to_cancel"] = [];
    results.forEach((res, i) => {
      const sessionId = active[i]!.protocol.session_id;
      if (res.status === "fulfilled") {
        cancelled.push(sessionId);
      } else {
        failed_to_cancel.push({
          session_id: sessionId,
          reason:
            res.reason instanceof Error
              ? res.reason.message
              : String(res.reason),
        });
      }
    });

    // Phase B leaves EMERGENCY-{ts}.md write to v0.2 S10 — JSDoc above
    // describes the contract; this is the documented hook point.

    return { cancelled, failed_to_cancel };
  }

  /**
   * Resolve when the session's natural-settle chain has fully landed
   * (status persisted, `runtime.session_ended` emitted, transcript closed).
   *
   * Returns immediately if the session is unknown, already settled, or
   * was cancelled (the cancel path runs synchronously inside
   * `cancelSession`, not through this chain).
   *
   * Primarily a test seam — production code observes settlement via
   * `onEvent("runtime.session_ended")` instead. Kept on the public
   * surface because Phase C's Task Scheduler may want it for "wait for
   * task to finish" semantics.
   */
  async awaitSettled(sessionId: string): Promise<void> {
    const chain = this._settlementChain.get(sessionId);
    if (!chain) return;
    await chain;
  }

  /**
   * Subscribe to runtime events (12 types — see `RuntimeEventType`).
   *
   * Listeners receive events from BOTH the SDK stream (for sessions
   * started via this manager) and the runtime layer (lifecycle).
   * Filtering is the listener's job.
   *
   * Throwing listeners are unsubscribed and the error is logged; the
   * other listeners continue to receive events. Unsubscribe is idempotent.
   */
  onEvent(handler: (event: RuntimeEvent) => void): Unsubscribe {
    this._eventListeners.add(handler);
    return () => {
      this._eventListeners.delete(handler);
    };
  }

  // ── private helpers ──────────────────────────────────────────────

  private _emit(event: RuntimeEvent): void {
    this._dispatchToListeners(event);
  }

  private _dispatchToListeners(event: RuntimeEvent): void {
    for (const listener of [...this._eventListeners]) {
      try {
        listener(event);
      } catch (err) {
        this._eventListeners.delete(listener);
        // eslint-disable-next-line no-console -- contract-mandated visibility
        console.error(
          `[SessionManager] listener threw on event ${event.event_type}; unsubscribed: ${
            err instanceof Error ? err.message : String(err)
          }`,
        );
      }
    }
  }

  private async _handleNaturalSettle(
    sessionId: string,
    settledRun: SessionRun,
    err?: Error,
  ): Promise<void> {
    const record = await this._sessionStore.load(sessionId);
    if (!record) return; // already removed; nothing to do
    if (record.protocol.status !== "running") return; // cancel already won

    const endedAt = this._now().toISOString();
    const updated: SessionRecord = {
      ...record,
      protocol: {
        ...record.protocol,
        status: settledRun.status === "finished" ? "completed" : "failed",
        ended_at: endedAt,
        runs: record.protocol.runs.map((r, i, arr) =>
          i === arr.length - 1 ? settledRun : r,
        ),
      },
      runtime_last_event_at: endedAt,
    };
    try {
      await this._sessionStore.save(updated);
    } catch {
      // Persistence failure here is logged by the store layer; we cannot
      // rollback the SDK side, so the session record on disk remains
      // "running" until a future reconciliation.
    }
    this._activeRuns.delete(sessionId);

    this._emit({
      event_id: `${sessionId}-ended`,
      at: endedAt,
      event_type: "runtime.session_ended",
      session_id: sessionId,
      run_id: settledRun.run_id,
      agent_id: record.protocol.agent_id,
      payload: {
        status: updated.protocol.status,
        error: err?.message,
      },
    });
  }
}
