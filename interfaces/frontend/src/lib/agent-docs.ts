import { INGEST_API_URL } from "@/lib/rag-upload";

export type AgentDocumentName = "agents" | "userinfo" | "system-prompt";

export const ADDITIONAL_INSTRUCTIONS_HEADING = "## Additional instructions";

const HEADING_PATTERN = /^##\s+additional instructions\s*$/im;
const NEXT_HEADING_PATTERN = /^#{1,2}\s/m;

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* response was not JSON */
  }
  return `request failed (${response.status})`;
}

export async function readAgentDocument(
  name: AgentDocumentName,
): Promise<string> {
  const response = await fetch(
    `${INGEST_API_URL}/agent/docs/${encodeURIComponent(name)}`,
  );
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { content?: string };
  return body.content ?? "";
}

export async function writeAgentDocument(
  name: AgentDocumentName,
  content: string,
): Promise<void> {
  const response = await fetch(
    `${INGEST_API_URL}/agent/docs/${encodeURIComponent(name)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    },
  );
  if (!response.ok) throw new Error(await readError(response));
}

export function extractAdditionalInstructions(content: string): string {
  const match = HEADING_PATTERN.exec(content);
  if (!match) return "";
  const rest = content.slice(match.index + match[0].length);
  const next = NEXT_HEADING_PATTERN.exec(rest);
  return (next ? rest.slice(0, next.index) : rest).trim();
}

function findSection(content: string): { start: number; end: number } | null {
  const match = HEADING_PATTERN.exec(content);
  if (!match) return null;
  const bodyStart = match.index + match[0].length;
  const next = NEXT_HEADING_PATTERN.exec(content.slice(bodyStart));
  return {
    start: match.index,
    end: next ? bodyStart + next.index : content.length,
  };
}

export function mergeAdditionalInstructions(
  content: string,
  instructions: string,
): string {
  const section = instructions.trim();
  const block = section ? `${ADDITIONAL_INSTRUCTIONS_HEADING}\n\n${section}` : "";
  const range = findSection(content);
  if (!range) {
    if (!block) return content;
    const base = content.trimEnd();
    return `${base ? `${base}\n\n` : ""}${block}\n`;
  }
  const before = content.slice(0, range.start).trimEnd();
  const after = content.slice(range.end).trim();
  const body = [before, block, after].filter(Boolean).join("\n\n");
  return body ? `${body}\n` : "";
}
