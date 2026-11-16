"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { FileIcon, Loader2Icon, PlusIcon, Trash2Icon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  deleteMemoryFile,
  listMemoryFiles,
  type StoredFile,
} from "@/lib/files";
import { ACCEPT, uploadToMemory } from "@/lib/rag-upload";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatEdited(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const day = date.getDate();
  const month = date.toLocaleString(undefined, { month: "short" });
  return `Edited ${day} ${month} ${date.getFullYear()}`;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function MemoryBrowser() {
  const [files, setFiles] = useState<StoredFile[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState(false);
  const [fraction, setFraction] = useState(0);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const [deleteTarget, setDeleteTarget] = useState<StoredFile | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const next = await listMemoryFiles();
      setFiles(next);
      setError("");
    } catch (err) {
      setFiles([]);
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadFiles();
  }, [loadFiles]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 2000);
    return () => clearTimeout(timer);
  }, [notice]);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    setFraction(0);
    setError("");
    try {
      const source = await uploadToMemory(file, setFraction);
      setNotice(`Added ${source}`);
      await loadFiles();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      setFraction(0);
    }
  };

  const closeDelete = () => {
    setDeleteTarget(null);
    setDeleteError("");
  };

  const submitDelete = async () => {
    const target = deleteTarget;
    if (!target) return;
    setDeleteBusy(true);
    try {
      await deleteMemoryFile(target.path);
      setNotice(`Deleted ${target.name}`);
      closeDelete();
      await loadFiles();
    } catch (err) {
      setDeleteError(errorMessage(err));
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <div className="app-files">
      <header className="app-files-header">
        <h2 className="app-files-title">Memory</h2>
        <input
          ref={uploadInputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(event) => void handleUpload(event)}
        />
        <button
          type="button"
          className="app-files-upload"
          onClick={() => uploadInputRef.current?.click()}
          disabled={uploading}
          aria-busy={uploading}
        >
          {uploading ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            <PlusIcon className="size-4" />
          )}
          <span>{uploading ? "Uploading" : "Add file"}</span>
        </button>
      </header>
      {uploading && (
        <div
          className="app-memory-progress"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(fraction * 100)}
        >
          <div
            className="app-memory-progress-fill"
            style={{
              ["--upload-progress" as string]: `${Math.round(fraction * 100)}%`,
            }}
          />
        </div>
      )}
      {error && <p className="app-files-note app-files-note-error">{error}</p>}
      {notice && <p className="app-files-note">{notice}</p>}
      {files === null ? (
        <p className="app-files-note">Loading files…</p>
      ) : files.length === 0 ? (
        <p className="app-files-note">No files in memory yet</p>
      ) : (
        <div className="app-files-grid">
          {files.map((file) => (
            <div key={file.path} className="app-file-card">
              <div className="app-file-card-open" title={file.path}>
                <span className="app-file-card-icon">
                  <FileIcon className="size-4" />
                </span>
                <span className="app-file-card-name">{file.name}</span>
                <span className="app-file-card-meta">
                  {formatSize(file.size)} · {formatEdited(file.modified)}
                </span>
              </div>
              <button
                type="button"
                className="app-file-card-menu-trigger"
                onClick={() => setDeleteTarget(file)}
                aria-label={`Delete ${file.name}`}
              >
                <Trash2Icon className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeDelete();
        }}
      >
        <DialogContent className="app-file-dialog">
          <DialogHeader>
            <DialogTitle className="app-file-dialog-title">
              Delete {deleteTarget?.name}?
            </DialogTitle>
            <DialogDescription>
              This removes the file from memory and cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError && (
            <p className="app-files-note app-files-note-error">{deleteError}</p>
          )}
          <div className="app-file-dialog-actions">
            <button
              type="button"
              className="app-dialog-btn"
              onClick={closeDelete}
            >
              Cancel
            </button>
            <button
              type="button"
              className="app-dialog-btn app-dialog-btn-danger"
              disabled={deleteBusy}
              onClick={() => void submitDelete()}
            >
              {deleteBusy ? "Deleting…" : "Delete"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
