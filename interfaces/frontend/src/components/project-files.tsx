"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CopyIcon,
  EllipsisVerticalIcon,
  FileIcon,
  Loader2Icon,
  PencilIcon,
  Trash2Icon,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MarkdownContent } from "@/components/assistant-ui/elements/markdown-content";
import {
  deleteProjectFile,
  listProjectFiles,
  readProjectFile,
  renameProjectFile,
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

function splitName(name: string): { stem: string; extension: string } {
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return { stem: name, extension: "" };
  return { stem: name.slice(0, dot), extension: name.slice(dot) };
}

function joinName(stem: string, extension: string): string {
  if (!extension) return stem;
  if (stem.toLowerCase().endsWith(extension.toLowerCase())) return stem;
  return `${stem}${extension}`;
}

const MARKDOWN_EXTENSIONS = [".md", ".markdown"];

function isMarkdownName(name: string): boolean {
  const { extension } = splitName(name);
  return MARKDOWN_EXTENSIONS.includes(extension.toLowerCase());
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function ProjectFiles() {
  const [files, setFiles] = useState<ProjectFile[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<ProjectFileContent | null>(null);
  const [loadingPath, setLoadingPath] = useState<string | null>(null);

  const [renameTarget, setRenameTarget] = useState<ProjectFile | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renameError, setRenameError] = useState("");
  const [renameBusy, setRenameBusy] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<ProjectFile | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const next = await listProjectFiles();
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

  const openFile = async (file: ProjectFile) => {
    setLoadingPath(file.path);
    try {
      const content = await readProjectFile(file.path);
      setError("");
      setSelected(content);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingPath(null);
    }
  };

  const copyPath = async (file: ProjectFile) => {
    try {
      await navigator.clipboard.writeText(file.full_path);
      setNotice(`Copied ${file.full_path}`);
    } catch {
      setError("Could not copy the file path");
    }
  };

  const startRename = (file: ProjectFile) => {
    setRenameTarget(file);
    setRenameDraft(splitName(file.name).stem);
    setRenameError("");
  };

  const closeRename = () => {
    setRenameTarget(null);
    setRenameError("");
  };

  const submitRename = async () => {
    const target = renameTarget;
    if (!target) return;
    const stem = renameDraft.trim();
    if (!stem) return;
    const name = joinName(stem, splitName(target.name).extension);
    if (name === target.name) {
      closeRename();
      return;
    }
    setRenameBusy(true);
    try {
      await renameProjectFile(target.path, name);
      setNotice(`Renamed to ${name}`);
      closeRename();
      await loadFiles();
    } catch (err) {
      setRenameError(errorMessage(err));
    } finally {
      setRenameBusy(false);
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
      await deleteProjectFile(target.path);
      setNotice(`Deleted ${target.name}`);
      closeDelete();
      await loadFiles();
    } catch (err) {
      setDeleteError(errorMessage(err));
    } finally {
      setDeleteBusy(false);
    }
  };

  const renameExtension = renameTarget
    ? splitName(renameTarget.name).extension
    : "";

  return (
    <div className="app-files">
      <header className="app-files-header">
        <h2 className="app-files-title">Project Files</h2>
      </header>
      {error && <p className="app-files-note app-files-note-error">{error}</p>}
      {notice && <p className="app-files-note">{notice}</p>}
      {files === null ? (
        <p className="app-files-note">Loading files…</p>
      ) : files.length === 0 ? (
        <p className="app-files-note">No files yet</p>
      ) : (
        <div className="app-files-grid">
          {files.map((file) => (
            <div key={file.path} className="app-file-card">
              <button
                type="button"
                className="app-file-card-open"
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
              <DropdownMenu>
                <DropdownMenuTrigger
                  className="app-file-card-menu-trigger"
                  aria-label={`Actions for ${file.name}`}
                >
                  <EllipsisVerticalIcon className="size-3.5" />
                </DropdownMenuTrigger>
                <DropdownMenuContent className="app-file-card-menu">
                  <DropdownMenuItem
                    className="app-file-card-menu-item"
                    onClick={() => startRename(file)}
                  >
                    <PencilIcon className="size-3.5" />
                    <span>Rename</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="app-file-card-menu-item"
                    onClick={() => void copyPath(file)}
                  >
                    <CopyIcon className="size-3.5" />
                    <span>Copy path</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="app-file-card-menu-item app-file-card-menu-item-danger"
                    onClick={() => setDeleteTarget(file)}
                  >
                    <Trash2Icon className="size-3.5" />
                    <span>Delete</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
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
              {selected && isMarkdownName(selected.name) ? (
                <div className="app-file-viewer-markdown">
                  <MarkdownContent text={selected.text} />
                </div>
              ) : (
                <pre className="app-file-viewer-pre">{selected?.text}</pre>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
      <Dialog
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeRename();
        }}
      >
        <DialogContent className="app-file-dialog">
          <DialogHeader>
            <DialogTitle>Rename file</DialogTitle>
            <DialogDescription className="app-file-dialog-path">
              {renameTarget?.path}
            </DialogDescription>
          </DialogHeader>
          <form
            className="app-file-dialog-form"
            onSubmit={(event) => {
              event.preventDefault();
              void submitRename();
            }}
          >
            <div className="app-file-rename-field">
              <input
                autoFocus
                className="app-file-rename-input"
                value={renameDraft}
                onChange={(event) => {
                  setRenameDraft(event.target.value);
                  setRenameError("");
                }}
                aria-label="New file name"
              />
              {renameExtension && (
                <span className="app-file-rename-extension">
                  {renameExtension}
                </span>
              )}
            </div>
            {renameError && (
              <p className="app-files-note app-files-note-error">{renameError}</p>
            )}
            <div className="app-file-dialog-actions">
              <button
                type="button"
                className="app-dialog-btn"
                onClick={closeRename}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="app-dialog-btn app-dialog-btn-primary"
                disabled={renameBusy || !renameDraft.trim()}
              >
                {renameBusy ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
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
            <DialogDescription>This cannot be undone.</DialogDescription>
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
