/**
 * Runtime-private state types for @codeflow/runtime.
 *
 * GOVERNANCE RULES (READ FIRST):
 *
 * 1. **Schema-mirrored fields are NOT redeclared here.**
 *    All Agent / Session / Review / Task / Skill *protocol* fields come from
 *    `@codeflow/protocol`. If you find yourself typing field names from the
 *    JSON schemas (`agent_id`, `layer`, `risk_level`, `decision`, etc.) in
 *    this file — STOP. Import the protocol type instead.
 *
 * 2. **Runtime-private constructs ARE allowed here.**
 *    Pure runtime concepts that have no place in the FCoP protocol — for
 *    example: `RuntimeEvent`, `SessionHandle`, `Unsubscribe` callbacks,
 *    `RuntimeBindingMode`, in-memory caches — live in this file.
 *    These don't go through D:\FCoP because they're not protocol contracts.
 *
 * 3. **Schema gaps go to the report, NOT to this file.**
 *    If runtime needs a field that's missing from `@codeflow/protocol`,
 *    add it to the "schema gaps" list in `REPORT-20260509-002-DEV-to-PM.md`.
 *    Per design doc §8.0 Hard Rule #4 + §3.3.1.b: schema evolution must
 *    originate in `D:\FCoP` (https://github.com/joinwell52-AI/FCoP),
 *    propagate through `packages/codeflow-protocol/`, and only then be
 *    consumed here.
 *
 * Reference: design doc `docs/design/codeflow-v2-on-fcop-sdk.md` §2.1, §3, §8.
 */

import type {
  Agent,
  IsoDateTime,
  Session,
  SessionRun,
} from "@codeflow/protocol";

// ───────────────────────────────────────────────────────────────────────────
// AgentRecord — Agent + runtime bookkeeping
// ───────────────────────────────────────────────────────────────────────────

/**
 * Where the runtime currently holds a binding to the SDK Agent.
 * Pure runtime concept — not in any FCoP schema.
 */
export type RuntimeBindingMode = "local" | "cloud";

/**
 * Why the runtime put an agent into the `failed` state.
 * Pure runtime diagnostic — not in any FCoP schema.
 */
export interface AgentFailure {
  /** ISO-8601 timestamp the failure was recorded. */
  failed_at: string;
  /** Human-readable reason. */
  reason: string;
  /** Optional structured cause (e.g. SDK error code). */
  cause?: unknown;
}

/**
 * AgentRecord = the protocol-level Agent (from @codeflow/protocol)
 *             + runtime-only bookkeeping fields.
 *
 * The runtime persists this in `agents.json` (Agent Registry's PCB).
 * The protocol-level Agent never has the `runtime_*` prefix; everything
 * runtime-private here is namespaced with `runtime_` to make it visually
 * obvious which fields cross the schema boundary.
 */
export interface AgentRecord {
  /** Protocol-level fields — direct passthrough of FCoP Agent schema. */
  protocol: Agent;
  /** Where the runtime currently believes the SDK Agent is bound. */
  runtime_binding_mode: RuntimeBindingMode;
  /** Last time runtime successfully reconciled with SDK. */
  runtime_last_reconciled_at?: string;
  /** Set when status === "error" or runtime marks failed. */
  runtime_failure?: AgentFailure;
}

// ───────────────────────────────────────────────────────────────────────────
// SessionRecord — Session + runtime bookkeeping
// ───────────────────────────────────────────────────────────────────────────

/**
 * SessionRecord = the protocol-level Session (from @codeflow/protocol)
 *               + runtime-only bookkeeping fields.
 *
 * Same `runtime_` prefix discipline as AgentRecord.
 */
export interface SessionRecord {
  /** Protocol-level fields — direct passthrough of FCoP Session schema. */
  protocol: Session;
  /**
   * Last event timestamp (any kind: token, tool_call, status_change).
   * Used for liveness heuristics; not promoted to protocol because
   * SessionRun.ended_at already covers terminal liveness needs.
   */
  runtime_last_event_at?: string;
  /**
   * Active run handle id, if any. Maps 1:1 to SessionRun.run_id but
   * only set while the run is actually in-flight.
   */
  runtime_active_run_id?: string;
}

// ───────────────────────────────────────────────────────────────────────────
// RunHandle — runtime-only abstraction
// ───────────────────────────────────────────────────────────────────────────

