/**
 * Public surface of the review subsystem (Sprint S4).
 *
 * Importers MAY pull from `@codeflow/runtime/review` (when path-mapped)
 * or `@codeflow/runtime` (top-level barrel — see `src/index.ts`).
 * Either way, only the symbols re-exported here are part of the package's
 * stable v0.1 contract.
 */

export {
  DefaultReviewPolicy,
  ReviewEngine,
  defaultMakeReviewId,
  parseVerdict,
  type ReviewEngineLogger,
  type ReviewEngineOptions,
  type ReviewPolicy,
  type TaskReference,
} from "./ReviewEngine.ts";

export {
  NeedsHumanGate,
  UnsupportedHumanPushSinkError,
  type HumanApprovedSpec,
  type HumanPushRequest,
  type NeedsHumanGateLogger,
  type NeedsHumanGateOptions,
} from "./NeedsHumanGate.ts";

export {
  ReviewWriter,
  renderReviewMarkdown,
  type HumanApproval,
  type ReviewDecision,
  type ReviewSubjectType,
  type ReviewVerdict,
  type ReviewWriterOptions,
} from "./ReviewWriter.ts";

export {
  ReviewWriteError,
  ReviewerNotFoundError,
  VerdictParseError,
} from "../registry/errors.ts";
