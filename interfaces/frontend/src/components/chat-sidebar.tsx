"use client";

import { useCallback, useEffect, useState } from "react";
import { PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";
import { useAuiState } from "@assistant-ui/react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  listChats,
  deleteChat,
  renameChat,
  type ChatSummary,
} from "@/lib/langgraph";

export function ChatSidebar({
  activeThreadId,
  onSelect,
}: {
  activeThreadId?: string | undefined;
  onSelect: (threadId: string | undefined) => void;
}) {
  const messagesCount = useAuiState((s) => s.thread.messages.length);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [editingId, setEditingId] = useState<string | undefined>(undefined);
  const [draftTitle, setDraftTitle] = useState("");
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<
    string | undefined
  >(undefined);

  const reloadChats = useCallback(() => {
    let cancelled = false;
    listChats()
      .then((next) => {
        if (cancelled) return;
        setChats(next);
        setLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => reloadChats(), [reloadChats, messagesCount]);

  const startRename = (chat: ChatSummary) => {
    setEditingId(chat.id);
    setDraftTitle(chat.title);
  };

  const commitRename = async () => {
    const id = editingId;
    setEditingId(undefined);
    if (!id) return;
    const title = draftTitle.trim();
    if (!title) return;
    await renameChat(id, title);
    reloadChats();
  };

  const performDelete = async () => {
    const id = confirmingDeleteId;
    setConfirmingDeleteId(undefined);
    if (!id) return;
    await deleteChat(id);
    if (id === activeThreadId) onSelect(undefined);
    reloadChats();
  };

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-header">
        <h1 className="app-sidebar-title">Charles</h1>
        <ThemeToggle />
      </div>
      <nav className="app-chat-list" aria-label="Chats">
        <button
          type="button"
          className="app-new-chat"
          onClick={() => onSelect(undefined)}
        >
          <PlusIcon className="size-4" />
          <span>New chat</span>
        </button>
<div className="app-chat-scroll">
          {!loaded ? (
            <p className="app-chat-note">Loading chats…</p>
          ) : chats.length === 0 ? (
            <p className="app-chat-note">No chats yet</p>
          ) : (
            chats.map((chat) => {
              const isActive = chat.id === activeThreadId;
              const isEditing = editingId === chat.id;
              const isConfirmingDelete = confirmingDeleteId === chat.id;
              return (
              <div key={chat.id} className="app-chat-row">
                {isEditing ? (
                  <input
                    autoFocus
                    className="app-chat-input"
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") void commitRename();
                      if (event.key === "Escape") setEditingId(undefined);
                    }}
                    onBlur={() => void commitRename()}
                  />
                ) : isConfirmingDelete ? (
                  <div className="app-chat-confirm">
                    <span className="app-chat-confirm-label">Delete chat?</span>
                    <button
                      type="button"
                      className="app-chat-confirm-btn app-chat-confirm-danger"
                      onClick={() => void performDelete()}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      className="app-chat-confirm-btn"
                      onClick={() => setConfirmingDeleteId(undefined)}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      className={cn(
                        "app-chat-item",
                        isActive && "app-chat-item-active",
                      )}
                      onClick={() => onSelect(chat.id)}
                      aria-current={isActive ? "true" : undefined}
                    >
                      <span className="app-chat-title">{chat.title}</span>
                    </button>
                    <div className="app-chat-actions">
                      <button
                        type="button"
                        className="app-chat-action"
                        onClick={() => startRename(chat)}
                        aria-label={`Rename ${chat.title}`}
                      >
                        <PencilIcon className="size-3.5" />
                      </button>
                      <button
                        type="button"
                        className="app-chat-action app-chat-action-danger"
                        onClick={() => setConfirmingDeleteId(chat.id)}
                        aria-label={`Delete ${chat.title}`}
                      >
                        <Trash2Icon className="size-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
            })
          )}
        </div>
      </nav>
    </aside>
  );
}