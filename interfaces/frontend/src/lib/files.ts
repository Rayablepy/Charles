import { INGEST_API_URL } from "@/lib/rag-upload";

export type FileScope = "project" | "skills";

export type StoredFile = {
  path: string;
  name: string;
  size: number;
  modified: string;
  full_path: string;
};

export type StoredFileContent = {
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

export async function listFiles(scope: FileScope): Promise<StoredFile[]> {
  const response = await fetch(`${INGEST_API_URL}/${scope}/files`);
  if (!response.ok) throw new Error(await readError(response));
  const body = (await response.json()) as { files?: StoredFile[] };
  return body.files ?? [];
}

export async function readFile(
  scope: FileScope,
  path: string,
): Promise<StoredFileContent> {
  const response = await fetch(
    `${INGEST_API_URL}/${scope}/file?path=${encodeURIComponent(path)}`,
  );
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as StoredFileContent;
}

export async function renameFile(
  scope: FileScope,
  path: string,
  name: string,
): Promise<void> {
  const query = `path=${encodeURIComponent(path)}&name=${encodeURIComponent(name)}`;
  const response = await fetch(
    `${INGEST_API_URL}/${scope}/file/rename?${query}`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error(await readError(response));
}

export async function deleteFile(
  scope: FileScope,
  path: string,
): Promise<void> {
  const response = await fetch(
    `${INGEST_API_URL}/${scope}/file?path=${encodeURIComponent(path)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw new Error(await readError(response));
}