/**
 * Lightweight handle to a single in-flight Run. Wraps the SDK Run object.
 *
 * Not in any schema — purely a runtime convenience for cancellation,
 * event subscription, and waiting. The persisted form is `SessionRun`
 * inside `SessionRecord.protocol.runs[]`.
 *
 * Defined as an interface so concrete runtime impls (S3+) can wrap the
 * SDK Run however they like, as long as they expose this shape.
 *
 * Phase B (TASK-013) added `onEvent` so TranscriptWriter can subscribe
 * to the SDK event stream without coupling itself to `@cursor/sdk`.
 * The handle is responsible for translating SDKMessage → RuntimeEvent
 * (decision M / spike-aligned 8 sdk.* types) before emitting.
 */
export interface RunHandle {
  /** Pattern: `^run-[a-z0-9-]+$` (matches SessionRun.run_id). */
  readonly run_id: string;
  /** Owning session_id. */
  readonly session_id: string;
  /** Owning agent_id. */
  readonly agent_id: string;
  /** Whether the underlying SDK run is still streaming. */
  isActive(): boolean;
  /** Request graceful cancellation. Idempotent. */
  cancel(reason: string): Promise<void>;
  /** Resolve when the run reaches a terminal status. */
  whenSettled(): Promise<SessionRun>;
  /**
   * Subscribe to runtime events emitted by this run. Listener fires once
   * per SDKMessage observed in the underlying `run.stream()` (mapped to
   * `sdk.*` `RuntimeEventType`). Returns an `Unsubscribe`.
   *
   * Listeners MUST NOT throw — a throwing listener is unsubscribed and
   * the error is logged via `console.error`. Idempotent: re-subscribing
   * the same function returns a fresh `Unsubscribe`.
   */
  onEvent(listener: (event: RuntimeEvent) => void): Unsubscribe;
}

// ───────────────────────────────────────────────────────────────────────────
// RuntimeEvent — what SessionManager.onEvent streams
// ───────────────────────────────────────────────────────────────────────────

/**
 * The 8 SDK message types observed in the spike (`_ignore/spike_sdk_doorbell/
 * ringer.ts` switch on `event.type`) + 4 runtime-internal lifecycle events.
 *
 * Sprint S3 Phase B alignment (TASK-20260509-013 §主交付 3):
 *
 * - **8 SDK types** mirror the `SDKMessage` discriminator from `@cursor/sdk@1.0.12`
 *   exactly as observed live in the spike on 2026-05-08:
 *   `system | thinking | assistant | tool_call | status | task | request | user`.
 *   We prefix each with `sdk.` to keep dot-namespacing consistent with the
 *   runtime side. **NOTE**: TASK-013 §主交付 3 line 110 lists a different
 *   8-name set (`message_start / message_delta / ...`) — that wording mirrors
 *   the Anthropic Messages SSE schema, NOT the Cursor SDK surface. The
 *   spike is the ground truth and what TranscriptWriter actually subscribes
 *   to; this is captured as decision M in REPORT-20260509-013.
 *
 * - **4 runtime types** match crash-recovery.md decision 1 (`persistence_flushed`)
 *   + decision 4 (`session_started` / `session_ended` / `session_cancelled`).
 *   Mobile emergency-stop fires `session_cancelled` per cancelled session
 *   (no separate `emergency_stop` event), per TASK-013 §主交付 1 cancel-flow.
 *
 * Not in any FCoP schema. Subscribers (TranscriptWriter, Mobile push,
 * audit log) switch on `event_type` to dispatch.
 */
export type RuntimeEventType =
  // SDK-originated events (8) — mirrors SDKMessage discriminator from spike.
  | "sdk.system"
  | "sdk.thinking"
  | "sdk.assistant"
  | "sdk.tool_call"
  | "sdk.status"
  | "sdk.task"
  | "sdk.request"
  | "sdk.user"
  // Runtime-originated events (4) — lifecycle + persistence.
  | "runtime.session_started"
  | "runtime.session_ended"
  | "runtime.session_cancelled"
  | "runtime.persistence_flushed";

export interface RuntimeEvent {
  /** Monotonic-ish event id (e.g. ULID). */
  event_id: string;
  /** ISO-8601. */
  at: string;
  /** Coarse event family. */
  event_type: RuntimeEventType;
  session_id: string;
  /** Set for events tied to a specific run; absent for session-level events. */
  run_id?: string;
  /** Convenience: the agent_id for the session at event time. */
  agent_id: string;
  /** Free-form structured payload — shape varies by event_type. */
  payload?: unknown;
}

