import { INGEST_API_URL } from "@/lib/rag-upload";

export type ProjectFile = {
  path: string;
  name: string;
  size: number;
  modified: string;
  full_path: string;
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

export async function renameProjectFile(path: string, name: string): Promise<void> {
  const query = `path=${encodeURIComponent(path)}&name=${encodeURIComponent(name)}`;
  const response = await fetch(`${INGEST_API_URL}/project/file/rename?${query}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(await readError(response));
}

export async function deleteProjectFile(path: string): Promise<void> {
  const response = await fetch(
    `${INGEST_API_URL}/project/file?path=${encodeURIComponent(path)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw new Error(await readError(response));
}
