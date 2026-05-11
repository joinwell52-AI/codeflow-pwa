/**
 * TaskParser — read + parse a `TASK-*.md` file into front-matter + body.
 *
 * Scope (TASK-20260509-018 §主交付 2):
 *
 * - Front-matter delimiter is `^---\r?\n` matched at the very start of the
 *   file (line 1) and on a line of its own thereafter.
 * - YAML parsing uses the `yaml` npm package (not a hand-rolled parser).
 * - Files WITHOUT front-matter return `{ frontmatter: {}, body: <whole file> }`
 *   — they are NOT errors. This is the only reasonable behavior for files
 *   the watcher might briefly see during a `git checkout` or partial write.
 * - YAML PARSE failures (i.e. front-matter exists but is malformed) DO throw
 *   `TaskParseError`. Callers (TaskDispatcher) catch and log a state_history
 *   `to: parse_failed` entry.
 * - Convenience field accessors (`task_id / sender / recipient / priority /
 *   thread_key / layer`) are typed-coerced if the front-matter has them in
 *   the right shape; otherwise they're `undefined` while the raw value is
 *   preserved in `frontmatter` (lenient mode — TASK-018 §主交付 2 line 113).
 *
 * # Day 2 (TASK-20260511-009) — fcop bridge path
 *
 * The static `TaskParser.parse(filepath)` API is kept exactly as it was —
 * back-compat for 4 existing tests + the `CODEFLOW_SKIP_FCOP_PROBE=1`
 * escape hatch (codeflow-shell starts without fcop, dispatcher should
 * still run on yaml-only fallback).
 *
 * NEW: an instance API. `new TaskParser({ fcopClient })` and
 * `instance.parse(filepath)` delegate to `fcopClient.readTask(filename)`
 * and **synthesize a `ParsedTask`** from the resulting `FcopTask`. This is
 * what `Runtime.create` wires up when a `fcopClient` is provided in opts.
 *
 * Path A from PM TASK-009 §3.1 — TaskDispatcher remains untouched; only
 * the parse step changes implementation.
 */

import { promises as fs } from "node:fs";
import { basename } from "node:path";
import { parse as parseYaml } from "yaml";

import type { FcopProjectClient, FcopTask } from "../_external/fcop-client.ts";
import { FcopClientError } from "../_external/fcop-client.ts";
import { TaskParseError } from "../registry/errors.ts";

/** Recognized priority values per FCoP / TASK schema. */
const PRIORITY_VALUES = ["P0", "P1", "P2", "P3"] as const;
type Priority = (typeof PRIORITY_VALUES)[number];

/** Recognized layer values per design doc §3.2 / Agent schema. */
const LAYER_VALUES = ["worker", "governance", "admin"] as const;
type Layer = (typeof LAYER_VALUES)[number];

export interface ParsedTask {
  /** Absolute path the parser was called with. */
  filepath: string;
  /** Just the basename of `filepath`. */
  filename: string;
  /** Raw YAML object after parse — may be `{}` if no front-matter. */
  frontmatter: Record<string, unknown>;
  /** Markdown body AFTER the closing `---`. May be empty string. */
  body: string;

  // Convenience accessors — type-coerced from `frontmatter` when shape matches.
  task_id?: string;
  sender?: string;
  recipient?: string;
  priority?: Priority;
  thread_key?: string;
  layer?: Layer;
}

/** Front-matter delimiter regex — start of file, line of `---`. */
const FRONTMATTER_OPEN = /^---\r?\n/;

/**
 * Find the closing `---` line by scanning manually after the opening
 * delimiter. We can't use a single regex because YAML bodies can contain
 * `---` inside multi-line strings; we want only `---\n` on a line of its
 * own, *after* the opening.
 */
function findClosingDelimiter(
  source: string,
  startIndex: number,
): { yamlBody: string; bodyStart: number } | null {
  // Walk line by line.
  let i = startIndex;
  let lineStart = startIndex;
  while (i < source.length) {
    const nl = source.indexOf("\n", i);
    const lineEnd = nl === -1 ? source.length : nl;
    const line = source.slice(lineStart, lineEnd).replace(/\r$/, "");
    if (line === "---") {
      return {
        yamlBody: source.slice(startIndex, lineStart),
        bodyStart: nl === -1 ? source.length : nl + 1,
      };
    }
    if (nl === -1) break;
    i = nl + 1;
    lineStart = i;
  }
  return null;
}

