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
import { createLangGraphThreadListAdapter } from "@/lib/langgraph-thread-list";

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

  const threadListAdapter = useMemo(
    () => createLangGraphThreadListAdapter(langgraphClient),
    [],
  );

  const runtime = useLangGraphRuntime({
    unstable_allowCancellation: true,
    unstable_threadListAdapter: threadListAdapter,
    threadId,
    onThreadIdChange,
    stream,
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