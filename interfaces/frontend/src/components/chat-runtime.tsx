"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import {
  unstable_createLangGraphStream,
  useLangGraphRuntime,
  type LangChainMessage,
} from "@assistant-ui/react-langgraph";
import { LANGGRAPH_ASSISTANT_ID, langgraphClient } from "@/lib/langgraph";

export function ChatRuntimeProvider({
  children,
  threadId,
  onThreadIdChange,
}: {
  children: ReactNode;
  threadId?: string | undefined;
  onThreadIdChange?: (threadId: string | undefined) => void;
}) {
  const stream = useMemo(
    () =>
      unstable_createLangGraphStream({
        client: langgraphClient,
        assistantId: LANGGRAPH_ASSISTANT_ID,
      }),
    [],
  );

  const runtime = useLangGraphRuntime({
    unstable_allowCancellation: true,
    threadId,
    onThreadIdChange,
    stream,
    create: async () => {
      const thread = await langgraphClient.threads.create();
      return { externalId: thread.thread_id };
    },
    load: async (externalId) => {
      try {
        const state = await langgraphClient.threads.getState(externalId);
        const values = state.values as unknown as
          | { messages?: LangChainMessage[] }
          | undefined;
        return { messages: values?.messages ?? [] };
      } catch {
        return { messages: [] };
      }
    },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}