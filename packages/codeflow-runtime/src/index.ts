/**
 * @codeflow/runtime — public API surface (Sprint S5 — Skill Runtime + fcop hard-dep).
 *
 * What's exported:
 *   - AgentRegistry + RuntimeBootstrap + PersistentStore + AgentSdkAdapter
 *     (§2.1 subsystem 3 + 6; Sprint S3 Phase A done — `407cfa5` checkpoint)
 *   - SessionManager + SessionStore + TranscriptWriter + SdkRunHandle
 *     (§2.1 subsystem 1 + decision 4 right-half; Sprint S3 Phase B — `8c49907` checkpoint)
 *   - InboxWatcher + TaskParser + StateHistoryWriter + TaskDispatcher + Runtime
 *     (§2.4 doorbell + §3.3 task lifecycle; Sprint S3 Phase C — `bd7d3d8` checkpoint)
 *   - ReviewEngine + ReviewWriter + NeedsHumanGate + AgentStatusReconciler
 *     (§3.4 review schema + §0.9.4 HITL + REPORT-018 §五决策 B'; Sprint S4 — `1ba2aa6`)
 *   - SkillRegistry + KernelDependencyValidator + MCPInjector
 *     (§0.5 fcop hard-dep + §0.7.5 skill runtime + §3.6 skill schema;
 *      Sprint S5 — this commit)
 *   - State types (runtime-private; layered on @codeflow/protocol)
 *
 * What's NOT here (and why):
 *   - codeflow-shell EXE      → S6 (Node SEA bundle that imports `Runtime`)
 *   - Mobile Console / relay  → v0.2 (separate effort)
 *   - Cloud agent runtime     → v0.x; binding-mode field exists, but
 *                               local-only is the v0.1 reality
 *   - Real MCP spawning       → v0.2 (`MCPInjector` mode="live" is
 *                               eager-throw-stubbed in v0.1)
 *
 * See `README.md` for the full sprint roadmap and `docs/crash-recovery.md`
 * for the 4 persistence/recovery decisions.
 */

export {
  AgentRegistry,
  type AgentRegistryFilter,
  type AgentRegistryOptions,
  type PersistentStore,
  JsonFileStore,
  type JsonFileStoreOptions,
  type AgentSdkAdapter,
  type AgentCreateSpec,
  type AgentSendSpec,
  CursorSdkAdapter,
  type CursorSdkAdapterOptions,
  InMemorySdkAdapter,
  InMemoryRunHandle,
  type InMemoryRunHandleOptions,
  InMemorySdkPlantedError,
  ValidationError,
  LayerViolationError,
  AgentNotFoundError,
  RegistryWriteError,
  RuntimeBootstrapError,
  RuntimeNotReadyError,
  SessionNotFoundError,
  InvalidAgentStatusError,
  RuntimeBootstrap,
  type RuntimeBootstrapOptions,
  AgentStatusReconciler,
  type AgentStatusReconcilerLogger,
  type AgentStatusReconcilerOptions,
  KernelDependencyError,
  MCPInjectorLiveModeNotImplementedError,
  SkillSchemaError,
} from "./registry/index.ts";

export {
  SessionManager,
  type SessionManagerOptions,
  type SessionStartPayload,
  type SessionHandle,
  type EmergencyStopResult,
  SessionStore,
  type SessionStoreOptions,
  TranscriptWriter,
  type TranscriptWriterOptions,
  type TranscriptEntryKind,
  SdkRunHandle,
  type SdkRunHandleOptions,
  type SdkRunLike,
  type RunHandle,
} from "./session/index.ts";

export {
  InboxWatcher,
  type InboxEvent,
  type InboxEventHandler,
  type InboxWatcherOpts,
  TaskParser,
  type ParsedTask,
  StateHistoryWriter,
  type StateHistoryEntry,
  TaskDispatcher,
  type TaskDispatcherLogger,
  type TaskDispatcherOpts,
  TaskParseError,
  TaskFileNotFoundError,
} from "./scheduler/index.ts";

export {
  ReviewEngine,
  DefaultReviewPolicy,
  defaultMakeReviewId,
  parseVerdict,
  type ReviewEngineLogger,
  type ReviewEngineOptions,
  type ReviewPolicy,
  type TaskReference,
  ReviewWriter,
  renderReviewMarkdown,
  type HumanApproval,
  type ReviewDecision,
  type ReviewSubjectType,
  type ReviewVerdict,
  type ReviewWriterOptions,
  NeedsHumanGate,
  UnsupportedHumanPushSinkError,
  type HumanApprovedSpec,
  type HumanPushRequest,
  type NeedsHumanGateLogger,
  type NeedsHumanGateOptions,
  ReviewWriteError,
  ReviewerNotFoundError,
  VerdictParseError,
} from "./review/index.ts";

export {
  SkillRegistry,
  KernelDependencyValidator,
  MCPInjector,
  FCOP_KERNEL_PATTERN,
  type SkillRecord,
  type SkillToolSpec,
  type SkillProvider,
  type SkillRegistryOptions,
  type SkillRegistryLogger,
  type SkillSkippedEntry,
  type KernelDependencyValidatorOptions,
  type KernelDependencyValidatorLogger,
  type ValidationFailure,
  type MCPInjectorOptions,
  type MCPInjectorLogger,
  type MCPMount,
} from "./skill/index.ts";

export {
  Runtime,
  type RuntimeCreateOptions,
  type RuntimeBootstrapResult,
} from "./Runtime.ts";

export type {
  AgentRecord,
  SessionRecord,
  RuntimeBindingMode,
  AgentFailure,
  RuntimeEvent,
  RuntimeEventType,
  Unsubscribe,
  ReconciliationReport,
  ReconciliationSuccessEntry,
  ReconciliationFailedEntry,
  ReconciliationOrphanedEntry,
  ReconciliationForeignEntry,
  ReconciliationDriftEntry,
  KernelValidationFailureEntry,
} from "./types/state.ts";

export { ReconciliationStrategy } from "./types/state.ts";

// ─────────────────────────────────────────────────────────────────────────
// P4 sprint Day 1 (TASK-20260511-007) — fcop@1.1.0 bridge via pythonia.
// `FcopProjectClient` is the new TS façade for fcop's Python API. Calling
// any exported symbol from here boots the pythonia child Python process
// (StdioCom.start runs at `import 'pythonia'` time), so consumers MUST
// also call `disposeFcopBridge()` on graceful shutdown — see fcop-client.ts
// JSDoc.
// ─────────────────────────────────────────────────────────────────────────
export {
  FcopProjectClient,
  FcopClientError,
  assertFcopReady,
  disposeFcopBridge,
  type FcopProjectClientOptions,
  type FcopTask,
  type FcopTaskFrontmatter,
  type FcopReview,
  type FcopHumanApproval,
  type FcopValidationIssue,
  type WriteTaskSpec,
  type ListTasksFilter,
  type WriteReviewSpec,
  type MarkHumanApprovedSpec,
  type Priority as FcopPriority,
  type RiskLevel as FcopRiskLevel,
  type ReviewDecision as FcopReviewDecision,
  type ReviewSubjectType as FcopReviewSubjectType,
  type HumanApprovalDecision,
  type HumanApprovalChannel,
} from "./_external/fcop-client.ts";
