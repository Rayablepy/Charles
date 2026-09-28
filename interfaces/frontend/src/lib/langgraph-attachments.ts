import type {
  AttachmentAdapter,
  CompleteAttachment,
  PendingAttachment,
} from "@assistant-ui/react";

/*whitelist allowed file types*/
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

const INGEST_API_URL =
  import.meta.env.VITE_INGEST_API_URL ?? "http://127.0.0.1:2030";

const POLL_INTERVAL_MS = 500;
const POLL_TIMEOUT_MS = 60_000;

type JobStatus = {
  job_id: string;
  status: "queued" | "ingesting" | "indexed" | "already-indexed" | "failed";
  source: string;
  error?: string;
};

async function errorDetail(res: Response): Promise<string> {
  let detail = "";
  try {
    const body = (await res.json()) as { detail?: string; error?: string };
    detail = body.detail ?? body.error ?? "";
  } catch {
    /* non-JSON error body */
  }
  return detail || `request failed (${res.status})`;
}

/*check if job is complete by polling the endpoint and returning status*/
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
    const source = await this.uploadAndWait(attachment);
    return {
      ...attachment,
      status: { type: "complete" },
      content: [
        {
          type: "text",
          text: `[The file "${escapeLabel(
            source,
          )}" was added to the knowledge base and can be retrieved via query_data.]`,
        },
      ],
    };
  }

  /** Enqueues the upload, waits for indexing, returns the display source name. */
  private async uploadAndWait(attachment: PendingAttachment): Promise<string> {
    let jobId: string
    let source: string
    try {
      const form = new FormData();
      form.append("file", attachment.file, attachment.name);
      const res = await fetch(`${INGEST_API_URL}/uploads`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        throw new Error(await errorDetail(res));
      }
      const body = (await res.json()) as { job_id?: string; source?: string };
      jobId = body.job_id ?? "";
      source = body.source ?? attachment.name;
      if (!jobId) throw new Error("no job id returned");
    } catch (err) {
      throw new Error(
        `Could not add ${attachment.name} to the knowledge base: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    }

    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (Date.now() < deadline) {
      const res = await fetch(`${INGEST_API_URL}/uploads/${jobId}`);
      if (res.status === 404) {
        throw new Error(
          `Could not add ${attachment.name} to the knowledge base: ingest job was lost`,
        );
      }
      if (res.ok) {
        const job = (await res.json()) as JobStatus;
        if (job.status === "indexed" || job.status === "already-indexed") {
          return source;
        }
        if (job.status === "failed") {
          throw new Error(
            `Could not add ${attachment.name} to the knowledge base: ${
              job.error ?? "indexing failed"
            }`,
          );
        }
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
    throw new Error(
      `Could not add ${attachment.name} to the knowledge base: indexing timed out`,
    );
  }

  async remove() {}
}