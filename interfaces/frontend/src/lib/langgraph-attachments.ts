import type {
  AttachmentAdapter,
  CompleteAttachment,
  PendingAttachment,
} from "@assistant-ui/react";

/**
 * Whitelist of attachable file types for the RAG upload flow.
 * Deliberately excludes images, videos and audio — those are blocked for now.
 * Matched by MIME type and by file extension (see fileMatchesAccept).
 */
const ACCEPT = [
  "text/*",
  "application/json",
  "application/xml",
  "application/csv",
  "application/pdf",
  "application/msword",
  "application/rtf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.oasis.opendocument.text",
  "application/vnd.oasis.opendocument.spreadsheet",
  ".md",
  ".markdown",
  ".txt",
  ".rtf",
  ".csv",
  ".tsv",
  ".json",
  ".jsonl",
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".cfg",
  ".conf",
  ".env",
  ".ipynb",
  ".py",
  ".js",
  ".mjs",
  ".cjs",
  ".jsx",
  ".ts",
  ".tsx",
  ".css",
  ".scss",
  ".html",
  ".htm",
  ".xml",
  ".sql",
  ".sh",
  ".bash",
  ".zsh",
  ".bat",
  ".cmd",
  ".ps1",
  ".java",
  ".c",
  ".cpp",
  ".h",
  ".hpp",
  ".cs",
  ".go",
  ".rs",
  ".rb",
  ".php",
  ".swift",
  ".kt",
  ".r",
  ".jl",
  ".lua",
  ".scala",
  ".vue",
  ".svelte",
  ".rst",
  ".tex",
  ".diff",
  ".patch",
].join(",");

function escapeLabel(name: string) {
  return name.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

/**
 * Uploads the raw file bytes to the backend (Vite middleware → ingest
 * script → RAG vector store), then emits a short notice so the agent knows
 * the document is queryable via query_data.
 */
export class RagUploadAttachmentAdapter implements AttachmentAdapter {
  public readonly accept = ACCEPT;

  async add(state: { file: File }): Promise<PendingAttachment> {
    return {
      id: crypto.randomUUID(),
      type: "document",
      name: state.file.name,
      contentType: state.file.type,
      file: state.file,
      status: { type: "requires-action", reason: "composer-send" },
    };
  }

  async send(attachment: PendingAttachment): Promise<CompleteAttachment> {
    try {
      const res = await fetch("/rag/upload", {
        method: "POST",
        headers: {
          "content-type": attachment.file.type || "application/octet-stream",
          "x-file-name": encodeURIComponent(attachment.name),
        },
        body: attachment.file,
      });
      if (!res.ok) {
        let detail = "";
        try {
          detail = ((await res.json()) as { error?: string }).error ?? "";
        } catch {
          /* non-JSON error body */
        }
        throw new Error(detail || `Upload failed (${res.status})`);
      }
      const { source, job_id } = (await res.json()) as {
        source: string
        job_id?: string
      }
      return {
        ...attachment,
        status: { type: "complete" },
        content: [
          {
            type: "text",
            text: `[The file "${escapeLabel(
              source,
            )}" was uploaded for indexing${
              job_id ? ` (job ${job_id})` : ""
            }. It becomes searchable via query_data once indexing finishes. If query_data returns nothing yet, wait a few seconds and call query_data again.]`,
          },
        ],
      };
    } catch (err) {
      throw new Error(
        `Could not add ${attachment.name} to the knowledge base: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    }
  }

  async remove() {}
}