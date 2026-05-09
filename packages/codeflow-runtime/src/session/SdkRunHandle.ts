/**
 * SdkRunHandle — concrete `RunHandle` backed by `@cursor/sdk`.
 *
 * Lifecycle (matches the spike `_ignore/spike_sdk_doorbell/ringer.ts`):
 *
 *   1. `Agent.resume(sdkAgentId)` → agent instance
 *   2. `agent.send(payload.text)` → run object
 *   3. `run.stream()` async iterator → emit per-event
 *   4. `run.wait()` → terminal status
 *   5. `agent[Symbol.asyncDispose]()` → release SDK resources
 *
 * Steps 1+2 happen INSIDE `CursorSdkAdapter.send`. By the time a
 * `SdkRunHandle` is constructed, the agent + run are already in flight.
 * The handle owns steps 3-5: it backgrounds the stream loop, fans out
 * `RuntimeEvent`s to subscribers, and disposes the agent on terminal.
 *
 * Reference:
 *   - design doc §3.5 (Session Schema, SessionRun)
 *   - TASK-20260509-013 §主交付 1 (cancelSession invariant: SDK cancel
 *     before persistence)
 *   - decision M (REPORT-013): SDKMessage.type → RuntimeEventType mapping
 */

import type { Agent, SDKMessage } from "@cursor/sdk";

import type { SessionRun } from "@codeflow/protocol";

import type {
  RunHandle,
  RuntimeEvent,
  RuntimeEventType,
  Unsubscribe,
} from "../types/state.ts";

/**
 * Cursor SDK `Run` surface used by the handle. Defined as a structural
 * type instead of importing `Run` directly so this file does not pin a
 * specific `@cursor/sdk` Run-object shape (the SDK's public types are
 * intentionally narrow; the spike confirmed the runtime shape).
 *
 * Exported so `CursorSdkAdapter.send` can cast its raw SDK `Run` object
 * to this shape without `as any`.
 */
export interface SdkRunLike {
  readonly id: string;
  supports(capability: "stream" | "cancel"): boolean;
  stream(): AsyncIterable<SDKMessage>;
  wait(): Promise<{ status: string; [k: string]: unknown }>;
  cancel?(reason?: string): Promise<unknown> | unknown;
}

/**
 * `id` generator. ULID would be fancier but adds a dependency for one
 * call site; a 12-byte random hex from crypto is sufficient and matches
 * the `^[a-z0-9-]+$` pattern in `SessionRun.run_id`.
 */
function makeRunIdFromSdk(sdkRunId: string): string {
  return `run-${sdkRunId.replace(/[^a-z0-9-]/gi, "").toLowerCase()}`;
}

/**
 * Map a Cursor SDK `SDKMessage.type` to our `RuntimeEventType`. The 8
 * SDK-side names mirror the spike (`ringer.ts` switch). See decision M.
 */
function mapSdkType(t: SDKMessage["type"]): RuntimeEventType {
  switch (t) {
    case "system":
      return "sdk.system";
    case "thinking":
      return "sdk.thinking";
    case "assistant":
      return "sdk.assistant";
    case "tool_call":
      return "sdk.tool_call";
    case "status":
      return "sdk.status";
    case "task":
      return "sdk.task";
    case "request":
      return "sdk.request";
    case "user":
      return "sdk.user";
    default: {
      // Forward-compat: an unknown SDK type falls under sdk.system as a
      // safe default (system is already a heterogeneous bucket per spike).
      // The raw type is preserved in `event.payload.sdk_type` for audit.
      return "sdk.system";
    }
  }
}

/** Construction options for `SdkRunHandle`. */
export interface SdkRunHandleOptions {
  agent: Agent;
  run: SdkRunLike;
  /** Pattern: `^session-[a-z0-9-]+$`. */
  sessionId: string;
  /** Owning agent_id (FCoP role id, e.g. `"DEV-01"`). */
  agentId: string;
  /** Override the auto-derived run_id. Mostly for tests / replays. */
  runIdOverride?: string;
  /** Wall clock for event timestamps. Tests inject a controlled clock. */
  now?: () => Date;
}

export class SdkRunHandle implements RunHandle {
  readonly run_id: string;
  readonly session_id: string;
  readonly agent_id: string;

