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

const INGEST_API_URL =
  import.meta.env.VITE_INGEST_API_URL ?? "http://127.0.0.1:2030";

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

const POLL_INTERVAL_MS = 500;
const POLL_TIMEOUT_MS = 60_000;

/*upload part of the bar, index part fills the rest*/
const UPLOAD_PROGRESS_MAX = 0.7;
const INDEX_PROGRESS_INGESTING = 0.85;
const INDEX_PROGRESS_INDEXED = 1;

type JobStatus = {
  job_id: string;
  status: "queued" | "ingesting" | "indexed" | "already-indexed" | "failed";
  source: string;
  error?: string;
};

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(bytes >= 100 * 1024 * 1024 ? 0 : 1)} MB`;
}

function tooLargeMessage(name: string, size: number): string {
  return `${name} is too large (${formatBytes(size)}). Maximum file size is ${formatBytes(MAX_UPLOAD_BYTES)}.`;
}

function isTooLarge(file: { name: string; size: number }): boolean {
  return file.size > MAX_UPLOAD_BYTES;
}

function wrapError(name: string, detail: string): Error {
  return new Error(`Could not add ${name} to the knowledge base: ${detail}`);
}

type UploadResult = { jobId: string; source: string };

/*POST the file via XHR so byte-level upload progress can be reported*/
function postUpload(
  file: File,
  onProgress:(fraction: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file, file.name);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${INGEST_API_URL}/uploads`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress(Math.min(event.loaded / event.total, 1) * UPLOAD_PROGRESS_MAX);
      }
    };
    xhr.onerror = () =>
      reject(wrapError(file.name, `network error (${INGEST_API_URL})`));
    xhr.onload = () => {
      let body: { job_id?: string; source?: string };
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        reject(wrapError(file.name, `request failed (${xhr.status})`));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        const jobId = body.job_id ?? "";
        const source = body.source ?? file.name;
        if (!jobId) reject(wrapError(file.name, "no job id returned"));
        else resolve({ jobId, source });
        return;
      }
      const detail = "detail" in body && typeof body.detail === "string"
        ? body.detail
        : "";
      reject(wrapError(file.name, detail || `request failed (${xhr.status})`));
    };
    xhr.send(form);
  });
}

/*upload the file, poll the ingest job, report progress 0..1 as it goes*/
export async function uploadToMemory(
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<string> {
  if (isTooLarge(file)) throw new Error(tooLargeMessage(file.name, file.size));

  let source: string;
  let jobId: string;
  try {
    const result = await postUpload(file, (fraction) =>
      onProgress?.(fraction),
    );
    source = result.source;
    jobId = result.jobId;
  } catch (err) {
    if (err instanceof Error) throw err;
    throw wrapError(file.name, String(err));
  }

  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const res = await fetch(`${INGEST_API_URL}/uploads/${jobId}`);
    if (res.status === 404) {
      throw wrapError(file.name, "ingest job was lost");
    }
    if (res.ok) {
      const job = (await res.json()) as JobStatus;
      if (job.status === "indexed" || job.status === "already-indexed") {
        onProgress?.(INDEX_PROGRESS_INDEXED);
        return source;
      }
      if (job.status === "failed") {
        throw wrapError(file.name, job.error ?? "indexing failed");
      }
      onProgress?.(
        job.status === "ingesting" ? INDEX_PROGRESS_INGESTING : UPLOAD_PROGRESS_MAX,
      );
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw wrapError(file.name, "indexing timed out");
}

export { ACCEPT, INGEST_API_URL, MAX_UPLOAD_BYTES, tooLargeMessage, isTooLarge };