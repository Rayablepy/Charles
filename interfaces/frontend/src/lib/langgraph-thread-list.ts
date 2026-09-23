import type {
  RemoteThreadListAdapter,
  RemoteThreadMetadata,
} from "@assistant-ui/core";
import type { AssistantStream } from "assistant-stream";
import type { Client, Thread } from "@langchain/langgraph-sdk";
import { deleteChat, renameChat, titleForChat } from "./langgraph";

/**
 * RemoteThreadListAdapter backed by the LangGraph API. Lets `useLangGraphRuntime`
 * manage real server threads through `useRemoteThreadListRuntime`: the sidebar
 * list is sourced from `threads/search`, and selecting an existing chat switches
 * the active thread so its prior conversation loads via the runtime's `load`
 * callback. Without this adapter the runtime falls back to an in-memory list,
 * which cannot select or load an existing thread ID.
 */
export function createLangGraphThreadListAdapter(
  client: Client,
): RemoteThreadListAdapter {
  function toRemoteMetadata(thread: Thread): RemoteThreadMetadata {
    return {
      status: "regular",
      remoteId: thread.thread_id,
      externalId: thread.thread_id,
      title: titleForChat(thread),
      lastMessageAt: new Date(
        thread.updated_at ?? thread.state_updated_at ?? thread.created_at,
      ),
      custom: thread.metadata ?? undefined,
    };
  }

  return {
    list: async () => {
      const threads = await client.threads.search({ limit: 50 });
      return { threads: threads.map(toRemoteMetadata) };
    },
    fetch: async (threadId) =>
      toRemoteMetadata(await client.threads.get(threadId)),
    rename: async (threadId, newTitle) => {
      await renameChat(threadId, newTitle);
    },
    archive: async () => {},
    unarchive: async () => {},
    delete: async (threadId) => {
      await deleteChat(threadId);
    },
    initialize: async () => {
      const thread = await client.threads.create();
      return { remoteId: thread.thread_id, externalId: thread.thread_id };
    },
    generateTitle: async () =>
      new ReadableStream<unknown>({
        start(controller) {
          controller.close();
        },
      }) as unknown as AssistantStream,
  };
}