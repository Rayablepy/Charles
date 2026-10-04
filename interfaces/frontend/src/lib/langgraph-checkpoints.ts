import type { LangChainMessage } from "@assistant-ui/react-langgraph";
import type { Client, Config } from "@langchain/langgraph-sdk";

const PAGE_SIZE = 100;

const matchesSequence = (
  expected: readonly LangChainMessage[],
  actual: unknown,
) => {
  if (!Array.isArray(actual)) return false;
  if (actual.length !== expected.length) return false;
  return actual.every((message, index) => {
    if (message === null || typeof message !== "object") return false;
    const id = (message as { id?: unknown }).id;
    return typeof id === "string" && id === expected[index]?.id;
  });
};

export async function resolveForkCheckpoint(
  client: Client,
  threadId: string,
  messagesUpToParent: readonly LangChainMessage[],
): Promise<string | null> {
  if (!messagesUpToParent.every((message) => typeof message.id === "string"))
    return null;
  const scanned = new Set<string>();
  let before: Config | undefined;
  for (;;) {
    const page = await client.threads.getHistory(
      threadId,
      before ? { limit: PAGE_SIZE, before } : { limit: PAGE_SIZE },
    );
    let oldestCheckpointId: string | undefined;
    let advanced = false;
    for (const state of page) {
      const checkpointId = state.checkpoint?.checkpoint_id;
      if (typeof checkpointId === "string") {
        oldestCheckpointId = checkpointId;
        if (!scanned.has(checkpointId)) {
          scanned.add(checkpointId);
          advanced = true;
        }
      }
      const stateMessages = (
        state.values as unknown as { messages?: unknown } | undefined
      )?.messages;
      if (checkpointId && matchesSequence(messagesUpToParent, stateMessages)) {
        return checkpointId;
      }
    }
    // Stalled cursor pages would loop forever so just stop instead
    if (page.length < PAGE_SIZE || oldestCheckpointId === undefined || !advanced)
      return null;
    before = { configurable: { checkpoint_id: oldestCheckpointId } };
  }
}