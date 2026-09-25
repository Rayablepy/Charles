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

export type ChatSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

function firstUserMessageText(values: unknown): string {
  const messages = (
    values as { messages?: readonly { type?: string; content?: unknown }[] } | null
  )?.messages;
  if (!messages) return "";
  for (const message of messages) {
    if (message.type !== "human") continue;
    const text = textFromContent(message.content);
    if (text) return text;
  }
  return "";
}

/** Strip the auto-generated "[The file ... was uploaded for indexing]" marker. */
function stripUploadMarker(text: string): string {
  return text.replace(/^\[The file .*?\]\s*/s, "").trim();
}

/** Display title for a chat: metadata.title → first user message → fallback. */
export function titleForChat(thread: {
  metadata?: Record<string, unknown> | null;
  values?: unknown;
}): string {
  const named = thread.metadata?.title;
  if (typeof named === "string" && named.trim()) return named.trim();
  const first = stripUploadMarker(firstUserMessageText(thread.values));
  if (first) return first.length > 60 ? `${first.slice(0, 57)}…` : first;
  return "Untitled chat";
}

/** Persist a custom title for a chat (replaces metadata.title). */
export async function renameChat(threadId: string, title: string): Promise<void> {
  const thread = await langgraphClient.threads.get(threadId);
  await langgraphClient.threads.update(threadId, {
    metadata: { ...(thread.metadata ?? {}), title },
  });
}

/** Delete a chat and its whole conversation from the server. */
export async function deleteChat(threadId: string): Promise<void> {
  await langgraphClient.threads.delete(threadId);
}

/** List chats newest-first for the sidebar, backed by the LangGraph API. */
export async function listChats(limit = 50): Promise<ChatSummary[]> {
  const threads = await langgraphClient.threads.search({ limit });
  return threads
    .map((thread) => ({
      id: thread.thread_id,
      title: titleForChat(thread),
      updatedAt:
        thread.updated_at ?? thread.state_updated_at ?? thread.created_at,
    }))
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
}