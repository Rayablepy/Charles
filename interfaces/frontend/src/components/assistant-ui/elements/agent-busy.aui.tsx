"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useAuiState } from "@assistant-ui/react";
import { useLangGraphInterruptState } from "@assistant-ui/react-langgraph";

export type AgentBusy = "approval" | "responding" | undefined;

const AgentBusyContext = createContext<AgentBusy>(undefined);

// Sending is blocked while a run streams or awaits approval.
export const AgentBusyProvider = ({ children }: { children: ReactNode }) => {
  const interrupt = useLangGraphInterruptState();
  const running = useAuiState((s) => s.thread.isRunning);
  const busy: AgentBusy =
    interrupt === undefined ? (running ? "responding" : undefined) : "approval";
  return (
    <AgentBusyContext.Provider value={busy}>
      {children}
    </AgentBusyContext.Provider>
  );
};

export const useAgentBusy = () => useContext(AgentBusyContext);
