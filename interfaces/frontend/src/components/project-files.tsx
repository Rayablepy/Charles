"use client";

import { useEffect, useState } from "react";
import { FileIcon, Loader2Icon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  listProjectFiles,
  readProjectFile,
  type ProjectFile,
  type ProjectFileContent,
} from "@/lib/project-files";

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

export function ProjectFiles() {
  const [files, setFiles] = useState<ProjectFile[] | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<ProjectFileContent | null>(null);
  const [loadingPath, setLoadingPath] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listProjectFiles()
      .then((next) => {
        if (active) setFiles(next);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setFiles([]);
        setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      active = false;
    };
  }, []);

  const openFile = async (file: ProjectFile) => {
    setLoadingPath(file.path);
    try {
      const content = await readProjectFile(file.path);
      setError("");
      setSelected(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingPath(null);
    }
  };

  return (
    <div className="app-files">
      <header className="app-files-header">
        <h2 className="app-files-title">Project Files</h2>
      </header>
      {error && <p className="app-files-note app-files-note-error">{error}</p>}
      {files === null ? (
        <p className="app-files-note">Loading files…</p>
      ) : files.length === 0 ? (
        <p className="app-files-note">No files yet</p>
      ) : (
        <div className="app-files-grid">
          {files.map((file) => (
            <button
              key={file.path}
              type="button"
              className="app-file-card"
              onClick={() => void openFile(file)}
              aria-busy={loadingPath === file.path}
            >
              <span className="app-file-card-icon">
                {loadingPath === file.path ? (
                  <Loader2Icon className="size-4 animate-spin" />
                ) : (
                  <FileIcon className="size-4" />
                )}
              </span>
              <span className="app-file-card-name">{file.name}</span>
              <span className="app-file-card-meta">
                {formatSize(file.size)} · {formatEdited(file.modified)}
              </span>
            </button>
          ))}
        </div>
      )}
      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent className="app-file-viewer">
          <DialogHeader>
            <DialogTitle className="app-file-viewer-title">
              {selected?.name}
            </DialogTitle>
          </DialogHeader>
          <p className="app-file-viewer-path">{selected?.path}</p>
          {selected?.binary ? (
            <p className="app-file-viewer-note">
              Binary file — preview unavailable.
            </p>
          ) : (
            <>
              {selected?.truncated && (
                <p className="app-file-viewer-note">
                  Preview truncated to the first {formatSize(selected.size)}.
                </p>
              )}
              <pre className="app-file-viewer-pre">{selected?.text}</pre>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
