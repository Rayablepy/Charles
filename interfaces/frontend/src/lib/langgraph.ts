import { Client } from "@langchain/langgraph-sdk";

/**
 * Base URL of the LangGraph API server (the `langgraph dev` server).
 * Override via VITE_LANGGRAPH_API_URL in interfaces/frontend/.env.
 */
export const LANGGRAPH_API_URL =
  import.meta.env.VITE_LANGGRAPH_API_URL ?? "http://127.0.0.1:2024";

/**
 * Key of the graph declared in langgraph.json (`agent` → agent/agent.py:stack_agent).
 */
export const LANGGRAPH_ASSISTANT_ID =
  import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID ?? "agent";

export const langgraphClient = new Client({
  apiUrl: LANGGRAPH_API_URL,
  apiKey: null,
});

/**
 * Messages returned by the LangGraph API server are serialized LangChain
 * messages ({ type: "human" | "ai" | "tool" | "system", content, ... }).
 */
export type ServerMessage = Record<string, unknown>;

function textFromContent(content: unknown): string {
  if (typeof content === "string") return content.trim();
  if (!Array.isArray(content)) return "";
  return content
    .filter((block): block is Record<string, unknown> =>
      typeof block === "object" && block !== null,
    )
    .flatMap((block) =>
      block.type === "text" && typeof block.text === "string" && block.text.trim()
        ? [block.text.trim()]
        : [],
    )
    .join("\n");
}

/**
 * True for plain agent text messages. Filters out tool calls, tool results,
 * subagent (web_agent) messages, and anything that isn't an AI message.
 */
export function isAgentMessage(m: ServerMessage): boolean {
  const type = (m.type ?? m.role) as string | undefined;
  if (type !== "ai" && type !== "assistant") return false;
  if (Array.isArray(m.tool_calls) && m.tool_calls.length > 0) return false;
  const name = typeof m.name === "string" ? m.name.toLowerCase() : "";
  return !name.includes("web_agent");
}

/**
 * Mirrors agent.extract_answer for the chat UI: the latest agent text message.
 */
export function extractAgentAnswer(messages: readonly ServerMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (!isAgentMessage(message)) continue;
    const text =
      textFromContent(message.content) || textFromContent(message.content_blocks);
    if (text) return text;
  }
  return "";
}

/** LangChain-style input message the LangGraph server / graph accepts. */
export function toLangGraphUserMessage(text: string) {
  return { role: "user", content: text };
}