"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { LoaderIcon, ShieldAlertIcon } from "lucide-react";
import {
  useLangGraphInterruptState,
  useLangGraphSendCommand,
  type LangGraphCommand,
} from "@assistant-ui/react-langgraph";
import {
  actionDetails,
  actionLabel,
  actionTarget,
  decisionsCommand,
  parseInterrupt,
  valueCommand,
  type DecisionChoice,
  type HitlDecision,
  type PendingAction,
} from "@/lib/langgraph-interrupts";

const describe = (value: unknown): string => {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2) ?? String(value);
};

const isBlock = (value: unknown): boolean =>
  typeof value === "string" && (value.length > 72 || value.includes("\n"));

const ActionArgs = ({ action }: { action: PendingAction }) => {
  const target = actionTarget(action);
  const details = actionDetails(action);
  return (
    <div className="app-approval-detail">
      {target === undefined ? null : (
        <p className="app-approval-target">{target}</p>
      )}
      {details.map(([key, value]) => (
        <div key={key} className="app-approval-arg">
          <span className="app-approval-arg-key">{key}</span>
          {isBlock(value) ? (
            <pre className="app-approval-arg-block">{String(value)}</pre>
          ) : (
            <code className="app-approval-arg-value">{describe(value)}</code>
          )}
        </div>
      ))}
    </div>
  );
};

const ChoiceButton = ({
  active,
  disabled,
  children,
  onClick,
}: {
  active?: boolean;
  disabled: boolean;
  children: string;
  onClick: () => void;
}) => (
  <button
    type="button"
    className={`app-approval-btn${active ? " app-approval-btn-on" : ""}`}
    disabled={disabled}
    onClick={onClick}
  >
    {children}
  </button>
);

export const InterruptPrompt = () => {
  const interrupt = useLangGraphInterruptState();
  const sendCommand = useLangGraphSendCommand();
  const pending = useMemo(() => parseInterrupt(interrupt), [interrupt]);
  const pendingKey = pending?.key;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [choices, setChoices] = useState<Record<string, DecisionChoice>>({});
  const [answer, setAnswer] = useState("");

  useEffect(() => {
    setBusy(false);
    setError(null);
    setChoices({});
    setAnswer("");
  }, [pendingKey]);

  const resolve = useCallback(
    async (command: LangGraphCommand) => {
      setBusy(true);
      setError(null);
      try {
        await sendCommand(command);
      } catch (cause) {
        setBusy(false);
        setError(cause instanceof Error ? cause.message : String(cause));
      }
    },
    [sendCommand],
  );

  if (pending === undefined) return null;

  const actions = pending.actions;
  const multiple = actions.length > 1;
  const interactive = pending.resumable && !busy;
  const decided = actions.every((action) => choices[action.key] !== undefined);

  const choose = (action: PendingAction, kind: HitlDecision["type"]) => {
    if (!interactive) return;
    if (!multiple) {
      void resolve(decisionsCommand([{ type: kind }]));
      return;
    }
    setChoices((prev) => ({ ...prev, [action.key]: kind }));
  };

  const submit = () => {
    if (!interactive) return;
    const decisions: HitlDecision[] = [];
    for (const action of actions) {
      const choice = choices[action.key];
      if (choice === undefined) return;
      decisions.push({ type: choice });
    }
    void resolve(decisionsCommand(decisions));
  };

  const resumeWithAnswer = () => {
    if (!interactive) return;
    void resolve(valueCommand(answer));
  };

  return (
    <div
      className="app-approval"
      data-slot="app_interrupt-prompt"
      role="group"
      aria-label="Approval required"
    >
      <div className="app-approval-header">
        {busy ? (
          <LoaderIcon className="app-approval-icon app-approval-icon-busy" />
        ) : (
          <ShieldAlertIcon className="app-approval-icon" />
        )}
        <span>{busy ? "Submitting decision" : "Approval required"}</span>
      </div>

      {actions.length === 0 ? (
        <div className="app-approval-detail">
          <pre className="app-approval-arg-block">{describe(pending.value)}</pre>
          {interactive ? (
            <div className="app-approval-answer">
              <input
                className="app-approval-input"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Resume value"
                aria-label="Resume value"
              />
              <button
                type="button"
                className="app-approval-btn"
                onClick={resumeWithAnswer}
              >
                Resume
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {actions.map((action) => (
        <div key={action.key} className="app-approval-action">
          <div className="app-approval-action-head">
            <span className="app-approval-action-name">
              {actionLabel(action)}
            </span>
          </div>
          <ActionArgs action={action} />
          {multiple ? (
            <div className="app-approval-actions">
              <ChoiceButton
                disabled={!interactive || !action.allowed.includes("reject")}
                active={choices[action.key] === "reject"}
                onClick={() => choose(action, "reject")}
              >
                Reject
              </ChoiceButton>
              <ChoiceButton
                disabled={!interactive || !action.allowed.includes("approve")}
                active={choices[action.key] === "approve"}
                onClick={() => choose(action, "approve")}
              >
                Approve
              </ChoiceButton>
            </div>
          ) : null}
        </div>
      ))}

      {multiple ? (
        <div className="app-approval-actions">
          <button
            type="button"
            className="app-approval-btn app-approval-btn-primary"
            disabled={!interactive || !decided}
            onClick={submit}
          >
            Submit decisions
          </button>
        </div>
      ) : null}

      {actions.length === 1 ? (
        <div className="app-approval-actions">
          <ChoiceButton
            disabled={!interactive || !actions[0].allowed.includes("reject")}
            onClick={() => choose(actions[0], "reject")}
          >
            Reject
          </ChoiceButton>
          <button
            type="button"
            className="app-approval-btn app-approval-btn-primary"
            disabled={!interactive || !actions[0].allowed.includes("approve")}
            onClick={() => choose(actions[0], "approve")}
          >
            Approve
          </button>
        </div>
      ) : null}

      {!pending.resumable ? (
        <p className="app-approval-note">
          This interrupt cannot be resumed from here.
        </p>
      ) : null}

      {error === null ? null : (
        <p className="app-approval-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
