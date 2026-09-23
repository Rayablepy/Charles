"use client";

import { useState } from "react";
import { ChatRuntimeProvider } from "@/components/chat-runtime";
import { ChatSidebar } from "@/components/chat-sidebar";
import { AppWelcome } from "@/components/app-welcome";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";

export default function ChatPage() {
  const [selectedThreadId, setSelectedThreadId] = useState<
    string | undefined
  >(undefined);

  const handleSelectThread = (threadId: string | undefined) => {
    setSelectedThreadId(threadId);
  };

  return (
    <div className="app">
      <ChatRuntimeProvider
        threadId={selectedThreadId}
        onThreadIdChange={setSelectedThreadId}
      >
        <ChatSidebar
          activeThreadId={selectedThreadId}
          onSelect={handleSelectThread}
        />
        <main className="app-main">
          <header className="app-header">
            <h1 className="app-title">Charles</h1>
          </header>
          <div className="app-thread">
            <Thread
              components={{
                Welcome: AppWelcome,
                ToolFallback: () => null,
                ToolGroup: () => null,
                TaskGroup: () => null,
              }}
            />
          </div>
        </main>
      </ChatRuntimeProvider>
    </div>
  );
}