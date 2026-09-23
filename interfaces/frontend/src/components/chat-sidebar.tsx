"use client";

import { useEffect, useState } from "react";
import { PlusIcon } from "lucide-react";
import { useAuiState } from "@assistant-ui/react";
import { cn } from "@/lib/utils";
import { listChats, type ChatSummary } from "@/lib/langgraph";

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

  useEffect(() => {
    let cancelled = false;
    setLoaded(false);
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
  }, [messagesCount]);

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-header">
        <button
          type="button"
          className="app-new-chat"
          onClick={() => onSelect(undefined)}
        >
          <PlusIcon className="size-4" />
          <span>New chat</span>
        </button>
      </div>
      <nav className="app-chat-list" aria-label="Chats">
        {!loaded ? (
          <p className="app-chat-note">Loading chats…</p>
        ) : chats.length === 0 ? (
          <p className="app-chat-note">No chats yet</p>
        ) : (
          chats.map((chat) => (
            <button
              key={chat.id}
              type="button"
              className={cn(
                "app-chat-item",
                chat.id === activeThreadId && "app-chat-item-active",
              )}
              onClick={() => onSelect(chat.id)}
              aria-current={chat.id === activeThreadId ? "true" : undefined}
            >
              <span className="app-chat-title">{chat.title}</span>
            </button>
          ))
        )}
      </nav>
    </aside>
  );
}