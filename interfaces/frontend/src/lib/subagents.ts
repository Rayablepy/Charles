import { INGEST_API_URL } from "@/lib/rag-upload";

export type ConfiguredSubagent = {
  subagent: string;
  enabled: boolean;
};

export const SUBAGENTS = [
  { id: "web_agent", name: "web_agent" },
  { id: "sandbox_agent", name: "sandbox_agent" },
];

async function readError(response: Response): Promise<string> {
  let detail = "";
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    detail = "";
  }
  return detail || `request failed (${response.status})`;
}

export async function listSubagents(): Promise<ConfiguredSubagent[]> {
  const response = await fetch(`${INGEST_API_URL}/subagents`);
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as {
    subagents?: ConfiguredSubagent[];
  };
  return body.subagents ?? [];
}

export async function setSubagentEnabled(
  subagent: string,
  enabled: boolean,
): Promise<void> {
  const response = await fetch(`${INGEST_API_URL}/subagents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subagent, enabled, model: "" }),
  });
  if (!response.ok) throw new Error(await readError(response));
}
