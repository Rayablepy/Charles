"use client";

import { AssistantRuntimeProvider, useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react";
import type { ReactNode } from "react";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Demo adapter — replies with a canned, streamed response so the chat UI
 * runs on localhost without a backend.
 *
 * To wire the real LangGraph agent (the `agent` graph in `langgraph.json`),
 * replace this provider with the LangGraph runtime:
 *
 *   npm install @assistant-ui/react-langgraph @langchain/langgraph-sdk
 *
 *   const runtime = useLangGraphRuntime({
 *     stream: unstable_createLangGraphStream(...),
 *     ...
 *   });
 *
 * See https://www.assistant-ui.com/docs/runtimes/langgraph/quickstart.
 */
const DemoModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const lastUser = [...messages].reverse().find((message) => message.role === "user");
    const text = (lastUser?.content ?? []).flatMap((part) =>
      part.type === "text" ? [part.text] : [],
    ).join(" ");

    const reply =
      `Demo runtime — no backend connected yet.\n\n` +
      (text ? `You asked: "${text}".\n\n` : "") +
      `Point this adapter at LangGraph to get real answers from the local agent.`;

    let acc = "";
    for (const token of reply.split(/\b/)) {
      if (abortSignal.aborted) return;
      acc += token;
      yield { content: [{ type: "text", text: acc }] };
      await sleep(24);
    }
  },
};

export function ChatRuntimeProvider({ children }: { children: ReactNode }) {
  const runtime = useLocalRuntime(DemoModelAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}