  private readonly _agent: Agent;
  private readonly _run: SdkRunLike;
  private readonly _now: () => Date;
  private readonly _listeners = new Set<(event: RuntimeEvent) => void>();

  private _eventSeq = 0;
  private _settled = false;
  private _settlementPromise: Promise<SessionRun>;
  private readonly _startedAt: string;

  constructor(opts: SdkRunHandleOptions) {
    this._agent = opts.agent;
    this._run = opts.run;
    this.run_id = opts.runIdOverride ?? makeRunIdFromSdk(opts.run.id);
    this.session_id = opts.sessionId;
    this.agent_id = opts.agentId;
    this._now = opts.now ?? (() => new Date());
    this._startedAt = this._now().toISOString();
    this._settlementPromise = this._driveStream();
  }

  isActive(): boolean {
    return !this._settled;
  }

  async cancel(reason: string): Promise<void> {
    if (this._settled) {
      // Idempotent — see TASK-013 §主交付 1 invariant: cancel(twice) succeeds.
      return;
    }
    if (this._run.supports("cancel") && this._run.cancel) {
      try {
        await this._run.cancel(reason);
      } catch {
        // Cancellation is best-effort — the SDK's own state machine will
        // surface a terminal `error` or `cancelled` status via wait().
        // We swallow here to keep cancel(reason) idempotent.
      }
    }
  }

  whenSettled(): Promise<SessionRun> {
    return this._settlementPromise;
  }

  onEvent(listener: (event: RuntimeEvent) => void): Unsubscribe {
    this._listeners.add(listener);
    return () => {
      this._listeners.delete(listener);
    };
  }

  private async _driveStream(): Promise<SessionRun> {
    let toolCallsCount = 0;
    try {
      if (this._run.supports("stream")) {
        for await (const message of this._run.stream()) {
          this._dispatch(this._toEvent(message));
          if (message.type === "tool_call") {
            toolCallsCount += 1;
          }
        }
      }
      const result = await this._run.wait();
      const endedAt = this._now().toISOString();
      const sessionRun: SessionRun = {
        run_id: this.run_id,
        started_at: this._startedAt,
        ended_at: endedAt,
        status: this._mapWaitStatus(result.status),
        tool_calls_count: toolCallsCount,
      };
      this._settled = true;
      return sessionRun;
    } finally {
      try {
        // Cursor SDK's public Agent type omits the async-dispose symbol from
        // its type surface even though the runtime does implement it (per
        // spike `_ignore/spike_sdk_doorbell/sender.ts` line 114). Cast keeps
        // this site honest about the gap without disabling tsc globally.
        const disposable = this._agent as unknown as {
          [Symbol.asyncDispose]?: () => Promise<void>;
        };
        await disposable[Symbol.asyncDispose]?.();
      } catch {
        // Dispose failure is not actionable from this layer — best-effort.
      }
    }
  }

  private _dispatch(event: RuntimeEvent): void {
    for (const listener of [...this._listeners]) {
      try {
        listener(event);
      } catch (err) {
        // Per RunHandle.onEvent contract: throwing listener gets unsubbed.
        this._listeners.delete(listener);
        // eslint-disable-next-line no-console -- contract-mandated visibility
        console.error(
          `[SdkRunHandle] listener threw on run_id="${this.run_id}"; unsubscribed: ${
            err instanceof Error ? err.message : String(err)
          }`,
        );
      }
    }
  }

  private _toEvent(message: SDKMessage): RuntimeEvent {
    return {
      event_id: `${this.run_id}-${(this._eventSeq++).toString(36)}`,
      at: this._now().toISOString(),
      event_type: mapSdkType(message.type),
      session_id: this.session_id,
      run_id: this.run_id,
      agent_id: this.agent_id,
      payload: { sdk_type: message.type, raw: message },
    };
  }

  private _mapWaitStatus(s: string): SessionRun["status"] {
    // Cursor SDK terminal `wait()` statuses (per spike) are
    // `success | error | cancelled`. We map to our 4-value union
    // `running | finished | failed | cancelled`.
    if (s === "cancelled") return "cancelled";
    if (s === "error") return "failed";
    return "finished";
  }
}
