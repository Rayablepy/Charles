import { INGEST_API_URL } from "@/lib/rag-upload";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* response was not JSON */
  } 
  return `request failed (${response.status})`;
}

export async function readAgentMemory(): Promise<string> {
  const response = await fetch(`${INGEST_API_URL}/agentmemory`);
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { content?: string };
  return body.content ?? "";
}

export async function saveAgentMemory(content: string): Promise<void> {
  const response = await fetch(`${INGEST_API_URL}/agentmemory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) throw new Error(await readError(response));
}