/** Returned by `onEvent` so callers can `unsubscribe()`. */
export type Unsubscribe = () => void;

// ───────────────────────────────────────────────────────────────────────────
// Reconciliation — runtime-only types for RuntimeBootstrap (Sprint S3 Phase A)
// ───────────────────────────────────────────────────────────────────────────

/**
 * Strategy applied per-record during startup reconciliation, when
 * `agents.json` and the SDK back end disagree.
 *
 * Pure runtime concept (per `docs/crash-recovery.md` decision 3) — not in
 * any FCoP schema. Each enum value pins a single resolution rule so the
 * `ReconciliationReport` is unambiguous for audit.
 *
 * | Value | Trigger | Behavior |
 * |---|---|---|
 * | `ORPHAN_LOCAL` | local has record, SDK doesn't | mark record `error`, keep PCB for audit |
 * | `IGNORE_FOREIGN` | SDK has agent, local doesn't | warn + record in report, do NOT take over |
 * | `ACCEPT_DRIFT_WITH_AUDIT` | both have it but metadata diverges | overwrite PCB with SDK truth + audit entry (Phase B wires the detection) |
 */
export enum ReconciliationStrategy {
  ORPHAN_LOCAL = "orphan_local",
  IGNORE_FOREIGN = "ignore_foreign",
  ACCEPT_DRIFT_WITH_AUDIT = "accept_drift_with_audit",
}

/**
 * Single audit entry for a record that was successfully resumed against
 * the SDK back end during startup reconciliation.
 */
export interface ReconciliationSuccessEntry {
  agent_id: string;
  sdk_agent_id: string;
}

/**
 * Single audit entry for a record whose `Agent.resume()` call failed.
 * The record is also marked `status: "error"` via `markFailed()` so the
 * persisted state agrees with the report.
 */
export interface ReconciliationFailedEntry {
  agent_id: string;
  sdk_agent_id: string;
  reason: string;
}

/**
 * Single audit entry for the orphan_local scenario (decision 3 case X):
 * `agents.json` references an `sdk_agent_id` the SDK no longer recognizes.
 */
export interface ReconciliationOrphanedEntry {
  agent_id: string;
  sdk_agent_id: string;
  strategy: ReconciliationStrategy.ORPHAN_LOCAL;
}

/**
 * Single audit entry for the ignore_foreign scenario (decision 3 case Y):
 * SDK exposes an `sdk_agent_id` not in `agents.json`. Runtime does NOT
 * adopt it — only records the sighting.
 */
export interface ReconciliationForeignEntry {
  sdk_agent_id: string;
  strategy: ReconciliationStrategy.IGNORE_FOREIGN;
}

/**
 * Single audit entry for the accept_drift_with_audit scenario (case Z).
 * Phase A leaves the detector unimplemented (capability spike pending),
 * so this array is always empty for now; the field exists so consumers
 * (Mobile, audit log) can be built once and not change shape later.
 */
export interface ReconciliationDriftEntry {
  agent_id: string;
  field: string;
  old: string;
  new: string;
}

/**
 * Aggregate result of one `RuntimeBootstrap.run()` invocation.
 *
 * Returned to the caller and ALSO printed to stdout as a one-line
 * summary on startup. Pure runtime type — never persisted via the
 * FCoP protocol; lives in audit logs at v0.5+.
 */
export interface ReconciliationReport {
  /** ISO-8601 — when `RuntimeBootstrap.run()` started. */
  startedAt: IsoDateTime;
  /** ISO-8601 — when `RuntimeBootstrap.run()` returned. */
  finishedAt: IsoDateTime;
  /** Records resumed cleanly. */
  success: ReconciliationSuccessEntry[];
  /** Records found in PCB but `Agent.resume()` failed. Marked `error`. */
  failed: ReconciliationFailedEntry[];
  /** Decision-3 case X (orphan_local). */
  orphaned: ReconciliationOrphanedEntry[];
  /** Decision-3 case Y (ignore_foreign). */
  foreign: ReconciliationForeignEntry[];
  /** Decision-3 case Z (accept_drift_with_audit). Empty until Phase B. */
  drifted: ReconciliationDriftEntry[];
}
