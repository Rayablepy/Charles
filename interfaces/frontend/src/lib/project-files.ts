import { INGEST_API_URL } from "@/lib/rag-upload";

export type ProjectFile = {
  path: string;
  name: string;
  size: number;
  modified: string;
};

export type ProjectFileContent = {
  path: string;
  name: string;
  size: number;
  binary: boolean;
  truncated: boolean;
  text: string;
};

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) return body.detail;
  } catch {
    /* response was not JSON */
  }
  return `request failed (${response.status})`;
}

export async function listProjectFiles(): Promise<ProjectFile[]> {
  const response = await fetch(`${INGEST_API_URL}/project/files`);
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { files?: ProjectFile[] };
  return body.files ?? [];
}

export async function readProjectFile(path: string): Promise<ProjectFileContent> {
  const response = await fetch(
    `${INGEST_API_URL}/project/file?path=${encodeURIComponent(path)}`,
  );
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as ProjectFileContent;
}
