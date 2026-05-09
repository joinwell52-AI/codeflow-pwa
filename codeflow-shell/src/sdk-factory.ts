/**
 * SDK adapter factory — picks the right `AgentSdkAdapter` for the
 * environment the shell is starting in.
 *
 * v0.2.0-alpha (sprint 0 P1):
 *
 *   - `makeRealCursorSdkAdapter(cfg)` returns a real `CursorSdkAdapter`
 *     IFF `cfg.apiKey` (or `process.env.CURSOR_API_KEY`) is set, else
 *     returns `null` so callers chain `??` to the in-memory fallback.
 *
 *   - `makeFakeCursorSdkAdapter()` returns the in-memory adapter
 *     (`InMemorySdkAdapter`) — settles agents synthetically via
 *     `setImmediate`, without making any real SDK / network call. Used
 *     by automated tests AND by users who haven't configured a Cursor
 *     API key yet (so first launch still smoke-tests cleanly).
 *
 * Reference: TASK-20260510-002-PM-to-DEV §三 P1 §1
 */

import {
  CursorSdkAdapter,
  InMemorySdkAdapter,
  type AgentSdkAdapter,
} from "@codeflow/runtime";

/**
 * Subset of `CodeflowConfig.cursor` consumed by this factory.
 * Decoupled from the full `CodeflowConfig` so unit tests can call the
 * factory with a tiny literal object.
 */
export interface CursorAdapterConfig {
  /**
   * Cursor API key. If absent and `process.env.CURSOR_API_KEY` is also
   * absent, this factory returns `null` and the caller falls back to
   * `makeFakeCursorSdkAdapter()`.
   */
  apiKey?: string;
  /**
   * Per-call default model hint. NOT yet wired to `CursorSdkAdapter`'s
   * 4 methods (the SDK's `Agent.create` / `Agent.resume` accept `model`
   * per-call, not as constructor state). Recorded here for surfacing
   * in the banner; full wiring is a P3+ follow-up — see REPORT-002 §决策.
   */
  defaultModel?: string;
  /**
   * `local` (the v0.1 default — scopes Agent.list to the current cwd) or
   * `cloud` (cross-machine listing). Optional; defaults to `local`.
   */
  listScope?: "local" | "cloud";
}

/**
 * Returns a real `@cursor/sdk`-backed adapter, OR `null` if the SDK
 * isn't reachable (no `apiKey` and no `process.env.CURSOR_API_KEY`).
 *
 * Callers chain `??` to fall back to the in-memory adapter:
 *
 * ```ts
 * const sdk = makeRealCursorSdkAdapter(cfg.cursor) ?? makeFakeCursorSdkAdapter();
 * ```
 */
export function makeRealCursorSdkAdapter(
  cfg: CursorAdapterConfig,
): AgentSdkAdapter | null {
  const apiKey = cfg.apiKey ?? process.env["CURSOR_API_KEY"];
  if (!apiKey) return null;

  // Pass the resolved key explicitly so subsequent `process.env` mutations
  // (e.g., from a long-running process where the env later changes) don't
  // cause a different key to flow into individual SDK calls.
  return new CursorSdkAdapter({
    apiKey,
    listScope: cfg.listScope ?? "local",
    defaultCwd: process.cwd(),
  });
}

/**
 * Returns the in-memory adapter (`InMemorySdkAdapter`) — settles
 * agents synthetically via `setImmediate`, without making any real
 * SDK / network call. Used by:
 *
 *   - Automated tests (94/94 in `@codeflow/runtime`).
 *   - Local smoke tests where no `CURSOR_API_KEY` is present.
 *   - The Hello World demo (so `examples/hello-world/sample-task.md`
 *     drops cleanly even without a Cursor account).
 */
export function makeFakeCursorSdkAdapter(): AgentSdkAdapter {
  return new InMemorySdkAdapter();
}

/**
 * Diagnostic helper for the banner — returns a one-line description
 * of which adapter mode we picked (and why).
 */
export function describeAdapterChoice(
  cfg: CursorAdapterConfig,
  picked: AgentSdkAdapter,
): string {
  const isReal = picked instanceof CursorSdkAdapter;
  if (isReal) {
    const keySource = cfg.apiKey ? "config" : "process.env.CURSOR_API_KEY";
    const modelSuffix = cfg.defaultModel
      ? `, defaultModel="${cfg.defaultModel}"`
      : "";
    return `live (CursorSdkAdapter; apiKey from ${keySource}, listScope="${cfg.listScope ?? "local"}"${modelSuffix})`;
  }
  return "fake (InMemorySdkAdapter; CURSOR_API_KEY not set — set it in ~/.codeflow/v2/.env or config.json to use real SDK)";
}
