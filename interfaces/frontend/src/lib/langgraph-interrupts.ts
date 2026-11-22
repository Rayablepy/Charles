import type {
  LangGraphCommand,
  LangGraphInterruptState,
} from "@assistant-ui/react-langgraph";

export type DecisionKind = "approve" | "edit" | "reject" | "respond";

export type HitlDecision =
  | { type: "approve" }
  | { type: "reject"; message?: string };

export type DecisionChoice = HitlDecision["type"];

export type PendingAction = {
  key: string;
  name: string;
  args: Record<string, unknown>;
  allowed: DecisionKind[];
};

export type PendingInterrupt = {
  key: string;
  resumable: boolean;
  actions: PendingAction[];
  value: unknown;
};

const DECISION_KINDS: readonly DecisionKind[] = [
  "approve",
  "edit",
  "reject",
  "respond",
];

const DEFAULT_DECISIONS: DecisionKind[] = ["approve", "reject"];

const ACTION_LABELS: Record<string, string> = {
  edit_file: "Edit file",
  glob: "Find files",
  grep: "Search files",
  ls: "List directory",
  read_file: "Read file",
  write_file: "Write file",
};

const PATH_ARGS = new Set(["file_path", "path"]);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const readString = (value: unknown): string | undefined =>
  typeof value === "string" && value !== "" ? value : undefined;

const readDecisions = (value: unknown): DecisionKind[] => {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is DecisionKind =>
    DECISION_KINDS.includes(entry as DecisionKind),
  );
};

const stringifyKey = (value: unknown): string => {
  try {
    return JSON.stringify(value) ?? "interrupt";
  } catch {
    return "interrupt";
  }
};

const interruptKey = (interrupt: LangGraphInterruptState): string => {
  const wire = interrupt as { id?: unknown; interrupt_id?: unknown };
  return (
    readString(wire.interrupt_id) ??
    readString(wire.id) ??
    stringifyKey(interrupt.value)
  );
};

const toAction = (
  request: unknown,
  index: number,
  configs: unknown[],
): PendingAction | undefined => {
  if (!isRecord(request)) return undefined;
  const name = readString(request.name);
  if (name === undefined) return undefined;
  const config = configs.find(
    (entry) => isRecord(entry) && entry.action_name === name,
  );
  const allowed = readDecisions(
    isRecord(config) ? config.allowed_decisions : undefined,
  );
  return {
    key: `${index}:${name}`,
    name,
    args: isRecord(request.args) ? request.args : {},
    allowed: allowed.length > 0 ? allowed : DEFAULT_DECISIONS,
  };
};

export const parseInterrupt = (
  interrupt: LangGraphInterruptState | undefined,
): PendingInterrupt | undefined => {
  if (interrupt === undefined) return undefined;
  const value = interrupt.value;
  const record = isRecord(value) ? value : {};
  const requests = Array.isArray(record.action_requests)
    ? record.action_requests
    : [];
  const configs = Array.isArray(record.review_configs)
    ? record.review_configs
    : [];
  const actions = requests
    .map((request, index) => toAction(request, index, configs))
    .filter((action): action is PendingAction => action !== undefined);
  return {
    key: interruptKey(interrupt),
    resumable: interrupt.resumable !== false,
    actions,
    value,
  };
};

// The SDK types resume as a string; HITL resumes with an object.
export const decisionsCommand = (decisions: HitlDecision[]): LangGraphCommand =>
  ({ resume: { decisions } }) as unknown as LangGraphCommand;

export const valueCommand = (value: unknown): LangGraphCommand =>
  ({ resume: value }) as unknown as LangGraphCommand;

export const actionLabel = (action: PendingAction): string =>
  ACTION_LABELS[action.name] ?? action.name;

export const actionTarget = (action: PendingAction): string | undefined => {
  for (const key of PATH_ARGS) {
    const value = action.args[key];
    if (typeof value === "string" && value !== "") return value;
  }
  return undefined;
};

export const actionDetails = (action: PendingAction): [string, unknown][] =>
  Object.entries(action.args).filter(([key]) => !PATH_ARGS.has(key));