function pickStringField(
  fm: Record<string, unknown>,
  key: string,
): string | undefined {
  const v = fm[key];
  return typeof v === "string" ? v : undefined;
}

function pickPriority(fm: Record<string, unknown>): Priority | undefined {
  const v = fm["priority"];
  if (typeof v !== "string") return undefined;
  return (PRIORITY_VALUES as readonly string[]).includes(v)
    ? (v as Priority)
    : undefined;
}

function pickLayer(fm: Record<string, unknown>): Layer | undefined {
  const v = fm["layer"];
  if (typeof v !== "string") return undefined;
  return (LAYER_VALUES as readonly string[]).includes(v)
    ? (v as Layer)
    : undefined;
}

/** Constructor options for the instance API. */
export interface TaskParserOptions {
  /**
   * When provided, `instance.parse(filepath)` delegates to
   * `fcopClient.readTask(filename)` instead of doing in-process YAML
   * parsing. Day 2 P4 sprint addition.
   *
   * When omitted, the instance falls back to the same static yaml-based
   * implementation `TaskParser.parse` always used — useful for
   * `CODEFLOW_SKIP_FCOP_PROBE=1` paths and unit tests that don't want
   * to spin up the python bridge.
   */
  fcopClient?: FcopProjectClient;
}

export class TaskParser {
  private readonly _fcopClient: FcopProjectClient | null;

  constructor(opts: TaskParserOptions = {}) {
    this._fcopClient = opts.fcopClient ?? null;
  }

  /**
   * Read + parse the file at `filepath`. Static API kept identical to the
   * Phase C contract — uses in-process YAML parsing. **Does NOT touch
   * fcop**; use the instance API when fcop should be in the loop.
   *
   * Continues to back this name to keep the 4 existing
   * `TaskParser.test.ts` cases green AND to keep the
   * `CODEFLOW_SKIP_FCOP_PROBE=1` happy path working (skip mode = dispatcher
   * still expects to parse tasks; yaml fallback is exactly the right
   * thing).
   *
   * @throws `TaskParseError` if the file exists but its front-matter YAML
   *   is malformed. Read errors (ENOENT, EACCES) propagate as-is — the
   *   caller is expected to handle missing-file races itself (via
   *   `TaskFileNotFoundError` in StateHistoryWriter, etc.).
   */
  static async parse(filepath: string): Promise<ParsedTask> {
    return parseYamlOnDisk(filepath);
  }

  /**
   * Instance API: parse `filepath`, optionally via fcop bridge.
   *
   * - If a `fcopClient` was supplied to the constructor, delegate to
   *   `fcopClient.readTask(basename(filepath))` and shape the result into
   *   the same `ParsedTask` interface callers (TaskDispatcher) already
   *   consume. The CodeFlow-specific `layer` field is pulled from
   *   `frontmatter.extra.layer` (where fcop stores anything outside its
   *   own schema).
   *
   * - If fcop call fails (the file doesn't conform to fcop's TaskFrontmatter
   *   schema, the `--- block can't be parsed, etc.), fall back to the
   *   in-process yaml parser and continue. This way fcop-incompatible
   *   files (legacy demos, partial writes, etc.) still flow through
   *   TaskDispatcher with a clean `parse_failed` state_history entry
   *   rather than blowing up the dispatcher loop.
   *
   * - If no `fcopClient` was provided, this is identical to the static
   *   API (`parseYamlOnDisk`).
   */
  async parse(filepath: string): Promise<ParsedTask> {
    if (this._fcopClient === null) {
      return parseYamlOnDisk(filepath);
    }
    const filename = basename(filepath);
    let fcopTask: FcopTask;
    try {
      fcopTask = await this._fcopClient.readTask(filename);
    } catch (err) {
      // fcop refused the file. Fall back to the yaml parser so the
      // dispatcher can still surface a `parse_failed` state_history entry
      // for malformed files (rather than the entire bridge looking
      // broken). The original FcopClientError is preserved on the
      // TaskParseError `cause` chain if yaml ALSO fails.
      if (err instanceof FcopClientError) {
        try {
          return await parseYamlOnDisk(filepath);
        } catch (yamlErr) {
          throw new TaskParseError(
            filepath,
            `fcop refused the file AND yaml parse failed: ${err.message}`,
            { cause: yamlErr },
          );
        }
      }
      throw err;
    }
    return fcopTaskToParsedTask(filepath, fcopTask);
  }
}

