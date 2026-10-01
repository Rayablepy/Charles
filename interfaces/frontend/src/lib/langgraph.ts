import { Client } from "@langchain/langgraph-sdk";

export const LANGGRAPH_API_URL =
  import.meta.env.VITE_LANGGRAPH_API_URL ?? "http://127.0.0.1:2024";

export const LANGGRAPH_ASSISTANT_ID =
  import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID ?? "agent";

export const langgraphClient = new Client({
  apiUrl: LANGGRAPH_API_URL,
  apiKey: null,
});

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


export function isAgentMessage(m: ServerMessage): boolean {
  const type = (m.type ?? m.role) as string | undefined;
  if (type !== "ai" && type !== "assistant") return false;
  if (Array.isArray(m.tool_calls) && m.tool_calls.length > 0) return false;
  const name = typeof m.name === "string" ? m.name.toLowerCase() : "";
  return !name.includes("web_agent");
}


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

function stripUploadMarker(text: string): string {
  return text.replace(/^\[The file .*?\]\s*/s, "").trim();
}

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

export async function renameChat(threadId: string, title: string): Promise<void> {
  const thread = await langgraphClient.threads.get(threadId);
  await langgraphClient.threads.update(threadId, {
    metadata: { ...(thread.metadata ?? {}), title },
  });
}

export async function deleteChat(threadId: string): Promise<void> {
  await langgraphClient.threads.delete(threadId);
}

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