"use client";

import { useRef, useState } from "react";
import { Loader2Icon, PlusIcon } from "lucide-react";
import { ACCEPT, uploadToMemory } from "@/lib/rag-upload";

type Phase = "idle" | "uploading" | "done" | "error";
type Progress = { phase: Phase; fraction: number; message?: string };

export function MemoryUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<Progress>({ phase: "idle", fraction: 0 });

  const pickFile = () => inputRef.current?.click();

  const handleChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setState({ phase: "uploading", fraction: 0 });
    try {
      const source = await uploadToMemory(file, (fraction) =>
        setState({ phase: "uploading", fraction }),
      );
      setState({ phase: "done", fraction: 1, message: `Added ${source}` });
    } catch (err) {
      setState({
        phase: "error",
        fraction: 0,
        message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const isUploading = state.phase === "uploading";

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(event) => void handleChange(event)}
      />
      <div className="app-memory">
        <div className="app-memory-label">Memory</div>
        <button
          type="button"
          className="app-memory-button"
          onClick={pickFile}
          disabled={isUploading}
          aria-busy={isUploading}
        >
          {isUploading ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            <PlusIcon className="size-4" />
          )}
          <span>{isUploading ? "Uploading" : "Add to memory"}</span>
        </button>
        {isUploading && (
          <div
            className="app-memory-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(state.fraction * 100)}
          >
            <div
              className="app-memory-progress-fill"
              style={{ width: `${Math.round(state.fraction * 100)}%` }}
            />
          </div>
        )}
        {state.phase === "done" && state.message && (
          <p className="app-memory-note app-memory-note-ok">
            {state.message}
          </p>
        )}
        {state.phase === "error" && state.message && (
          <p className="app-memory-note app-memory-note-error">
            {state.message}
          </p>
        )}
      </div>
    </>
  );
}