/**
 * The pre-Day-2 implementation — read + yaml-parse the file at `filepath`.
 * Exposed as a module-private helper so both the static API and the
 * instance fallback path can share the same code.
 */
async function parseYamlOnDisk(filepath: string): Promise<ParsedTask> {
  const filename = basename(filepath);
  const source = await fs.readFile(filepath, "utf-8");

  // Tolerance #1: no front-matter at all → return whole file as body.
  if (!FRONTMATTER_OPEN.test(source)) {
    return {
      filepath,
      filename,
      frontmatter: {},
      body: source,
    };
  }

  // Find the start of the YAML payload (after the opening `---\n`).
  const openMatch = source.match(FRONTMATTER_OPEN)!;
  const yamlStart = openMatch[0].length;

  const closing = findClosingDelimiter(source, yamlStart);
  if (!closing) {
    // Tolerance #2: opening `---` but no closing one → treat as no
    // front-matter. The watcher might have caught a partial write.
    return {
      filepath,
      filename,
      frontmatter: {},
      body: source,
    };
  }

  let frontmatter: Record<string, unknown>;
  try {
    const parsed = parseYaml(closing.yamlBody);
    frontmatter =
      parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
  } catch (err) {
    throw new TaskParseError(
      filepath,
      `YAML front-matter parse failed: ${
        err instanceof Error ? err.message : String(err)
      }`,
      { cause: err },
    );
  }

  const body = source.slice(closing.bodyStart);

  return {
    filepath,
    filename,
    frontmatter,
    body,
    task_id: pickStringField(frontmatter, "task_id"),
    sender: pickStringField(frontmatter, "sender"),
    recipient: pickStringField(frontmatter, "recipient"),
    priority: pickPriority(frontmatter),
    thread_key: pickStringField(frontmatter, "thread_key"),
    layer: pickLayer(frontmatter),
  };
}

/**
 * Shape an `FcopTask` into the `ParsedTask` interface TaskDispatcher already
 * consumes. We reuse the existing field semantics so dispatcher / state
 * history / session manager paths don't need to change:
 *
 *   - `frontmatter` is a flat `Record<string, unknown>` (dispatcher passes
 *     it on to SessionManager as session context). We flatten fcop's
 *     nested `TaskFrontmatter` here so dispatcher's existing access
 *     pattern (`payload.context.frontmatter.sender`) still works.
 *   - `layer` continues to come from `frontmatter.extra.layer` (CodeFlow-
 *     specific key fcop preserves in `extra`).
 *   - `priority` is round-tripped through `pickPriority` for the same
 *     P0-P3 narrowing the static parser does (preserves the existing
 *     "unknown priority → undefined" contract).
 */
function fcopTaskToParsedTask(filepath: string, t: FcopTask): ParsedTask {
  // Flatten fcop's nested frontmatter into the same shape callers used
  // to receive from the in-process yaml parser. The `extra` keys are
  // spread at the top so layer / status / etc. live where dispatcher
  // already looks for them.
  const flatFrontmatter: Record<string, unknown> = {
    protocol: t.frontmatter.protocol,
    version: t.frontmatter.version,
    task_id: t.task_id,
    sender: t.frontmatter.sender,
    recipient: t.frontmatter.recipient,
    priority: t.frontmatter.priority,
    thread_key: t.frontmatter.thread_key,
    subject: t.frontmatter.subject,
    references: t.frontmatter.references,
    risk_level: t.frontmatter.risk_level,
    ...t.frontmatter.extra,
  };

  return {
    filepath,
    filename: t.filename,
    frontmatter: flatFrontmatter,
    body: t.body,
    task_id: t.task_id,
    sender: t.frontmatter.sender,
    recipient: t.frontmatter.recipient,
    priority: pickPriority(flatFrontmatter),
    ...(t.frontmatter.thread_key !== null
      ? { thread_key: t.frontmatter.thread_key }
      : {}),
    ...(pickLayer(flatFrontmatter) !== undefined
      ? { layer: pickLayer(flatFrontmatter)! }
      : {}),
  };
}
